"""Rhythmic-signature analysis of perfect_melodies.json.

Treats each phrase as a duration sequence (ignoring pitch) and asks two things:
  1. What is the repeating rhythmic CELL (smallest period the phrase loops on)?
  2. Which FAMILY does the phrase belong to (isochronous / run-to-landing /
     dotted-lilt / gallop / hold-anchored)?

This is the chord-riff-fingerprint lens (layer 1 = durations) applied to melody.
Run:  python _music/rhythm_signatures.py
"""
import json, os
from collections import Counter

CORPUS = os.path.join(os.path.dirname(__file__), 'perfect_melodies.json')
def g(x): return format(round(x, 3), 'g')


def durs(phrase):
    return [round(n['duration'], 2) for n in phrase]


def repeating_cell(seq):
    """The dominant repeated CELL, tolerant of a phrase that establishes a loop
    then varies. Finds the longest cell length L (2..len/2) whose consecutive
    tiling covers the most notes, preferring longer cells on ties. Returns
    (cell, n_reps) where reps>=2, else (None, 1)."""
    n = len(seq)
    best = None  # (coverage, L, start)
    for L in range(2, n // 2 + 1):
        for start in range(0, n - 2 * L + 1):
            cell = seq[start:start + L]
            reps = 1
            j = start + L
            while j + L <= n and seq[j:j + L] == cell:
                reps += 1
                j += L
            if reps >= 2:
                cov = reps * L
                cand = (cov, L, start)
                if best is None or cand > best:
                    best = cand
    if best is None:
        return None, 1
    cov, L, start = best
    return seq[start:start + L], cov // L


def motifs(seq, lo=3, hi=6):
    """All contiguous sub-cells of length lo..hi (for cross-song matching)."""
    return {tuple(seq[i:i + L]) for L in range(lo, hi + 1)
            for i in range(len(seq) - L + 1)}


def family(seq):
    """Coarse rhythm-shape bucket."""
    n = len(seq)
    short = sum(1 for x in seq if x <= 0.5)
    longest = max(seq)
    tail = seq[-1]
    uniq = set(seq)
    dotted = sum(1 for x in seq if x in (0.75, 1.25, 1.5, 1.75))

    if uniq <= {1.0} or (uniq <= {1.0} | {longest} and seq.count(1.0) >= n - 3):
        # walking quarters, maybe with a held cadence note
        return 'isochronous'
    if dotted >= n * 0.35:
        return 'dotted-lilt'
    if longest >= 3 and tail >= 2 and short >= n * 0.3:
        return 'run-to-landing'
    if short >= n * 0.6:
        return 'gallop'
    if longest >= 4:
        return 'hold-anchored'
    return 'mixed'


def main():
    d = json.load(open(CORPUS))
    fams = {}
    motif_index = {}
    print(f"{'SONG / PHRASE':30} {'FAMILY':15} {'DOMINANT CELL (reps)':30} texture")
    print('-' * 98)
    for k, v in d.items():
        if not (isinstance(v, list) and v and isinstance(v[0], list)):
            continue
        for i, ph in enumerate(v):
            s = durs(ph)
            tag = f'{k} ph{i+1}'
            cell, reps = repeating_cell(s)
            fam = family(s)
            fams.setdefault(fam, []).append(tag)
            cellstr = (' '.join(g(x) for x in cell) + f'  x{reps}') if cell else '(no loop)'
            for m in motifs(s):
                motif_index.setdefault(m, set()).add(tag)
            short = sum(1 for x in s if x <= 0.5)
            held = sum(1 for x in s if x >= 2)
            tex = f'n={len(s):>2} short={short:>2} held={held:>2} long={g(max(s))}'
            print(f'{tag[:30]:30} {fam:15} {cellstr[:30]:30} {tex}')

    print('\n=== FAMILIES ===')
    for fam, items in sorted(fams.items(), key=lambda x: -len(x[1])):
        print(f'  {fam:16} {len(items):>2}  {", ".join(items)}')

    def song(tag): return tag.rsplit(' ph', 1)[0]
    shared = [(m, xs) for m, xs in motif_index.items()
              if len({song(x) for x in xs}) > 1]
    # keep the longest / most-distinctive shared motifs, drop trivial all-1s
    shared = [(m, xs) for m, xs in shared if not set(m) <= {1.0}]
    shared.sort(key=lambda mx: (-len(mx[0]), -len(mx[1])))
    print('\n=== RHYTHMIC MOTIFS SHARED ACROSS DIFFERENT SONGS (len>=3, non-trivial) ===')
    seen = []
    for m, xs in shared:
        if any(set(m) <= set(bigger) and m != bigger for bigger, _ in seen):
            continue  # skip sub-motifs already covered by a longer shared one
        seen.append((m, xs))
        print(f'  [{" ".join(g(x) for x in m)}]  ->  {", ".join(sorted(xs))}')
    if not seen:
        print('  (none)')


if __name__ == '__main__':
    main()
