#!/usr/bin/env python3
"""
Six units then a doubled one, built out of two-chord cells.

This is the same rhythm as ABABABCC -- six equal holds and then one of double
length -- written in half-bars, so the whole thing is four measures instead of
eight. What is free is the pattern over the six: ABABAB is only one of them.

Three songs sit in this shape and all three arrange their cells the same way:

    Tom Petty, A Higher Place      (V I)(IV I)(V I)    | IV
    Counting Crows, A Long December (IV I)(V ii)(IV I) | IV
    Dylan, Tangled Up in Blue      (I bVII) x3         | IV

Cell 1 returns as cell 3 in every one -- a return, at cell level -- and every
one lands on IV. So that is the default shape here, and --free drops it.

    python3 cell_perms.py --pool I,ii,IV,V --landing IV
    python3 cell_perms.py --pool I,ii,iii,IV,V,vi --answer I --landing IV
    python3 cell_perms.py --free --pool I,IV,V --landing IV
"""
import argparse, itertools, json, os

DEG = {'I':1, 'ii':2, 'iii':3, 'IV':4, 'V':5, 'vi':6, 'bVII':7}
BORROWED = {7: 'mixolydian'}


def chord(root, beat, dur):
    return {'root': root, 'beat': beat, 'duration': dur, 'type': 5, 'inversion': 0,
            'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': BORROWED.get(root), 'isRest': False, 'recordingEndBeat': None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', default='I,ii,IV,V')
    ap.add_argument('--landing', default='IV')
    ap.add_argument('--answer', default='',
                    help='force both cells to answer to this chord (Petty does: V-I, IV-I)')
    ap.add_argument('--free', action='store_true',
                    help='let cell 3 differ from cell 1 instead of returning')
    ap.add_argument('--bpm', type=int, default=92)
    ap.add_argument('--unit', type=float, default=2, help='beats per cell half (2 = half-bar)')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/cell-perms.txt'))
    a = ap.parse_args()

    pool = [p.strip() for p in a.pool.split(',') if p.strip()]
    for p in pool + [a.landing] + ([a.answer] if a.answer else []):
        if p not in DEG: raise SystemExit(f'unknown degree {p!r}; use {sorted(DEG)}')

    cells = [(x, y) for x in pool for y in pool if x != y]
    if a.answer:
        cells = [c for c in cells if c[1] == a.answer]

    # cell 2 may repeat cell 1: that is the all-identical case, which is the
    # pure ABABAB and the one Tangled Up in Blue uses. Excluding it as a
    # degenerate throws away the shape the whole family is named after.
    if a.free:
        combos = [(c1, c2, c3) for c1 in cells for c2 in cells for c3 in cells]
    else:
        combos = [(c1, c2, c1) for c1 in cells for c2 in cells]

    u = a.unit
    chords, sections, beat = [], [], 1
    for c1, c2, c3 in combos:
        seq = list(c1) + list(c2) + list(c3)
        sections.append({'beat': beat,
                         'name': f"({c1[0]}-{c1[1]})({c2[0]}-{c2[1]})({c3[0]}-{c3[1]})>{a.landing}"})
        for i, d in enumerate(seq):
            chords.append(chord(DEG[d], beat + i * u, u))
        chords.append(chord(DEG[a.landing], beat + 6 * u, u * 2))
        beat += int(8 * u)

    song = {'version': 1, 'chords': chords, 'notes': [],
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [], 'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    print(f'{len(cells)} cells from {a.pool}'
          + (f' answering to {a.answer}' if a.answer else '')
          + f' -> {len(sections)} progressions, {(beat-1)//4} bars')
    print(f'holds {[u]*6 + [u*2]}  (the ABABABCC rhythm, in {u}-beat units)')
    print(f'-> {a.out}\n')
    for s in sections[:8]: print(f"   bar {(s['beat']-1)//4+1:>4}  {s['name']}")


if __name__ == '__main__':
    main()
