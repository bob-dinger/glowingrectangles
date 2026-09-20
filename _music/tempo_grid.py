#!/usr/bin/env python3
"""Every song's tempo snapped to the 10-bpm grid.

Ties -- a tempo landing exactly on a 5, like 125 -- are SPLIT: half go down,
half go up. Rounding them all one way would pile a real bulge onto one grid
value and invent a peak that is not in the music. Within a tie group songs are
sorted by name and then alternated, so the split is even and the same every run.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

raw = []
for name, d, nb in corpus.songs(need_chords=False):
    t = (d.get('tempos') or [{}])[0].get('bpm')
    if t is not None:
        raw.append((name, round(t)))

ties = collections.defaultdict(list)
grid = collections.Counter()
exact = 0
for name, t in sorted(raw):
    if t % 10 == 5:
        ties[t].append(name)
    else:
        grid[int(round(t / 10.0)) * 10] += 1
        exact += 1

split = []
for t, names in sorted(ties.items()):
    for i, n in enumerate(sorted(names)):
        g = (t - 5) if i % 2 == 0 else (t + 5)      # alternate down, up
        grid[g] += 1
        split.append((n, t, g))

tot = sum(grid.values())
print(f"  {tot:,} songs with a tempo   ({exact:,} rounded normally, "
      f"{len(split):,} were exact ties and got split)\n")
mx = max(grid.values())
for b in sorted(grid):
    n = grid[b]
    bar = '#' * max(1, round(40 * n / mx))
    print(f"  {b:>4} bpm  {n:>4}  {100*n/tot:>4.1f}%  {bar}")
print(f"\n  ties by value:")
for t, names in sorted(ties.items()):
    d = sum(1 for n, tt, g in split if tt == t and g < t)
    print(f"    {t:>4} bpm  {len(names):>3} songs  ->  {d} down to {t-5}, "
          f"{len(names)-d} up to {t+5}")
