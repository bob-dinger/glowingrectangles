"""Build _music/mixolydian.html — the mixolydian family across the library.

Major-key sections coloured by mixolydian markers, in three flavours:
  double-plagal   bVII -> IV -> I    (the "Hey Jude" cadence; With a Little Help refrain)
  I-bVII vamp     I rocks against bVII, never leaves home (ZZ Top, Bennie and the Jets)
  minor-v         a v chord (minor five) instead of V (Clocks, Yellow, Strawberry Fields)

bVII is detected including its IV/IV spelling (a secondary subdominant == the flat-seven).
Grouped by flavour, filterable by scope, playable. Reuses the roll/modal from vamp-home.
"""
import os, re, json
from collections import Counter
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label
import phrase_forms as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mixolydian.html')
PCN = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
PCIDX = {n: i for i, n in enumerate(PCN)}
for _a, _b in [('C#', 1), ('D#', 3), ('F#', 6), ('G#', 8), ('A#', 10)]: PCIDX[_a] = _b

def tonic_pc(k):
    t = k.get('tonic', 0)
    pc = PCIDX.get(str(t), t if isinstance(t, int) else 0)
    return (pc + 3) % 12 if k.get('scale') == 'minor' else pc

def mixotok(l):
    if l.startswith('IV/IV') or l.startswith('bVII'): return 'bVII'   # IV/IV == the flat-seven
    m = re.match(r'^([b#]*[ivxIVX]+)', l); return m.group(1) if m else l

