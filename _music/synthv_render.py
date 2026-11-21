#!/usr/bin/env python3
"""
Hookpad song -> sung WAV, hands-free: writes the Synthesizer V project
(synthv_song.py), opens it in the app, presses Render -> Bounce to Files, waits
for the WAV. Drag the result from ~/Desktop/synthv_renders/ into GarageBand.

    themap_venv/python synthv_render.py <hookpad.json> --from-bar 18 --bars 16 --name dixieland_verse1
    themap_venv/python synthv_render.py --svp ~/Desktop/synthv_renders/x.svp     # render an edited project

How: Synthesizer V has no command line, and its plugin will not sing for a
Python host (it needs a running event loop AND a host pressing play; pedalboard
and DawDreamer each give one of the two). So this drives the app through the
macOS accessibility API: it finds controls by name, not screen position. The
Render tab is the side-panel button whose tooltip begins "Export the whole
project"; the export is the button named "Bounce to Files". The project's own
renderConfig already points the files at synthv_renders/.

Needs Accessibility permission for Terminal (System Settings -> Privacy &
Security -> Accessibility). Opening a project replaces whatever the app shows,
so save your own work in it first.
"""
import argparse, glob, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthv_song as S

PROC = 'synthv-studio'


def osa(script):
    r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=120)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def window_title():
    try: return osa(f'tell application "System Events" to tell process "{PROC}" to get name of window 1')
    except Exception: return ''


def render(svp, timeout=300):
    name = os.path.splitext(os.path.basename(svp))[0]
    before = {f: os.path.getmtime(f) for f in glob.glob(os.path.join(S.RENDERS, name + '_*.wav'))}
    subprocess.run(['open', '-a', 'Synthesizer V Studio 2 Pro', svp], check=True)
    end = time.time() + 60
    while os.path.basename(svp) not in window_title():
        if time.time() > end: raise RuntimeError(f'the app never showed {svp} (an unsaved-changes dialog?)')
        time.sleep(1)
    time.sleep(2)
    # the tab toggles the panel, so only press it when the panel is not already showing
    if osa(f'tell application "System Events" to tell process "{PROC}" to exists button "Bounce to Files" of window 1') != 'true':
      osa(f'''tell application "System Events" to tell process "{PROC}"
        set hs to help of every button of window 1
        set i to 0
        repeat with h in hs
            set i to i + 1
            if (h as text) contains "Export the whole project" then
                click button i of window 1
                exit repeat
            end if
        end repeat
    end tell''')
      time.sleep(1.5)
    osa(f'tell application "System Events" to tell process "{PROC}" to click button "Bounce to Files" of window 1')
    # the files appear at once (0 bytes) and fill when the render is done; wait for a stable size
    end, last = time.time() + timeout, None
    while time.time() < end:
        fs = [f for f in glob.glob(os.path.join(S.RENDERS, name + '_*.wav')) if os.path.getmtime(f) > before.get(f, 0)]
        sizes = tuple(sorted((f, os.path.getsize(f)) for f in fs))
        if fs and all(s > 0 for _, s in sizes) and sizes == last:
            break
        last = sizes; time.sleep(2)
    else:
        raise RuntimeError('render did not finish in time')
    voice = [f for f in fs if not f.endswith('_MixDown.wav')]
    mix = [f for f in fs if f.endswith('_MixDown.wav')]
    if len(voice) == 1 and mix: os.remove(mix[0])            # one track: the mixdown is the same file
    return voice or mix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song', nargs='?'); ap.add_argument('--svp')
    ap.add_argument('--voice', default='Liam'); ap.add_argument('--from-bar', type=int, default=1)
    ap.add_argument('--bars', type=int); ap.add_argument('--name')
    a = ap.parse_args()
    if a.svp:
        svp = os.path.abspath(os.path.expanduser(a.svp))
    else:
        d = json.load(open(a.song))
        name = a.name or os.path.splitext(os.path.basename(a.song))[0].replace(' ', '_')
        b0 = (a.from_bar - 1) * 4 + 1
        p, nn, nt = S.build(d, name, a.voice, b0, b0 + a.bars * 4 if a.bars else None)
        svp = os.path.join(S.RENDERS, name + '.svp')
        open(svp, 'w').write(json.dumps(p))
        print(f'{svp}: {len(p["tracks"][0]["mainGroup"]["notes"])} notes'
              + ('' if nn == nt else f'  (lyric tokens {nt} vs notes {nn})'))
    t = time.time()
    for f in render(svp):
        print(f'{f}  ({time.time() - t:.0f}s)')


if __name__ == '__main__':
    main()
