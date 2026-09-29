"""The two notes that matter: what lands at bar 4 and bar 8.

The user's model, arrived at over this session: "movement is of course more than 4
quarter notes. there is endless variation. but combine that with the rest note.
and the previous notes can be anything that gets the listener there."

melody_measures.py found the breaks: bar 4 is non-running 55% of the time and bar 8
60%, against ~36% for bars 1/3/5. So an 8-bar melody is movement-movement-movement-
BREAK, twice. This measures only those two break notes:

    degree    the scale degree that lands (key-relative) — the cadence
    function  its interval above the chord under it (chord-relative)
    pair      what bar 4 lands on, and what bar 8 answers with

The longest note in the bar is taken as the landing, and only if it is held at
least --hold beats; bars with nothing sustained are reported as 'running through'.

    themap_venv/python melody_landings.py
"""
import os, re, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

BAR=4; DEG={'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
FUNC={0:'root',1:'9th',2:'3rd',3:'11th',4:'5th',5:'13th',6:'7th'}
def degree(n):
    m=re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
    return None if not m else DEG[m.group(1)]+1

def landing(notes, chords, s0, m, hold):
    """The LANDING in measure m (0-based): the last onset in the bar that is
    actually held — a note of at least `hold` beats, or one followed by a gap of
    at least `hold` before the next onset. That is the note where the motion
    stops, which is what the ear calls the landing; a short pickup at the end of
    the bar is skipped. Falls back to the longest note in the bar."""
    lo, hi = s0+m*BAR, s0+(m+1)*BAR
    inbar=[n for n in notes if lo <= n['beat'] < hi]
    if inbar:
        after=sorted([n['beat'] for n in notes if n['beat'] >= hi])
        held=[]
        for n in inbar:
            nxt=next((b for b in sorted(x['beat'] for x in notes) if b > n['beat']), None)
            gap=(nxt - n['beat']) if nxt is not None else n['duration']
            if n['duration'] >= hold or gap >= hold: held.append(n)
        best = held[-1] if held else max(inbar, key=lambda n: n['duration'])
    else:
        # no onset in the bar: the landing is whatever is still ringing through it
        over=[n for n in notes if n['beat'] < lo < n['beat'] + n['duration']]
        if not over: return None
        best=over[-1]
    if best['duration'] < hold: return None
    g=degree(best)
    live=[(c,b,du) for c,b,du in chords if b <= best['beat'] < b+du]
    if not g or not live: return None
    root=live[-1][0].get('root')
    if not root or live[-1][0].get('applied'): return None
    return g, FUNC[(g-root)%7]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--hold', type=float, default=1.5)
    a=ap.parse_args()
    deg4=collections.Counter(); deg8=collections.Counter()
    fn4=collections.Counter(); fn8=collections.Counter()
    pairs=collections.Counter(); n=0; running=[0,0]
    for name,d,nb in corpus.songs():
        if nb!=BAR: continue
        notes=sorted([x for x in (d.get('notes') or []) if not x.get('isRest')], key=lambda x:x['beat'])
        if len(notes)<8: continue
        ch=corpus.merged(d.get('chords') or [])
        for sec,s0,s1 in corpus.sections(d):
            end=min(s1,(d.get('endBeat') or 10**9))
            if int((end-s0)//BAR) < 8: continue
            n+=1
            L4=landing(notes,ch,s0,3,a.hold); L8=landing(notes,ch,s0,7,a.hold)
            running[0]+= L4 is None; running[1]+= L8 is None
            if L4: deg4[L4[0]]+=1; fn4[L4[1]]+=1
            if L8: deg8[L8[0]]+=1; fn8[L8[1]]+=1
            if L4 and L8: pairs[(L4[0],L8[0])]+=1
    print(f"{n} eight-bar sections   (no sustained landing: bar 4 in {100*running[0]/n:.0f}%, "
          f"bar 8 in {100*running[1]/n:.0f}%)\n")
    print(f"  {'':10}{'bar 4':>16}{'bar 8':>16}")
    print("  scale degree that lands")
    t4,t8=sum(deg4.values()),sum(deg8.values())
    for g in range(1,8):
        print(f"   degree {g}  {100*deg4[g]/t4:9.1f}%     {100*deg8[g]/t8:9.1f}%"
              f"   {'#'*int(30*deg8[g]/t8)}")
    print("\n  function over the chord")
    f4,f8=sum(fn4.values()),sum(fn8.values())
    for k in ('root','3rd','5th','7th','9th','11th','13th'):
        print(f"   {k:8}  {100*fn4[k]/f4:9.1f}%     {100*fn8[k]/f8:9.1f}%")
    pt=sum(pairs.values())
    print(f"\n  most common bar4 -> bar8 landing pairs  ({pt} sections with both)")
    for (x,y),c in pairs.most_common(10):
        print(f"   {x} -> {y}   {c:5} {100*c/pt:5.1f}%{'   (same note)' if x==y else ''}")
    same=sum(c for (x,y),c in pairs.items() if x==y)
    print(f"\n  bar 8 lands on the SAME degree as bar 4: {100*same/pt:.1f}%")

if __name__=='__main__':
    main()
