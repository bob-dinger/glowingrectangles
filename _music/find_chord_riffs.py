"""Which songs actually have chord-riff rhythm, rather than one chord per measure?

Most of the library changes chords on the bar or the half-bar. A chord RIFF is
the exception: changes pushed onto an eighth — a 3.5-beat chord, a half-beat
flick, a 4.5-beat hold spilling over the barline. Those are the songs worth
feeding to build_perm_pastes.py.

Consecutive slots on the same chord are merged first (that is strum texture, not
a change), then each CHANGE is bucketed by where it lands in the bar:

    push     onset on an eighth (x.5) — the riff signature
    quarter  onset on an odd quarter (beat 2 or 4) — rhythm, but squarer
    strike   re-strikes of the same chord — the strum layer

Ranked by push count. The user's own workbenches (mine_*, perms_*, music_*) and
the chord-riffs workbench are excluded.

    themap_venv/python find_chord_riffs.py             # ranked list
    themap_venv/python find_chord_riffs.py --min 8     # only songs with 8+ pushes
    themap_venv/python find_chord_riffs.py --song malibu   # show one song's changes
"""
import json, os, glob, argparse
from fractions import Fraction as F

CORPUS = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
SKIP   = ('mine_', 'perms_', 'music_', 'chord-riffs', '_')

def ident(c):
    return (c.get('root'), c.get('applied') or 0, c.get('type'),
            c.get('borrowed') or '', tuple(c.get('adds') or []))

def changes(song):
    """Merged chord changes: [(onset_beats, total_dur, ident, n_strikes)]."""
    out = []
    for c in song.get('chords') or []:
        if c.get('isRest'): continue
        b, d = c.get('beat'), c.get('duration')
        if b is None or d is None: continue
        on, dur = F(str(b)) - 1, F(str(d))
        if out and out[-1][2] == ident(c) and out[-1][0] + out[-1][1] == on:
            o, t, i, n = out[-1]; out[-1] = (o, t + dur, i, n + 1)
        else:
            out.append((on, dur, ident(c), 1))
    return out

def profile(song):
    bar = F((song.get('meters') or [{}])[0].get('numBeats') or 4)
    push = quarter = strike = 0
    durs = set()
    for on, dur, _, n in changes(song):
        inbar = on % bar
        if inbar % 1:                      # lands on an eighth
            push += 1; durs.add(float(dur))
        elif inbar % (bar / 2):            # odd quarter
            quarter += 1
        strike += n - 1
    return push, quarter, strike, len(changes(song)), sorted(durs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min', type=int, default=4)
    ap.add_argument('--song', help="show the merged changes of one song (substring match)")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(CORPUS, '*.json')))
    if a.song:
        for f in files:
            name = os.path.basename(f)[:-5]
            if a.song.lower() not in name.lower(): continue
            song = json.load(open(f))
            print(f"\n{name}")
            for on, dur, i, n in changes(song):
                mark = '  <-- push' if (on % 4) % 1 else ''
                print(f"   beat {float(on)+1:7g}  dur {float(dur):5g}  root {i[0]}"
                      f"  strikes {n}{mark}")
        return

    rows = []
    for f in files:
        name = os.path.basename(f)[:-5]
        if name.lower().startswith(SKIP): continue
        try: song = json.load(open(f))
        except Exception: continue
        push, quarter, strike, tot, durs = profile(song)
        if push >= a.min:
            rows.append((push, quarter, strike, tot, name, durs))
    rows.sort(key=lambda r: (-r[0], r[4]))
    print(f"{'push':>5}{'qtr':>5}{'strike':>7}{'chgs':>6}  {'song':46} pushed-chord lengths")
    for push, quarter, strike, tot, name, durs in rows:
        ds = ' '.join(f"{d:g}" for d in durs[:8]) + (' …' if len(durs) > 8 else '')
        print(f"{push:>5}{quarter:>5}{strike:>7}{tot:>6}  {name[:46]:46} {ds}")
    print(f"\n{len(rows)} songs with >= {a.min} pushed chord changes")

if __name__ == '__main__':
    main()
