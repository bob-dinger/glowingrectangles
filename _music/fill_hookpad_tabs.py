"""Fill open Hookpad tabs in a running Brave window. Tabs are filled in
the order they appear in Brave's tab bar (left to right).

Setup (do this ONCE per session):

    bash _music/launch_hookpad_debug.sh          # default 25 tabs
    bash _music/launch_hookpad_debug.sh 10       # custom N

That launches an ISOLATED Brave (separate user-data-dir at ~/BraveHookpadDebug)
with CDP on port 9222 and N Hookpad tabs. Doesn't disturb your regular Brave.
First time you launch it, sign into Hookpad in any tab — auth persists.

Then run the filler:

    python _music/fill_hookpad_tabs.py "song one" "song two" ...

How it works:
  1. Connect via CDP to the debug Brave.
  2. Stamp every Playwright page with a unique title-marker.
  3. For each tab index in Brave's tab bar order: AppleScript-activate that tab,
     read its current (stamped) title, map back to Playwright page, drive it
     (dismiss startup modal -> File menu -> Open -> type song -> Enter).
"""
import sys, time, subprocess
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"


def applescript(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def active_tab_index():
    return int(applescript('tell application "Brave Browser" to tell front window to active tab index'))


def set_active_tab(idx):
    applescript(f'tell application "Brave Browser" to tell front window to set active tab index to {idx}')


def active_tab_title():
    return applescript('tell application "Brave Browser" to tell front window to tell active tab to title')


def brave_tab_count():
    return int(applescript('tell application "Brave Browser" to tell front window to count of tabs'))


def build_mapping(pages):
    """Map Brave tab-bar index (1-based) -> Playwright page. Done via title-stamping."""
    # Stamp each Playwright page with a unique marker
    timestamp = int(time.time())
    for i, pg in enumerate(pages):
        try:
            pg.evaluate(f"document.title = 'MARK_{i}_{timestamp}'")
        except Exception:
            pass
    time.sleep(0.3)
    # Walk Brave's tab bar in order; for each tab, read its title and parse the marker.
    n_tabs = brave_tab_count()
    mapping = {}
    for tab_idx in range(1, n_tabs + 1):
        set_active_tab(tab_idx)
        time.sleep(0.05)
        title = active_tab_title()
        if title.startswith("MARK_"):
            try:
                page_idx = int(title.split("_")[1])
                mapping[tab_idx] = pages[page_idx]
            except Exception:
                pass
    return mapping


def fill_one(page, song):
    """Drive File -> Open -> paste song -> click Open button on the given Playwright page."""
    t0 = time.time()
    try:
        # Dismiss any startup modal by clicking an empty area
        page.mouse.click(20, 200)
        page.wait_for_timeout(120)
        page.locator("button.button-menu[title*='open']").first.click(timeout=5000)
        page.wait_for_timeout(200)
        page.locator(".popper-file >> :text-is('Open')").first.click(timeout=5000)
        page.wait_for_timeout(900)   # let Open modal appear + auto-focus its input
        # Clear any stale text, then paste so Hookpad's DB query fires once
        page.keyboard.press("Meta+A")
        page.wait_for_timeout(40)
        subprocess.run(["pbcopy"], input=song.encode("utf-8"), check=False)
        page.keyboard.press("Meta+V")
        page.wait_for_timeout(700)   # one DB query needs to settle
        # Click the Open submit button (more reliable than pressing Enter)
        page.locator("[data-type='new-and-open-modal'] button:has-text('Open')").first.click(timeout=4000)
        page.wait_for_timeout(900)
        return "ok", time.time() - t0
    except Exception as e:
        return f"err: {type(e).__name__}: {e}", time.time() - t0


def main():
    songs = sys.argv[1:]
    if not songs:
        print("usage: fill_hookpad_tabs.py <song1> <song2> ...")
        sys.exit(1)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"can't connect to Brave at {CDP_URL}: {e}")
            print("relaunch with `bash _music/launch_hookpad_debug.sh`")
            sys.exit(2)

        hookpad_pages = [pg for ctx in browser.contexts for pg in ctx.pages
                         if "hookpad.hooktheory.com" in pg.url]
        print(f"connected. {len(hookpad_pages)} hookpad pages, {len(songs)} songs.")

        if not hookpad_pages:
            print("no Hookpad tabs"); sys.exit(3)

        print("building tab-bar -> Playwright-page mapping...")
        mapping = build_mapping(hookpad_pages)
        if len(mapping) < min(len(songs), len(hookpad_pages)):
            print(f"only mapped {len(mapping)} tabs; some may not respond")
        print(f"  mapped {len(mapping)} tabs.")

        n = min(len(mapping), len(songs))
        t_overall = time.time()
        for i in range(n):
            tab_idx = i + 1
            if tab_idx not in mapping:
                print(f"  [{tab_idx}/{n}] skipped (no mapping)")
                continue
            set_active_tab(tab_idx)
            time.sleep(0.15)
            page = mapping[tab_idx]
            status, dt = fill_one(page, songs[i])
            print(f"  [{tab_idx}/{n}] {songs[i]:<40}  {status}  ({dt:.1f}s)")
        total = time.time() - t_overall
        print(f"\nfilled {n} tabs in {total:.1f}s  (avg {total/max(n,1):.1f}s/tab)")
        browser.close()


if __name__ == "__main__":
    main()
