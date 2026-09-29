"""Only the sustained notes. Where do they land on the progression, and what are they?

The user: "the melody analysis from a rhythm perspective is incredibly loose.
That's why the sustained notes and where they land on the progression really
matter. all the notes in between are just like flair."

So this drops the flair. A note counts only if it is held at least `--hold` beats
(default 2 = half a bar). For each one:

    function  its interval above the chord sounding at its ONSET
    landing   whether it arrives ON a chord change, or inside a chord's span
    slot      where in the bar it starts, in sixteenths

and then the SEQUENCE of sustained functions per section, which is the honest
version of "the skeleton" — the previous attempt used whichever tone held longest
in each chord span, which on a bar of straight quarters is arbitrary.

    themap_venv/python melody_sustained.py --hold 2
"""
import os, re, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

DEG={'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
FUNC={0:'root',1:'9th',2:'3rd',3:'11th',4:'5th',5:'13th',6:'7th'}
ORDER=['root','3rd','5th','7th','9th','11th','13th']
RN={1:'I',2:'ii',3:'iii',4:'IV',5:'V',6:'vi',7:'vii'}

def degree(n):
    m=re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
    return None if not m else DEG[m.group(1)]+1

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--hold', type=float, default=2.0, help="minimum beats to count as sustained")
    a=ap.parse_args()

    durs=collections.Counter(); kept=tot=0
    overall=collections.Counter(); by_chord=collections.defaultdict(collections.Counter)
    landing=collections.Counter(); slots=collections.Counter()
    seqs=collections.Counter(); nsec=0
    per_section=collections.Counter()

    for name, d, nb in corpus.songs():
        if nb != 4: continue
        notes=[n for n in (d.get('notes') or []) if not n.get('isRest')]
        if not notes: continue
        ch=corpus.merged(d.get('chords') or [])
        onsets={round(b,3) for c,b,du in ch}
        for sec, s0, s1 in corpus.sections(d):
            sk=[]
            for n in notes:
                if not (s0 <= n['beat'] < s1): continue
                tot += 1; durs[min(n['duration'], 8)] += 1
                if n['duration'] < a.hold: continue
                g=degree(n)
                live=[(c,b,du) for c,b,du in ch if b <= n['beat'] < b+du]
                if not g or not live: continue
                c,b,du = live[-1]
                root=c.get('root')
                if not root or c.get('applied'): continue
                kept += 1
                fn=FUNC[(g-root)%7]
                overall[fn]+=1; by_chord[root][fn]+=1
                landing['on the chord change' if round(n['beat'],3) in onsets
                        else 'inside the chord'] += 1
                slots[int(round(((n['beat']-1) % 4)*4))] += 1
                sk.append(fn)
            if len(sk) >= 3:
                nsec += 1; seqs[tuple(sk[:4])] += 1
            per_section[len(sk)] += 1

    print(f"{tot} melody notes, {kept} sustained >= {a.hold:g} beats  ({100*kept/tot:.1f}%)\n")
    print("what a sustained note IS, relative to its chord")
    t=sum(overall.values())
    for f in ORDER:
        print(f"  {f:5} {overall[f]:6} {100*overall[f]/t:5.1f}%  {'#'*int(48*overall[f]/t)}")
    print("\nby chord")
    print(f"  {'chord':6}" + ''.join(f"{f:>7}" for f in ORDER) + "      n")
    for root in sorted(by_chord, key=lambda r:-sum(by_chord[r].values())):
        c=by_chord[root]; n=sum(c.values())
        if n < 100: continue
        print(f"  {RN[root]:6}" + ''.join(f"{100*c[f]/n:6.1f}%" for f in ORDER) + f" {n:7}")
    print("\nwhere a sustained note arrives")
    lt=sum(landing.values())
    for k,v in landing.most_common(): print(f"  {k:22} {v:6} {100*v/lt:5.1f}%")
    print("\n  starting slot in the bar (0 = downbeat)")
    st=sum(slots.values())
    for s in sorted(slots):
        if 100*slots[s]/st >= 1:
            print(f"   {s:2} {100*slots[s]/st:5.1f}%  {'#'*int(46*slots[s]/st)}")
    print(f"\nsustained notes per section: median "
          f"{sorted(per_section.elements())[sum(per_section.values())//2]}")
    st=sum(seqs.values())
    top=seqs.most_common(10)
    print(f"\nfirst four sustained functions: {len(seqs)} distinct, "
          f"top 10 = {100*sum(n for _,n in top)/st:.1f}% of {st} sections")
    for s,n in top:
        print(f"   {'-'.join(s):26} {n:5} {100*n/st:5.1f}%")

if __name__=='__main__':
    main()
