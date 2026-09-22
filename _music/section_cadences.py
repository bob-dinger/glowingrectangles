#!/usr/bin/env python3
"""The chord move at a section SEAM — last chord of one part into the first of
the next — counted only across the parts that carry the song.

The user: "only count verse -> chorus, chorus -> verse, and each of those to
bridge and back. I'm not as interested in outros and intros and solos. we do
need pre-chorus's however."

So intro / outro / solo / interlude / instrumental are dropped, and a seam only
counts when BOTH sides are one of verse, pre-chorus, chorus, bridge. Dropping a
section does not join its neighbours: verse -> solo -> chorus is not a
verse -> chorus seam.
"""
import sys, os, re, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

NAME = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'Bdim'}
KEEP = ['pre-chorus', 'chorus', 'verse', 'bridge']      # pre- before chorus: it contains "chorus"

def role(s):
    s = s.lower().strip()
    s = re.sub(r'\b(i{1,3}|iv|v|\d+|first|second|third|final|last|half|alt)\b', '', s)
    s = s.replace('prechorus', 'pre-chorus').replace('pre chorus', 'pre-chorus')
    for k in KEEP:
        if k in s:
            return k
    return None

seam = collections.Counter()       # (from_role,to_role) -> n
move = collections.Counter()       # (from_chord,to_chord) -> n
pair = collections.Counter()       # (roles, chords)
for name, d, nb in corpus.songs():
    secs = list(corpus.sections(d))
    runs_by = []
    for s, st, en in secs:
        r = corpus.merged([c for c in d['chords'] if st <= c['beat'] < en])
        runs_by.append((role(s), r))
    for (r1, a), (r2, b) in zip(runs_by, runs_by[1:]):
        if not r1 or not r2 or not a or not b:
            continue
        c1, c2 = a[-1][0], b[0][0]
        lab = lambda c: (NAME.get(c.get('root'), '?') +
                         ('*' if (c.get('borrowed') or c.get('applied')) else ''))
        seam[(r1, r2)] += 1
        move[(lab(c1), lab(c2))] += 1
        pair[((r1, r2), (lab(c1), lab(c2)))] += 1

print(f"  {sum(seam.values()):,} seams between verse / pre-chorus / chorus / bridge\n")
print(f"  {'seam':<28}{'n':>6}   commonest chord move")
for (r1, r2), n in seam.most_common():
    top = collections.Counter({cc: v for (rr, cc), v in pair.items() if rr == (r1, r2)})
    t = top.most_common(3)
    s = ", ".join(f"{a}->{b} {v}" for (a, b), v in t)
    print(f"  {r1+' -> '+r2:<28}{n:>6}   {s}")
print(f"\n  the chord move at a seam, all seams pooled:")
tot = sum(move.values())
for i, ((a, b), v) in enumerate(move.most_common(14), 1):
    end = '\n' if i % 2 == 0 else '    '
    print(f"  {i:>2}. {a}->{b:<5}{v:>5} {v/tot:>5.1%}", end=end)
rows = ["from_section\tto_section\tfrom_chord\tto_chord\tn"]
for ((r1, r2), (a, b)), v in pair.most_common():
    rows.append(f"{r1}\t{r2}\t{a}\t{b}\t{v}")
subprocess.run(['pbcopy'], input="\n".join(rows).encode())
print(f"\n  {len(rows)-1} rows on your clipboard")
