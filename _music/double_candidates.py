#!/usr/bin/env python3
"""Which songs are notated at the wrong metric level.

double_song.py --candidates looks for fractional SECTION lengths. This looks at
the chord rhythm instead, which is the thing the notation is really about:

  DOUBLE  most chord changes last less than a bar, so the song is written
          "cramped" -- doubling the metric level puts each chord on its own bar.
          (The 16-slot census found most shape matches live at HALF-BAR units,
          which is this, library-wide.)
  HALVE   most chord runs last two bars or more, so the song is written
          "stretched" and halving gives it one chord per bar.

Layer 1 only: re-strikes are merged, so a chord struck twice in a bar counts as
one bar-long run, not two half-bar ones.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

rows = []
for name, d, nb in corpus.songs():
    runs = []
    for nm, st, en in corpus.sections(d):
        runs += [dur / nb for _, _, dur in
                 corpus.merged([c for c in d['chords'] if st <= c['beat'] < en])]
    if len(runs) < 8:
        continue
    # The test is the MODE, not a share. "Most runs are under a bar" catches
    # every song with two chords to the bar, which is the third-commonest
    # pattern in the library and perfectly normal -- it flagged 445 songs.
    # A song is at the wrong metric level when its TYPICAL chord lasts half a
    # bar (write it doubled) or two bars (write it halved).
    hist = collections.Counter(round(r * 4) / 4 for r in runs)   # quarter-bar bins
    mode, n_mode = hist.most_common(1)[0]
    if n_mode / len(runs) < 0.4:          # no clear typical length
        continue
    bpm = (d.get('tempos') or [{}])[0].get('bpm')
    bpm = round(bpm) if bpm else None
    if not bpm: continue
    if mode <= 0.5:
        rows.append(('DOUBLE', n_mode / len(runs), name, bpm, bpm * 2, len(runs)))
    elif mode >= 2:
        rows.append(('HALVE', n_mode / len(runs), name, bpm, bpm // 2, len(runs)))

rows.sort(key=lambda r: (r[0], -r[1]))
c = collections.Counter(r[0] for r in rows)
print(f"  {c['DOUBLE']} doubling candidates, {c['HALVE']} halving candidates\n")
for kind in ('DOUBLE', 'HALVE'):
    sub = [r for r in rows if r[0] == kind]
    print(f"  {kind}  ({len(sub)})   {'share':>6}{'bpm':>6} -> {'new':<6}{'runs':>5}  song")
    for _, share, name, bpm, new, n in sub[:14]:
        print(f"      {'':<12}{share:>6.0%}{bpm:>6} -> {new:<6}{n:>5}  {name}")
    print()
