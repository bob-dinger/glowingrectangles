#!/usr/bin/env python3
"""
Pick a progression, permute the strum over it, get a Hookpad paste.

The chords stay fixed and in order; what varies is which strum each chord gets.
With two chords and six strums that is 36 assignments, six of them uniform (the
same strum on both) and thirty role-based -- which is the line between strumming
a progression and playing a riff.

    python3 strum_perms.py --chords Dm,C
    python3 strum_perms.py --chords Am,F,C,G --bars 1 --strums folk-DDU-UDU,wonderwall,eighths
    python3 strum_perms.py --chords Dm,C --no-push

THE PUSH is the whole reason Simple Kind of Life sounds the way it does. No Doubt
hold Dm for two bars and C for two, with the SAME strum on both -- the second bar
of each pair differs only because the &4 of the first bar is held across the
downbeat, so beat 1 never gets struck. With --push (the default) every chord's
last eighth is lengthened to cover the next downbeat, and that downbeat's strike
is dropped. Turn it off and the same strums sound square.
"""
import argparse, itertools, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DEG = {'C':1, 'Dm':2, 'Em':3, 'F':4, 'G':5, 'Am':6, 'A#':7}
BORROWED = {7: 'mixolydian'}
DEFAULT = ['simple-kind-of-life', 'folk-DDU-UDU', 'wonderwall',
           'driving-DU-UDU-U', 'quarters', 'eighths']


def load_library():
    d = json.load(open(os.path.join(HERE, 'strum_library.json')))
    return d['patterns']


def onsets(cells):
    """'D. D. DU DU' -> eighth-slot indices that are struck.

    A cell's LENGTH is its subdivision, so 'D.' is two eighths and '.' is a
    whole silent beat. Only eighth cells are emitted here; a 16th or triplet
    cell would need a finer grid than one byte can hold."""
    out, slot = [], 0
    for cell in cells.split():
        n = len(cell)
        for i, chx in enumerate(cell):
            if chx in 'DUx':
                out.append(slot + (i * 2 // n if n > 1 else 0))
        slot += 2
    return sorted(set(out))


def chord(root, beat, dur):
    return {'root': root, 'beat': beat, 'duration': dur, 'type': 5, 'inversion': 0,
            'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': BORROWED.get(root), 'isRest': False, 'recordingEndBeat': None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chords', default='Dm,C', help='in order, e.g. Am,F,C,G')
    ap.add_argument('--bars', type=int, default=2, help='bars each chord is held')
    ap.add_argument('--strums', default=','.join(DEFAULT))
    ap.add_argument('--no-push', dest='push', action='store_false')
    ap.add_argument('--push-changes', action='store_true',
                    help='also push across a chord change (No Doubt do not)')
    ap.add_argument('--bpm', type=int, default=104)
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/strum-perms.txt'))
    a = ap.parse_args()

    lib = load_library()
    names = [s.strip() for s in a.strums.split(',') if s.strip()]
    missing = [n for n in names if n not in lib]
    if missing:
        raise SystemExit(f'not in strum_library.json: {missing}\navailable: {sorted(lib)}')
    prog = [c.strip() for c in a.chords.split(',') if c.strip()]
    bad = [c for c in prog if c not in DEG]
    if bad:
        raise SystemExit(f'unknown chord(s): {bad}\nknown: {sorted(DEG)}')

    chords, sections, beat = [], [], 1
    for combo in itertools.product(names, repeat=len(prog)):
        uniform = len(set(combo)) == 1
        sections.append({'beat': beat,
                         'name': ('= ' if uniform else '') +
                                 ' / '.join(f'{c}:{n}' for c, n in zip(prog, combo))})
        for ci, (cname, sname) in enumerate(zip(prog, combo)):
            root = DEG[cname]
            slots = onsets(lib[sname])
            for b in range(a.bars):
                bar0 = beat + (ci * a.bars + b) * 4
                # A push only carries WITHIN a chord's own bars. On a chord
                # change the new chord gets struck on the downbeat -- checked
                # against the record: No Doubt's bar 3 starts C on beat 1, and
                # the &4 before it is a plain eighth, not a held one. Treating
                # every bar line the same silently swallowed that downbeat.
                into_change = (b == 0)
                pushes_out = a.push and 7 in slots and (
                    b < a.bars - 1 or a.push_changes)
                pushed_into = a.push and 7 in slots and (
                    (b > 0) or (ci > 0 and a.push_changes))
                live = [x for x in slots if not (x == 0 and pushed_into)]
                for i, s in enumerate(live):
                    # a strike rings until the next one, which is what the
                    # record does: beat 1 with no '&1' after it is a quarter,
                    # not an eighth followed by silence
                    nxt = live[i+1] if i+1 < len(live) else 8
                    dur = (nxt - s) * 0.5
                    if s == 7 and pushes_out:
                        dur = 1.5
                    chords.append(chord(root, bar0 + s * 0.5, dur))
        beat += len(prog) * a.bars * 4

    song = {'version': 1, 'chords': chords, 'notes': [],
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [], 'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    uni = sum(1 for s in sections if s['name'].startswith('= '))
    print(f'{" ".join(prog)}, {a.bars} bar(s) each, push {"on" if a.push else "off"}')
    print(f'{len(sections)} assignments ({uni} uniform, {len(sections)-uni} role-based), '
          f'{(beat-1)//4} bars, {len(chords)} strikes')
    print(f'-> {a.out}\n')
    for s in sections[:8]:
        print(f"   bar {(s['beat']-1)//4+1:>4}  {s['name']}")


if __name__ == '__main__':
    main()