def collapse(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x: out.append(x)
    return out

def flavors_of(seq):
    S = set(seq); fl = []
    dp = any(seq[j:j + 3] == ['bVII', 'IV', 'I'] for j in range(len(seq) - 2))
    ibv = any((seq[j], seq[j + 1]) in [('I', 'bVII'), ('bVII', 'I')] for j in range(len(seq) - 1))
    if dp: fl.append('double-plagal')
    if ibv: fl.append('I-bVII vamp')
    if 'v' in S: fl.append('minor-v')
    if 'bVII' in S and not dp and not ibv: fl.append('other-bVII')
    return fl

def body(hj, b0, b1, sc):
    notes = []
    for n in hj.get('notes') or []:
        nb = n.get('beat', 0)
        if not (b0 <= nb < b1) or n.get('isRest'): continue
        sem = P.sd_semis(n.get('sd'))
        if sem is None: continue
        notes.append({'sem': sem, 'o': int(n.get('octave', 0)), 'sd': str(n.get('sd')),
                      'b': round(nb - b0, 3), 'd': round(n.get('duration', 1), 3)})
    chords = []
    for c in hj.get('chords') or []:
        cb, cd = c.get('beat', 0), c.get('duration', 1)
        if not c.get('root') or not 1 <= c['root'] <= 7: continue
        st, en = max(cb, b0), min(cb + cd, b1)
        if en > st: chords.append({'n': chord_label(c, sc), 'b': round(st - b0, 3), 'd': round(en - st, 3)})
    return notes, sorted(chords, key=lambda c: c['b'])

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select artist,title,hookpad_json,bpm from parcels.songs where has_chords and hookpad_json is not null")
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -len((r[2] or {}).get('chords') or []))

    seen, items = set(), []
    for artist, t, hj, bpm in rows:
        t = (t or '').strip()
        if not t or P.VARIANT.search(t): continue
        k = P.norm((artist or '') + t)
        if k in seen: continue
        seen.add(k)
        beatles = 'beatle' in (artist or '').lower()
        kk = (hj.get('keys') or [{}])[0]; sc = kk.get('scale', 'major')
        if sc != 'major': continue
        secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0)); end = hj.get('endBeat', 0) + 1
        per = set()
        for i, s in enumerate(secs):
            nm = (s.get('name') or '').strip(); b0 = s['beat']; b1 = secs[i + 1]['beat'] if i + 1 < len(secs) else end
            seq = collapse([mixotok(chord_label(x, 'major')) for x in hj.get('chords') or [] if x.get('root') and b0 <= x.get('beat', 0) < b1])
            fl = flavors_of(seq)
            if not fl: continue
            sig = (re.sub(r'[^a-z]', '', nm.lower()), tuple(seq))
            if sig in per: continue
            per.add(sig)
            notes, chords = body(hj, b0, b1, 'major')
            items.append({'title': t, 'artist': artist or '', 'beatles': beatles, 'sec': nm,
                          'seq': seq, 'flavors': fl, 'primary': fl[0],
                          'tonic': tonic_pc(kk), 'scale': sc,
                          'bpm': (hj.get('tempos') or [{}])[0].get('bpm') or bpm,
                          'notes': notes, 'chords': chords})
    for i, it in enumerate(items): it['i'] = i
    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps(items)))
    fl = Counter(f for x in items for f in x['flavors'])
    print(f'wrote {OUT}  |  {len(items)} sections  ·  flavours {dict(fl)}')

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Mixolydian</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:240px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff;padding-bottom:20px}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:14px 16px 4px;margin:0}
.tog2{display:flex;gap:6px;padding:6px 14px}
.tog2 button{flex:1;padding:6px 0;border:1px solid #ccd;background:#f6f6fb;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;color:#556}
.tog2 button.on{background:#2a7a44;border-color:#2a7a44;color:#fff}
.frow{padding:7px 16px;cursor:pointer;border-bottom:1px solid #f2f2f6;display:flex;justify-content:space-between;gap:8px}
.frow:hover{background:#eef}.frow.on{background:#2a2a44;color:#fff}.frow.all{border-bottom:2px solid #ddd;font-style:italic}
.frow .fm{font-weight:700}.frow .ct{font-size:11px;color:#aaa}.frow.on .ct{color:#dde}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}.meta{color:#888;font-size:12px;margin-bottom:14px}
.sec{display:flex;align-items:baseline;gap:12px;padding:7px 0;border-bottom:1px solid #ededf2;cursor:pointer}
.sec:hover{background:#f6f6ff}
.sec .t{width:230px;flex:none;font-weight:600;font-size:13px}
.sec .t .be{color:#c0392b;font-size:10px;font-weight:700;margin-left:6px}
.sec .t .sub{display:block;color:#aaa;font-weight:400;font-size:11px}
.seq{display:flex;gap:3px;flex-wrap:wrap;align-items:center}
.ch{font:700 11px/18px ui-monospace,monospace;border-radius:4px;padding:1px 6px;color:#556;background:#eef0f4}
.ch.b7{background:#e8734a;color:#fff}.ch.mv{background:#7040b0;color:#fff}
.ftag{font-size:10px;font-weight:700;border-radius:4px;padding:1px 7px;margin-left:8px}
.ftag.dp{color:#b5651d;background:#fbeede}.ftag.iv{color:#c0392b;background:#fdeaea}.ftag.mv{color:#7040b0;background:#f0eafa}.ftag.ob{color:#556;background:#eef0f4}
#ov{position:fixed;inset:0;background:rgba(20,20,35,.55);display:none;align-items:center;justify-content:center;z-index:50}
#ov.on{display:flex}
#mod{background:#fff;border-radius:12px;padding:18px 20px;max-width:min(1100px,94vw);max-height:90vh;overflow:auto;box-shadow:0 18px 60px rgba(0,0,0,.3)}
#mod h3{margin:0 0 2px;font-size:17px}#mod .mmeta{color:#888;font-size:12px;margin-bottom:12px}
#mod .close{float:right;cursor:pointer;color:#aaa;font-size:20px;padding:0 4px}#mod .close:hover{color:#333}
.roll{position:relative;border:1px solid #e4e4ec;border-radius:8px;background:#fbfbfe;overflow-x:auto}
.rollin{position:relative}.lane.tonic{position:absolute;left:0;right:0;height:1px;background:#d8d8ea}
.barline{position:absolute;top:0;bottom:0;width:1px;background:#e8e8f0}.barline.b4{background:#d4d4e2}
.nb{position:absolute;height:9px;border-radius:3px;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cb{position:absolute;bottom:0;height:22px;border-radius:4px;color:#fff;font:700 10px/22px sans-serif;text-align:center;text-shadow:0 1px 2px rgba(0,0,0,.4);overflow:hidden;white-space:nowrap}
.mtools{display:flex;gap:10px;align-items:center;margin-top:10px;font-size:12px}
.mtools button{padding:5px 12px;border:1px solid #ccd;background:#f6f6fb;border-radius:7px;cursor:pointer;font-weight:600}
</style></head><body><div id=wrap>
<div id=side>
  <div class="tog2 scope"><button data-sc=beatles>Beatles</button><button data-sc=others>others</button><button data-sc=all class=on>all</button></div>
  <h1>Flavour</h1><div id=list></div>
</div>
<div id=main><h2 id=ttl></h2><div class=meta id=sub></div><div id=body></div></div></div>
<div id=ov><div id=mod>
  <span class=close onclick="closeMod()">&times;</span>
  <h3 id=mtitle></h3><div class=mmeta id=msub></div>
  <div class=roll id=mroll></div>
  <div class=mtools><button id=mplay>▶ Play</button><span id=mnote></span></div>
</div></div>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script>
const D=__DATA__;
const PCN=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const DEGCOL={0:'#e84545',2:'#f0a040',4:'#e8c828',5:'#50c878',7:'#5090f0',9:'#7040b0',11:'#e070b0'};
const R2D={i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7},D2S={1:0,2:2,3:4,4:5,5:7,6:9,7:11};
const FTAG={'double-plagal':'dp','I-bVII vamp':'iv','minor-v':'mv','other-bVII':'ob'};
let FLAV=null,SCOPE='all';
const inScope=x=>SCOPE==='all'||(SCOPE==='beatles'?x.beatles:!x.beatles);
function degBg(semi){semi=((semi%12)+12)%12;return DEGCOL[semi]!==undefined?DEGCOL[semi]
  :`linear-gradient(135deg,${DEGCOL[(semi+11)%12]||'#889'} 0 50%,${DEGCOL[(semi+1)%12]||'#889'} 50%)`;}
function parseRoman(lbl){
  if(lbl.indexOf('/')>-1&&lbl.indexOf('°')===-1){const[l,r]=lbl.split('/');const L=parseRoman(l),R=parseRoman(r);
    if(L&&R)return{semi:(L.semi+R.semi)%12,q:'maj',suf:L.suf};}
  if(lbl.indexOf('°')>-1){const tgt=lbl.indexOf('/')>-1?parseRoman(lbl.split('/')[1]):{semi:0};
    return{semi:((tgt?tgt.semi:0)-1+12)%12,q:'dim',suf:/7/.test(lbl.split('/')[0])?'7':''};}
  const m=lbl.match(/^([b#]*)([ivxIVX]+)(.*)$/);if(!m)return null;
  const d=R2D[m[2].toLowerCase()];if(!d)return null;let acc=0;for(const c of m[1])acc+=c==='b'?-1:1;
  return{semi:(D2S[d]+acc+12)%12,q:m[2]===m[2].toUpperCase()?'maj':'min',suf:m[3]||''};}
function chordBg(n){const p=parseRoman(n);return p?degBg(p.semi):'#889';}
function chordName(l,t){const p=parseRoman(l);if(!p)return l;return PCN[(t+p.semi)%12]+(p.q==='min'?'m':p.q==='dim'?'°':'')+p.suf;}
function chip(tok){const cls=tok==='bVII'?' b7':(tok==='v'?' mv':'');return `<span class="ch${cls}">${tok}</span>`;}
function buildList(){
  const items=D.filter(inScope), fl={};
  items.forEach(x=>x.flavors.forEach(f=>fl[f]=(fl[f]||0)+1));
  const L=document.getElementById('list');
  const order=['double-plagal','I-bVII vamp','minor-v','other-bVII'];
  let h=`<div class="frow all${FLAV===null?' on':''}" onclick="pick(null)"><span class=fm>all</span><span class=ct>${items.length}</span></div>`;
  order.forEach(f=>{if(fl[f])h+=`<div class="frow${FLAV===f?' on':''}" onclick="pick('${f}')"><span class=fm>${f}</span><span class=ct>${fl[f]}</span></div>`;});
  L.innerHTML=h;
}
function pick(f){FLAV=f;render();buildList();}
function render(){
  const items=D.filter(x=>inScope(x)&&(FLAV===null||x.flavors.includes(FLAV)));
  document.getElementById('ttl').textContent=`Mixolydian${FLAV?' · '+FLAV:''}`;
  document.getElementById('sub').textContent=`${items.length} sections · bVII (orange) and minor-v (purple) are the markers · click for the piano roll`;
  document.getElementById('body').innerHTML=items.sort((a,b)=>a.primary.localeCompare(b.primary)||a.title.localeCompare(b.title)).map(x=>{
    const seq=x.seq.map(chip).join('');
    const be=x.beatles?'':`<span class=be>${x.artist}</span>`;
    const tags=x.flavors.map(f=>`<span class="ftag ${FTAG[f]}">${f}</span>`).join('');
    return `<div class=sec onclick="openMod(${x.i})">
      <div class=t>${x.title}${be}<span class=sub>${x.sec} · ${PCN[x.tonic]} major</span></div>
      <div class=seq>${seq}${tags}</div></div>`;
  }).join('');
}
document.querySelectorAll('.scope button').forEach(b=>b.onclick=()=>{SCOPE=b.dataset.sc;document.querySelectorAll('.scope button').forEach(x=>x.classList.toggle('on',x===b));FLAV=null;buildList();render();});

let CUR=null,synth=null,part=null;
function openMod(i){const x=D.find(y=>y.i===i);CUR=x;
  document.getElementById('mtitle').textContent=`${x.title}${x.beatles?'':' · '+x.artist} — ${x.sec}`;
  document.getElementById('msub').textContent=`${x.flavors.join(' · ')} · ${x.seq.join(' ')} · ${PCN[x.tonic]} major · ${x.bpm||'?'}bpm`;
  drawRoll(x);document.getElementById('ov').classList.add('on');}
function closeMod(){document.getElementById('ov').classList.remove('on');stopPlay();}
document.getElementById('ov').onclick=e=>{if(e.target.id==='ov')closeMod();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMod();});
function drawRoll(b){
  const beats=Math.max(...b.chords.map(c=>c.b+c.d),...b.notes.map(n=>n.b+n.d),4);
  const PX=Math.max(8,Math.min(20,1000/beats)),H=200,CH=26;
  const vals=b.notes.map(n=>n.sem+12*n.o);const lo=vals.length?Math.min(...vals):0,hi=vals.length?Math.max(...vals):12;
  const span=Math.max(hi-lo,7),top=12,usable=H-CH-24,y=v=>top+usable-((v-lo)/span)*usable;
  let h=`<div class=rollin style="width:${Math.ceil(beats*PX)}px;height:${H}px">`;
  for(let v=Math.floor(lo/12)*12;v<=hi+1;v+=12)h+=`<div class="lane tonic" style="top:${y(v)}px"></div>`;
  for(let bar=0;bar<=Math.ceil(beats/4);bar++)h+=`<div class="barline${bar%4===0?' b4':''}" style="left:${bar*4*PX}px"></div>`;
  b.chords.forEach(c=>{h+=`<div class=cb title="${c.n}" style="left:${c.b*PX}px;width:${Math.max(c.d*PX-2,14)}px;background:${chordBg(c.n)}">${chordName(c.n,b.tonic)}</div>`;});
  b.notes.forEach(n=>{const v=n.sem+12*n.o;h+=`<div class=nb title="${n.sd}" style="left:${n.b*PX}px;top:${y(v)}px;width:${Math.max(n.d*PX-2,4)}px;background:${degBg(n.sem)}"></div>`;});
  document.getElementById('mroll').innerHTML=h+'</div>';}
function nameOf(m){return PCN[((m%12)+12)%12]+(Math.floor(m/12)-1);}
async function play(){if(!CUR)return;if(typeof Tone==='undefined'){document.getElementById('mnote').textContent='audio unavailable offline';return;}
  await Tone.start();stopPlay();
  synth=synth||new Tone.PolySynth(Tone.Synth,{oscillator:{type:'triangle'},envelope:{attack:.01,decay:.2,sustain:.3,release:.4}}).toDestination();
  const bpm=CUR.bpm||120;Tone.Transport.bpm.value=bpm;const spb=60/bpm,ev=[];
  CUR.notes.forEach(n=>ev.push([n.b*spb,{n:[nameOf(60+CUR.tonic+n.sem+12*n.o)],d:Math.max(.05,n.d*spb*.95)}]));
  part=new Tone.Part((t,e)=>synth.triggerAttackRelease(e.n,e.d,t,.85),ev);part.start(0);Tone.Transport.start();
  document.getElementById('mplay').textContent='■ Stop';}
function stopPlay(){if(typeof Tone==='undefined')return;Tone.Transport.stop();Tone.Transport.cancel(0);
  if(part){part.dispose();part=null;}document.getElementById('mplay').textContent='▶ Play';}
document.getElementById('mplay').onclick=()=>{if(document.getElementById('mplay').textContent.startsWith('■'))stopPlay();else play();};
buildList();render();
</script></body></html>"""

if __name__ == '__main__':
    main()
