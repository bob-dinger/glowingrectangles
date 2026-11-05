#!/usr/bin/env python3
"""
The 36 four-bar orders of the three pillars (and of every other set of three diatonic chords) that use all three -> _music/pillar-perms.html
and their runners (one chord held 2 bars, first or last) on one screen -> _music/runners.html

    themap_venv/python pillar_perms.py

Four bars, one chord a bar, each I, IV or V: 3^4 = 81 orders. 36 of them use all
three, which means one chord is doubled: 3 choices of doubled chord x 12 ways to
place two of one and one each of the others (4!/2!). The page lays them out that
way: a row per doubled chord, a column per placement.

A song plays an order when a major- or minor-key section (minor through its
relative major), read in 4-bar blocks from its first bar, has a block whose every bar holds a single chord and those chords
spell the order. Plain triads (V7 -> V), so it is the harmony, not the voicing.
Copies of a song collapse to one (same_progressions.same) and a song counts once
per order, listed at the first place it plays it. Its tempo copies (-170) and
-right corrections are read too: Wonderwall is written two chords a bar, its
-170 copy one, and only the copy shows the pre-chorus's IV V vi vi. Last, the
same read at half-bar speed (2-beat blocks of 2 bars): It Ain't Me's bridge,
Dm Am | Em, is ii vi iii iii.
"""
import itertools, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from same_progressions import same, plain, title_case, HASH

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = re.compile(r'-(\d{2,3}|right)$', re.I)      # other readings of a song that count: tempo copies, corrections
# every set of three of the six diatonic chords (in C: C Dm Em F G Am, minor keys read
# through their relative major), with its palette word: the pillars, the other two majors +
# a minor sets, then one major + two minors, then the three minors
SETS = [(('I', 'IV', 'V'), 'HAGFISH'),
        (('I', 'IV', 'vi'), 'FOX'), (('I', 'V', 'vi'), 'SCOTCH'), (('IV', 'V', 'vi'), 'SUNFISH'),
        (('I', 'IV', 'ii'), 'GIFT'), (('I', 'V', 'ii'), 'JACKET'), (('IV', 'V', 'ii'), 'SHAFT'),
        (('I', 'IV', 'iii'), 'FLAMINGO'), (('I', 'V', 'iii'), 'COACHMAN'), (('IV', 'V', 'iii'), 'FLEMISH'),
        (('I', 'ii', 'vi'), 'DESK'), (('I', 'iii', 'vi'), 'MASK'), (('I', 'ii', 'iii'), 'COMET'),
        (('IV', 'ii', 'vi'), 'FEAST'), (('IV', 'iii', 'vi'), 'MASSIF'), (('IV', 'ii', 'iii'), 'FOOTMAN'),
        (('V', 'ii', 'vi'), 'JOUST'), (('V', 'iii', 'vi'), 'JASMINE'), (('V', 'ii', 'iii'), 'MACHETE'),
        (('ii', 'iii', 'vi'), 'MAST')]
GROUPS = [('two majors + a minor', 0, 10), ('one major + two minors, and the three minors', 10, 20)]
ORDERS, ORDER_SET = [], []
for si, (P, _) in enumerate(SETS):
    for o in itertools.product(P, repeat=4):
        if set(o) == set(P):
            ORDERS.append(o); ORDER_SET.append(si)


def orders_in(d, nb, index, unit=1):
    """{order: (section, bar)} for each order a major- or minor-key section plays in a block of
    four units, first place only. unit=1 reads a chord a bar; unit=0.5 a chord a half bar, so
    It Ain't Me's bridge Dm Am | Em is Dm Am Em Em"""
    mc = C.merged(d.get('chords') or [])
    w = nb * unit
    found = {}
    for sec, b0, end in C.sections(d):
        mode = C.mode_at(d, b0)
        if mode not in ('major', 'minor', None, ''):
            continue
        units = []
        for i in range(int((end - b0) // w)):
            s, e = b0 + i * w, b0 + (i + 1) * w
            labs = {plain(C.roman(c, mode or 'major')) for c, b, du in mc if b < e and b + du > s}
            units.append(labs.pop() if len(labs) == 1 else None)
        for i in range(0, len(units) - 3, 4):
            o = tuple(units[i:i + 4])
            if o in index and o not in found:
                found[o] = (str(sec), int(i * unit) + 1)
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
        # then the same at half-bar speed (a chord every two beats), marked as such
        for unit in (1, 0.5):
            for cn, cd, cnb in [(name, d, nb)] + [c for c in copies[same(name)] if c[0] != name and COPY.search(c[0])]:
                tag = COPY.search(cn)
                for o, (sec, bar) in orders_in(cd, cnb, index, unit).items():
                    how = ([] if cn == name else [f"{tag.group(1) + ' bpm' if tag.group(1).isdigit() else 'corrected'} copy"]) + \
                          ([] if unit == 1 else ['half bars'])
                    found.setdefault(o, (sec + (f" ({', '.join(how)})" if how else ''), bar, int(unit != 1)))
        if not found:
            continue
        base = same(name)
        artist, title = base.split('_', 1) if '_' in base else ('', base)
        si = len(songs)
        k0 = (d.get('keys') or [{}])[0] or {}
        songs.append(dict(t=title_case(title), a=title_case(artist),
                          k=f"{k0.get('tonic', '')} {k0.get('scale') or 'major'}".strip(),
                          bpm=((d.get('tempos') or [{}])[0] or {}).get('bpm'),
                          u=HASH.encode(ids[name.lower()]) if name.lower() in ids else ''))
        for o, (sec, bar, half) in found.items():
            hits.append([index[o], si, sec, bar, half])
    data = dict(orders=[list(o) for o in ORDERS], sets=[[list(p), w] for p, w in SETS], groups=GROUPS, order_set=ORDER_SET, songs=songs, hits=hits)
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
