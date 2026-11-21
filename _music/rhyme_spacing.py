#!/usr/bin/env python3
"""
Where do the rhyme notes fall? Only sections carrying the user's rhyme markers
("( a)" at a line end, or "[a]" on the syllable).

    themap_venv/python rhyme_spacing.py
    themap_venv/python rhyme_spacing.py --show 4-4      # the sections of one shape
    themap_venv/python rhyme_spacing.py --exact         # only 1:1-aligned sections

ALIGNMENT. Syllable i is note i only when the counts match, which is 40 of ~290
rhyme sections; most have 1-6 more notes than syllables (uncounted melismas, a
bleed from the next section). So each rhyme syllable gets a WINDOW of candidate
notes: its index counted from the section start, and counted from the end. If
every candidate sits in the same bar the bar is CERTAIN; otherwise the candidate
followed by the longest silence wins (a rhyme ends its line, and a line ends on a
gap), marked as a guess. Sections more than 6 off are skipped.

A rhyme note's BAR counts from the section's notated barline; a note on the "and"
of 4 is an anticipation and belongs to the next bar. The SHAPE is the bar gaps
between successive rhyme notes, starting from the section start: rhymes on bars
4 and 8 read 4-4, on 2 4 6 8 read 2-2-2-2.
"""
import argparse, collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from parse_lyrics import parse_song, syllables_in

SLACK = 6


def bar_of(n, b0):
    return int((n['beat'] - b0 + .5) // 4) + 1


def rhyme_notes(r, inn, b0):
    """-> [(bar, beat-in-bar, letter, certain)] or None"""
    flat = []                                    # (letter or None) per expected note
    for l in r['lines']:
        for i, t in enumerate(l['syllables']):
            k = syllables_in(t)
            for j in range(k):
                hit = l['rhyme'] if (l['rhyme'] and i == l['rhyme_at'] and j == k - 1) else None
                flat.append(hit)
    k = len(inn) - len(flat)
    if abs(k) > SLACK: return None
    out = []
    for i, letter in enumerate(flat):
        if not letter: continue
        lo, hi = sorted((i, i + k))
        cand = [inn[x] for x in range(max(lo, 0), min(hi, len(inn) - 1) + 1)]
        if not cand: continue
        bars = {bar_of(n, b0) for n in cand}
        def gap(n):
            j = inn.index(n)
            nxt = inn[j + 1]['beat'] if j + 1 < len(inn) else n['beat'] + 8
            return nxt - n['beat'] - n.get('duration', 0)
        n = cand[0] if len(bars) == 1 else max(cand, key=gap)
        out.append((bar_of(n, b0), (n['beat'] - b0) % 4 + 1, letter, len(bars) == 1, n))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--show'); ap.add_argument('--exact', action='store_true')
    a = ap.parse_args()
    rows = []
    for name, d, nb in corpus.songs():
        if nb != 4: continue
        rs, _ = parse_song(d)
        secs = list(corpus.sections(d))
        notes = sorted((n for n in d.get('notes') or [] if not n.get('isRest')), key=lambda n: n['beat'])
        for r in rs:
            if r['index'] is None or r['index'] >= len(secs): continue
            if not any(l['rhyme'] for l in r['lines']): continue
            sname, b0, b1 = secs[r['index']]
            inn = [n for n in notes if b0 <= n['beat'] < b1]
            if a.exact and len(inn) != r['syllables']: continue
            hits = rhyme_notes(r, inn, b0)
            if not hits: continue
            bars = [h[0] for h in hits]
            gaps = [bars[0]] + [y - x for x, y in zip(bars, bars[1:])]
            rows.append(dict(name=name, sec=sname, nbars=round((b1 - b0) / 4), scheme=r['scheme'],
                             shape='-'.join(map(str, gaps)), hits=hits,
                             certain=all(h[3] for h in hits)))
    cert = sum(x['certain'] for x in rows)
    nh = sum(len(x['hits']) for x in rows)
    print(f"{len(rows)} sections with rhyme notes, from {len({x['name'] for x in rows})} songs   "
          f"bars certain for every rhyme: {cert}   rhyme notes {nh}, certain {sum(h[3] for x in rows for h in x['hits'])}\n")
    if a.show:
        for x in rows:
            if x['shape'] == a.show:
                print(f"  {x['name'][:34]:34} {x['sec'][:12]:12} {x['nbars']:>3} bars  {x['scheme']:10} "
                      + '  '.join(f"{l}@{b}" + ('' if c else '?') for b, bt, l, c, _ in x['hits']))
        return
    for L in (4, 8, 16):
        R = [x for x in rows if x['nbars'] == L]
        if not R: continue
        c = collections.Counter(x['shape'] for x in R)
        print(f'{L}-BAR SECTIONS ({len(R)} sections, {len({x["name"] for x in R})} songs)')
        for k, v in c.most_common(10):
            songs = len({x['name'] for x in R if x['shape'] == k})
            print(f'  {k:22} {v:4}  {v / len(R):5.1%}   ({songs} songs)')
        print()
    other = collections.Counter(x['nbars'] for x in rows if x['nbars'] not in (4, 8, 16))
    print('other lengths: ' + '  '.join(f'{k} bars:{v}' for k, v in sorted(other.items())))
    allh = [h for x in rows for h in x['hits'] if h[3]]
    beat = collections.Counter(h[1] for h in allh)
    print(f'\nRHYME NOTE starts on beat (certain ones, {len(allh)}): ' +
          '  '.join(f'{k:g}:{v / len(allh):.0%}' for k, v in beat.most_common(8)))
    gaps = collections.Counter(g for x in rows for g in map(int, x['shape'].split('-')[1:]))
    tg = sum(gaps.values())
    print('gap between successive rhymes, bars: ' + '  '.join(f'{k}:{v / tg:.0%}' for k, v in sorted(gaps.items()) if v / tg >= .01))
    pos = collections.Counter(h[0] for x in rows if x['nbars'] == 8 for h in x['hits'])
    t8 = sum(pos.values())
    print('8-bar sections, which bar a rhyme lands in: ' + '  '.join(f'{k}:{v / t8:.0%}' for k, v in sorted(pos.items())))


if __name__ == '__main__':
    main()
