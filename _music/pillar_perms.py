#!/usr/bin/env python3
"""
The 36 four-bar orders of the three pillars that use all three -> _music/pillar-perms.html

    themap_venv/python pillar_perms.py

Four bars, one chord a bar, each I, IV or V: 3^4 = 81 orders. 36 of them use all
three, which means one chord is doubled: 3 choices of doubled chord x 12 ways to
place two of one and one each of the others (4!/2!). The page lays them out that
way: a row per doubled chord, a column per placement.

A song plays an order when a major-key section, read in 4-bar blocks from its
first bar, has a block whose every bar holds a single chord and those chords
spell the order. Plain triads (V7 -> V), so it is the harmony, not the voicing.
Copies of a song collapse to one (same_progressions.same) and a song counts once
per order, listed at the first place it plays it.
"""
import itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from same_progressions import same, plain, title_case, HASH

HERE = os.path.dirname(os.path.abspath(__file__))
P = ('I', 'IV', 'V')
ORDERS = [o for o in itertools.product(P, repeat=4) if set(o) == set(P)]


def main():
    ids = {}
    for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json'))):
        ids.setdefault(s['song'].replace('/', '_').lower(), s['ID'])
    best = {}
    for name, d, nb in C.songs():
        k = same(name)
        # a copy with chords beats one without (Talk-chords, -audiochords over a
        # melody-only original), then the plain name, then the most melody
        rank = (len(d.get('chords') or []) >= 4, name.lower() == k, len(d.get('notes') or []))
        if k not in best or rank > best[k][0]:
            best[k] = (rank, name, d, nb)
    index = {o: i for i, o in enumerate(ORDERS)}
    songs, hits = [], []
    for _, name, d, nb in sorted(best.values(), key=lambda b: b[1].lower()):
        mc = C.merged(d['chords'])
        found = {}
        for sec, b0, end in C.sections(d):
            mode = C.mode_at(d, b0)
            if mode not in ('major', None, ''):
                continue
            bars = []
            for i in range(int((end - b0) // nb)):
                s, e = b0 + i * nb, b0 + (i + 1) * nb
                labs = {plain(C.roman(c, mode)) for c, b, du in mc if b < e and b + du > s}
                bars.append(labs.pop() if len(labs) == 1 else None)
            for i in range(0, len(bars) - 3, 4):
                o = tuple(bars[i:i + 4])
                if o in index and o not in found:
                    found[o] = (str(sec), i + 1)
        if not found:
            continue
        base = same(name)
        artist, title = base.split('_', 1) if '_' in base else ('', base)
        si = len(songs)
        songs.append(dict(t=title_case(title), a=title_case(artist),
                          k=f"{((d.get('keys') or [{}])[0] or {}).get('tonic', '')} major".strip(),
                          bpm=((d.get('tempos') or [{}])[0] or {}).get('bpm'),
                          u=HASH.encode(ids[name.lower()]) if name.lower() in ids else ''))
        for o, (sec, bar) in found.items():
            hits.append([index[o], si, sec, bar])
    data = dict(orders=[list(o) for o in ORDERS], songs=songs, hits=hits)
    tpl = open(os.path.join(HERE, 'pillar_perms_template.html')).read()
    open(os.path.join(HERE, 'pillar-perms.html'), 'w').write(
        tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    n = [0] * len(ORDERS)
    for o, *_ in hits: n[o] += 1
    print(f'{len(ORDERS)} orders, {sum(1 for x in n if x)} heard, {len(songs)} songs, {len(hits)} song-orders')
    for i in sorted(range(len(ORDERS)), key=lambda i: -n[i])[:12]:
        print(f'  {n[i]:4d}  {" ".join(ORDERS[i])}')


if __name__ == '__main__':
    main()
