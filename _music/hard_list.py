#!/usr/bin/env python3
"""
Which sections actually need a memory trick?

You already know most of these progressions. The ones worth a card are the
ones that are unlike the rest: a cell that appears nowhere else in the
hundred, a form with several distinct phrases, an odd chord, no clean shape.
So rank by difficulty and look at the top of the list — do not generate 383
pictures nobody needs.

    python3 hard_list.py                 # top 25 hardest
    python3 hard_list.py --n 40 --pools G50
    python3 hard_list.py --song "blue on black"     # why is this one ranked here
"""
import argparse, collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp

NAMED = {'AA','AAA','AAAA','AAAB','ABAC','ABAB','AABB','AABA','ABCB','AAB','ABA'}
# chords that are not the everyday six in a major key
ODD = {'A#', 'D', 'E'}


def sections(pools):
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    out = []
    for slug in sorted(k for k, v in pm.items() if v in pools):
        path = pp.find(slug, idx)
        if not path: continue
        try: tonic, scale, _, secs = B.bars_for(path)
        except Exception: continue
        seen = set()
        for name, bb in secs:
            key = (name, tuple(bb))
            if key in seen: continue
            seen.add(key)
            f = (B.forms(bb) or [None])[0]
            if not f: continue
            out.append(dict(song=pp.strip_tags(os.path.basename(path)), part=name,
                            pool=pm[slug], key=f'{tonic} {scale}', bars=bb, f=f))
    return out


def score(s, freq):
    """Higher = more worth a picture. Each term is a reason you'd struggle."""
    f = s['f']
    run = not B.sayable(f)
    cells = [tuple(B.phrase_chords(c)[0]) for c in f['chunks']]
    rarest = min((freq[c] for c in cells), default=1)
    why, pts = [], 0.0

    if run:
        pts += 4; why.append('no repeating shape')
    else:
        if f['nbase'] >= 3: pts += 2.5; why.append(f'{f["nbase"]} distinct phrases')
        elif f['nbase'] == 2: pts += 1; why.append('2 phrases')
        if B.shape(f['labs']) not in NAMED:
            pts += 1.5; why.append(f'odd shape {B.shape(f["labs"])}')
    if rarest <= 1: pts += 3; why.append('cell unique in the pools')
    elif rarest <= 3: pts += 1.5; why.append(f'cell seen only {rarest}x')
    widest = f['widest']
    if widest >= 5: pts += 2; why.append(f'{widest}-chord cell')
    elif widest == 4: pts += 0.5
    odd = {c for cell in cells for c in cell} & ODD
    if odd: pts += 1.5; why.append('outside chord: ' + '/'.join(sorted(odd)))
    if f['head'] or f['tail']: pts += 0.5; why.append('pickup/ending')
    return pts, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--n', type=int, default=25)
    ap.add_argument('--song', default=None)
    a = ap.parse_args()

    secs = sections(set(a.pools.split(',')))
    freq = collections.Counter()
    for s in secs:
        for c in {tuple(B.phrase_chords(ch)[0]) for ch in s['f']['chunks']}:
            freq[c] += 1

    ranked = sorted(((score(s, freq), s) for s in secs), key=lambda x: -x[0][0])
    if a.song:
        ranked = [r for r in ranked if a.song.lower() in r[1]['song'].lower()]

    print(f'\n{len(secs)} sections ranked by how much a picture would help\n')
    for (pts, why), s in ranked[:a.n]:
        f = s['f']
        art, _, ttl = s['song'].partition('_')
        def cellstr(c):
            core, reps, tail = B.phrase_chords(c)
            return ('-'.join(core) + (f'x{reps}' if reps > 1 else '')
                    + ('+' + '-'.join(tail) if tail else ''))
        cells = {l: cellstr(c) for l, c in zip(f['labs'], f['chunks'])}
        prog = '   '.join(f'{l}={c}' for l, c in sorted(cells.items()))
        print(f'  {pts:>4.1f}  {ttl.replace("-"," ")[:30]:<31} {s["part"][:11]:<12} '
              f'{s["pool"]:<5} {B.shape(f["labs"]):<8} {prog[:46]}')
        print(f'        {", ".join(why)}')

    print(f'\n  the other {max(0, len(secs)-a.n)} score below '
          f'{ranked[min(a.n, len(ranked)-1)][0][0]:.1f} — you likely know them.')


if __name__ == '__main__':
    main()
