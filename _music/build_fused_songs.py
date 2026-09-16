"""End-to-end: wipe-and-rebuild a chordless Hookpad song from MIDI + UG.
  melody  <- MIDI track chosen by matching the existing Hookpad melody (answer key)
  chords  <- UG (correct labels + structure), aligned to MIDI change timings
  timing  <- MIDI (one shared clock for melody + chords)
Outputs a Hookpad paste per song to ~/Desktop/fused_songs/.
"""
import os, re, glob, json, math, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import mido
from parse_ug import parse_tab, infer_key
from v0_chord_extract import load_midi_beats
from fuse import ug_pcq, midi_changes, align
from ug_chart import find_ug
from fill_preview import build_midi_index, find_midi, sd_interval
from chord_to_hookpad import chord_to_hookpad

TONIC_PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
MAJ=[0,2,4,5,7,9,11]; MIN=[0,2,3,5,7,8,10]

def load_tracks(path):
    mid=mido.MidiFile(path); tpb=mid.ticks_per_beat; out=[]
    for tr in mid.tracks:
        t=0; on={}; notes=[]
        for msg in tr:
            t+=msg.time
            if msg.type=='note_on' and msg.velocity>0 and getattr(msg,'channel',0)!=9:
                on.setdefault(msg.note,[]).append(t)
            elif msg.type=='note_off' or (msg.type=='note_on' and msg.velocity==0):
                if on.get(msg.note):
                    s=on[msg.note].pop(0)
                    if t>s: notes.append((msg.note, s/tpb, t/tpb))
        if notes: out.append(notes)
    return out

def corr(a,b):
    n=12; ma=sum(a)/n; mb=sum(b)/n
    num=sum((a[i]-ma)*(b[i]-mb) for i in range(n))
    da=sum((x-ma)**2 for x in a)**.5; db=sum((x-mb)**2 for x in b)**.5
    return num/(da*db) if da and db else -9

def pick_melody(tracks, hp_hist):
    best=(-9,None,0)
    for notes in tracks:
        th=[0.0]*12
        for p,s,e in notes: th[p%12]+=(e-s)
        bt=max(corr([th[(i-T)%12] for i in range(12)], hp_hist) for T in range(12))
        meanpitch=sum(p for p,_,_ in notes)/len(notes)
        score=bt + 0.002*meanpitch                      # nudge toward higher (melody) tracks
        if score>best[0]: best=(score,notes,meanpitch)
    return best[1]

def pitch_to_sdoct(pitch, tonic_pc, mode):
    scale=MIN if mode=='minor' else MAJ                  # use the key's scale so minor 3/6/7 are clean
    ref=60 + (tonic_pc if tonic_pc<=6 else tonic_pc-12)
    rel=pitch-ref; octv=rel//12; semis=rel%12
    if semis in scale: return str(scale.index(semis)+1), int(octv)
    if (semis-1) in scale: return '#'+str(scale.index(semis-1)+1), int(octv)
    if (semis+1) in scale and semis+1<12: return 'b'+str(scale.index(semis+1)+1), int(octv)
    return '1', int(octv)

def build(artist, title, hp_notes, midx):
    ugp=find_ug(artist,title); midp=find_midi(artist,title,midx)
    if not ugp or not midp: return None,'no ug/midi'
    _,secs=parse_tab(open(ugp,encoding='utf-8',errors='replace').read()),None
    meta,seclist=parse_tab(open(ugp,encoding='utf-8',errors='replace').read())
    tonic_let,mode=infer_key(seclist); tpc=TONIC_PC.get(tonic_let,0)
    # ug seq
    ug=[]
    for s in seclist:
        nm=s.get('name') or '(sec)'
        for kind,pl in s.get('events',[]):
            if kind=='chord_line':
                for cn,_ in pl:
                    pcq=ug_pcq(cn)
                    if pcq and (not ug or ug[-1][1]!=cn): ug.append((pcq,cn,nm))
    if not ug: return None,'ug empty'
    notes,nbeats=load_midi_beats(midp)
    mid=midi_changes(notes,nbeats)
    best=(-1e9,0,[])
    for t in range(12):
        sc,pairs=align(ug,mid,t)
        if sc>best[0]: best=(sc,t,pairs)
    sc,t,pairs=best
    matched={ui:mid[mj] for ui,mj in pairs}
    # melody track via answer key
    hp_hist=[0.0]*12
    for n in hp_notes or []:
        iv=sd_interval(n.get('sd'))
        if iv is not None and not n.get('isRest'): hp_hist[(tpc+iv)%12]+=n.get('duration',1)
    mel=pick_melody(load_tracks(midp), hp_hist)
    # build events (MIDI beats, shift later)
    chords=[]
    for i,(pcq,raw,nm) in enumerate(ug):
        if i in matched:
            _,start,dur=matched[i]
            hc=chord_to_hookpad(raw, tpc, 'major' if mode!='minor' else 'minor')
            if hc: chords.append((start,dur,hc,nm))
    mnotes=[]
    for p,s,e in mel:
        sd,octv=pitch_to_sdoct(p-t, tpc, mode)          # -t: MIDI->UG key
        mnotes.append((s, e-s, sd, octv))
    if not chords: return None,'no chords matched'
    allb=[b for b,_,_,_ in chords]+[b for b,_,_,_ in mnotes]
    shift=1-min(allb)
    return dict(tonic=tonic_let,mode=mode,t=t,match=f'{len(matched)}/{len(ug)}',
                chords=chords,notes=mnotes,secs=seclist,shift=shift), None

