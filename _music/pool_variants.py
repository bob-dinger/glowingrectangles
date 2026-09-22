#!/usr/bin/env python3
"""A second metric version of every song in G50-G250.

Not error-correction (see music_doubling_variants): the point is to SEE each
song at the other metric level. A song whose chords land every half bar reads
differently when each chord owns a bar, and vice versa.

Which direction:
  modal chord < 1 bar  -> DOUBLE, which brings the typical chord to one bar
  modal chord > 1 bar  -> HALVE, same target
  modal chord = 1 bar  -> already ideal, so pick by tempo: slow songs double
                          (240bpm is uncountable), fast songs halve.

The new tempo is flagged when it leaves 60-190, where a pulse stops being
something you can feel.
"""
import json, re, sys, os, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

WANT = ['G50','G100','G150','G200','G250']
def norm(s):
    s=s.lower(); s=re.sub(r"[''`]",'',s); s=re.sub(r'\band\b','',s)
    return re.sub(r'[^a-z0-9]+','',s)
def debase(x):
    prev=None
    while prev!=x:
        prev=x; x=re.sub(r'-[0-9a-f]{6}$','',x); x=re.sub(r'_(o|c|ly|j|s|m|r|x)$','',x)
    return x

pool = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'pool_map.json')))
P={}
for slug,g in pool.items():
    if g in WANT: P.setdefault(norm(debase(slug)), g)

rows=[]
for name, d, nb in corpus.songs():
    g = P.get(norm(debase(name)))
    if not g: continue
    runs=[]
    for _, st, en in corpus.sections(d):
        runs += [dur/nb for _,_,dur in corpus.merged([c for c in d['chords'] if st<=c['beat']<en])]
    if not runs: continue
    hist = collections.Counter(round(r*4)/4 for r in runs)
    mode, nmode = hist.most_common(1)[0]
    t = (d.get('tempos') or [{}])[0].get('bpm')
    bpm = round(t) if t else None
    if mode < 1:    action = 'double'
    elif mode > 1:  action = 'halve'
    else:           action = 'double' if (bpm or 120) < 110 else 'halve'
    new = (bpm*2 if action=='double' else bpm//2) if bpm else None
    newmode = mode*2 if action=='double' else mode/2
    flag = '' if (new and 60 <= new <= 190) else 'check'
    artist,_,title = name.partition('_')
    rows.append([g, artist.title(), title.title(), bpm, mode, action, new,
                 newmode, f"{title}-{new}" if new else '', flag, name])

rows.sort(key=lambda r: (WANT.index(r[0]), r[1], r[2]))
hdr = ("pool\tartist\tsong\tbpm\tchord_bars\taction\tnew_bpm\tnew_chord_bars\t"
       "variant_name\tflag\thookpad_file")
out = hdr + "\n" + "\n".join("\t".join('' if x is None else str(x) for x in r) for r in rows)
subprocess.run(['pbcopy'], input=out.encode())
c = collections.Counter(r[5] for r in rows)
print(f"  {len(rows)} songs  ({c['double']} double, {c['halve']} halve)")
print(f"  {sum(1 for r in rows if r[9]=='check')} land outside 60-190 and are flagged")
for g in WANT:
    print(f"    {g:<6}{sum(1 for r in rows if r[0]==g):>4}")
print(f"\n  {len(rows)} rows + header, tab-separated, on your clipboard")
