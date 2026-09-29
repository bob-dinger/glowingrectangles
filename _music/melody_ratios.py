"""Is there a ratio? Melody note-density per bar, across every 4-bar phrase.

The user: "many seem to have something like 4 quarter notes per measure for 3
measures, then a long full measure note... there HAS to be some math ratio of
good melodies per chord."

This counts melody ONSETS per bar in 4-bar windows tiled from each section start,
in WHATEVER meter the song is in (the two songs that prompted this, Seashores of
Old Mexico and Norwegian Wood, are both in 3), and tests the claim four ways:

  profile   the raw tuple, e.g. (4,4,4,1)
  shape     each bar marked against the phrase mean: H high, m mid, l low
  where the phrase's LONGEST note sits, and how long it is
  gap       the silence after the phrase's last onset — the felt "hold" is often
            a short note plus space, not a long note (phrase boundaries are
            inter-onset gaps, per memory music_melody_conceptual_model)

    themap_venv/python melody_ratios.py
    themap_venv/python melody_ratios.py --song "norwegian wood"
"""
import os, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

def phrases(d, bar):
    """Yield (section, bar0, [onsets/bar], [longest/bar], end_gap). `bar` = beats
    per measure for this song, so 3- and 6-beat songs are included."""
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    if not notes: return
    onsets = [n['beat'] for n in notes]
    for name, s0, s1 in corpus.sections(d):
        end = min(s1, (d.get('endBeat') or 10**9))
        nbars = int((end - s0) // bar)
        for w in range(nbars // 4):
            b0 = s0 + w*4*bar
            counts, longest, last = [], [], None
            for m in range(4):
                lo, hi = b0 + m*bar, b0 + (m+1)*bar
                inbar = [n for n in notes if lo <= n['beat'] < hi]
                counts.append(len(inbar))
                longest.append(max((n['duration'] for n in inbar), default=0))
                if inbar: last = inbar[-1]
            if sum(counts) < 4: continue
            nxt = next((o for o in onsets if o > last['beat']), None)
            gap = (nxt - last['beat']) if nxt else last['duration']
            yield name, b0, counts, longest, gap

def shape(counts):
    """Each bar against the phrase mean: H above, l below, m within 25%."""
    avg = sum(counts)/4 or 1
    out = ''
    for c in counts:
        out += 'H' if c > avg*1.25 else ('l' if c < avg*0.75 else 'm')
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--song')
    ap.add_argument('--top', type=int, default=14)
    a = ap.parse_args()

    if a.song:
        for name, d, nb in corpus.songs(need_chords=False):
            if a.song.lower() not in name.lower(): continue
            print(f"\n{name}")
            print(f"  ({nb} beats to the bar)")
            for sec, b0, counts, longest, gap in phrases(d, nb):
                print(f"   bar {int((b0-1)//nb)+1:4}  {sec[:20]:20} "
                      f"{'-'.join(str(c) for c in counts):12} {shape(counts)}  "
                      f"longest {max(longest):4g} in bar {longest.index(max(longest))+1}"
                      f"   last onset held+silent {gap:g} beats ({gap/nb:.2f} bars)")
        return

    prof = collections.Counter(); shp = collections.Counter()
    last_fewest = tail_long = big_gap = total = 0
    hold_bar = collections.Counter()
    for name, d, nb in corpus.songs(need_chords=False):
        for sec, b0, counts, longest, gap in phrases(d, nb):
            total += 1
            prof[tuple(counts)] += 1
            shp[shape(counts)] += 1
            if counts[3] == min(counts) and counts[3] < max(counts): last_fewest += 1
            if max(longest) >= nb: tail_long += 1
            if gap >= nb: big_gap += 1
            hold_bar[longest.index(max(longest)) + 1] += 1

    print(f"{total} four-bar melodic phrases\n")
    print("most common onsets-per-bar profiles")
    for p, n in prof.most_common(a.top):
        print(f"  {'-'.join(str(x) for x in p):14} {n:5}  {100*n/total:4.1f}%")
    print("\nmost common shapes (H above phrase mean, m within 25%, l below)")
    for p, n in shp.most_common(10):
        print(f"  {p:6} {n:5}  {100*n/total:4.1f}%")
    print(f"\nbar 4 has the fewest onsets:        {last_fewest:5}  {100*last_fewest/total:4.1f}%")
    print(f"phrase contains a note >= a bar long: {tail_long:5}  {100*tail_long/total:4.1f}%")
    print(f"last onset gets >= a bar of space:    {big_gap:5}  {100*big_gap/total:4.1f}%")
    print("\nwhich bar holds the phrase's longest note")
    for b in (1,2,3,4):
        print(f"  bar {b}  {hold_bar[b]:5}  {100*hold_bar[b]/total:4.1f}%")

if __name__ == '__main__':
    main()
