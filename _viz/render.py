#!/usr/bin/env python3
"""
Render a GSAP timeline to MP4 / GIF by seeking it frame by frame.

The point: a GSAP timeline is *seekable*. We drive it to an exact time,
screenshot, advance, repeat. Output is frame-accurate and deterministic —
identical every run, regardless of how fast the machine is. D3 transitions
run on wall-clock time and can't be positioned, which is why this approach
only works if the animation layer is GSAP.

    python3 render.py texas-demo.html --gif --mp4
    python3 render.py page.html --fps 30 --width 1200 --scale 2
    python3 render.py page.html --selector "#stage" --out ~/Desktop/out

CONTRACT — the page must expose:
    window.TL           a gsap.timeline({paused: true})
    window.RENDER_READY  set to true once data is loaded and drawn

Everything else (size, duration, easing) is read off the page itself.
"""
import argparse, contextlib, functools, http.server, os, shutil
import socketserver, subprocess, sys, tempfile, threading

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright missing.  pip install playwright && playwright install chromium")


def ff(*args):
    """Run ffmpeg quietly; raise with real output if it fails."""
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "ffmpeg failed")


@contextlib.contextmanager
def serve(directory):
    """Serve `directory` on a free localhost port.

    We can't use file:// — fetch() is blocked there, so any page that loads
    its data (every interesting one) would fail. Serving over http also means
    the page behaves exactly as it will on the deployed site.
    """
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=directory)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        httpd.log_message = lambda *a: None
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield httpd.server_address[1]
        finally:
            httpd.shutdown()


def capture(html, frames_dir, fps, width, height, scale, selector, timeout):
    path = os.path.abspath(html)
    root, name = os.path.dirname(path), os.path.basename(path)
    with serve(root) as port, sync_playwright() as pw:
        url = f"http://127.0.0.1:{port}/{name}"
        # keep the renderer awake — headless pages get throttled otherwise
        browser = pw.chromium.launch(args=[
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
        ])
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=scale)
        page.goto(url)

        # wait for the page to say it has drawn
        # polling=100 (ms), NOT the default "raf" — rAF is throttled to a halt
        # in a headless page, so raf-polling here never resolves.
        page.wait_for_function("window.TL && window.RENDER_READY === true",
                               timeout=timeout, polling=100)
        page.evaluate("window.TL.pause(0)")

        duration = page.evaluate("window.TL.duration()")
        if not duration or duration <= 0:
            browser.close()
            sys.exit("timeline duration is 0 — nothing to render")

        # Resolve the crop box ONCE, then use page.screenshot(clip=...).
        # Locator.screenshot() runs actionability checks — including a
        # "is the element stable?" test driven by requestAnimationFrame —
        # which never resolves in a throttled headless page.
        clip = None
        if selector:
            box = page.locator(selector).bounding_box()
            if not box:
                browser.close()
                sys.exit(f"selector {selector!r} matched nothing")
            clip = {k: box[k] for k in ("x", "y", "width", "height")}

        total = max(1, round(duration * fps))
        print(f"  timeline {duration:.2f}s · {fps} fps · {total} frames")

        for i in range(total + 1):
            t = min(i / fps, duration)
            # gsap.seek() writes the tweened values to the DOM synchronously,
            # so there is nothing to wait for. Do NOT wait on rAF here: a
            # headless page is never "visible", rAF gets throttled, and the
            # capture hangs on frame 0 forever.
            page.evaluate("t => { window.TL.seek(t); }", t)
            page.screenshot(path=os.path.join(frames_dir, f"f{i:05d}.png"),
                            clip=clip, animations="disabled")
            if i % 20 == 0 or i == total:
                print(f"\r  frame {i}/{total}", end="", flush=True)
        print()
        browser.close()
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1000)
    ap.add_argument("--height", type=int, default=750)
    ap.add_argument("--scale", type=int, default=2, help="device pixel ratio")
    ap.add_argument("--selector", default=None,
                    help="capture just this element instead of the viewport")
    ap.add_argument("--out", default=None, help="output basename (no extension)")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--mp4", action="store_true")
    ap.add_argument("--gif-width", type=int, default=800)
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--timeout", type=int, default=30000)
    a = ap.parse_args()

    if not (a.gif or a.mp4):
        a.mp4 = True  # sensible default

    base = a.out or os.path.splitext(os.path.abspath(a.html))[0]
    frames = tempfile.mkdtemp(prefix="frames_")

    try:
        print(f"→ {os.path.basename(a.html)}")
        capture(a.html, frames, a.fps, a.width, a.height,
                a.scale, a.selector, a.timeout)
        pat = os.path.join(frames, "f%05d.png")

        if a.mp4:
            # yuv420p + even dimensions = plays everywhere
            ff("-framerate", str(a.fps), "-i", pat,
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
               "-movflags", "+faststart", base + ".mp4")
            print(f"  ✓ {base}.mp4  ({os.path.getsize(base+'.mp4')//1024} KB)")

        if a.gif:
            # two-pass palette — the difference between a good gif and a bad one
            pal = os.path.join(frames, "palette.png")
            vf = f"fps={a.fps},scale={a.gif_width}:-1:flags=lanczos"
            ff("-i", pat, "-vf", vf + ",palettegen=stats_mode=diff", pal)
            ff("-framerate", str(a.fps), "-i", pat, "-i", pal,
               "-lavfi", vf + "[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
               "-loop", "0", base + ".gif")
            print(f"  ✓ {base}.gif  ({os.path.getsize(base+'.gif')//1024} KB)")

        if a.keep_frames:
            dest = base + "_frames"
            shutil.rmtree(dest, ignore_errors=True)
            shutil.move(frames, dest)
            print(f"  ✓ {dest}/")
            frames = None
    finally:
        if frames:
            shutil.rmtree(frames, ignore_errors=True)


if __name__ == "__main__":
    main()
