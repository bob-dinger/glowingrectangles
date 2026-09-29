"""How a 4-measure melody is grouped: 112, 211, 22, 4-along.

The user: "song melody starts at 4 measures... there is 112 and 211 in melody.
there is 4 along (no structure). lots of it."

A 4-bar window can break at the 3 internal bar lines, so there are 8 possible
groupings — the compositions of 4:

    1111  112  121  211  22  13  31  4

A break is found the way the user hears one: an inter-onset GAP straddling the
bar line (memory music_melody_conceptual_model — boundaries are gaps, not
notated rests). The threshold is reported at two settings because the answer
moves with it, and pretending otherwise would be false precision.

Also reports where notes land inside the bar, on the 16-slot sixteenth grid that
melody_rhythm.py measured.

    themap_venv/python melody_structure.py
    themap_venv/python melody_structure.py --scales     # which bar-scale the seams live at
    themap_venv/python melody_structure.py --song "norwegian wood"
"""
import os, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

def windows(d, bar):
    """Yield (section, bar0, [onset beats relative to window]) for each 4-bar window."""
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    if not notes: return
    for name, s0, s1 in corpus.sections(d):
        end = min(s1, (d.get('endBeat') or 10**9))
        for w in range(int((end - s0) // bar) // 4):
            b0 = s0 + w*4*bar
            ons = [n['beat'] - b0 for n in notes if b0 <= n['beat'] < b0 + 4*bar]
            if len(ons) >= 4:
                yield name, b0, ons

def grouping(ons, bar, thresh):
    """Segment lengths in bars, e.g. [1,1,2]. A bar line breaks if the gap
    straddling it is >= thresh beats."""
    cuts = []
    for line in (1, 2, 3):
        t = line * bar
        before = [o for o in ons if o < t]
        after = [o for o in ons if o >= t]
        if not before or not after:
            continue                      # an empty side is not evidence of a break
        if after[0] - before[-1] >= thresh:
            cuts.append(line)
    segs, prev = [], 0
    for c in cuts + [4]:
        segs.append(c - prev); prev = c
    return segs

def seams(ons, bar, nbars, thresh):
    """Bar lines (1..nbars-1) where an inter-onset gap straddles the line."""
    out = []
    for line in range(1, nbars):
        t = line*bar
        before = [o for o in ons if o < t]
        after = [o for o in ons if o >= t]
        if not before or not after: continue
        if after[0] - before[-1] >= thresh: out.append(line)
    return out

def scales():
    """Which bar-scale do the seams actually fall on? A 4-bar window cannot see an
    8-bar phrase, so measuring only at 4 mis-segments every half-speed melody."""
    hit = collections.Counter(); per = collections.Counter()
    lens = collections.Counter(); tot = 0
    for name, d, nb in corpus.songs(need_chords=False):
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if len(notes) < 8: continue
        for sec, s0, s1 in corpus.sections(d):
            end = min(s1, (d.get('endBeat') or 10**9))
            nbars = int((end - s0) // nb)
            if nbars < 4: continue
            ons = [n['beat'] - s0 for n in notes if s0 <= n['beat'] < s0 + nbars*nb]
            if len(ons) < 4: continue
            sm = seams(ons, nb, nbars, nb/2)
            if not sm: continue
            tot += 1
            ok = [P for P in (1, 2, 4, 8, 16) if all(x % P == 0 for x in sm)]
            for P in ok: hit[P] += 1
            per[max(ok or [1])] += 1
            segs, prev = [], 0
            for c in sm + [nbars]:
                segs.append(c - prev); prev = c
            lens[tuple(segs)] += 1
    print(f"{tot} sections with at least one seam\n")
    print("  every seam falls on a multiple of...")
    for P in (1, 2, 4, 8, 16):
        print(f"   {P:2} bars  {100*hit[P]/tot:5.1f}%  {'#'*int(46*hit[P]/tot)}")
    print("\n  largest scale every seam agrees with (= the phrase scale)")
    for P in (1, 2, 4, 8, 16):
        print(f"   {P:2} bars  {100*per[P]/tot:5.1f}%  {'#'*int(46*per[P]/tot)}")
    print("\n  most common full segmentations (segment lengths in bars)")
    for seg, n in lens.most_common(12):
        print(f"   {'-'.join(str(x) for x in seg):24} {n:5} {100*n/tot:5.1f}%")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--song')
    ap.add_argument('--scales', action='store_true',
                    help="which bar-scale the seams live at, across the corpus")
    a = ap.parse_args()
    if a.scales: return scales()

    if a.song:
        for name, d, nb in corpus.songs(need_chords=False):
            if a.song.lower() not in name.lower(): continue
            print(f"\n{name}  ({nb} beats to the bar)")
            for sec, b0, ons in windows(d, nb):
                g1 = ''.join(str(x) for x in grouping(ons, nb, nb/2))
                g2 = ''.join(str(x) for x in grouping(ons, nb, nb))
                print(f"   bar {int((b0-1)//nb)+1:4}  {sec[:18]:18} "
                      f"{len(ons):3} notes   half-bar gaps: {g1:5}  full-bar gaps: {g2:5}")
        return

    counts = {0.5: collections.Counter(), 1.0: collections.Counter()}
    slots = collections.Counter(); total = 0
    for name, d, nb in corpus.songs(need_chords=False):
        for sec, b0, ons in windows(d, nb):
            total += 1
            for mult in (0.5, 1.0):
                counts[mult][''.join(str(x) for x in grouping(ons, nb, nb*mult))] += 1
            if nb == 4:                    # the slot grid is 16 sixteenths of a 4/4 bar
                for o in ons:
                    slots[int(round((o % nb) * 4)) % 16] += 1

    print(f"{total} four-bar melodic windows\n")
    print(f"{'grouping':10} {'break = half-bar gap':>22} {'break = full-bar gap':>22}")
    order = ['4','22','13','31','112','211','121','1111']
    for g in order:
        a_, b_ = counts[0.5][g], counts[1.0][g]
        print(f"  {g:8} {a_:8} {100*a_/total:5.1f}%      {b_:8} {100*b_/total:5.1f}%")
    print("\nwhere notes land in the bar — 4/4 songs only (16 sixteenth slots)")
    tot = sum(slots.values())
    for s in sorted(slots):
        bar_ = '#' * int(60*slots[s]/max(slots.values()))
        mark = 'beat' if s % 4 == 0 else ('and' if s % 4 == 2 else '16th')
        print(f"  {s:2} {mark:5} {100*slots[s]/tot:5.1f}% {bar_}")

if __name__ == '__main__':
    main()
