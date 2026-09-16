import json, os, glob, statistics as st, collections
from v0_chord_extract import load_midi_beats, ground_truth
from v2_chord_extract import segment
from v1_chord_extract import align_score
pairs=json.load(open('midi_hookpad_pairs.json'))
names=[k for k in pairs if k.lower().startswith('beatles')]
rows=[]; cat=collections.Counter()
for nm in names:
    jp=os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{nm}.json')
    if not os.path.exists(jp): cat['no-json']+=1; continue
    hk=json.load(open(jp))
    gt=ground_truth(hk)
    if sum(1 for g in gt if g) < 8: cat['no-chords (chordless entry)']+=1; continue
    try:
        mp=next(glob.iglob(os.path.expanduser('~/Desktop/**/'+pairs[nm]),recursive=True))
        notes,nb=load_midi_beats(mp)
    except Exception: cat['bad-midi (unparseable)']+=1; continue
    if nb<8 or len(notes)<30: cat['empty/melody-only midi']+=1; continue
    pred,_=segment(notes,nb,0.5,0.6)
    h,t,tr,off=align_score(pred,gt)
    if t==0: cat['no-overlap']+=1; continue
    qh=qt=0
    for b in range(len(gt)):
        pb=b+off
        if gt[b] and 0<=pb<len(pred) and pred[pb] and (pred[pb][0]+tr)%12==gt[b][0]:
            qt+=1; qh+=(pred[pb][1]==gt[b][1])
    rows.append((nm,h/t,qh/max(qt,1)))
rows.sort(key=lambda r:r[1])
roots=[r[1] for r in rows]
print(f'VALID scored pairs: {len(rows)} / {len(names)}')
print('excluded:', dict(cat))
print(f'\nROOT: mean {st.mean(roots):.0%}  median {st.median(roots):.0%}')
print(f'QUAL: mean {st.mean([r[2] for r in rows]):.0%}')
b=collections.Counter(min(int(r*10)*10,90) for r in roots)
print('\ndistribution:')
for lo in range(20,100,10): print(f'  {lo:>2}-{lo+9}%: {b.get(lo,0):>2} {"#"*b.get(lo,0)}')
print('\nworst 8:'); [print(f'  {r:.0%} {q:.0%} {n}') for n,r,q in rows[:8]]
print('best 6:'); [print(f'  {r:.0%} {q:.0%} {n}') for n,r,q in rows[-6:]]
