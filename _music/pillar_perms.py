#!/usr/bin/env python3
"""
The 36 four-bar orders of the three pillars (and of two pillars + vi or ii) that use all three -> _music/pillar-perms.html
and their runners (one chord held 2 bars, first or last) on one screen -> _music/runners.html

    themap_venv/python pillar_perms.py

Four bars, one chord a bar, each I, IV or V: 3^4 = 81 orders. 36 of them use all
three, which means one chord is doubled: 3 choices of doubled chord x 12 ways to
place two of one and one each of the others (4!/2!). The page lays them out that
way: a row per doubled chord, a column per placement.

A song plays an order when a major-key section, read in 4-bar blocks from its
first bar, has a block whose every bar holds a single chord and those chords
spell the order. Plain triads (V7 -> V), so it is the harmony, not the voicing.
Copies of a song collapse to one (same_progressions.same) and a song counts once
per order, listed at the first place it plays it. Its tempo copies (-170) and
-right corrections are read too: Wonderwall is written two chords a bar, its
-170 copy one, and only the copy shows the pre-chorus's IV V vi vi.
"""
import itertools, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from same_progressions import same, plain, title_case, HASH

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = re.compile(r'-(\d{2,3}|right)$', re.I)      # other readings of a song that count: tempo copies, corrections
# the pillars, then two pillars + one minor (vi or ii), with their palette words
SETS = [(('I', 'IV', 'V'), 'HAGFISH'),
        (('I', 'IV', 'vi'), 'FOX'), (('I', 'V', 'vi'), 'SCOTCH'), (('IV', 'V', 'vi'), 'SUNFISH'),
        (('I', 'IV', 'ii'), 'GIFT'), (('I', 'V', 'ii'), 'JACKET'), (('IV', 'V', 'ii'), 'SHAFT')]
ORDERS, ORDER_SET = [], []
for si, (P, _) in enumerate(SETS):
    for o in itertools.product(P, repeat=4):
        if set(o) == set(P):
            ORDERS.append(o); ORDER_SET.append(si)


def orders_in(d, nb, index):
    """{order: (section, bar)} for each order a major-key section plays in a 4-bar block, first place only"""
    mc = C.merged(d.get('chords') or [])
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
    return found


def main():
    ids = {}
    for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json'))):
        ids.setdefault(s['song'].replace('/', '_').lower(), s['ID'])
    best, copies = {}, {}
    for name, d, nb in C.songs():
        k = same(name)
        copies.setdefault(k, []).append((name, d, nb))
        # a copy with chords beats one without (Talk-chords, -audiochords over a
        # melody-only original), then the plain name, then the most melody
        rank = (len(d.get('chords') or []) >= 4, name.lower() == k, len(d.get('notes') or []))
        if k not in best or rank > best[k][0]:
            best[k] = (rank, name, d, nb)
    index = {o: i for i, o in enumerate(ORDERS)}
    songs, hits = [], []
    for _, name, d, nb in sorted(best.values(), key=lambda b: b[1].lower()):
        # every copy is read, the kept one first: a doubled-tempo copy (Wonderwall-170)
        # has one chord a bar where the original has two
        found = {}
        # (tempo copies and -right corrections only: -simple / -midi copies aren't the record's chords)
        for cn, cd, cnb in [(name, d, nb)] + [c for c in copies[same(name)] if c[0] != name and COPY.search(c[0])]:
            tag = COPY.search(cn)
            for o, (sec, bar) in orders_in(cd, cnb, index).items():
                found.setdefault(o, (sec if cn == name else f"{sec} ({tag.group(1) + ' bpm' if tag.group(1).isdigit() else 'corrected'} copy)", bar))
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
    data = dict(orders=[list(o) for o in ORDERS], sets=[[list(p), w] for p, w in SETS], order_set=ORDER_SET, songs=songs, hits=hits)
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    for tpl, out in (('pillar_perms_template.html', 'pillar-perms.html'), ('runners_template.html', 'runners.html')):
        open(os.path.join(HERE, out), 'w').write(open(os.path.join(HERE, tpl)).read().replace('__DATA__', js))
    n = [0] * len(ORDERS)
    for o, *_ in hits: n[o] += 1
    print(f'{len(ORDERS)} orders, {sum(1 for x in n if x)} heard, {len(songs)} songs, {len(hits)} song-orders')
    for si, (P, w) in enumerate(SETS):
        mine = [i for i in range(len(ORDERS)) if ORDER_SET[i] == si]
        sg = len({h[1] for h in hits if ORDER_SET[h[0]] == si})
        print(f'  {w:8} {" ".join(P):10} {sum(1 for i in mine if n[i]):2}/36 heard, {sg:3} songs   top: ' +
              ', '.join(f'{" ".join(ORDERS[i])} ({n[i]})' for i in sorted(mine, key=lambda i: -n[i])[:3]))


if __name__ == '__main__':
    main()
