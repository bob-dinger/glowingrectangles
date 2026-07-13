"""Calibration tool. Locate every instance of a LITERAL chord (e.g. "D7", "Fm",
"Bb", "Gmaj7") across the Hookpad corpus, with its exact address (song / key /
section / beat) + how we labeled it. Open a few in Hookpad and confirm we're
seeing the same chord — mismatches are parsing bugs.

    themap_venv/python find_chord.py D7
    themap_venv/python find_chord.py Fm --all-keys
"""
import os, re, sys, argparse, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label, MAJ_INT, MODE_INT
TONIC_PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def abs_pc(ch, tpc):
    r=ch['root']; ap=ch.get('applied',0) or 0; bor=ch.get('borrowed')
    if ap: rel=(MAJ_INT[ap]+MAJ_INT[r])%12
    elif isinstance(bor,str) and bor in MODE_INT: rel=MODE_INT[bor][r]
    else: rel=MAJ_INT[r]
    return (tpc+rel)%12

def quality_of(ch, lab):
    t=ch.get('type')
    m=re.match(r'^[b#]*([a-zA-Z])', lab)
    triad='maj' if (m and m.group(1).isupper()) else 'min'
    if 'maj7' in lab: return 'maj7'
    if t==7: return 'dom7' if triad=='maj' else 'min7'
    return triad

def parse_target(s):
    m=re.match(r'^([A-G][#b]?)(.*)$', s)
    if not m or m.group(1) not in TONIC_PC: sys.exit(f'bad chord: {s}')
    pc=TONIC_PC[m.group(1)]; suf=m.group(2).strip()
    q={'':'maj','m':'min','7':'dom7','maj7':'maj7','M7':'maj7','m7':'min7'}.get(suf,'maj')
    return pc, q

def sect(beat, secs):
    cur='?'
    for s in sorted(secs, key=lambda x:x.get('beat',0)):
        if s.get('beat',0)<=beat: cur=s.get('name') or '?'
    return cur

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('chord'); ap.add_argument('--all-keys',action='store_true')
    a=ap.parse_args()
    tpc, tq = parse_target(a.chord)
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor(); cur.execute("select artist,title,hookpad_json from parcels.songs where has_chords and hookpad_json is not null")
    rows=cur.fetchall(); c.close()
    seen=set(); found=[]
    for artist,title,hj in rows:
        key=(hj.get('keys') or [{}])[0]
        if key.get('scale')!='major' and not a.all_keys: continue
        kpc=TONIC_PC.get(key.get('tonic'),0)
        for ch in hj.get('chords') or []:
            r=ch.get('root')
            if not(r and 1<=r<=7): continue
            if abs_pc(ch,kpc)!=tpc: continue
            lab=chord_label(ch, key.get('scale') if key.get('scale') in ('major','minor') else 'major')
            if quality_of(ch,lab)!=tq: continue
            k=(artist,title)
            if k in seen: continue
            seen.add(k)
            found.append((artist,title,key.get('tonic'),sect(ch.get('beat',0),hj.get('sections') or []),ch.get('beat'),lab))
    print(f'{a.chord}: {len(found)} songs' + ('' if a.all_keys else '  (major-key only; --all-keys for all)') + '\n')
    print(f"{'SONG':38} {'key':4} {'section':12} {'beat':>6}  label")
    for artist,title,tn,s,b,lab in found:
        print(f'{(artist+" - "+title)[:37]:38} {tn:4} {s[:12]:12} {b!s:>6}  {lab}')

if __name__=='__main__':
    main()
