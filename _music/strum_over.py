#!/usr/bin/env python3
"""
Take a progression you already like and strum it every way.

Reads a Hookpad paste (the chords with their pushes and suspensions already in
place), then re-emits it once per strum assignment. The chords and their change
points never move; only the strikes do.

    python3 strum_over.py prog.json
    python3 strum_over.py prog.json --per bar --strums folk-DDU-UDU,wonderwall

Two rules, both from how a strum relates to a progression:

A strike plays whatever chord is ACTIVE at that moment. The strum is a grid of
times; the progression says what is sounding. That is the whole relationship.

Every change onset is struck whether the strum asks for it or not. If the strum
has no stroke at the & of 4 and the chord changes there, the change would go
unheard -- the push would vanish. Those inserted strikes are counted and
reported, because a strum that needs many of them is not really the strum you
chose.
"""
import argparse, itertools, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = ['simple-kind-of-life', 'folk-DDU-UDU', 'wonderwall',
           'driving-DU-UDU-U', 'quarters', 'eighths']


def onsets(cells):
    """cell string -> struck eighth-slots within a bar"""
    out, slot = [], 0
    for cell in cells.split():
        n = len(cell)
        for i, c in enumerate(cell):
            if c in 'DUx':
                out.append(slot + (i * 2 // n if n > 1 else 0))
        slot += 2
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paste', help='a Hookpad paste holding the progression')
    ap.add_argument('--strums', default=','.join(DEFAULT))
    ap.add_argument('--per', choices=['pair', 'bar'], default='pair',
                    help='assign a strum per 2-bar pair (default) or per bar')
    ap.add_argument('--bpm', type=int, default=96)
    ap.add_argument('--key', default='A')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/strum-over.txt'))
    a = ap.parse_args()

    lib = json.load(open(os.path.join(HERE, 'strum_library.json')))['patterns']
    names = [s.strip() for s in a.strums.split(',') if s.strip()]
    for n in names:
        if n not in lib: raise SystemExit(f'not in library: {n}\n{sorted(lib)}')

    src = json.load(open(a.paste))['chords']
    src = sorted(src, key=lambda c: c['beat'])
    origin = src[0]['beat']
    span = src[-1]['beat'] + src[-1]['duration'] - origin
    nbars = int(round(span / 4))
    changes = [c['beat'] - origin for c in src]          # offsets of real changes

    def active(t):
        cur = src[0]
        for c in src:
            if c['beat'] - origin <= t + 1e-9: cur = c
            else: break
        return cur

    units = nbars // 2 if a.per == 'pair' else nbars
    per_unit = 2 if a.per == 'pair' else 1

    chords, sections, beat, inserted_tot = [], [], 1, 0
    for combo in itertools.product(names, repeat=units):
        uniform = len(set(combo)) == 1
        sections.append({'beat': beat,
                         'name': ('= ' if uniform else '') + ' / '.join(combo)})
        strikes = []
        for ui, sname in enumerate(combo):
            for b in range(per_unit):
                bar = ui * per_unit + b
                for s in onsets(lib[sname]):
                    strikes.append(bar * 4 + s * 0.5)
        # a change must be heard even if the strum is silent there
        inserted = [t for t in changes if t not in strikes]
        inserted_tot += len(inserted)
        strikes = sorted(set(strikes) | set(changes))
        # ...and a pushed chord must be allowed to RING across the downbeat it
        # anticipated. Striking beat 1 again there throws away the only thing
        # that makes a push a push, which is the silence on the beat.
        for bar in range(1, nbars):
            down = bar * 4.0
            if (down - 0.5) in changes and down not in changes:
                strikes = [t for t in strikes if t != down]
        for i, t in enumerate(strikes):
            nxt = strikes[i+1] if i+1 < len(strikes) else nbars * 4
            base = active(t)
            chords.append({**base, 'beat': beat + t, 'duration': round(nxt - t, 4)})
        beat += nbars * 4

    song = {'version': 1, 'chords': chords, 'notes': [],
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': a.key}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [], 'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    uni = sum(1 for s in sections if s['name'].startswith('= '))
    print(f'{nbars}-bar progression, strum per {a.per}: {len(sections)} assignments '
          f'({uni} uniform, {len(sections)-uni} mixed)')
    print(f'{(beat-1)//4} bars, {len(chords)} strikes, '
          f'{inserted_tot} added to keep changes audible -> {a.out}\n')
    for s in sections[:8]:
        print(f"   bar {(s['beat']-1)//4+1:>4}  {s['name']}")


if __name__ == '__main__':
    main()
