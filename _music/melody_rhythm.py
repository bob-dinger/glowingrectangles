#!/usr/bin/env python3
"""Melody rhythm as onsets in a 16-slot bar.

The user: "I'd love to study the rhythm of melody. it's the only thing that
matters." Matches their own model -- phrase shape and where notes land, not
pitch contour.

The grid is SIXTEENTHS, measured not assumed: 85% of notes land on a beat or
its "and", and 15% on a sixteenth. Triplets are 0.03% and are dropped. So one
bar of 4/4 is 16 slots, which is the same slot count as the chord notation
(music_rhythm_slots) at half the span -- melody is twice as dense as harmony.

Even slots are eighth positions; odd slots are sixteenths.
"""
import sys, os, json, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

rows = json.load(open(os.path.expanduser('~/Desktop/melody_map.json')))
want = {(r['file'], r['section']): r for r in rows}

bars = collections.Counter()
ex = collections.defaultdict(list)
per_role = collections.defaultdict(collections.Counter)
nbars = 0
for name, d, nb in corpus.songs():
    notes = [x for x in (d.get('notes') or []) if not x.get('isRest')]
    if not notes or nb != 4:
        continue
    for sec, st, en in corpus.sections(d):
        meta = want.get((name, sec))
        if not meta:
            continue
        ns = [x for x in notes if st <= x['beat'] < en]
        if len(ns) < 4:
            continue
        span = max(x['beat'] + x['duration'] for x in ns) - st
        for b in range(int(span // nb)):
            b0 = st + b * nb
            slots = sorted({round((x['beat'] - b0) * 4) for x in ns
                            if -1e-6 <= x['beat'] - b0 < nb})
            if not slots:
                continue
            key = tuple(slots)
            bars[key] += 1
            per_role[meta['role']][key] += 1
            nbars += 1
            if len(ex[key]) < 3:
                ex[key].append(f"{meta['song'][:22]} {meta['role']}")

print(f"  {nbars:,} bars of melody, {len(bars):,} distinct onset patterns\n")
print(f"  {'onsets in the bar':<26}{'notes':>6}{'bars':>7}{'share':>7}   examples")
run = 0
for k, v in bars.most_common(18):
    run += v
    grid = ''.join('#' if i in k else '.' for i in range(16))
    print(f"  {grid:<26}{len(k):>6}{v:>7,}{v/nbars:>7.1%}   {', '.join(ex[k][:2])}")
print(f"\n  top 18 patterns = {run/nbars:.0%} of all bars")
sixt = sum(v for k, v in bars.items() if any(i % 2 for i in k))
print(f"  {sixt/nbars:.0%} of bars use at least one sixteenth")
rows_out = ["pattern\tnotes\tbars\tshare"]
for k, v in bars.most_common():
    rows_out.append(f"{''.join('#' if i in k else '.' for i in range(16))}\t{len(k)}\t{v}\t{v/nbars:.5f}")
subprocess.run(['pbcopy'], input="\n".join(rows_out).encode())
print(f"  all {len(bars):,} on your clipboard")
