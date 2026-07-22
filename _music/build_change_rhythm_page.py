"""Build _music/change-rhythm.html — sections grouped by their repeating change-rhythm cell.

The change-rhythm = how long each chord is held, as a repeating cell (durations in beats):
[4] = one chord per bar (even), [4,2,2] = long-short-short (the "224"), [1.5,2.5] = a limping
pair, etc. A section's cell is the shortest period that tiles its chord durations. The even
cells ([4],[2]) are the boring majority, so the page leads with the ASYMMETRIC ones — those
carry a feel. Grouped by cell, filterable, playable. Reuses the roll/modal from vamp-home.
"""
import os, re, json
from collections import Counter
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label
import phrase_forms as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'change-rhythm.html')
PCN = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
PCIDX = {n: i for i, n in enumerate(PCN)}
for _a, _b in [('C#', 1), ('D#', 3), ('F#', 6), ('G#', 8), ('A#', 10)]: PCIDX[_a] = _b

def tonic_pc(k):
    t = k.get('tonic', 0)
    pc = PCIDX.get(str(t), t if isinstance(t, int) else 0)
    return (pc + 3) % 12 if k.get('scale') == 'minor' else pc

def core(l):
    m = re.match(r'^([b#]*[ivxIVX]+)', l); return m.group(1) if m else l

