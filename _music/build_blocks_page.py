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
    def roll_compact(hj, lo, hi, label, ug, hp):
        """Compact section roll (~4 bars): notes as [sd,oct,beat,dur], chords as [root,beat,dur,borrowed]."""
        meter=(hj.get('meters') or [{}])[0]; nb=meter.get('numBeats',4)
        cap=min(hi, lo+4*nb); off=lo-1
        n=[[str(x['sd']),x['octave'],round(x['beat']-off,3),x['duration']]
           for x in (hj.get('notes') or []) if lo<=x['beat']<cap and not x.get('isRest')]
        cc=[[ch['root'],round(ch['beat']-off,3),ch.get('duration',1),ch.get('borrowed') or '']
           for ch in (hj.get('chords') or []) if lo<=ch['beat']<cap and ch.get('root')]
        return {'lab':label,'nb':nb,'n':n,'c':cc,'ug':ug,'hp':hp}

    blocks=defaultdict(list); seen=set(); block_rolls=defaultdict(list)
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
            if 6<=ncount<=200:   # roll for essentially every section with a real melody
                block_rolls[(core,focus)].append((ncount, roll_compact(hj,lo,hi,f"{a} – {t} · {s.get('name','?')}",ug2,(hp or '').strip())))
    data=[]
    for (core,focus),songs in blocks.items():
        if len(songs)<2: continue
        chords=sorted((toC(x) for x in core), key=cpc)
        roman=' '.join(sorted(core,key=lambda x:(len(x),x)))
        regs=Counter(s['reg'] for s in songs); domreg=regs.most_common(1)[0][0]
        rolls=[r for _,r in sorted(block_rolls.get((core,focus),[]),key=lambda x:-x[0])]   # ALL sections for this block
        data.append({'chords':chords,'roman':roman,'focus':focus,'note':FOCUSNOTE.get(focus,'?'),
                     'reg':domreg,'n':len(songs),'rolls':rolls,'songs':sorted(songs,key=lambda s:(s['a'].lower(),s['t'].lower()))})
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
 #stopbar{position:fixed;top:14px;right:18px;z-index:50}
 #stopbtn{padding:7px 16px;font-size:13px;font-weight:700;border:none;border-radius:7px;background:#e84545;color:#fff;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.15)}
 #stopbtn:active{transform:translateY(1px)}
 .rlk{font-size:10px;font-weight:700;text-decoration:none;border-radius:4px;padding:1px 6px;margin-left:5px;color:#fff}
 .rlk.ug{background:#c8600f}.rlk.hp{background:#5090f0}.rlk.off{background:#3a3a5a;color:#888}
 #roll{border:1px solid #eee;border-radius:8px;padding:6px;margin-bottom:14px;min-height:80px;background:#fafafb}
 #roll .status{color:#aaa;font-size:13px;padding:20px}
 table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:5px 10px;border-bottom:1px solid #eee;font-size:13px}
 th{color:#999;font-size:11px;text-transform:uppercase}.reg{font-weight:700;color:#4060c0}
 .lk{font-size:10px;font-weight:700;text-decoration:none;border-radius:4px;padding:2px 6px;margin-right:4px;color:#fff}
 .lk.ug{background:#c8600f}.lk.hp{background:#5090f0}.lk.off{background:#eee;color:#bbb}
 .deg1{background:#e84545}.deg2{background:#f0a040}.deg3{background:#e8c828;color:#333!important}.deg4{background:#50c878}.deg5{background:#5090f0}.deg6{background:#7040b0}.deg7{background:#e070b0}.degx{background:#9aa}
</style></head><body>
<div id="stopbar"><button id="stopbtn">&#9632; Stop</button></div>
<div id="wrap">
<div id="side"><h1>Block Browser</h1><div class="sub" id="sub"></div><div id="list"></div></div>
<div id="main"><div id="hd"></div><div id="sub2"></div><div id="roll"></div><div id="body"></div></div></div>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>
<script>
const D=__DATA__;
const DEG={C:1,Dm:2,Em:3,F:4,G:5,Am:6,Bdim:7};
function chip(ch){let d=DEG[ch]||'x';return `<span class="chip deg${d}">${ch}</span>`;}
const viewer=new SongViewer({supabase:null,mainEl:'#roll',followPlayhead:false});
document.getElementById('stopbtn').onclick=()=>viewer.stop();
function injectLinks(rolls){
 document.querySelectorAll('#roll .section-block').forEach(bl=>{
  const rc=rolls[+bl.dataset.sectionIdx]; const hdr=bl.querySelector('.section-header');
  if(!rc||!hdr||hdr.querySelector('.rlk'))return;
  const ug=rc.ug?`<a class="rlk ug" href="${rc.ug}" target=_blank>UG</a>`:`<span class="rlk off">UG</span>`;
  const hp=rc.hp?`<a class="rlk hp" href="${rc.hp}" target=_blank>HP</a>`:`<span class="rlk off">HP</span>`;
  const sp=document.createElement('span'); sp.style.marginLeft='auto'; sp.innerHTML=ug+hp; hdr.appendChild(sp);});
}
// expand a compact roll [sd,oct,beat,dur] / [root,beat,dur,bor] into Hookpad objects, offset in beats
function expand(rc,off){
 const notes=rc.n.map(a=>({sd:a[0],octave:a[1],beat:a[2]+off,duration:a[3],isRest:false,recordingEndBeat:null}));
 const chords=rc.c.map(a=>({root:a[0],beat:a[1]+off,duration:a[2],type:5,inversion:0,applied:0,adds:[],omits:[],
   alterations:[],suspensions:[],substitutions:[],pedal:null,alternate:"",borrowed:a[3],isRest:false,recordingEndBeat:null}));
 return {notes,chords};
}
function stack(rolls){
 const nb=rolls[0].nb; let cur=1,notes=[],chords=[],sections=[];
 rolls.forEach(rc=>{const off=cur-1,{notes:nn,chords:cc}=expand(rc,off);
  notes.push(...nn);chords.push(...cc);sections.push({beat:cur,name:rc.lab});
  const end=Math.max(cur,...nn.map(n=>n.beat+n.duration),...cc.map(c=>c.beat+c.duration));
  cur=Math.ceil(end/nb)*nb+nb;});
 return {notes,chords,keys:[{beat:1,scale:"major",tonic:"C"}],meters:[{beat:1,numBeats:nb,beatUnit:1}],
   tempos:[{beat:1,bpm:100,swingFactor:0,swingBeat:0.5}],sections,breaks:[],endBeat:cur,audioTracks:[]};
}
const L=document.getElementById('list');
document.getElementById('sub').textContent=`${D.length} blocks · chords × melodic focus`;
D.forEach((b,i)=>{const r=document.createElement('div');r.className='brow';r.dataset.i=i;
 r.innerHTML=`<span class=chips>${b.chords.map(chip).join('')}</span><span><span class=foc>focus ${b.focus} (${b.note})</span> <span class=ct>${b.n}</span></span>`;
 r.onclick=()=>sel(i);L.appendChild(r);});
function sel(i){document.querySelectorAll('.brow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
 const b=D[i];document.getElementById('hd').innerHTML=b.chords.map(chip).join(' ')+` &nbsp; <span class=foc>focus ${b.focus} = ${b.note}</span>`;
 document.getElementById('sub2').textContent=`${b.n} sections · reciting the ${b.note} · register ${b.reg>=0?'+':''}${b.reg}  —  ${b.rolls.length} shown as piano rolls`;
 viewer.stop();
 if(b.rolls&&b.rolls.length){try{viewer.loadData(stack(b.rolls),{title:'examples'});injectLinks(b.rolls);}catch(e){document.getElementById('roll').innerHTML='<div class=status>rolls unavailable</div>';}}
 else document.getElementById('roll').innerHTML='<div class=status>no example rolls for this block</div>';
 // remaining songs (those not shown as rolls) as compact links
 const shown=new Set(b.rolls.map(r=>r.lab));
 const rest=b.songs.filter(o=>!shown.has(`${o.a} – ${o.t} · ${o.sec}`));
 let h=rest.length?`<div style="font-size:12px;color:#999;margin:4px 0 6px">+ ${rest.length} more songs with this block</div><table>`:'<table>';
 rest.forEach(o=>{const ug=o.ug?`<a class="lk ug" href="${o.ug}" target=_blank>UG</a>`:`<span class="lk ug off">UG</span>`;
  const hp=o.hp?`<a class="lk hp" href="${o.hp}" target=_blank>HP</a>`:`<span class="lk hp off">HP</span>`;
  h+=`<tr><td>${o.a}</td><td>${o.t}</td><td>${o.sec}</td><td style=white-space:nowrap>${ug}${hp}</td></tr>`;});
 document.getElementById('body').innerHTML=h+'</table>';}
sel(0);
</script></body></html>
"""
if __name__=='__main__': main()
