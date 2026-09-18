#!/usr/bin/env python3
"""
Every ordering of a handful of chords, arranged as pushed pairs. No rhythm.

The unit is two bars: the first chord holds for three and a half beats, the
second arrives on the & of 4 and rings through the second bar. That early
arrival is the push -- the same shape Simple Kind of Life uses, where the
chord genuinely changes on the push rather than merely being re-struck.

Four chords make two pushed pairs, so a section is four bars and there are
4! = 24 orderings.

    python3 push_perms.py --chords Asus2,A,D,Dsus4 --key A
    python3 push_perms.py --chords Dmadd9,Dm,Cadd9,C --key C
"""
import argparse, itertools, json, os

MAJOR = ['A','A#','B','C','C#','D','D#','E','F','F#','G','G#']
STEPS = [0, 2, 4, 5, 7, 9, 11]           # degrees 1..7 of a major scale


def degree_in(key, note):
    """note name -> scale degree in key, or None if it is not diatonic"""
    ki, ni = MAJOR.index(key), MAJOR.index(note)
    semis = (ni - ki) % 12
    return STEPS.index(semis) + 1 if semis in STEPS else None


def parse(tok, key):
    """'Asus2' -> (degree, suspensions, adds).  Also add9, sus4, plain."""
    t = tok.strip()
    sus, adds = [], []
    for suffix, bucket, val in (('sus2', sus, 2), ('sus4', sus, 4),
                                ('add9', adds, 9), ('add2', adds, 2)):
        if t.endswith(suffix):
            bucket.append(val); t = t[:-len(suffix)]
    t = t.replace('b', '#') if False else t
    m = t.rstrip('m')                      # Dm -> D; quality follows the degree
    if m not in MAJOR:
        raise SystemExit(f'unknown chord {tok!r}; use note names like A, Dm, Asus2')
    d = degree_in(key, m)
    if d is None:
        raise SystemExit(f'{tok!r} is not diatonic in {key} major')
    return d, sus, adds


def chord(root, beat, dur, sus, adds):
    return {'root': root, 'beat': beat, 'duration': dur, 'type': 5, 'inversion': 0,
            'applied': 0, 'adds': list(adds), 'omits': [], 'alterations': [],
            'suspensions': list(sus), 'substitutions': [], 'pedal': None,
            'alternate': '', 'borrowed': None, 'isRest': False,
            'recordingEndBeat': None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chords', default='Asus2,A,D,Dsus4')
    ap.add_argument('--key', default='A')
    ap.add_argument('--bpm', type=int, default=96)
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/push-combos.txt'))
    a = ap.parse_args()

    toks = [c.strip() for c in a.chords.split(',') if c.strip()]
    spec = {t: parse(t, a.key) for t in toks}

    chords, sections, beat = [], [], 1
    for order in itertools.permutations(toks):
        sections.append({'beat': beat,
                         'name': ' '.join(f'{order[i]}>{order[i+1]}'
                                          for i in range(0, len(order), 2))})
        for pair in range(len(order) // 2):
            first, second = order[pair*2], order[pair*2+1]
            b0 = beat + pair * 8
            d1, s1, a1 = spec[first]
            d2, s2, a2 = spec[second]
            # first chord holds to the & of 4; second arrives there and rings
            # through the whole of the next bar -- that is the push
            chords.append(chord(d1, b0, 3.5, s1, a1))
            chords.append(chord(d2, b0 + 3.5, 4.5, s2, a2))
        beat += len(order) * 4

    song = {'version': 1, 'chords': chords, 'notes': [],
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': a.key}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [], 'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    print(f'{len(sections)} orderings of {", ".join(toks)} in {a.key} major')
    print(f'{(beat-1)//4} bars, {len(chords)} chords -> {a.out}\n')
    for s in sections[:8]:
        print(f"   bar {(s['beat']-1)//4+1:>3}  {s['name']}")


if __name__ == '__main__':
    main()
