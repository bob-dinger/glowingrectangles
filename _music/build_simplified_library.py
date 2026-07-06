"""Build _music/simplified-library.html — the whole library's harmonic reductions,
grouped by the user's 50-song POOLS. Looks like songs.html: a left drawer (pool
pills + section list) and a main pane that renders EVERY section of the pool as full
piano rolls stacked one after another (8-bar rows, wrapping for 12/16), via
song_viewer.js — playable, with per-section copy-to-Hookpad-txt. See REDUCER.md."""
import os, json, html, collections
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2
import skeleton as sk
from find_structures import detect_grid, detect_pick, contour, motif, VOCAL, SKIP
from build_reductions import prog

SLUG2POOL = json.load(open('/tmp/slug2pool.json'))
BEATLES_PROJ = {k: tuple(v) for k, v in json.load(open('/tmp/beatles_proj.json')).items()}

def build_items():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("""select slug, title, artist, key_tonic, key_scale, bpm, hookpad_json,
                          coalesce(jsonb_array_length(hookpad_json->'notes'),0)
                   from parcels.songs where has_chords and has_melody and hookpad_json is not null""")
    best = {}
    for slug, title, artist, kt, ks, bpm, hj, nc in cur.fetchall():
        if slug.startswith('beatles_'):
            projn, pool = BEATLES_PROJ.get(slug, (99, 'Other / Anthology'))
        else:
            pool = SLUG2POOL.get(slug); projn = 999
            if not pool: continue
        notes = [x for x in (hj.get('notes') or []) if not x.get('isRest')]
        chords = hj.get('chords') or []; secs = hj.get('sections') or []
        nb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        if not (notes and chords and secs): continue
        endb = hj.get('endBeat') or max(x['beat'] for x in notes) + nb
        bpm = bpm or (hj.get('tempos') or [{}])[0].get('bpm') or 120
        done = set()
        for i, s in enumerate(secs):
            name = (s.get('name') or '').lower()
            if not any(v in name for v in VOCAL) or any(k in name for k in SKIP): continue
            sec = name.split()[0]
            if sec in done: continue
            b0 = s['beat']; b1 = secs[i+1]['beat'] if i+1 < len(secs) else endb
            sn = [x for x in notes if b0 <= x['beat'] < b1]
            scc = [x for x in chords if b0 <= x['beat'] < b1]
            if len(sn) < 4 or len(scc) < 3: continue
            done.add(sec)
            grid = detect_grid(sn, scc, nb, b1 - b0); pk = detect_pick(sn, scc, nb)
            red = sk.simplify_harmonic(sn, scc, merge=False, fill=True, measure=grid, pick=pk)
            r_mg = sk.simplify_harmonic(sn, scc, merge=True, measure=grid, pick=pk)
            if len(red) < 3 or len(r_mg) < 3: continue
            ct = contour([(int(''.join(ch for ch in str(n['sd']) if ch.isdigit()) or 0)) + 7*n['octave'] for n in r_mg])
            if not ct: continue
            sh = b0 - 1
            NB = [[str(n['sd']), n['octave'], round(n['beat']-sh, 3), n['duration']] for n in red]
            CB = [[cc['root'], round(cc['beat']-sh, 3), cc.get('duration', nb), cc.get('type', 5),
                   (cc.get('borrowed') if isinstance(cc.get('borrowed'), str) else '') or '', cc.get('applied', 0)] for cc in scc]
            item = {"song": title or slug, "artist": artist or "", "sec": sec, "pool": pool, "projn": projn,
                    "prog": prog(scc), "main": '-'.join(str(n['sd']) for n in r_mg),
                    "contour": ct, "motif": motif([str(n['sd']) for n in r_mg]),
                    "bars": round((b1-b0)/nb), "kt": kt or 'C', "ks": ks or 'major', "bpm": int(bpm), "nb": nb,
                    "n": NB, "c": CB}
            key = ((artist or '').lower().strip(), (title or slug).lower().strip(), sec)
            if key not in best or nc > best[key][0]:
                best[key] = (nc, item)
    c.close()
    return [v[1] for v in best.values()]

items = build_items()
items.sort(key=lambda i: (i['projn'], (i['song'] or '').lower(), i['sec']))
bpn = {}
for i in items:
    if i['projn'] < 999:
        bpn[i['pool']] = min(i['projn'], bpn.get(i['pool'], 999))
BEAT = [p for p, _ in sorted(bpn.items(), key=lambda x: x[1])]
POOLS = BEAT + [p for p in (f'G{n}' for n in range(50, 700, 50)) if any(i['pool'] == p for i in items)]
print("pooled sections:", len(items), "| pools:", {p: sum(1 for i in items if i['pool'] == p) for p in POOLS})
DATA = json.dumps(items, separators=(',', ':'))

PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Simplified Library — Glowing Gardens</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#1a1a1a;color:#e0e0e0;margin:0;height:100vh;overflow:hidden;display:flex;flex-direction:column}
  .back-link{position:fixed;top:15px;left:18px;color:#6a6a8a;text-decoration:none;font-size:13px;z-index:50}.back-link:hover{color:#e0e0e0}
  header{padding:10px 20px 10px 92px;border-bottom:1px solid #2a2a4a;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  header h1{font-size:17px;font-weight:700;margin:0}
  .pills{display:flex;gap:4px;flex-wrap:wrap}
  .pill{padding:4px 10px;background:#20203a;color:#e0e0e0;border:1px solid #2a2a4a;border-radius:12px;font-size:11px;font-weight:600;cursor:pointer}
  .pill:hover{background:#2a3a7a}.pill.on{background:#3050d0;border-color:#3050d0;color:#fff}.pill.ct.on{background:#6e16a5;border-color:#8e26c5}
  .transport{display:flex;gap:6px;align-items:center;margin-left:auto}
  .transport button{background:#2a2a4a;color:#e0e0e0;border:1px solid #3a3a5a;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600}
  .transport button:hover{background:#3a3a5a}.transport button.playing{background:#6e16a5;border-color:#8e26c5}
  .transport .tempo-input{width:48px;background:#16162a;color:#e0e0e0;border:1px solid #3a3a5a;border-radius:4px;padding:4px;text-align:center;font-size:12px}
  .transport label{font-size:11px;color:#8a8ab0;display:flex;align-items:center;gap:4px}
  .layout{flex:1;display:flex;min-height:0}
  .sidebar{width:300px;min-width:300px;background:#16162a;border-right:1px solid #2a2a4a;display:flex;flex-direction:column}
  .side-top{padding:8px 10px;border-bottom:1px solid #2a2a4a;display:flex;flex-direction:column;gap:7px}
  .side-top input{width:100%;padding:6px 9px;background:#1e1e3a;border:1px solid #2a2a4a;border-radius:6px;color:#e0e0e0;outline:none;font-size:12px;box-sizing:border-box}
  #seclist{flex:1;overflow-y:auto;padding:4px 0}
  .si{padding:6px 12px;cursor:pointer;display:flex;justify-content:space-between;gap:6px;align-items:center}
  .si:hover{background:#20203a}.si.active{background:#1e3a8a}
  .si .t{font-size:12px;color:#e0e0e0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .si .t small{color:#7a7a9a}
  .si .cp{opacity:0;font-size:10px;color:#a5b4fc;border:1px solid #3a3a5a;border-radius:3px;padding:1px 4px;flex-shrink:0}
  .si:hover .cp{opacity:1} .si .cp.ok{color:#22c55e;border-color:#22c55e;opacity:1}
  #poolMain{flex:1;overflow:auto;padding:12px;background:#1a1a1a}
  .cnt{color:#8a8ab0;font-size:11px;padding:2px 4px}
</style></head><body>
<a class="back-link" href="index.html">&larr; Music</a>
<header><h1>Simplified Library</h1>
  <div class="pills" id="contours"></div>
  <div class="transport">
    <button id="expPlayBtn">▶ Play</button><button id="expStopBtn">■</button>
    <label>BPM <input type="number" id="expTempoInput" class="tempo-input" min="40" max="260" value="100"></label>
    <select id="expDisplaySelect" class="tempo-input" style="width:auto"><option value="chord">chords</option><option value="roman">roman</option></select>
  </div></header>
<div class="layout">
  <aside class="sidebar">
    <div class="side-top"><div class="pills" id="pools"></div>
      <input id="q" placeholder="filter this group…"></div>
    <div class="cnt" id="cnt"></div>
    <div id="seclist"></div>
  </aside>
  <main style="flex:1;display:flex;flex-direction:column;min-height:0"><div id="poolMain"><div style="color:#6a6a8a;padding:40px;text-align:center">Pick a group.</div></div></main>
</div>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>
<script>
const DATA=__DATA__, POOLS=__POOLS__;
const CONTOURS=['oscillation','arch','descent','valley','ascent','pedal','wander'];
let pool=POOLS[0], active=new Set(), q='', shown=[];
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const viewer=new SongViewer({supabase:null,mainEl:'#poolMain',
  transport:{playBtn:'#expPlayBtn',stopBtn:'#expStopBtn',tempoInput:'#expTempoInput',displaySelect:'#expDisplaySelect'}});
function secDoc(it,sh){   // one section's notes/chords shifted to start at beat sh+1
  return {
    notes: it.n.map(a=>({sd:String(a[0]),octave:a[1],beat:a[2]+sh,duration:a[3],isRest:false,recordingEndBeat:null})),
    chords: it.c.map(a=>({root:a[0],beat:a[1]+sh,duration:a[2],type:a[3],inversion:0,applied:a[5],adds:[],omits:[],
      alterations:[],suspensions:[],substitutions:[],pedal:null,alternate:"",borrowed:a[4]||null,isRest:false,recordingEndBeat:null}))};
}
function pasteFor(it){
  const d=secDoc(it,0);
  return JSON.stringify({notes:d.notes,chords:d.chords,keys:[{beat:1,tonic:it.kt,scale:it.ks}],
    tempos:[{beat:1,bpm:it.bpm,swingFactor:0,swingBeat:0.5}],meters:[{beat:1,numBeats:it.nb,beatUnit:1}],
    sections:[{beat:1,name:it.sec}],breaks:[],endBeat:Math.ceil(Math.max(...d.chords.map(c=>c.beat+c.duration))/it.nb)*it.nb+1,
    audioTracks:[],version:1});
}
function buildPoolDoc(list){
  let cur=1, notes=[], chords=[], sections=[], keys=[];
  list.forEach(it=>{
    const d=secDoc(it,cur-1);
    notes.push(...d.notes); chords.push(...d.chords);
    sections.push({beat:cur,name:it.song+' · '+it.sec});
    keys.push({beat:cur,tonic:it.kt,scale:it.ks});
    const end=Math.max(...d.notes.map(n=>n.beat+n.duration),...d.chords.map(c=>c.beat+c.duration));
    cur=Math.ceil(end/4)*4+4;   // next section on a 4-bar boundary, +1 gap bar
  });
  return {notes,chords,keys,tempos:[{beat:1,bpm:100,swingFactor:0,swingBeat:0.5}],
    meters:[{beat:1,numBeats:4,beatUnit:1}],sections,breaks:[],endBeat:cur,audioTracks:[]};
}
function refresh(){
  shown=DATA.filter(it=>it.pool===pool && (!active.size||active.has(it.contour))
    && (!q || (it.song+' '+it.artist+' '+it.prog+' '+it.main+' '+it.sec+' '+it.contour).toLowerCase().includes(q)));
  document.getElementById('cnt').textContent=pool+' · '+shown.length+' sections';
  // sidebar list
  document.getElementById('seclist').innerHTML=shown.map((it,k)=>
    `<div class="si" data-k="${k}"><span class="t">${esc(it.song)} <small>· ${esc(it.sec)} · ${it.bars}b</small></span><span class="cp">⧉</span></div>`).join('');
  // main render (stacked piano rolls)
  viewer.loadData(buildPoolDoc(shown),{title:pool});
}
document.getElementById('pools').innerHTML=POOLS.map(p=>`<span class="pill${p===pool?' on':''}" data-p="${p}">${p}</span>`).join('');
document.getElementById('contours').innerHTML=CONTOURS.map(c=>`<span class="pill ct" data-c="${c}">${c}</span>`).join('');
document.getElementById('pools').onclick=e=>{const el=e.target.closest('.pill');if(!el)return;pool=el.dataset.p;
  document.querySelectorAll('#pools .pill').forEach(x=>x.classList.toggle('on',x.dataset.p===pool));refresh();};
document.getElementById('contours').onclick=e=>{const el=e.target.closest('.pill');if(!el)return;const c=el.dataset.c;
  if(active.has(c)){active.delete(c);el.classList.remove('on');}else{active.add(c);el.classList.add('on');}refresh();};
document.getElementById('q').addEventListener('input',e=>{q=e.target.value.toLowerCase().trim();refresh();});
document.getElementById('seclist').addEventListener('click',async e=>{
  const cp=e.target.closest('.cp'); const si=e.target.closest('.si'); if(!si)return; const it=shown[+si.dataset.k];
  if(cp){await navigator.clipboard.writeText(pasteFor(it));cp.textContent='✓';cp.classList.add('ok');setTimeout(()=>{cp.textContent='⧉';cp.classList.remove('ok');},1000);return;}
  document.querySelectorAll('.si.active').forEach(x=>x.classList.remove('active')); si.classList.add('active');
  const b=document.getElementById('sec-'+si.dataset.k); if(b)b.scrollIntoView({behavior:'smooth',block:'start'});});
refresh();
</script></body></html>'''.replace('__DATA__', DATA).replace('__POOLS__', json.dumps(POOLS))

out = '/Users/robert/Desktop/glowinggardens_claude/_music/simplified-library.html'
open(out, 'w').write(PAGE)
print("wrote", out, f"({len(PAGE)//1024} KB)")
