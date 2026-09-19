#!/usr/bin/env python3
"""
Find sections by their CHANGE RHYTHM -- how long each chord is held.

Two things this does that comparing raw chord events does not, and both were
learned the hard way:

MERGE same-chord runs first. A re-strike of the same chord is Layer 2 texture,
not a change. Tangled Up in Blue is written as eight two-beat events, the last
two both IV; as changes that is 2,2,2,2,2,2,4 -- six units then a doubled one.
Compared event-by-event it looks like a different shape entirely.

NORMALISE to ratios. The same progression at half speed is the same
progression. Dylan sits in the corpus three times at 87 and 174 bpm, written in
half-bars and whole bars, and absolute durations match none of them to each
other. 1,1,1,1,1,1,2 catches all three.

    python3 find_holds.py 1,1,1,1,1,1,2
    python3 find_holds.py 2,2,2,2,2,2,4 --exact
    python3 find_holds.py 1,1,2 --min 3
"""
import argparse, collections, glob, json, os
from fractions import Fraction

RN = {1:'I', 2:'ii', 3:'iii', 4:'IV', 5:'V', 6:'vi', 7:'bVII'}


def label(c):
    s = RN.get(c['root'], f"?{c['root']}")
    if c.get('applied'):   s = f"{RN.get(c['root'])}/{RN.get(c['applied'])}"
    if c.get('borrowed'):  s += '*'
    if c.get('suspensions'): s += 's' + ''.join(map(str, c['suspensions']))
    if c.get('adds'):      s += 'a' + ''.join(map(str, c['adds']))
    return s


def merged(chords):
    """-> [(label, start, held)] with consecutive identical chords joined.

    Held time runs to the NEXT change, not the written duration, so a chord
    struck repeatedly reads as one long hold."""
    out = []
    for c in sorted(chords, key=lambda x: x['beat']):
        lb = label(c)
        if out and out[-1][0] == lb and abs(out[-1][1] + out[-1][2] - c['beat']) < 1e-6:
            out[-1][2] += c['duration']
        else:
            out.append([lb, c['beat'], c['duration']])
    return [tuple(x) for x in out]


def ratios(holds):
    g = None
    fr = [Fraction(h).limit_denominator(16) for h in holds]
    for f in fr:
        g = f if g is None else Fraction(__import__('math').gcd(
            (g * 48).numerator, (f * 48).numerator), 48)
    if not g or g == 0: return None
    return tuple(int(f / g) for f in fr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pattern', help='hold pattern, e.g. 1,1,1,1,1,1,2')
    ap.add_argument('--exact', action='store_true', help='match absolute beats, not ratios')
    ap.add_argument('--min', type=int, default=1)
    ap.add_argument('--corpus', default=os.path.expanduser('~/Desktop/music/hookpad_songs_full'))
    a = ap.parse_args()
    want = [float(x) for x in a.pattern.split(',')]
    want_key = tuple(want) if a.exact else ratios(want)
    n = len(want)

    found = collections.defaultdict(set)
    for f in glob.glob(os.path.join(a.corpus, '*.json')):
        name = os.path.basename(f)[:-5]
        if name.startswith(('_', 'mine', 'perms', 'music_')): continue
        try: d = json.load(open(f))
        except Exception: continue
        ch = d.get('chords') or []
        if len(ch) < n: continue
        runs = merged(ch)
        secs = sorted(d.get('sections') or [], key=lambda s: s['beat']) or [{'beat':1,'name':'(whole)'}]
        bpm = (d.get('tempos') or [{}])[0].get('bpm')
        for i in range(len(runs) - n + 1):
            w = runs[i:i+n]
            holds = [h for _, _, h in w]
            key = tuple(holds) if a.exact else ratios(holds)
            if key != want_key: continue
            sec = max((s for s in secs if s['beat'] <= w[0][1]),
                      key=lambda s: s['beat'], default={'name': '?'})
            found[' '.join(lb for lb, _, _ in w)].add(
                (name.split('-hooktab')[0], sec['name'], bpm, holds[0]))

    mode = 'absolute' if a.exact else f'ratio {"-".join(map(str, want_key))}'
    print(f'holds {a.pattern} ({mode}) -- {len(found)} distinct progressions\n')
    for prog, who in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        songs = sorted({s for s, _, _, _ in who})
        if len(songs) < a.min: continue
        units = sorted({u for _, _, _, u in who})
        tempos = sorted({b for _, _, b, _ in who if b})
        extra = f'   [unit {"/".join(f"{u:g}" for u in units)} beats' + \
                (f', {"/".join(map(str, tempos))} bpm]' if tempos else ']')
        print(f'  {prog:34}  {", ".join(songs)[:52]}{extra}')


if __name__ == '__main__':
    main()
