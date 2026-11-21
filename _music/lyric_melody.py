"""The 304 sections where syllable count EXACTLY equals note count.

Those are the only sections where the alignment is unambiguous: syllable i is note
i. That lets us ask the question the rest of the corpus cannot answer — what does a
melody DO at the words that matter? Specifically at a rhyme, which in the user's
model is the anchor of a phrase ("melody = rhythm + rhymes").

Measured per line: how long it is, what its last syllable lands on, and whether a
rhyme-marked syllable is treated differently from an ordinary one.

    themap_venv/python lyric_melody.py
    themap_venv/python lyric_melody.py --song yesterday
"""
import os, re, sys, argparse, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from parse_lyrics import parse_song, syllables_in

DEG = {'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
FUNC = {0:'root',1:'9th',2:'3rd',3:'11th',4:'5th',5:'13th',6:'7th'}

def degree(n):
    m = re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
    return None if not m else DEG[m.group(1)] + 1

def aligned(d, nb):
    """Yield (section, [(syllable, note, is_rhyme, is_line_end, is_melisma)]) for
    sections whose syllable count exactly matches their note count."""
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    rows, _ = parse_song(d)
    secs = list(corpus.sections(d))
    for r in rows:
        if r['index'] is None or r['index'] >= len(secs): continue
        _, b0, b1 = secs[r['index']]
        inn = [n for n in notes if b0 <= n['beat'] < b1]
        # expand each token to the number of notes it takes, keeping its flags
        toks = []
        for l in r['lines']:
            for i, t in enumerate(l['syllables']):
                k = syllables_in(t)
                for j in range(k):
                    toks.append((t, l['rhyme'] is not None and i == (l['rhyme_at'] or -1),
                                 i == len(l['syllables'])-1 and j == k-1,
                                 i in (l.get('melisma') or [])))
        if len(toks) != len(inn) or not inn: continue
        yield r, b0, list(zip(toks, inn))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--song'); a = ap.parse_args()
    nsec = 0; linelen = collections.Counter(); patterns = collections.Counter()
    dur = {'rhyme': [], 'line-end': [], 'plain': []}
    slot = {'rhyme': collections.Counter(), 'line-end': collections.Counter(),
            'plain': collections.Counter()}
    deg = {'rhyme': collections.Counter(), 'line-end': collections.Counter(),
           'plain': collections.Counter()}
    fn = {'rhyme': collections.Counter(), 'line-end': collections.Counter()}
    for name, d, nb in corpus.songs():
        if a.song and a.song.lower() not in name.lower(): continue
        ch = corpus.merged(d.get('chords') or [])
        for r, b0, pairs in aligned(d, nb):
            if nb != 4: continue
            nsec += 1
            lens = [sum(syllables_in(t) for t in l['syllables']) for l in r['lines']]
            for x in lens: linelen[x] += 1
            patterns['-'.join(str(x) for x in lens)] += 1
            if a.song:
                print(f"  {name[:26]:26} {r['name'][:12]:12} lines {lens}  scheme {r['scheme']}")
            for (tok, is_r, is_end, is_m), n in pairs:
                kind = 'rhyme' if is_r else ('line-end' if is_end else 'plain')
                dur[kind].append(n['duration'])
                slot[kind][int(round(((n['beat']-b0) % 4)*4))] += 1
                g = degree(n)
                if g: deg[kind][g] += 1
                if kind in fn:
                    live = [c for c, b, du in ch if b <= n['beat'] < b+du]
                    if live and live[-1].get('root') and not live[-1].get('applied'):
                        fn[kind][FUNC[(g - live[-1]['root']) % 7]] += 1
    if a.song: return
    print(f"{nsec} exactly-aligned sections in 4/4, syllable i = note i\n")
    print("  syllables per line")
    t = sum(linelen.values())
    for k in sorted(linelen):
        if 100*linelen[k]/t >= 2:
            print(f"   {k:3} {100*linelen[k]/t:5.1f}%  {'#'*int(44*linelen[k]/t)}")
    print(f"\n  most common line-length patterns")
    pt = sum(patterns.values())
    for p, c in patterns.most_common(10):
        print(f"   {p:24} {c:4} {100*c/pt:5.1f}%")
    print(f"\n  what the note under a syllable looks like")
    print(f"   {'':10}{'n':>7}{'mean dur':>10}{'on beat 1':>11}{'lands on 1':>12}")
    for k in ('rhyme', 'line-end', 'plain'):
        if not dur[k]: continue
        s = sum(slot[k].values()); dt = sum(deg[k].values()) or 1
        print(f"   {k:10}{len(dur[k]):7}{statistics.mean(dur[k]):10.2f}"
              f"{100*slot[k][0]/s:10.1f}%{100*deg[k][1]/dt:11.1f}%")
    print(f"\n  function over the chord, at a rhyme vs at a line end")
    order = ['root','3rd','5th','7th','9th','11th','13th']
    print(f"   {'':10}" + ''.join(f"{x:>7}" for x in order))
    for k in ('rhyme', 'line-end'):
        tt = sum(fn[k].values()) or 1
        print(f"   {k:10}" + ''.join(f"{100*fn[k][x]/tt:6.1f}%" for x in order))

if __name__ == '__main__':
    main()
