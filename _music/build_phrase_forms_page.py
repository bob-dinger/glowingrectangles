"""Build _music/phrases.html — every Beatles section by its melodic phrase form.

Filterable by bar-scale (16 / 12 / 8) and by form (AABA, AABC, AAB, ...). Each row shows
the phrase letters; click for a piano-roll modal with the phrase boundaries drawn in.

Reuses the machinery in phrase_forms.py (meter-aware bars, melodic phrase labelling) and
the roll/modal style from build_forms_page.py.
"""
import os, re, json, html
from collections import Counter, defaultdict
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label
import phrase_forms as P

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phrases.html')
PCN = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
PCIDX = {n: i for i, n in enumerate(PCN)}
for _a, _b in [('C#', 1), ('D#', 3), ('F#', 6), ('G#', 8), ('A#', 10)]: PCIDX[_a] = _b
# bar-scale -> phrase bar-lengths (its natural cut). The odd lengths read as deformations
# of the 8-bar core, which is how they're heard: 7 = 8 minus a bar (4+3), 9 = 8 plus a bar
# (4+4+1), 10 = 8 plus two (4+4+2). 6 = three 2-bar phrases (the classic AAB); 8/12/16 even.
SCALES = {16: [4, 4, 4, 4], 12: [4, 4, 4], 10: [4, 4, 2], 9: [4, 4, 1],
          8: [2, 2, 2, 2], 7: [4, 3], 6: [2, 2, 2]}
ORDER = [16, 12, 10, 9, 8, 7, 6]

def tonic_pc(k):
    t = k.get('tonic', 0)
    pc = PCIDX.get(str(t), t if isinstance(t, int) else 0)
    return (pc + 3) % 12 if k.get('scale') == 'minor' else pc

def key_at(hj, beat):
    ks = sorted(hj.get('keys') or [{'beat': 1}], key=lambda k: k.get('beat', 0))
    cur = ks[0]
    for k in ks:
        if k.get('beat', 0) <= beat: cur = k
    return cur

def body(hj, b0, b1, scale):
    notes = []
    for n in hj.get('notes') or []:
        nb = n.get('beat', 0)
        if not (b0 <= nb < b1) or n.get('isRest'): continue
        sem = P.sd_semis(n.get('sd'))
        if sem is None: continue
        notes.append({'sd': str(n.get('sd')), 'sem': sem, 'o': int(n.get('octave', 0)),
                      'b': round(nb - b0, 3), 'd': round(n.get('duration', 1), 3)})
    chords = []
    for c in hj.get('chords') or []:
        cb, cd = c.get('beat', 0), c.get('duration', 1)
        if not c.get('root') or not 1 <= c['root'] <= 7: continue
        st, en = max(cb, b0), min(cb + cd, b1)
        if en > st: chords.append({'n': chord_label(c, scale), 'b': round(st - b0, 3), 'd': round(en - st, 3)})
    return notes, sorted(chords, key=lambda c: c['b'])

# ---- chord-form (harmonic phrase form) ----
def coretok(lbl):
    m = re.match(r"^([b#]*[ivxIVX]+(?:/[b#]*[ivxIVX]+)?)", lbl)
    return m.group(1) if m else lbl

def phrase_chords(hj, a, b, sc):
    out = []
    for c in hj.get('chords') or []:
        if not c.get('root') or not 1 <= c['root'] <= 7: continue
        cb, cd = c.get('beat', 0), c.get('duration', 1)
        s, e = max(cb, a), min(cb + cd, b)
        if e > s: out.append((coretok(chord_label(c, sc)), round(s - a, 2)))
    return tuple(sorted(out, key=lambda x: x[1]))

def clabel(phrases):
    reps, out = [], []
    for p in phrases:
        hit = None
        for L, rep in reps:
            if p == rep: hit = L; break
        if hit is None:
            for L, rep in reps:
                n = 0
                while n < min(len(p), len(rep)) and p[n] == rep[n]: n += 1
                if p and rep and n / max(len(p), len(rep)) >= 0.5: hit = L + "'"; break
        if hit is None: hit = chr(65 + len(reps)); reps.append((hit, p))
        out.append(hit)
    return ''.join(out)