def dominant_cell(durs):
    n = len(durs)
    for p in range(1, min(9, n // 2 + 1)):
        good = sum(1 for i in range(n) if abs(durs[i] - durs[i % p]) < .02)
        if good / n >= 0.8 and n // p >= 2:
            return tuple(round(x, 2) for x in durs[:p])
    return None

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

def nice(x): return int(x) if x == int(x) else x

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
        kk = (hj.get('keys') or [{}])[0]; sc = kk.get('scale', 'major'); sc = sc if sc in ('major', 'minor') else 'major'
        secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0)); end = hj.get('endBeat', 0) + 1
        per = set()
        for i, s in enumerate(secs):
            nm = (s.get('name') or '').strip(); b0 = s['beat']; b1 = secs[i + 1]['beat'] if i + 1 < len(secs) else end
            ch = [x for x in hj.get('chords') or [] if x.get('root') and 1 <= x['root'] <= 7 and b0 <= x.get('beat', 0) < b1]
            durs = [x.get('duration', 1) for x in ch]
            if len(durs) < 4: continue
            cell = dominant_cell(durs)
            if cell is None: continue
            even = len(set(cell)) == 1
            cellkey = '·'.join(str(nice(x)) for x in cell)
            sig = (re.sub(r'[^a-z]', '', nm.lower()), cellkey)
            if sig in per: continue
            per.add(sig)
            notes, chords = body(hj, b0, b1, sc)
            seq = [core(chord_label(x, sc)) for x in ch[:len(cell) * 2]]
            items.append({'title': t, 'artist': artist or '', 'beatles': beatles, 'sec': nm,
                          'cell': [nice(x) for x in cell], 'cellkey': cellkey, 'even': even,
                          'reps': len(durs) // len(cell), 'seq': seq,
                          'tonic': tonic_pc(kk), 'scale': sc,
                          'bpm': (hj.get('tempos') or [{}])[0].get('bpm') or bpm,
                          'notes': notes, 'chords': chords})
    for i, it in enumerate(items): it['i'] = i
    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps(items)))
    asym = Counter(x['cellkey'] for x in items if not x['even'])
    print(f'wrote {OUT}  |  {len(items)} sections, {len(set(x["cellkey"] for x in items))} cells')
    print('  top asymmetric cells:', ', '.join(f'{c}×{n}' for c, n in asym.most_common(10)))

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Change Rhythm</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:240px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff;padding-bottom:20px}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:12px 16px 4px;margin:0}
.tog2{display:flex;gap:6px;padding:6px 14px}
.tog2 button{flex:1;padding:6px 0;border:1px solid #ccd;background:#f6f6fb;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;color:#556}
.tog2 button.on{background:#2a2a44;color:#fff;border-color:#2a2a44}
.tog2.typ button.on{background:#b5651d;border-color:#b5651d}
.crow{padding:6px 16px;cursor:pointer;border-bottom:1px solid #f2f2f6;display:flex;justify-content:space-between;gap:8px}
.crow:hover{background:#eef}.crow.on{background:#2a2a44;color:#fff}.crow.all{border-bottom:2px solid #ddd;font-style:italic}
.crow .cm{font-weight:700;font-family:ui-monospace,monospace}.crow .ct{font-size:11px;color:#aaa}.crow.on .ct{color:#dde}
.crow.evenrow .cm{color:#99a;font-weight:400}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}.meta{color:#888;font-size:12px;margin-bottom:14px}
.sec{display:flex;align-items:baseline;gap:12px;padding:7px 0;border-bottom:1px solid #ededf2;cursor:pointer}
.sec:hover{background:#f6f6ff}
.sec .t{width:230px;flex:none;font-weight:600;font-size:13px}
.sec .t .be{color:#c0392b;font-size:10px;font-weight:700;margin-left:6px}
.sec .t .sub{display:block;color:#aaa;font-weight:400;font-size:11px}
.seq{display:flex;gap:4px;flex-wrap:wrap;align-items:center}
.durcell{display:flex;gap:2px;align-items:center;margin-right:8px}
.dur{font:700 11px/16px ui-monospace,monospace;color:#fff;background:#b5651d;border-radius:3px;padding:1px 6px}
.dur.lng{background:#8a3fb0}
.ch{font:700 11px/18px ui-monospace,monospace;color:#556;background:#eef0f4;border-radius:4px;padding:1px 6px}
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
  <div class="tog2 typ"><button data-ty=asym class=on>asymmetric</button><button data-ty=even>even</button><button data-ty=all>all</button></div>
  <h1>Change-rhythm cell (beats)</h1><div id=list></div>
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
let CELL=null,TYP='asym',SCOPE='all';
const inType=x=>TYP==='all'||(TYP==='even'?x.even:!x.even);
const inScope=x=>SCOPE==='all'||(SCOPE==='beatles'?x.beatles:!x.beatles);
const ok=x=>inScope(x)&&inType(x);
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
function buildList(){
  const items=D.filter(ok), cells={};
  items.forEach(x=>cells[x.cellkey]=(cells[x.cellkey]||0)+1);
  const L=document.getElementById('list');
  let h=`<div class="crow all${CELL===null?' on':''}" onclick="pick(null)"><span class=cm>all cells</span><span class=ct>${items.length}</span></div>`;
  Object.keys(cells).sort((a,b)=>cells[b]-cells[a]||a.localeCompare(b)).forEach(ck=>{
    const ev=D.find(x=>x.cellkey===ck).even?' evenrow':'';
    h+=`<div class="crow${ev}${CELL===ck?' on':''}" onclick="pick('${ck}')"><span class=cm>${ck}</span><span class=ct>${cells[ck]}</span></div>`;});
  L.innerHTML=h;
}
function pick(ck){CELL=ck;render();buildList();}
function render(){
  const items=D.filter(x=>ok(x)&&(CELL===null||x.cellkey===CELL));
  document.getElementById('ttl').textContent=`Change Rhythm${CELL?' · '+CELL:''}`;
  document.getElementById('sub').textContent=`${items.length} sections · the cell (orange, purple=long) repeats as the chord-change pulse · click for the piano roll`;
  document.getElementById('body').innerHTML=items.sort((a,b)=>a.cellkey.localeCompare(b.cellkey)||b.reps-a.reps||a.title.localeCompare(b.title)).map(x=>{
    const mx=Math.max(...x.cell);
    const cell=x.cell.map(d=>`<span class="dur${d===mx&&x.cell.length>1?' lng':''}">${d}</span>`).join('');
    const chs=x.seq.map(ch=>`<span class=ch>${ch}</span>`).join('');
    const be=x.beatles?'':`<span class=be>${x.artist}</span>`;
    return `<div class=sec onclick="openMod(${x.i})">
      <div class=t>${x.title}${be}<span class=sub>${x.sec} · ${PCN[x.tonic]} ${x.scale} · ×${x.reps}</span></div>
      <div class=seq><span class=durcell>${cell}</span>${chs}</div></div>`;
  }).join('');
}
document.querySelectorAll('.scope button').forEach(b=>b.onclick=()=>{SCOPE=b.dataset.sc;document.querySelectorAll('.scope button').forEach(x=>x.classList.toggle('on',x===b));CELL=null;buildList();render();});
document.querySelectorAll('.typ button').forEach(b=>b.onclick=()=>{TYP=b.dataset.ty;document.querySelectorAll('.typ button').forEach(x=>x.classList.toggle('on',x===b));CELL=null;buildList();render();});

let CUR=null,synth=null,part=null;
function openMod(i){const x=D.find(y=>y.i===i);CUR=x;
  document.getElementById('mtitle').textContent=`${x.title}${x.beatles?'':' · '+x.artist} — ${x.sec}`;
  document.getElementById('msub').textContent=`cell ${x.cellkey} beats ×${x.reps} · ${x.seq.join(' ')} · ${PCN[x.tonic]} ${x.scale} · ${x.bpm||'?'}bpm`;
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
