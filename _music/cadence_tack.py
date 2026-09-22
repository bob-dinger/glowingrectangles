#!/usr/bin/env python3
"""Sections that tack a chord on the end purely to make a cadence.

The user: "the writers just kind of throw a G at the end of the section no
matter what the pattern was before ... in order to create a great cadence."

The signature is a final chord that appears NOWHERE ELSE in its section -- the
part establishes a palette, then lands on something outside it. Merged runs, so
a chord held or re-struck at the end still counts once.
"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

KEEP = ['pre-chorus', 'chorus', 'verse', 'bridge']
def role(s):
    s = s.lower().strip()
    s = re.sub(r'\b(i{1,3}|iv|v|\d+|first|second|third|final|last|half|alt)\b', '', s)
    s = s.replace('prechorus', 'pre-chorus').replace('pre chorus', 'pre-chorus')
    for k in KEEP:
        if k in s: return k
    return None

tack = collections.Counter(); ends = collections.Counter()
ex = collections.defaultdict(list)
n = 0
for name, d, nb in corpus.songs():
    for s, st, en in corpus.sections(d):
        if not role(s): continue
        runs = corpus.merged([c for c in d['chords'] if st <= c['beat'] < en])
        if len(runs) < 4: continue
        seq = [corpus.chord_name(c, corpus.mode_at(d, b)) for c, b, _ in runs]
        last = seq[-1]
        n += 1; ends[last] += 1
        if last not in seq[:-1]:                 # appears only at the end
            tack[last] += 1
            if len(ex[last]) < 4:
                art, _, t = name.partition('_')
                ex[last].append(f"{t.title()[:24]} {s[:8]}: {' '.join(seq[-6:])}")

print(f"  {n:,} sections with 4+ chord changes\n")
print(f"  {'final chord':<12}{'sections':>9}{'of those, tacked on':>21}{'rate':>7}")
for c, v in ends.most_common(8):
    print(f"  {c:<12}{v:>9,}{tack[c]:>21,}{tack[c]/v:>7.0%}")
print(f"\n  overall: {sum(tack.values()):,} of {n:,} sections "
      f"({sum(tack.values())/n:.0%}) end on a chord used nowhere else in the part\n")
for c in ('G', 'C', 'F'):
    print(f"  --- tacked-on {c}:")
    for e in ex[c]: print(f"      {e}")
