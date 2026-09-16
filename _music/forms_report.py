#!/usr/bin/env python3
"""
What do sections actually DO? Corpus-wide form trends.

A 16-bar section is never a random collection of chords, so the useful
question is not "which chords" but "which shape" — and the shapes turn out to
be few, lopsided, and not the ones the textbooks name.

    python3 forms_report.py                  # G50 + G100
    python3 forms_report.py --pools G50 --bars 16
"""
import argparse, collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp

# the user's own vocabulary for these shapes — speak it back
NAMED = {
    'AAAB': 'ender', 'ABAC': 'bounce', 'ABCB': 'return', 'AABB': 'shift',
    'ABAB': 'vamp', 'AABA': 'blues', 'AAAA': 'uniform', 'AA': 'doubled',
    'AAB': 'halver', 'ABC': 'through',
}


def collect(pools):
    pm = json.load(open(pp.POOLS))
    idx = pp.build_index()
    rows = []
    for slug in sorted(k for k, v in pm.items() if v in pools):
        path = pp.find(slug, idx)
        if not path: continue
        try: _, _, _, secs = B.bars_for(path)
        except Exception: continue
        seen = set()
        for name, bb in secs:
            key = (name, tuple(bb))
            if key in seen: continue         # a section marked N times is one section
            seen.add(key)
            fs = B.forms(bb)
            if not fs: continue
            f = fs[0]
            rows.append(dict(song=pp.strip_tags(os.path.basename(path)), part=name,
                             nbars=len(bb), run=not B.sayable(f), **f))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--bars', type=int, default=0, help='only sections this long')
    a = ap.parse_args()

    rows = collect(set(a.pools.split(',')))
    if a.bars: rows = [r for r in rows if r['nbars'] == a.bars]
    forms = [r for r in rows if not r['run']]
    labs = [r['labs'] for r in forms]
    P = lambda n, d: f'{n:>4}/{d}  {n/d:>4.0%}' if d else '   n/a'

    print(f'\n{len(rows)} distinct sections   {len(forms)} with a form   '
          f'{len(rows)-len(forms)} runs')
    print(f'  a form containing a variant (A\')   '
          f'{P(sum(any(chr(39) in l for l in x) for x in labs), len(forms))}')

    four = [l for l in labs if len(l) == 4]
    print(f'\n=== the four-phrase section ({len(four)} of them) ===')
    print(f'  phrase 2 repeats phrase 1          {P(sum(l[1]==l[0] for l in four), len(four))}')
    print(f'  phrase 3 RETURNS to phrase 1       {P(sum(l[2]==l[0] for l in four), len(four))}')
    print(f'  phrase 4 departs (new, or a prime) {P(sum(l[3] not in l[:3] for l in four), len(four))}')
    print(f'  phrase 3 is the odd one (a true AABA)'
          f'  {P(sum(l[2] not in (l[0],l[1],l[3]) for l in four), len(four))}')

    print('\n=== commonest shapes ===')
    c = collections.Counter(B.shape(l) for l in labs)
    for k, v in c.most_common(12):
        nm = NAMED.get(k, '')
        print(f'  {v:>4}  {k:<12} {nm}')

    print('\n=== by section length ===')
    bylen = collections.defaultdict(collections.Counter)
    for r in rows:
        bylen[r['nbars']]['run' if r['run'] else B.shape(r['labs'])] += 1
    for n in sorted(bylen):
        tot = sum(bylen[n].values())
        if tot < 8: continue
        top = '  '.join(f'{k}({v})' for k, v in bylen[n].most_common(4))
        print(f'  {n:>3} bars  ({tot:>3})   {top}')


if __name__ == '__main__':
    main()