def chord_form(hj, b0, plens, sc, offs):
    phs = [phrase_chords(hj, P.bar_at(hj, b0, offs[j]), P.bar_at(hj, b0, offs[j + 1]), sc)
           for j in range(len(plens))]
    return clabel(phs) if any(phs) else None

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select artist,title,hookpad_json,bpm from parcels.songs where hookpad_json is not null "
                "and (has_melody or has_chords)")
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -len((r[2] or {}).get('notes') or []))

    data = {}
    for bars in ORDER:
        plens = SCALES[bars]
        seen, items = set(), []
        for artist, t, hj, bpm in rows:
            t = (t or '').strip()
            if not t or P.VARIANT.search(t): continue
            k = P.norm((artist or '') + t)
            key = (k, bars)
            if key in seen: continue
            seen.add(key)
            beatles = 'beatle' in (artist or '').lower()
            perslug = set()
            for nm, b0, b1, stitched in P.spans(hj, bars):
                kk = key_at(hj, b0)
                sc = kk.get('scale', 'major'); sc = sc if sc in ('major', 'minor') else 'major'
                mform, offs = P.form_and_offsets(hj, b0, plens)          # melody form
                if not offs:                                            # no melody -> still want offsets for chords
                    offs = [0]
                    for L in plens: offs.append(offs[-1] + L)
                cform = chord_form(hj, b0, plens, sc, offs)             # harmonic form
                if not mform and not cform: continue
                sig = (re.sub(r'[^a-z]', '', nm.lower()), mform, cform)
                if sig in perslug: continue
                perslug.add(sig)
                notes, chords = body(hj, b0, b1, sc)
                mlabs = re.findall(r"[A-Z]'?", mform or '')
                clabs = re.findall(r"[A-Z]'?", cform or '')
                phrases = []
                for j in range(len(plens)):
                    pa = round(P.bar_at(hj, b0, offs[j]) - b0, 3)
                    pe = round(P.bar_at(hj, b0, offs[j + 1]) - b0, 3)
                    phrases.append({'b': pa, 'e': pe,
                                    'm': mlabs[j] if j < len(mlabs) else '',
                                    'c': clabs[j] if j < len(clabs) else ''})
                items.append({'m': mform or '', 'c': cform or '', 'title': t, 'artist': artist or '',
                              'beatles': beatles, 'sec': nm, 'stitched': stitched, 'bars': bars,
                              'tonic': tonic_pc(kk), 'scale': sc,
                              'bpm': (hj.get('tempos') or [{}])[0].get('bpm') or bpm,
                              'notes': notes, 'chords': chords, 'phrases': phrases})
        for i, it in enumerate(items): it['i'] = i
        data[str(bars)] = items
        nb = sum(1 for x in items if not x['beatles'])
        print(f'  {bars}-bar: {len(items)} sections ({len(items)-nb} Beatles, {nb} other)')

    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps(data)))
    print(f'wrote {OUT}')

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Phrase Forms</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:250px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff;padding-bottom:20px}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:14px 16px 4px;margin:0}
.scaletog{display:flex;gap:6px;padding:8px 14px}
.scaletog button{flex:1;padding:8px 0;border:1px solid #ccd;background:#f6f6fb;border-radius:7px;cursor:pointer;font-weight:600;color:#556}
.scaletog button.on{background:#2a2a44;color:#fff;border-color:#2a2a44}
.tog2{display:flex;gap:6px;padding:2px 14px 8px}
.tog2 button{flex:1;padding:6px 0;border:1px solid #ccd;background:#f6f6fb;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;color:#556}
.tog2 button.on{background:#8a2be2;color:#fff;border-color:#8a2be2}
.tog2.scope button.on{background:#2a7a44;border-color:#2a7a44}
.frow{padding:6px 16px;cursor:pointer;border-bottom:1px solid #f2f2f6;display:flex;justify-content:space-between;gap:8px;align-items:center}
.frow:hover{background:#eef}.frow.on{background:#2a2a44;color:#fff}
.frow .fm{font-weight:700;letter-spacing:.03em}.frow .ct{font-size:11px;color:#aaa}.frow.on .ct{color:#dde}
.frow.all{border-bottom:2px solid #ddd;font-style:italic}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}.meta{color:#888;font-size:12px;margin-bottom:14px}
.sec{display:flex;align-items:baseline;gap:12px;padding:6px 0;border-bottom:1px solid #ededf2;cursor:pointer}
.sec:hover{background:#f6f6ff}
.sec .ph{width:120px;flex:none;display:flex;gap:2px}
.pl{font:700 11px/18px ui-monospace,monospace;color:#fff;width:26px;text-align:center;border-radius:3px}
.sec .t{font-weight:600;font-size:13px}.sec .t .sub{color:#aaa;font-weight:400;font-size:11px;margin-left:8px}
.sec .t .be{color:#c0392b;font-size:10px;font-weight:700;margin-left:6px}
.other{font-size:10px;font-weight:700;border-radius:4px;padding:1px 6px;margin-left:8px}
.other.m{color:#5090f0;background:#eaf2fe}.other.c{color:#8a2be2;background:#f3ecff}
/* modal (from forms.html) */
#ov{position:fixed;inset:0;background:rgba(20,20,35,.55);display:none;align-items:center;justify-content:center;z-index:50}
#ov.on{display:flex}
#mod{background:#fff;border-radius:12px;padding:18px 20px;max-width:min(1100px,94vw);max-height:90vh;overflow:auto;box-shadow:0 18px 60px rgba(0,0,0,.3)}
#mod h3{margin:0 0 2px;font-size:17px}#mod .mmeta{color:#888;font-size:12px;margin-bottom:12px}
#mod .close{float:right;cursor:pointer;color:#aaa;font-size:20px;padding:0 4px}#mod .close:hover{color:#333}
.roll{position:relative;border:1px solid #e4e4ec;border-radius:8px;background:#fbfbfe;overflow-x:auto}
.rollin{position:relative}.lane.tonic{position:absolute;left:0;right:0;height:1px;background:#d8d8ea}
.barline{position:absolute;top:0;bottom:0;width:1px;background:#e8e8f0}.barline.b4{background:#d4d4e2}
.pdiv{position:absolute;top:0;bottom:22px;width:0;border-left:2px dashed #b03030;opacity:.6}
.plab{position:absolute;top:3px;font:700 12px/16px ui-monospace,monospace;color:#fff;padding:0 6px;border-radius:4px}
.nb{position:absolute;height:9px;border-radius:3px;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cb{position:absolute;bottom:0;height:22px;border-radius:4px;color:#fff;font:700 10px/22px sans-serif;text-align:center;text-shadow:0 1px 2px rgba(0,0,0,.4);overflow:hidden;white-space:nowrap}
.mtools{display:flex;gap:10px;align-items:center;margin-top:10px;font-size:12px}
.mtools button{padding:5px 12px;border:1px solid #ccd;background:#f6f6fb;border-radius:7px;cursor:pointer;font-weight:600}
</style></head><body><div id=wrap>
<div id=side>
  <div class=scaletog><button data-s=16 class=on>16</button><button data-s=12>12</button><button data-s=10>10</button><button data-s=9>9</button><button data-s=8>8</button><button data-s=7>7</button><button data-s=6>6</button></div>
  <div class="tog2 ftype"><button data-f=m class=on>melody form</button><button data-f=c>chord form</button></div>
  <div class="tog2 scope"><button data-sc=beatles class=on>Beatles</button><button data-sc=others>others</button><button data-sc=all>all</button></div>
  <h1>Phrase form</h1><div id=list></div>
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
const PHCOL=['#5090f0','#e8734a','#50c878','#a878d8','#e0a030','#d060a0'];  // A B C D by first-seen
let SC='16',FORM=null,FT='m',SCOPE='beatles';   // form-type: m=melody c=chord ; scope
const inScope=x=>SCOPE==='all'||(SCOPE==='beatles'?x.beatles:!x.beatles);
const formOf=x=>FT==='m'?x.m:x.c;
const R2D={i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7},D2S={1:0,2:2,3:4,4:5,5:7,6:9,7:11};
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
const NICE=n=>Number.isInteger(n)?n:Math.round(n*100)/100;

function phraseColors(form){const map={},cols={};let ci=0;
  (form.match(/[A-Z]/g)||[]).forEach(L=>{if(!(L in cols)){cols[L]=PHCOL[ci++%PHCOL.length];}});return cols;}
function buildList(){
  const items=D[SC].filter(x=>inScope(x)&&formOf(x)), forms={};
  items.forEach(x=>{const f=formOf(x);forms[f]=(forms[f]||0)+1;});
  const L=document.getElementById('list');
  let h=`<div class="frow all${FORM===null?' on':''}" onclick="pick(null)"><span class=fm>all forms</span><span class=ct>${items.length}</span></div>`;
  Object.keys(forms).sort((a,b)=>forms[b]-forms[a]||a.localeCompare(b)).forEach(f=>{
    h+=`<div class="frow${FORM===f?' on':''}" onclick="pick('${f.replace(/'/g,"\\'")}')"><span class=fm>${f}</span><span class=ct>${forms[f]}</span></div>`;});
  L.innerHTML=h;
}
function pick(f){FORM=f;render();buildList();}
function render(){
  const items=D[SC].filter(x=>inScope(x)&&formOf(x)&&(FORM===null||formOf(x)===FORM));
  const kind=FT==='m'?'melody':'chord';
  document.getElementById('ttl').textContent=`${SC}-bar · ${kind} form · ${FORM||'all'}`;
  document.getElementById('sub').textContent=`${items.length} sections · letters track the ${kind==='melody'?'melody':'chord progression'} · the other reading is shown small · click for the piano roll`;
  document.getElementById('body').innerHTML=items.sort((a,b)=>formOf(a).localeCompare(formOf(b))||a.title.localeCompare(b.title)).map(x=>{
    const f=formOf(x),cols=phraseColors(f);
    const chips=x.phrases.map(p=>{const L=(FT==='m'?p.m:p.c);return `<span class=pl style="background:${L?cols[L[0]]:'#ccc'}">${L||'·'}</span>`;}).join('');
    const other=FT==='m'?x.c:x.m; const olab=FT==='m'?'chords':'mel';
    const oth=(other&&other!==f)?`<span class="other ${FT==='m'?'c':'m'}">${olab} ${other}</span>`:'';
    const be=x.beatles?'':`<span class=be>${x.artist}</span>`;
    return `<div class=sec onclick="openMod('${SC}',${x.i})"><div class=ph>${chips}</div>
      <div class=t>${x.title}${be}<span class=sub>${x.sec} · ${PCN[x.tonic]} ${x.scale}${x.stitched?' · composite':''}</span>${oth}</div></div>`;
  }).join('');
}
function reset(){FORM=null;buildList();render();}
document.querySelectorAll('.scaletog button').forEach(b=>b.onclick=()=>{
  SC=b.dataset.s;document.querySelectorAll('.scaletog button').forEach(x=>x.classList.toggle('on',x===b));reset();});
document.querySelectorAll('.ftype button').forEach(b=>b.onclick=()=>{
  FT=b.dataset.f;document.querySelectorAll('.ftype button').forEach(x=>x.classList.toggle('on',x===b));reset();});
document.querySelectorAll('.scope button').forEach(b=>b.onclick=()=>{
  SCOPE=b.dataset.sc;document.querySelectorAll('.scope button').forEach(x=>x.classList.toggle('on',x===b));reset();});

// ---- modal / roll (melody by degree colour, chord names, phrase dividers) ----
let CUR=null,synth=null,part=null;
function openMod(sc,i){const x=D[sc].find(y=>y.i===i);CUR=x;
  document.getElementById('mtitle').textContent=`${x.title}${x.beatles?'':' · '+x.artist} — ${x.sec}`;
  const both=`melody ${x.m||'—'} · chords ${x.c||'—'}`;
  document.getElementById('msub').textContent=`${both} · ${x.bars} bars · ${PCN[x.tonic]} ${x.scale} · ${x.bpm||'?'}bpm`;
  drawRoll(x);document.getElementById('ov').classList.add('on');}
function closeMod(){document.getElementById('ov').classList.remove('on');stopPlay();}
document.getElementById('ov').onclick=e=>{if(e.target.id==='ov')closeMod();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMod();});
function drawRoll(b){
  const beats=Math.max(b.bars*4,...b.chords.map(c=>c.b+c.d),...b.notes.map(n=>n.b+n.d),4);
  const PX=Math.max(9,Math.min(20,900/beats)),H=200,CH=26,cols=phraseColors(FT==='m'?b.m:b.c);
  const vals=b.notes.map(n=>n.sem+12*n.o);const lo=vals.length?Math.min(...vals):0,hi=vals.length?Math.max(...vals):12;
  const span=Math.max(hi-lo,7),top=20,usable=H-CH-28,y=v=>top+usable-((v-lo)/span)*usable;
  let h=`<div class=rollin style="width:${Math.ceil(beats*PX)}px;height:${H}px">`;
  for(let v=Math.floor(lo/12)*12;v<=hi+1;v+=12)h+=`<div class="lane tonic" style="top:${y(v)}px"></div>`;
  for(let bar=0;bar<=Math.ceil(beats/4);bar++)h+=`<div class="barline${bar%4===0?' b4':''}" style="left:${bar*4*PX}px"></div>`;
  b.phrases.forEach(p=>{const lab=(FT==='m'?p.m:p.c);if(!lab)return;const L=lab[0];
    h+=`<div class=pdiv style="left:${p.b*PX}px"></div>`;
    h+=`<div class=plab style="left:${p.b*PX+4}px;background:${cols[L]}">${lab}</div>`;});
  b.chords.forEach(c=>{h+=`<div class=cb title="${c.n}" style="left:${c.b*PX}px;width:${Math.max(c.d*PX-2,14)}px;background:${chordBg(c.n)}">${chordName(c.n,b.tonic)}</div>`;});
  b.notes.forEach(n=>{const v=n.sem+12*n.o;
    h+=`<div class=nb title="${n.sd}" style="left:${n.b*PX}px;top:${y(v)}px;width:${Math.max(n.d*PX-2,4)}px;background:${degBg(n.sem)}"></div>`;});
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
