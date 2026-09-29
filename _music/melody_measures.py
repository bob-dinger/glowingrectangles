"""Is a melody "a bar of four quarters, then a rest, repeated"?

The user: "I'm still feeling like a melody consists of a measure of 4 quarter
notes. and then a rest. and repeats of them where they might be useful."

Every measure of every 4/4 section is typed:

    run    4 or more onsets, nothing held 2 beats or longer — the line is moving
    hold   a long note, or no onset at all because one is still ringing
    mixed  several onsets AND something sustained — usually a landing bar
    thin   1-3 onsets, nothing sustained — sparse, neither running nor holding

Then: how common each type is, which types follow which (the bigram), how often a
run bar is LITERALLY four quarters, and the most common 8-measure type strings.

    themap_venv/python melody_measures.py
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

BAR = 4
HOLD = 2.0          # beats: a note this long stops the motion

def type_of(inbar, held_over):
    if not inbar:
        return 'hold' if held_over else 'empty'
    longest = max(n['duration'] for n in inbar)
    if longest >= HOLD:
        return 'hold' if len(inbar) <= 2 else 'mixed'
    return 'run' if len(inbar) >= 4 else 'thin'

def is_four_quarters(inbar):
    return (len(inbar) == 4 and all(abs(n['duration'] - 1) < 1e-6 for n in inbar)
            and all(abs(n['beat'] - round(n['beat'])) < 1e-6 for n in inbar))

types = collections.Counter(); bigram = collections.Counter()
strings = collections.Counter(); quarters = [0, 0]
nsec = 0
for name, d, nb in corpus.songs(need_chords=False):
    if nb != BAR: continue
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    if len(notes) < 8: continue
    for sec, s0, s1 in corpus.sections(d):
        end = min(s1, (d.get('endBeat') or 10**9))
        nbars = int((end - s0) // BAR)
        if nbars < 4: continue
        seq = []
        for m in range(nbars):
            lo, hi = s0 + m*BAR, s0 + (m+1)*BAR
            inbar = [n for n in notes if lo <= n['beat'] < hi]
            held_over = any(n['beat'] < lo < n['beat'] + n['duration'] for n in notes)
            t = type_of(inbar, held_over)
            seq.append(t)
            if t == 'run':
                quarters[is_four_quarters(inbar)] += 1
        seq = [t for t in seq if t != 'empty']
        if len(seq) < 4: continue
        nsec += 1
        for t in seq: types[t] += 1
        for a, b in zip(seq, seq[1:]): bigram[(a, b)] += 1
        strings[''.join(t[0].upper() for t in seq[:8])] += 1

tot = sum(types.values())
print(f"{nsec} sections, {tot} measures typed\n")
for t, n in types.most_common():
    print(f"  {t:6} {n:7} {100*n/tot:5.1f}%  {'#'*int(48*n/tot)}")
print(f"\n  a run bar is LITERALLY four quarter notes: {quarters[1]} of "
      f"{sum(quarters)}  ({100*quarters[1]/sum(quarters):.1f}%)")

print("\nwhat follows what (row = this bar, column = next bar)")
kinds = ['run','hold','mixed','thin']
print(f"  {'':7}" + ''.join(f"{k:>8}" for k in kinds))
for a in kinds:
    row = sum(bigram[(a,b)] for b in kinds) or 1
    print(f"  {a:7}" + ''.join(f"{100*bigram[(a,b)]/row:7.1f}%" for b in kinds))

st = sum(strings.values())
print(f"\nmost common measure-type strings (R run, H hold, M mixed, T thin)")
for s, n in strings.most_common(14):
    print(f"   {s:10} {n:5} {100*n/st:5.1f}%")
alt = sum(n for s, n in strings.items() if s[:4] in ('RHRH','HRHR'))
print(f"\n  sections whose first four bars alternate run/hold: {alt} ({100*alt/st:.1f}%)")
