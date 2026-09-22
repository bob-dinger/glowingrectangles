#!/usr/bin/env python3
"""For every section: the note it sits on, the note it lands on, and the chord
under that landing.

The user, on melody: "I'm mostly interested in which note is used the most and
which note the melody lands on (and which chord as well)."

Home note is by TIME, not note count -- a melody that touches 7 once and holds
1 for two bars sits on 1. The landing is the last sounding note of the section,
and the chord is whichever is still ringing under it.

Degrees are as stored, so they inherit the relative-major convention: a minor
song written on C-major white notes reports its tonic as 6. That is the
tonal-centre ambiguity, unresolved here on purpose.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

rows = []
for name, d, nb in corpus.songs():
    notes = [n for n in (d.get('notes') or []) if not n.get('isRest')]
    if not notes: continue
    for sec, st, en in corpus.sections(d):
        ns = sorted([n for n in notes if st <= n['beat'] < en], key=lambda n: n['beat'])
        if len(ns) < 4: continue
        dur = collections.Counter()
        for n in ns: dur[str(n.get('sd'))] += n['duration']
        home = max(dur, key=dur.get)
        last = ns[-1]
        land = str(last.get('sd'))
        # The last note usually rings past the last chord's written duration,
        # so "the chord containing this beat" finds nothing 42% of the time.
        # The chord still in effect is the last one that STARTED at or before
        # the note.
        under = None
        for c in sorted(d['chords'], key=lambda c: c['beat']):
            if c['beat'] <= last['beat'] + 1e-6:
                under = c
            else:
                break
        ch = (corpus.chord_name(under, corpus.mode_at(d, under['beat']))
              if under else '?')
        rows.append((name, sec, home, land, ch, dur[home]/sum(dur.values())))

print(f"  {len(rows):,} sections from {len({r[0] for r in rows}):,} songs\n")
for lab, idx in (('home note (most time)', 2), ('landing note', 3), ('chord under the landing', 4)):
    c = collections.Counter(r[idx] for r in rows)
    top = ', '.join(f"{k} {v/len(rows):.0%}" for k, v in c.most_common(6))
    print(f"  {lab:<26}{top}")
print()
pair = collections.Counter((r[3], r[4]) for r in rows)
print(f"  {'landing note':<14}{'on chord':<10}{'sections':>9}")
for (n, ch), v in pair.most_common(12):
    print(f"  {n:<14}{ch:<10}{v:>9}")
