"""How an EIGHT-measure section groups into phrases — the compositions of 8.

The user's proposed shortlist for an 8-bar section:

    112-112      4-4      2-2-4      2-4-2      4-2-2

An 8-bar section can break at 7 internal bar lines, so there are 2^7 = 128 possible
groupings. This counts which ones the corpus actually uses, so the shortlist can be
checked rather than assumed.

A break is where the user hears one: an inter-onset GAP straddling the bar line
(memory music_melody_conceptual_model — boundaries are gaps, not notated rests).
Reported at two thresholds because the answer moves with it and pretending
otherwise would be false precision:

    half-bar gap (>= 2 beats)   sensitive: finds the inner 1-1-2 seams
    full-bar gap (>= 4 beats)   strict: only a whole bar of air counts

Bars are counted from the NOTATED BARLINE, not the phrase start — see
melody_bar_words.scan for why that matters (32% of sections have a pickup).

    themap_venv/python melody_grouping8.py
    themap_venv/python melody_grouping8.py --shortlist      # score the user's five
    themap_venv/python melody_grouping8.py --group 2-2-4    # who uses one grouping
"""
import os, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of

SHORTLIST = ['1-1-2-1-1-2', '4-4', '2-2-4', '2-4-2', '4-2-2']
NICE = {'1-1-2-1-1-2': '112-112'}

def grouping(ons, thresh, nbars=8, bar=4.0):
    """Segment lengths in bars, e.g. [2,2,4]."""
    cuts = []
    for line in range(1, nbars):
        t = line * bar
        before = [o for o in ons if o < t]
        after = [o for o in ons if o >= t]
        if not before or not after: continue     # an empty side is not a break
        if after[0] - before[-1] >= thresh: cuts.append(line)
    segs, prev = [], 0
    for c in cuts + [nbars]:
        segs.append(c - prev); prev = c
    return segs

def scan():
    """(onsets relative to b0, song, section) per eight-bar role section."""
    out = []
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if not notes: continue
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, d.get('endBeat') or 10**9)
            if int((end-b0)//4) != 8: continue
            inn, st, sp = corpus.section_phrase(notes, b0, end)
            if len(inn) < 6: continue
            used.add(role)
            ons = [n['beat']-b0 for n in inn if b0 <= n['beat'] < b0+32]
            if len(ons) >= 6: out.append((ons, name, sec, role))
    return out

def label(segs): 
    k = '-'.join(map(str, segs))
    return NICE.get(k, k)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=16)
    ap.add_argument('--shortlist', action='store_true')
    ap.add_argument('--group')
    a = ap.parse_args()
    rows = scan()
    tot = len(rows)
    tags = (('half-bar gap (>=2 beats)', 2.0), ('full-bar gap (>=4 beats)', 4.0))
    counts = {t: collections.Counter() for t, _ in tags}
    who = {t: collections.defaultdict(list) for t, _ in tags}
    for ons, name, sec, role in rows:
        for t, th in tags:
            k = '-'.join(map(str, grouping(ons, th)))
            counts[t][k] += 1; who[t][k].append((name, sec))

    if a.group:
        key = a.group.replace('112-112', '1-1-2-1-1-2')
        for t, _ in tags:
            hit = who[t][key]
            print(f"\n  {key} at {t}: {len(hit)} sections")
            for name, sec in hit[:20]: print(f"      {name[:38]:38} {sec[:14]}")
        return

    print(f"\n  {tot:,} eight-bar role sections, bars counted from the notated barline\n")
    for t, _ in tags:
        c = counts[t]
        print(f"  {t} — {len(c)} distinct groupings of 128 possible")
        cum = 0
        for k, n in c.most_common(a.top):
            cum += n
            segs = [int(x) for x in k.split('-')]
            star = ' <- shortlist' if k in SHORTLIST else ''
            print(f"      {label(segs):>12} {n:5} {100*n/tot:5.1f}%  cum {100*cum/tot:5.1f}%{star}")
        print()

    print(f"  the shortlist, scored\n")
    print(f"      {'grouping':>12} {'half-bar':>10} {'full-bar':>10}")
    sh = {t: 0 for t, _ in tags}
    for k in SHORTLIST:
        segs = [int(x) for x in k.split('-')]
        row = []
        for t, _ in tags:
            n = counts[t][k]; sh[t] += n; row.append(f"{100*n/tot:5.1f}%")
        print(f"      {label(segs):>12} {row[0]:>10} {row[1]:>10}")
    print(f"      {'TOTAL':>12} " + ' '.join(f"{100*sh[t]/tot:9.1f}%" for t, _ in tags))
    for t, _ in tags:
        c = counts[t]
        nobreak = 100*c['8']/tot
        print(f"\n  {t}: no break at all ('8') is {nobreak:.1f}%"
              f"; the top 5 cover {100*sum(n for _,n in c.most_common(5))/tot:.1f}%")

if __name__ == '__main__':
    main()