def to_paste(b):
    sh=b['shift']
    notes=[{'sd':str(sd),'octave':int(o),'beat':round(bt+sh,3),'duration':round(d,3),
            'isRest':False,'recordingEndBeat':None} for bt,d,sd,o in b['notes'] if bt+sh>=1]
    ORDER=['root','beat','duration','type','inversion','applied','adds','omits','alterations',
           'suspensions','substitutions','pedal','alternate','borrowed','isRest','recordingEndBeat']
    chords=[]; sections=[]; seen_sec=set()
    TMAP={'':5,'5':5,'7':7,'m':5,'maj7':7,'9':9,'11':11,'13':13,None:5}
    for bt,d,hc,nm in b['chords']:
        typ=hc.get('type'); typ=typ if isinstance(typ,int) else TMAP.get(typ,5)
        adds=[x for x in (hc.get('adds') or []) if isinstance(x,int)]
        sus=[x for x in (hc.get('suspensions') or []) if isinstance(x,int)]
        alts=[f"{a[1]}{a[0]}" for a in (hc.get('alterations') or []) if isinstance(a,(list,tuple)) and len(a)==2]
        ped=hc.get('pedal'); ped=ped if isinstance(ped,int) else None
        root=hc.get('root',1); root=root if isinstance(root,int) and 1<=root<=7 else 1
        c={'root':root,'beat':round(bt+sh,3),'duration':round(d,3),
           'type':typ,'inversion':0,'applied':int(hc.get('applied',0) or 0),
           'adds':adds,'omits':[],'alterations':alts,
           'suspensions':sus,'substitutions':[],'pedal':ped,
           'alternate':'','borrowed':hc.get('borrowed','') or '','isRest':False,'recordingEndBeat':None}
        chords.append({k:c[k] for k in ORDER})
        if nm not in seen_sec:
            sections.append({'beat':round(bt+sh,3),'name':nm}); seen_sec.add(nm)
    end=int(max([c['beat']+c['duration'] for c in chords]+[n['beat']+n['duration'] for n in notes]))+1
    return json.dumps({'notes':notes,'chords':chords,'audioTracks':[],
        'keys':[{'beat':1,'scale':b['mode'],'tonic':b['tonic']}],
        'tempos':[{'beat':1,'bpm':100,'swingFactor':0,'swingBeat':0.5}],
        'meters':[{'beat':1,'numBeats':4,'beatUnit':1}],
        'sections':sorted(sections,key=lambda s:s['beat']),'endBeat':end,'version':1},separators=(',',':'))

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor(); cur.execute("select artist,title,hookpad_json->'notes' from parcels.songs where not has_chords and has_melody and in_hookpad and artist is not null")
    rows=cur.fetchall(); c.close()
    targets=['mrs robinson','the cave','september','celebration','my generation',
             'lullaby','pinball wizard','mustang sally','wont get fooled','shiny happy']
    midx=build_midi_index()
    dest=os.path.expanduser('~/Desktop/fused_songs'); os.makedirs(dest,exist_ok=True)
    for tg in targets:
        row=next((r for r in rows if tg in (r[1] or '').lower()),None)
        if not row: print(f'{tg}: not found'); continue
        try:
            b,err=build(row[0],row[1],row[2],midx)
        except Exception as e:
            print(f'{row[1]}: ERR {str(e)[:50]}'); continue
        if err: print(f'{row[1]}: {err}'); continue
        fn=os.path.join(dest, re.sub(r'[^\w]+','_',f'{row[0]}_{row[1]}')+'.txt')
        open(fn,'w').write(to_paste(b))
        print(f'{row[1][:30]:30} key {b["tonic"]} {b["mode"]:6} match {b["match"]:8} '
              f'{len(b["chords"])} chords, {len(b["notes"])} notes -> {os.path.basename(fn)}')

if __name__=='__main__':
    main()
