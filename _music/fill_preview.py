"""Preview auto-filled chords for chordless Hookpad songs (no ground truth).
Finds a MIDI for each, runs the v2 segment extractor, detects the key
(Krumhansl-Schmuckler), and prints the chord chart in letters + roman numerals.
Eyeball test for "is MIDI->chords good enough to fill the ~646 chordless songs?"
"""
import os, re, glob, json, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from v0_chord_extract import load_midi_beats, PC
from v2_chord_extract import segment

MAJ_PROF=[6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88]
MIN_PROF=[6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17]
NOISE={'bought','done','final','master','new','ver','version','midi','mid','midis','the','a','of'}
SECT=re.compile(r'(verse|chorus|bridge|pre-?chorus|intro|outro|solo|riff|hook)',re.I)
NUMSIG=re.compile(r'(^|[_\s])\d{1,2}[_\s]\d{2,4}([_\s]\d{2,4})+|[_\s](x|tempo)([_\s]|$)',re.I)
MAJ_DEG={0:'I',2:'ii',4:'iii',5:'IV',7:'V',9:'vi',11:'vii'}

def toks(s):
    s=re.sub(r'\.(mid|midi)$','',s,flags=re.I); s=re.sub(r'[_\-\s]+',' ',s.lower()); s=re.sub(r"[^a-z0-9 ]",'',s)
    return [t for t in s.split() if t and t not in NOISE and not t.isdigit()]

def build_midi_index():
    idx=[]
    for p in glob.glob(os.path.expanduser('~/Desktop/**/*.mid'),recursive=True):
        nm=os.path.basename(p)
        if '/melodies/' in p or SECT.search(nm) or NUMSIG.search(nm): continue
        t=toks(nm)
        if t: idx.append((p,''.join(t),set(t)))
    return idx

def find_midi(artist,title,idx):
    at=set(toks(artist or '')); asq=''.join(toks(artist or '')); tsq=''.join(toks(title or ''))
    if len(tsq)<4: return None
    cands=[p for p,msq,mtok in idx if tsq in msq and (asq[:5] in msq or (at & mtok))]
    return min(cands,key=len) if cands else None   # shortest name = tightest match

def krumhansl(chroma_total):
    def corr(a,b):
        n=len(a); ma=sum(a)/n; mb=sum(b)/n
        num=sum((a[i]-ma)*(b[i]-mb) for i in range(n))
        da=sum((x-ma)**2 for x in a)**.5; db=sum((x-mb)**2 for x in b)**.5
        return num/(da*db) if da and db else 0
    best=(-9,0,'major')
    for t in range(12):
        rot=[chroma_total[(t+i)%12] for i in range(12)]
        for prof,scale in ((MAJ_PROF,'major'),(MIN_PROF,'minor')):
            r=corr(rot,prof)
            if r>best[0]: best=(r,t,scale)
    return best[1],best[2]   # tonic pc, scale

def roman(root_pc,qual,tonic):
    deg=(root_pc-tonic)%12
    base=MAJ_DEG.get(deg)
    if base is None:                       # chromatic root
        flat={1:'bII',3:'bIII',6:'#IV',8:'bVI',10:'bVII'}.get(deg,'?')
        return flat if qual=='maj' else flat.lower()
    if qual=='min' and base.isupper(): base=base.lower()
    if qual=='maj' and base.islower(): base=base.upper()
    return base

MAJ_INT={1:0,2:2,3:4,4:5,5:7,6:9,7:11}
TONIC_PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
          'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def sd_interval(sd):
    m=re.match(r'([#b]?)(\d)',str(sd))
    if not m: return None
    acc,dig=m.group(1),int(m.group(2))
    if dig not in MAJ_INT: return None
    return (MAJ_INT[dig]+(1 if acc=='#' else -1 if acc=='b' else 0))%12

def hp_melody_hist(notes,tonic_pc):
    h=[0.0]*12
    for n in notes or []:
        if n.get('isRest'): continue
        iv=sd_interval(n.get('sd'))
        if iv is None: continue
        h[(tonic_pc+iv)%12]+=n.get('duration',1)
    return h

def midi_pc_hist(notes):
    h=[0.0]*12
    for pitch,sb,eb in notes: h[pitch%12]+=(eb-sb)
    return h

def best_transpose(midi_h,hp_h):
    """T = shift (semitones) to add to MIDI pcs so they land in the Hookpad key."""
    def corr(a,b):
        n=12; ma=sum(a)/n; mb=sum(b)/n
        num=sum((a[i]-ma)*(b[i]-mb) for i in range(n))
        da=sum((x-ma)**2 for x in a)**.5; db=sum((x-mb)**2 for x in b)**.5
        return num/(da*db) if da and db else -9
    best=(-9,0)
    for T in range(12):
        shifted=[midi_h[(pc-T)%12] for pc in range(12)]
        r=corr(shifted,hp_h)
        if r>best[0]: best=(r,T)
    return best[1],best[0]

def preview(artist,title,hk_keys,hk_notes,idx,lam=0.5,bass_w=0.6):
    mp=find_midi(artist,title,idx)
    if not mp: return f'{artist} - {title}: NO MIDI'
    try:
        notes,nbeats=load_midi_beats(mp)
    except Exception as e:
        return f'{artist} - {title}: midi load err {str(e)[:30]}'
    pred,segs=segment(notes,nbeats,lam,bass_w)
    # --- melody-align: transpose MIDI into the Hookpad key ---
    hp_tonic_pc=TONIC_PC.get((hk_keys[0].get('tonic') if hk_keys else 'C'),0)
    hp_scale=(hk_keys[0].get('scale') if hk_keys else 'major')
    T,conf=best_transpose(midi_pc_hist(notes), hp_melody_hist(hk_notes,hp_tonic_pc))
    merged=[]
    for i,dur,lab in segs:
        if merged and merged[-1][2]==lab: merged[-1][1]+=dur
        else: merged.append([i,dur,lab])
    # relabel every chord in the Hookpad key
    chart=[(PC[(r+T)%12]+('m' if q=='min' else ''), roman((r+T)%12,q,hp_tonic_pc))
           for i,dur,(r,q) in merged if dur>=2][:14]
    hk=', '.join(f"{k.get('tonic')} {k.get('scale')}" for k in (hk_keys or [])) or '?'
    out=[f'\n### {artist} - {title}']
    out.append(f'  MIDI: {os.path.basename(mp)}  | transpose +{T} (align conf {conf:.2f})')
    out.append(f'  Hookpad key: {hk}')
    out.append('  chords: '+' '.join(L for L,_ in chart))
    out.append('  roman : '+' '.join(r for _,r in chart))
    return '\n'.join(out)

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor()
    targets=['do wah diddy','whats my name','rockin pneumonia','hungry heart',
             'riders on the storm','you make my dreams']
    cur.execute("""select artist,title,hookpad_json->'keys',hookpad_json->'notes' from parcels.songs
        where not has_chords and has_melody and in_hookpad and artist is not null""")
    rows=cur.fetchall(); c.close()
    idx=build_midi_index()
    for tg in targets:
        row=next((r for r in rows if tg in (r[1] or '').lower()), None)
        if row: print(preview(row[0],row[1],row[2],row[3],idx))
        else: print(f'\n### {tg}: not found as chordless')

if __name__=='__main__':
    main()
