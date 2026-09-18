#!/usr/bin/env python3
"""
ABABABCC over every three-chord group, as one Hookpad paste.

Three distinct chords give C(6,3) = 20 groups, and the shape has three roles,
so each group yields 3! = 6 assignments -- 120 permutations, 8 bars each.
A and B alternate for six bars, then C takes the last two, so the roles are
not interchangeable: which of the three chords lands on C is the whole
question the file is asking.

Groups are ordered by how many songs in the corpus use exactly that palette,
so the ones worth hearing come first.

    python3 perms_ababab_cc.py                 # -> ~/Desktop/perms-ababab-cc.txt
    python3 perms_ababab_cc.py --bpm 92
"""
import argparse, itertools, json, os

SHAPE = 'ABABABCC'
LET = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'A#'}
# A# is bVII: degree 7 carrying a borrowed label. mixolydian is the reading of
# a flat-seven in a major key; the corpus also writes it as 'minor', which
# sounds the same chord.
BORROWED = {7: 'mixolydian'}
HERE = os.path.dirname(os.path.abspath(__file__))


def popularity():
    """songs_exact_palette from chord_sets.json, so the common groups lead"""
    try:
        d = json.load(open(os.path.join(HERE, 'chord_sets.json')))
    except Exception:
        return {}
    out = {}
    for e in d.get('entries', []):
        if e.get('ordered') is False and e.get('n') == 3 and e.get('degrees'):
            out[tuple(e['degrees'])] = e.get('songs_exact_palette', 0)
    return out


def chord(root, beat):
    # field order is Hookpad's own; type and duration are ints, not strings
    return {'root': root, 'beat': beat, 'duration': 4, 'type': 5, 'inversion': 0,
            'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None,
            'alternate': '', 'borrowed': BORROWED.get(root), 'isRest': False,
            'recordingEndBeat': None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bpm', type=int, default=100)
    ap.add_argument('--ends', default='',
                    help='restrict the CC ending to these degrees, e.g. 1,4,5 for C/F/G')
    ap.add_argument('--pool', default='1,2,3,4,5,6',
                    help='degrees available to A and B; add 7 for A#')
    ap.add_argument('--tonic', default='C')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/perms-ababab-cc.txt'))
    a = ap.parse_args()

    pop = popularity()
    pool = [int(x) for x in a.pool.split(',') if x.strip()]

    if a.ends:
        # the ending is chosen, so enumerate (A,B) around each allowed ending
        # rather than permuting a set: A and B may be any two other chords.
        ends = [int(x) for x in a.ends.split(',') if x.strip()]
        triples = [(A, B, C) for C in ends
                   for A in pool if A != C
                   for B in pool if B != C and B != A]
        triples.sort(key=lambda t: (-pop.get(tuple(sorted(t)), 0), t))
    else:
        groups = sorted(itertools.combinations(pool, 3),
                        key=lambda g: (-pop.get(g, 0), g))
        triples = [p for g in groups for p in itertools.permutations(g)]

    chords, sections, beat = [], [], 1
    for perm in triples:
        roles = dict(zip('ABC', perm))
        seq = [roles[s] for s in SHAPE]
        sections.append({'beat': beat,
                         'name': '-'.join(LET[roles[s]] for s in 'ABC')})
        for i, deg in enumerate(seq):
            chords.append(chord(deg, beat + i * 4))
        beat += len(SHAPE) * 4

    song = {'version': 1, 'chords': chords, 'notes': [],
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': a.tonic}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [],
            'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    bars = (beat - 1) // 4
    sets = {tuple(sorted(t)) for t in triples}
    print(f'{len(sections)} permutations over {len(sets)} chord sets')
    print(f'{bars} bars, {len(chords)} chords -> {a.out}')
    print('\nfirst twelve:')
    for s in sections[:12]:
        print(f"   bar {(s['beat']-1)//4 + 1:>4}  {s['name']}")


if __name__ == '__main__':
    main()
