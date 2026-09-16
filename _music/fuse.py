"""Fuse UG tab (chords + structure) with MIDI (timing). Align the UG chord
sequence to the MIDI's detected chord-change sequence; matched UG chords inherit
the MIDI change's duration. Output = timed chart: sections with chords+durations.
"""
import os, re, glob, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from parse_ug import parse_tab
from v0_chord_extract import load_midi_beats, PC
from v2_chord_extract import segment
from ug_chart import find_ug

NOTE_PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def ug_pcq(raw):
    m=re.match(r'^([A-G][#b]?)(.*)$', raw)
    if not m or m.group(1) not in NOTE_PC: return None
    rest=m.group(2)
    q='min' if re.match(r'm(?!aj)', rest) else 'maj'
    return NOTE_PC[m.group(1)], q

def ug_sequence(path):
    _, secs = parse_tab(open(path, encoding='utf-8', errors='replace').read())
    seq=[]   # (pcq, raw, section_name)
    for s in secs:
        nm=s.get('name') or '(sec)'
        for kind,pl in s.get('events',[]):
            if kind=='chord_line':
                for cn,_ in pl:
                    pcq=ug_pcq(cn)
                    if pcq and (not seq or seq[-1][1]!=cn): seq.append((pcq,cn,nm))
    return seq

def midi_changes(notes, nbeats):
    pred,_=segment(notes,nbeats,0.5,0.6)
    segs=[]   # (pcq, start_beat, dur)
    for b,p in enumerate(pred):
        if not p: continue
        if segs and segs[-1][0]==p: segs[-1][2]+=1
        else: segs.append([p, b, 1])
    return [((p[0],p[1]), s, d) for p,s,d in segs]

def align(ug, mid, t):
    """global align ug (transposed by t) to mid by (pc,qual). returns matched pairs [(ug_i, mid_j)]."""
    A=[( (p+t)%12, q) for (p,q),_,_ in ug]
    B=[pcq for pcq,_,_ in mid]
    n,m=len(A),len(B); GAP=-1
    D=[[0]*(m+1) for _ in range(n+1)]
    for i in range(1,n+1): D[i][0]=i*GAP
    for j in range(1,m+1): D[0][j]=j*GAP
    for i in range(1,n+1):
        for j in range(1,m+1):
            s=2 if A[i-1]==B[j-1] else -1
            D[i][j]=max(D[i-1][j-1]+s, D[i-1][j]+GAP, D[i][j-1]+GAP)
    # backtrack
    pairs=[]; i,j=n,m
    while i>0 and j>0:
        s=2 if A[i-1]==B[j-1] else -1
        if D[i][j]==D[i-1][j-1]+s:
            if A[i-1]==B[j-1]: pairs.append((i-1,j-1))
            i-=1;j-=1
        elif D[i][j]==D[i-1][j]+GAP: i-=1
        else: j-=1
    return D[n][m], pairs[::-1]

def fuse(artist, title):
    p=find_ug(artist,title)
    if not p: return f'{artist} - {title}: no UG'
    ug=ug_sequence(p)
    from ug_chart import UGIDX  # noqa
    mp=None
    for cand in glob.glob(os.path.expanduser('~/Desktop/**/*.mid'),recursive=True):
        pass
    # reuse fill_preview midi finder
    from fill_preview import build_midi_index, find_midi
    global _MIDX
    try: _MIDX
    except NameError: _MIDX=build_midi_index()
    midp=find_midi(artist,title,_MIDX)
    if not midp: return f'{artist} - {title}: no MIDI'
    notes,nbeats=load_midi_beats(midp)
    mid=midi_changes(notes,nbeats)
    best=(-1e9,0,[])
    for t in range(12):
        sc,pairs=align(ug,mid,t)
        if sc>best[0]: best=(sc,t,pairs)
    sc,t,pairs=best
    matched={ui:mid[mj] for ui,mj in pairs}
    out=[f'\n### {artist} - {title}   (transpose +{t}, {len(pairs)}/{len(ug)} UG chords matched to MIDI)']
    cur=None; line=[]
    for i,(pcq,raw,nm) in enumerate(ug):
        if nm!=cur:
            if line: out.append('  '+cur+': '+'  '.join(line)); line=[]
            cur=nm
        if i in matched:
            dur=matched[i][2]
            line.append(f'{raw}({dur})')
        else:
            line.append(f'{raw}(?)')
    if line: out.append('  '+cur+': '+'  '.join(line))
    return '\n'.join(out)

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor(); cur.execute("select artist,title from parcels.songs where not has_chords and has_melody and in_hookpad and artist is not null")
    rows=cur.fetchall(); c.close()
    for tg in ['the cave','september','mrs robinson','celebration']:
        row=next((r for r in rows if tg in (r[1] or '').lower()),None)
        if row: print(fuse(*row))

if __name__=='__main__':
    main()
