import json, os, sys, statistics as st
from v2_chord_extract import run
pairs=json.load(open('midi_hookpad_pairs.json'))
names=[k for k in pairs if k.lower().startswith('beatles')]
rows=[]; errs=[]
for nm in names:
    if not os.path.exists(os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{nm}.json')):
        errs.append((nm,'no hookpad json')); continue
    try:
        root,qual,meta=run(nm,0.5,0.6)
        rows.append((nm,root,qual))
    except Exception as e:
        errs.append((nm,str(e)[:40]))
rows.sort(key=lambda r:r[1])
roots=[r[1] for r in rows]; quals=[r[2] for r in rows]
print(f'ran {len(rows)} / {len(names)} beatles pairs   ({len(errs)} errors)')
print(f'\nROOT accuracy:  mean {st.mean(roots):.0%}  median {st.median(roots):.0%}  min {min(roots):.0%}  max {max(roots):.0%}')
print(f'QUALITY:        mean {st.mean(quals):.0%}  median {st.median(quals):.0%}')
import collections
buckets=collections.Counter()
for r in roots:
    buckets[min(int(r*10)*10,90)]+=1
print('\nroot-accuracy distribution:')
for lo in range(0,100,10):
    n=buckets.get(lo,0); bar='#'*n
    print(f'  {lo:>3}-{lo+9}%: {n:>3} {bar}')
print('\nworst 12:')
for nm,root,qual in rows[:12]: print(f'  {root:>4.0%} {qual:>4.0%}  {nm}')
print('\nbest 8:')
for nm,root,qual in rows[-8:]: print(f'  {root:>4.0%} {qual:>4.0%}  {nm}')
if errs:
    print(f'\nerrors ({len(errs)}):')
    for nm,e in errs[:8]: print(f'  {nm}: {e}')
