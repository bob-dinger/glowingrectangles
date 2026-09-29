"""Are all melodic skeletons the same? Reduce every section and see.

The user: "it's just interesting to me that the bones or skeleton of all these
melodies ends up being very similar."

For each chord in each section, keep the melody tone that held the most TIME —
the same reduction simplify_melody.py calls 'chord'. Then describe it two ways:

    degree    the scale degree itself (1-7) — key-relative
    function  that degree's interval above the CHORD root (root, 3rd, 5th, 7th,
              9th, 11th, 13th) — chord-relative, and the thing the user hears as
              "the V over the I"

If the claim holds, the FUNCTION sequences should be far more concentrated than
chance, because the same handful of relationships would recur everywhere.

    themap_venv/python melody_skeletons.py
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

DEG = {'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
FUNC = {0:'root', 1:'9th', 2:'3rd', 3:'11th', 4:'5th', 5:'13th', 6:'7th'}
ORDER = ['root','3rd','5th','7th','9th','11th','13th']

def degree(n):
    m = re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
    return None if not m else DEG[m.group(1)] + 1

def skeletons():
    """Yield (song, section, [(chord_root, melody_degree, function)])."""
    for name, d, nb in corpus.songs():
        notes = [n for n in (d.get('notes') or []) if not n.get('isRest')]
        if not notes: continue
        ch = corpus.merged(d.get('chords') or [])
        for sec, s0, s1 in corpus.sections(d):
            spans = [(c, b, du) for c, b, du in ch if s0 <= b < s1]
            out = []
            for c, b, du in spans:
                root = c.get('root')
                if not root or c.get('applied'): continue
                held = collections.Counter()
                for n in notes:
                    if b <= n['beat'] < b + du:
                        g = degree(n)
                        if g: held[g] += n['duration']
                if not held: continue
                top = max(held, key=held.get)
                out.append((root, top, FUNC[(top - root) % 7]))
            if len(out) >= 4:
                yield name, sec, out

overall = collections.Counter()
by_chord = collections.defaultdict(collections.Counter)
seqs = collections.Counter(); degseq = collections.Counter()
nsec = 0
for name, sec, sk in skeletons():
    nsec += 1
    for root, deg_, fn in sk:
        overall[fn] += 1
        by_chord[root][fn] += 1
    seqs[tuple(f for _, _, f in sk[:4])] += 1
    degseq[tuple(d_ for _, d_, _ in sk[:4])] += 1

tot = sum(overall.values())
print(f"{nsec} sections, {tot} chord-spans reduced\n")
print("what the held tone IS, relative to the chord under it")
for f in ORDER:
    print(f"  {f:5} {overall[f]:7} {100*overall[f]/tot:5.1f}%  {'#'*int(50*overall[f]/tot)}")

RN = {1:'I',2:'ii',3:'iii',4:'IV',5:'V',6:'vi',7:'vii'}
print("\nby chord (share of that chord's spans)")
print(f"  {'chord':6}" + ''.join(f"{f:>7}" for f in ORDER) + "      n")
for root in sorted(by_chord, key=lambda r: -sum(by_chord[r].values())):
    c = by_chord[root]; t = sum(c.values())
    if t < 200: continue
    print(f"  {RN[root]:6}" + ''.join(f"{100*c[f]/t:6.1f}%" for f in ORDER) + f" {t:7}")

print(f"\nfirst-four-chord skeletons — how concentrated?")
for label, counter in (('by function', seqs), ('by scale degree', degseq)):
    t = sum(counter.values())
    top = counter.most_common(8)
    share = sum(n for _, n in top)
    print(f"\n  {label}: {len(counter)} distinct, top 8 = {100*share/t:.1f}% of {t} sections")
    for seq, n in top:
        print(f"     {'-'.join(str(x) for x in seq):26} {n:5} {100*n/t:5.1f}%")
