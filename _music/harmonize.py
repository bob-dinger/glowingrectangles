#!/usr/bin/env python3
"""
Generate a harmony voice from a Hookpad song's melody.

Produces a paste-JSON blob you drop into an empty voice slot in Hookpad,
then fix by ear. The point is to start from something close rather than
from nothing.

    python3 harmonize.py --song "beatles_Blackbird"
    python3 harmonize.py --song "fleetwood mac_landslide" --interval 3below
    python3 harmonize.py --song "beatles_Blackbird" --no-snap    # strict parallel

Intervals: 3above (default), 3below, 6below, 6above, octave
--snap (default on) moves a note to a chord tone when the plain interval
lands outside the chord. --no-snap gives strict parallel motion, which is
the country/brother-duet sound.
"""
import json, os, glob, argparse, sys

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
OUT = os.path.expanduser('~/Desktop/harmony_pastes')

# diatonic step offsets
STEPS = {'3above': 2, '3below': -2, '6above': 5, '6below': -5,
         'octave': 7, 'unison': 0}


def num(x, d=0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def load(name):
    p = os.path.join(D, name if name.endswith('.json') else name + '.json')
    if not os.path.exists(p):
        hits = [f for f in glob.glob(D + '/*.json')
                if name.lower() in os.path.basename(f).lower()]
        if not hits:
            sys.exit(f"no song matching {name!r}")
        if len(hits) > 1:
            print("matches:", *(os.path.basename(h) for h in hits[:10]), sep="\n  ")
            sys.exit("be more specific")
        p = hits[0]
    s = json.load(open(p))
    return (s.get('song') if isinstance(s.get('song'), dict) else s), os.path.basename(p)[:-5]


def abs_step(n):
    """scale degree + octave collapsed to one number, 1-indexed degrees"""
    return int(num(n.get('sd'), 1)) - 1 + 7 * int(num(n.get('octave')))


def to_note(step, src):
    """inverse of abs_step, preserving rhythm from the source note"""
    return {'sd': str(step % 7 + 1), 'octave': step // 7,
            'beat': num(src.get('beat')), 'duration': num(src.get('duration')),
            'isRest': False, 'recordingEndBeat': None}


def chord_at(chords, beat):
    cur = None
    for c in chords:
        if c.get('isRest'):
            continue
        b = num(c.get('beat'))
        if b <= beat + 1e-9:
            cur = c
        else:
            break
    return cur


def chord_tones(c):
    """triad degrees as 0-indexed scale steps; 7ths included when present"""
    if not c:
        return None
    r = int(num(c.get('root'), 1)) - 1
    tones = {r % 7, (r + 2) % 7, (r + 4) % 7}
    if str(c.get('type')) in ('7', '9', '11', '13'):
        tones.add((r + 6) % 7)
    for a in (c.get('adds') or []):
        tones.add((r + int(num(a)) - 1) % 7)
    return tones


def harmonize(song, interval='3above', snap=True, snap_min=1.0):
    """snap_min: only pull notes at least this long onto a chord tone.
    Shorter notes are passing tones and stay strictly parallel — snapping
    them turns half the thirds into fourths and loses the sound."""
    off = STEPS[interval]
    chords = song.get('chords') or []
    out = []
    for n in song.get('notes') or []:
        if n.get('isRest'):
            continue
        base = abs_step(n)
        cand = base + off
        if snap and chords and num(n.get('duration')) >= snap_min:
            tones = chord_tones(chord_at(chords, num(n.get('beat'))))
            if tones and cand % 7 not in tones:
                # nearest chord tone in the same direction, within a step either way
                for delta in (1, -1, 2, -2):
                    if (cand + delta) % 7 in tones:
                        cand += delta
                        break
        out.append(to_note(cand, n))
    return out


def paste_blob(notes):
    # version:1 skips Hookpad's fp check (see hookpad_paste_format_exact)
    return {'version': 1, 'notes': notes, 'chords': [], 'audioTracks': []}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--song', required=True)
    ap.add_argument('--interval', default='3above', choices=sorted(STEPS))
    ap.add_argument('--no-snap', dest='snap', action='store_false')
    ap.add_argument('--snap-min', type=float, default=1.0,
                    help='only snap notes at least this many beats long')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    song, name = load(a.song)
    mel = [n for n in (song.get('notes') or []) if not n.get('isRest')]
    if not mel:
        sys.exit(f"{name} has no melody notes")
    harm = harmonize(song, a.interval, a.snap, a.snap_min)

    os.makedirs(a.out, exist_ok=True)
    # .txt because anything meant for pasting has to be .txt
    path = os.path.join(a.out, f"{name}__{a.interval}{'' if a.snap else '_strict'}.txt")
    open(path, 'w').write(json.dumps(paste_blob(harm), separators=(',', ':')))

    moved = sum(1 for m, h in zip(mel, harm)
                if abs_step(h) - abs_step(m) != STEPS[a.interval])
    print(f"{name}")
    print(f"  {len(mel)} melody notes -> {len(harm)} harmony notes")
    print(f"  interval: {a.interval}{'' if a.snap else ' (strict parallel)'}")
    if a.snap:
        print(f"  {moved} notes ({moved/len(harm)*100:.0f}%) nudged to a chord tone")
    print(f"\n  {path}")
    print("\n  In Hookpad: switch to an empty voice, select all, paste.")
