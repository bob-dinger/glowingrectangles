"""Block Browser. Every section = a BLOCK: its core chord-set x melodic focus
(the most-recited scale degree) + register. Groups sections by block, ranks by
count, lists the songs. Writes _music/blocks.html.
"""
import os, re, json, psycopg2
from collections import defaultdict, Counter
from urllib.parse import quote_plus
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label

def norm(s): return re.sub(r'[^a-z0-9]','',(s or '').lower())
def coretok(t):
    m=re.match(r'^([b#]*[IiVvXx]+(?:/[b#]*[IiVvXx]+)?)',t); return m.group(1) if m else t
NUM={'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7}; MAJ={1:0,2:2,3:4,4:5,5:7,6:9,7:11}
PCN=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
FOCUSNOTE={1:'C',2:'D',3:'E',4:'F',5:'G',6:'A',7:'B'}
def _plain(t):
    m=re.match(r'^([b#]*)([ivxIVX]+)$',t)
    if not m: return None
    acc=sum(-1 if x=='b' else 1 for x in m.group(1)); deg=NUM.get(m.group(2).lower())
    if not deg: return None
    q='dim' if (m.group(2).lower()=='vii' and m.group(2).islower()) else ('maj' if m.group(2).isupper() else 'min')
    return (MAJ[deg]+acc)%12,q
def toC(t):
    if '/' in t or '°' in t: return t
    p=_plain(t)
    return PCN[p[0]]+('m' if p[1]=='min' else 'dim' if p[1]=='dim' else '') if p else t
def cpc(c):
    b=c.replace('dim','').rstrip('m'); return PCN.index(b) if b in PCN else 99

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor()
    cur.execute("select artist,title,hookpad_json,ug_url,hookpad_url from parcels.songs where has_chords and has_melody and (hookpad_json->'keys'->0->>'scale')='major'")
    rows=cur.fetchall(); c.close()
    def roll_doc(hj, lo, hi, secname, artist, title):
        """A minimal Hookpad doc for one section (capped to a ~preview length), for SongViewer."""
        meter=(hj.get('meters') or [{}])[0]; nb=meter.get('numBeats',4); bu=meter.get('beatUnit',1)
        cap=min(hi, lo+8*nb)   # first ~8 bars is plenty to see the block
        off=lo-1
        ns=[{"sd":n['sd'],"octave":n['octave'],"beat":round(n['beat']-off,4),"duration":n['duration'],
             "isRest":n.get('isRest',False),"recordingEndBeat":None} for n in (hj.get('notes') or []) if lo<=n['beat']<cap]
        cs=[{**{k:ch.get(k) for k in ('root','type','inversion','applied','adds','omits','alterations',
             'suspensions','substitutions','pedal','alternate','borrowed')},
             "beat":round(ch['beat']-off,4),"duration":ch.get('duration',1),"isRest":False,"recordingEndBeat":None}
             for ch in (hj.get('chords') or []) if lo<=ch['beat']<cap and ch.get('root')]
        end=int(round(cap-off,4))+1
        return {"notes":ns,"chords":cs,"keys":[{"beat":1,"scale":"major","tonic":"C"}],
                "meters":[{"beat":1,"numBeats":nb,"beatUnit":bu}],"tempos":[{"beat":1,"bpm":100,"swingFactor":0,"swingBeat":0.5}],
                "sections":[{"beat":1,"name":f"{artist} – {title} · {secname}"}],"breaks":[],"endBeat":end,"audioTracks":[]}

    blocks=defaultdict(list); seen=set(); block_roll={}
    for a,t,hj,ug,hp in rows:
        if not t or t.lower().endswith(('-hooktab','-simple')): continue
        secs=sorted(hj.get('sections') or [],key=lambda s:s.get('beat',0))
        if not secs: continue
        bounds=[s['beat'] for s in secs]+[hj.get('endBeat',1e9)]
        notes=hj.get('notes') or []; chords=hj.get('chords') or []
        ug2=(ug or '').strip() or ('https://www.ultimate-guitar.com/search.php?search_type=title&value='+quote_plus(f"{a or ''} {t}".strip()))
        for si,s in enumerate(secs):
            lo,hi=bounds[si],bounds[si+1]
            dur=Counter(); octs=[]; ncount=0
            for n in notes:
                if n.get('isRest') or not(lo<=n['beat']<hi): continue
                m=re.match(r'#?b?(\d)',str(n.get('sd','')));
                if m: dur[int(m.group(1))]+=n.get('duration',0); octs.append(n['octave']); ncount+=1
            if sum(dur.values())<4: continue
            focus=dur.most_common(1)[0][0]; reg=round(sum(octs)/len(octs)) if octs else 0
            cd=Counter()
            for ch in chords:
                if lo<=ch['beat']<hi and ch.get('root'): cd[coretok(chord_label(ch,'major'))]+=ch.get('duration',1)
            tot=sum(cd.values())
            core=frozenset(k for k,v in cd.items() if tot and v/tot>=0.15)
            if not(2<=len(core)<=4): continue
            key=(norm(a+t),core,focus)
            if key in seen: continue
            seen.add(key)
            blocks[(core,focus)].append({'a':a or '','t':t,'sec':s.get('name','?'),'reg':reg,'ug':ug2,'hp':(hp or '').strip()})
            # keep the roll for the meatiest example section (most notes) per block
            bk=(core,focus)
            if 12<=ncount<=120 and (bk not in block_roll or ncount>block_roll[bk][0]):
                block_roll[bk]=(ncount, roll_doc(hj,lo,hi,s.get('name','?'),a or '',t))
    data=[]
    for (core,focus),songs in blocks.items():
        if len(songs)<2: continue
        chords=sorted((toC(x) for x in core), key=cpc)
        roman=' '.join(sorted(core,key=lambda x:(len(x),x)))
        regs=Counter(s['reg'] for s in songs); domreg=regs.most_common(1)[0][0]
        roll=block_roll.get((core,focus),(0,None))[1]
        data.append({'chords':chords,'roman':roman,'focus':focus,'note':FOCUSNOTE.get(focus,'?'),
                     'reg':domreg,'n':len(songs),'roll':roll,'songs':sorted(songs,key=lambda s:(s['a'].lower(),s['t'].lower()))})
    data.sort(key=lambda b:-b['n'])
    out=os.path.join(os.path.dirname(__file__),'blocks.html')
    open(out,'w').write(PAGE.replace('__DATA__',json.dumps(data,ensure_ascii=False)))
    print(f"wrote {out}  |  {len(data)} blocks (>=2 songs), {sum(b['n'] for b in data)} song-sections")

PAGE=r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Block Browser</title><style>
 html,body{margin:0;height:100vh;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333;background:#fff}
 #wrap{display:flex;height:100vh}
 #side{width:340px;flex:0 0 340px;border-right:1px solid #eee;overflow-y:auto}
 #side h1{font-size:16px;margin:14px 16px 2px}#side .sub{font-size:12px;color:#999;margin:0 16px 8px}
 .brow{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 16px;cursor:pointer;border-bottom:1px solid #f4f4f7;font-size:13px}
 .brow:hover{background:#f8f8fc}.brow.on{background:#2a2a44;color:#fff}
 .chips{display:flex;gap:3px;flex-wrap:wrap}.chip{font-size:11px;font-weight:700;color:#fff;border-radius:4px;padding:1px 5px}
 .foc{font-weight:700;color:#c8600f}.brow.on .foc{color:#ffd23f}.ct{color:#aaa;font-weight:700}.brow.on .ct{color:#cfd}
 #main{flex:1;overflow-y:auto;padding:18px 22px}#hd{font-size:19px;font-weight:700}#sub2{color:#888;font-size:13px;margin:2px 0 10px}
 #roll{border:1px solid #eee;border-radius:8px;padding:6px;margin-bottom:14px;min-height:80px;background:#fafafb}
 #roll .status{color:#aaa;font-size:13px;padding:20px}
 table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:5px 10px;border-bottom:1px solid #eee;font-size:13px}
 th{color:#999;font-size:11px;text-transform:uppercase}.reg{font-weight:700;color:#4060c0}
 .lk{font-size:10px;font-weight:700;text-decoration:none;border-radius:4px;padding:2px 6px;margin-right:4px;color:#fff}
 .lk.ug{background:#c8600f}.lk.hp{background:#5090f0}.lk.off{background:#eee;color:#bbb}
 .deg1{background:#e84545}.deg2{background:#f0a040}.deg3{background:#e8c828;color:#333!important}.deg4{background:#50c878}.deg5{background:#5090f0}.deg6{background:#7040b0}.deg7{background:#e070b0}.degx{background:#9aa}
</style></head><body><div id="wrap">
<div id="side"><h1>Block Browser</h1><div class="sub" id="sub"></div><div id="list"></div></div>
<div id="main"><div id="hd"></div><div id="sub2"></div><div id="roll"></div><div id="body"></div></div></div>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>
<script>
const D=__DATA__;
const DEG={C:1,Dm:2,Em:3,F:4,G:5,Am:6,Bdim:7};
function chip(ch){let d=DEG[ch]||'x';return `<span class="chip deg${d}">${ch}</span>`;}
const viewer=new SongViewer({supabase:null,mainEl:'#roll'});
const L=document.getElementById('list');
document.getElementById('sub').textContent=`${D.length} blocks · chords × melodic focus`;
D.forEach((b,i)=>{const r=document.createElement('div');r.className='brow';r.dataset.i=i;
 r.innerHTML=`<span class=chips>${b.chords.map(chip).join('')}</span><span><span class=foc>focus ${b.focus} (${b.note})</span> <span class=ct>${b.n}</span></span>`;
 r.onclick=()=>sel(i);L.appendChild(r);});
function sel(i){document.querySelectorAll('.brow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
 const b=D[i];document.getElementById('hd').innerHTML=b.chords.map(chip).join(' ')+` &nbsp; <span class=foc>focus ${b.focus} = ${b.note}</span>`;
 document.getElementById('sub2').textContent=`${b.n} sections · reciting the ${b.note} · usually register ${b.reg>=0?'+':''}${b.reg}  —  piano roll = a real example section`;
 if(b.roll){try{viewer.loadData(b.roll,{title:'example'});}catch(e){document.getElementById('roll').innerHTML='<div class=status>roll unavailable</div>';}}
 else document.getElementById('roll').innerHTML='<div class=status>no example roll for this block</div>';
 let h='<table><tr><th>Artist</th><th>Song</th><th>Section</th><th>Reg</th><th>Links</th></tr>';
 b.songs.forEach(o=>{const ug=o.ug?`<a class="lk ug" href="${o.ug}" target=_blank>UG</a>`:`<span class="lk ug off">UG</span>`;
  const hp=o.hp?`<a class="lk hp" href="${o.hp}" target=_blank>HP</a>`:`<span class="lk hp off">HP</span>`;
  h+=`<tr><td>${o.a}</td><td>${o.t}</td><td>${o.sec}</td><td class=reg>${o.reg>=0?'+':''}${o.reg}</td><td style=white-space:nowrap>${ug}${hp}</td></tr>`;});
 document.getElementById('body').innerHTML=h+'</table>';}
sel(0);
</script></body></html>
"""
if __name__=='__main__': main()
