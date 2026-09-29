"""Corpus survey: is a melody structured by REPETITION even when it has no seams?

melody_structure.py finds seams — places the melody stops. But JoJo "Too Little Too
Late" has no seam in its chorus and is one of the most structured melodies in the
library: a figure dropped in repeatedly. A gap detector calls that "no structure",
which is wrong. This cross-tabs the two mechanisms across the corpus.

The motif engine is melody_motifs.find_motifs — maximal recurring n-grams, so a
6-note hook is not also reported as its 3-, 4- and 5-note prefixes. Match lens is
selectable: sd (octave-invariant), sd_oct (register-preserving), interval
(transposition-invariant).

    themap_venv/python melody_motif_survey.py
    themap_venv/python melody_motif_survey.py --mode interval
    themap_venv/python melody_motif_survey.py --song "too little"
"""
import os, re, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_motifs import find_motifs
from melody_structure import seams

DEG = {'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
COVER = 0.25          # a motif must own this much of the section to count as structure

def tokens(notes, mode):
    """The note sequence in the chosen match lens."""
    out = []
    for n in notes:
        m = re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
        if not m: continue
        d = DEG[m.group(1)]; o = n.get('octave', 0)
        out.append(d if mode == 'sd' else (d, o) if mode == 'sd_oct' else d + 7*o)
    if mode == 'interval':
        out = [b - a for a, b in zip(out, out[1:])]
    return out

def sections_of(d, nb):
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    for sec, s0, s1 in corpus.sections(d):
        end = min(s1, (d.get('endBeat') or 10**9))
        nbars = int((end - s0) // nb)
        inn = [n for n in notes if s0 <= n['beat'] < end]
        if len(inn) >= 8 and nbars >= 4:
            yield sec, s0, nbars, inn

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='sd', choices=['sd','sd_oct','interval'])
    ap.add_argument('--song')
    ap.add_argument('--trivial', action='store_true',
                    help="count one-note motifs (4-4-4-4) as structure; off by default")
    a = ap.parse_args()

    klen = collections.Counter(); cover = []; cross = collections.Counter()
    reps = collections.Counter(); tot = 0; withany = 0
    for name, d, nb in corpus.songs(need_chords=False):
        if a.song and a.song.lower() not in name.lower(): continue
        for sec, s0, nbars, inn in sections_of(d, nb):
            seq = tokens(inn, a.mode)
            if len(seq) < 8: continue
            tot += 1
            ms = find_motifs(seq, min_len=3, max_len=16, min_count=2)
            if not a.trivial:
                ms = [m for m in ms if len(set(m['motif'])) > 1]
            has_seam = bool(seams([n['beat']-s0 for n in inn], nb, nbars, nb/2))
            best = max(ms, key=lambda m: len(m['motif'])*m['count'], default=None)
            covered = (len(best['motif'])*best['count'])/len(seq) if best else 0.0
            has_motif = covered >= COVER
            if best:
                withany += 1
                klen[min(len(best['motif']), 16)] += 1
                reps[best['count']] += 1; cover.append(covered)
            cross[('motif' if has_motif else 'no motif',
                   'seam' if has_seam else 'no seam')] += 1
            if a.song and best:
                print(f"  {name[:32]:32} {sec[:12]:12} {len(seq):3} notes  "
                      f"motif len {len(best['motif'])} x{best['count']} "
                      f"covers {100*covered:3.0f}%  {'seam' if has_seam else 'NO seam'}")
    if a.song: return
    print(f"{tot} sections, lens = {a.mode}\n")
    print("  longest maximal recurring figure, in notes")
    t = sum(klen.values()) or 1
    for k in sorted(klen, reverse=True):
        print(f"   {k:2}  {klen[k]:6} {100*klen[k]/t:5.1f}%  {'#'*int(38*klen[k]/t)}")
    print(f"\n  sections with ANY recurring figure: {withany} of {tot} ({100*withany/tot:.1f}%)")
    if cover:
        cover.sort(); print(f"  median share of the section covered: {100*cover[len(cover)//2]:.0f}%")
    print(f"\n  cross-tab (motif = a figure covering >= {int(100*COVER)}%)")
    print(f"   {'':10}{'seam':>10}{'no seam':>10}")
    for mk in ('motif','no motif'):
        print(f"   {mk:10}" + ''.join(f"{100*cross[(mk,sk)]/tot:9.1f}%" for sk in ('seam','no seam')))

if __name__ == '__main__':
    main()
