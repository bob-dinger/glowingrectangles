#!/usr/bin/env python
"""Generate blues.html — every 12-bar-blues section in the library on the grid,
classified by which 'joints' it bends (quick-change, IV-start, turnaround, color).
Data from parcels.songs.hookpad_json. Tone.js playback (rendered in C)."""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_KEY'])
rows = []; step = 200; off = 0
while True:
    r = sb.schema('parcels').table('songs').select('artist,title,bpm,key_tonic,key_scale,hookpad_url,ug_url,hookpad_json').range(off, off+step-1).execute().data
    if not r: break
    rows += r; off += step
    if len(r) < step: break

def clean(t):
    t = re.sub(r'_(ly|o|completed|right|left|simple|hooktab)\b', '', t or '', flags=re.I)
    t = re.sub(r'\([^)]*\)', '', t); t = re.sub(r'[_]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()
def norm(t): return re.sub(r'[^a-z0-9]', '', (t or '').lower())
def disp(t):
    t = clean(t)
    if t == t.lower():
        t = t.title()
        t = re.sub(r"'(\w)", lambda m: "'" + m.group(1).lower(), t)  # Don'T->Don't, I'Ll->I'll
    return t
def better(a, b):
    """prefer the title with more case/punctuation info."""
    score = lambda s: (any(c.isupper() for c in s), "'" in s, len(s))
    return a if score(a) >= score(b) else b

def grid_of(hj, start, nxt, nb):
    """Return list of 12 (root,type) — primary chord per bar — or None."""
    chords = sorted([c for c in (hj.get('chords') or []) if start <= c.get('beat', 0) < nxt], key=lambda c: c['beat'])
    if not chords: return None
    cells = []
    prev = None
    for b in range(12):
        bs = start + b*nb
        inbar = [c for c in chords if bs <= c['beat'] < bs+nb]
        c = inbar[0] if inbar else prev
        if c is None:
            nxtc = [x for x in chords if x['beat'] >= bs]
            c = nxtc[0] if nxtc else chords[-1]
        prev = c
        cells.append((c.get('root'), str(c.get('type', '5'))))
    return cells

def classify(cells):
    roots = [r for r, _ in cells]
    types = [t for _, t in cells]
    quick = roots[1] == 4
    iv_start = roots[0] == 4
    dom7 = types.count('7') >= 7
    power = types.count('5') >= 7
    color = 'dom7' if dom7 else 'power' if power else 'triad'
    turn = f'{ {1:"I",4:"IV",5:"V"}.get(roots[10],"?")}–{ {1:"I",4:"IV",5:"V"}.get(roots[11],"?")}'
    return {'quick': quick, 'iv_start': iv_start, 'color': color, 'turn': turn}

seen = {}  # (art,title,signature) -> entry
for r in rows:
    hj = r.get('hookpad_json')
    if not isinstance(hj, dict): continue
    secs = hj.get('sections') or []; end = hj.get('endBeat')
    nb = (hj.get('meters') or [{}])[0].get('numBeats', 4) or 4
    for i, s in enumerate(secs):
        st = s['beat']; nx = secs[i+1]['beat'] if i+1 < len(secs) else end
        if not nx or round((nx-st)/nb) != 12: continue
        rootsall = [c.get('root') for c in (hj.get('chords') or []) if st <= c.get('beat', 0) < nx and c.get('root')]
        if len(rootsall) < 6 or not set(rootsall) <= {1, 4, 5} or 4 not in rootsall or 5 not in rootsall: continue
        cells = grid_of(hj, st, nx, nb)
        if not cells or any(c[0] not in (1, 4, 5) for c in cells): continue
        akey = norm(re.sub(r'^the\s+', '', clean(r['artist']).lower()))
        sig = tuple(cells)
        key = (akey, norm(clean(r['title'])), sig)
        if key in seen:
            seen[key]['count'] += 1
            seen[key]['title'] = better(seen[key]['title'], disp(r['title']))
            seen[key]['hookpad'] = seen[key]['hookpad'] or r.get('hookpad_url')
            seen[key]['ug'] = seen[key]['ug'] or r.get('ug_url')
            continue
        cl = classify(cells)
        seen[key] = {'artist': disp(r['artist']), 'title': disp(r['title']), 'section': s.get('name', '?'),
                     'cells': [[c[0], c[1]] for c in cells], 'bpm': r.get('bpm') or 120,
                     'key': f"{r.get('key_tonic','')} {r.get('key_scale','')}".strip(),
                     'hookpad': r.get('hookpad_url'), 'ug': r.get('ug_url'), 'count': 1, **cl}

data = sorted(seen.values(), key=lambda d: (d['artist'].lower(), d['title'].lower()))
n_songs = len({(d['artist'], d['title']) for d in data})

DOC = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>12-Bar Blues — Glowing Gardens</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html,body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#1a1a2e; color:#e0e0e0; }
.back-link { position:fixed; top:20px; left:20px; color:#4a4a6a; text-decoration:none; font-size:13px; z-index:100; }
.back-link:hover { color:#e0e0e0; }
.wrap { max-width:1180px; margin:0 auto; padding:40px 28px 70px; }
.header { text-align:center; margin-bottom:8px; }
.header h1 { font-size:26px; font-weight:700; }
.header p { font-size:13px; color:#6a6a8a; margin-top:6px; max-width:680px; margin-left:auto; margin-right:auto; line-height:1.5; }
.controls { display:flex; gap:8px; justify-content:center; align-items:center; flex-wrap:wrap; margin:22px 0 26px; position:sticky; top:0; background:#1a1a2e; padding:12px 0; z-index:50; }
#q { background:#16162a; border:1px solid #2a2a4a; border-radius:8px; padding:8px 12px; color:#e0e0e0; font-size:13px; width:220px; }
#q:focus { outline:none; border-color:#5a5a8a; }
.filt { font-size:12px; font-weight:600; padding:6px 11px; border-radius:6px; border:1px solid #2a2a4a; background:#16162a; color:#8a8aaa; cursor:pointer; }
.filt.on { background:#26264a; color:#e0e0e0; border-color:#4a4a7a; }
.count { font-size:12px; color:#6a6a8a; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(370px,1fr)); gap:14px; }
.song { background:#16162a; border:1px solid #2a2a4a; border-radius:11px; padding:15px 16px; }
.song .top { display:flex; justify-content:space-between; align-items:baseline; gap:8px; }
.song h3 { font-size:14.5px; font-weight:600; }
.song .art { font-size:11px; color:#6a6a8a; margin-top:1px; }
.song .meta { font-size:10.5px; color:#5a5a8a; white-space:nowrap; }
.bars { display:grid; grid-template-columns:repeat(4,1fr); gap:4px; margin:12px 0 10px; }
.bar { position:relative; height:34px; border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; border:1px solid transparent; }
.bar .n { position:absolute; top:1px; left:3px; font-size:8px; font-weight:600; opacity:.5; }
.bar .sup { font-size:8px; vertical-align:super; opacity:.8; margin-left:1px; }
.d1 { background:rgba(220,60,60,.22); color:#ffb0b0; }
.d4 { background:rgba(50,180,80,.22); color:#90e8a8; }
.d5 { background:rgba(60,120,220,.22); color:#98bcf8; }
.bar.playing { border-color:#f0e0a0; box-shadow:0 0 0 1px #f0e0a0; filter:brightness(1.35); }
.tags { display:flex; flex-wrap:wrap; gap:5px; margin-bottom:9px; }
.tag { font-size:9.5px; font-weight:600; padding:2px 7px; border-radius:4px; background:#22223e; color:#9a9ac0; }
.tag.hot { background:rgba(230,140,40,.2); color:#ffc888; }
.foot { display:flex; align-items:center; gap:10px; }
.play { font-size:12px; font-weight:600; padding:5px 13px; border-radius:6px; border:1px solid #3a3a5a; background:#1e1e3a; color:#d8d8f0; cursor:pointer; }
.play:hover { filter:brightness(1.25); }
.foot a { font-size:10.5px; color:#5a5a8a; text-decoration:none; }
.foot a:hover { color:#a5a8fc; }
.legend { text-align:center; font-size:11px; color:#6a6a8a; margin-bottom:18px; }
.legend b { padding:1px 6px; border-radius:3px; }
</style></head><body>
<a href="index.html" class="back-link">&larr; Back</a>
<div class="wrap">
  <div class="header">
    <h1>&#127928; The 12-Bar Blues</h1>
    <p>Every 12-bar-blues section in the library on one grid &mdash; three 4-bar lines, I&ndash;IV&ndash;V. They share a skeleton but bend it at the same joints. Filter by the bend; hit play to hear each (rendered in C).</p>
  </div>
  <div class="legend"><b class="d1">I</b>&nbsp;&nbsp;<b class="d4">IV</b>&nbsp;&nbsp;<b class="d5">V</b>&nbsp;&nbsp;&middot;&nbsp; <sup>7</sup> = dominant 7th</div>
  <div class="controls">
    <input id="q" type="text" placeholder="Search&hellip;" autocomplete="off">
    <button class="filt on" data-f="all">All</button>
    <button class="filt" data-f="quick">Quick-change</button>
    <button class="filt" data-f="slow">Slow-change</button>
    <button class="filt" data-f="iv_start">IV-start</button>
    <button class="filt" data-f="dom7">Dom7</button>
    <button class="filt" data-f="power">Power</button>
    <span class="count" id="count"></span>
  </div>
  <div class="grid" id="grid"></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/tone/15.3.5/Tone.js"></script>
<script>
const DATA = __DATA__;
const grid = document.getElementById('grid'), q = document.getElementById('q'), countEl = document.getElementById('count');
let filt = 'all';
const DEG = {1:'d1',4:'d4',5:'d5'}, LAB = {1:'I',4:'IV',5:'V'};
function passes(d){
  if (filt==='quick') return d.quick;
  if (filt==='slow') return !d.quick && !d.iv_start;
  if (filt==='iv_start') return d.iv_start;
  if (filt==='dom7') return d.color==='dom7';
  if (filt==='power') return d.color==='power';
  return true;
}
function render(){
  const term=q.value.trim().toLowerCase(); grid.innerHTML=''; let n=0;
  DATA.forEach((d,idx)=>{
    if(!passes(d)) return;
    if(term && !(d.title.toLowerCase().includes(term)||d.artist.toLowerCase().includes(term))) return;
    n++;
    const cells=d.cells.map((c,i)=>{
      const sup = c[1]==='7' ? '<span class="sup">7</span>' : '';
      return `<div class="bar ${DEG[c[0]]}" data-bar="${i}"><span class="n">${i+1}</span>${LAB[c[0]]}${sup}</div>`;
    }).join('');
    const tags=[];
    tags.push(d.quick?'<span class="tag hot">quick-change</span>':(d.iv_start?'<span class="tag hot">IV-start</span>':'<span class="tag">slow-change</span>'));
    tags.push(`<span class="tag">turn ${d.turn}</span>`);
    tags.push(`<span class="tag">${d.color}</span>`);
    if(d.count>1) tags.push(`<span class="tag">×${d.count}</span>`);
    let links=''; if(d.hookpad) links+=`<a target="_blank" rel="noopener" href="${d.hookpad}">Hookpad</a>`; if(d.ug) links+=`<a target="_blank" rel="noopener" href="${d.ug}">UG</a>`;
    const el=document.createElement('div'); el.className='song'; el.dataset.idx=idx;
    el.innerHTML=`<div class="top"><div><h3>${d.title}</h3><div class="art">${d.artist} &middot; ${d.section}</div></div>`
      +`<div class="meta">${d.key||''}<br>${d.bpm} bpm</div></div>`
      +`<div class="bars">${cells}</div><div class="tags">${tags.join('')}</div>`
      +`<div class="foot"><button class="play" data-idx="${idx}">&#9654; Play</button>${links}</div>`;
    grid.appendChild(el);
  });
  countEl.textContent = n+' sections';
}
document.querySelectorAll('.filt').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.filt').forEach(x=>x.classList.remove('on')); b.classList.add('on'); filt=b.dataset.f; render();
}));
q.addEventListener('input',render);

// ---- playback ----
let synth=null, bass=null, playingIdx=null;
function ensure(){ if(synth) return;
  synth=new Tone.PolySynth(Tone.Synth,{oscillator:{type:'triangle'},envelope:{attack:.02,decay:.3,sustain:.35,release:.6},volume:-11}).toDestination();
  bass=new Tone.Synth({oscillator:{type:'triangle'},envelope:{attack:.02,decay:.4,sustain:.5,release:.9},volume:-15}).toDestination();
}
const SEMI={1:0,4:5,5:7};       // I=C IV=F V=G
function notes(root,type){ const b=60+SEMI[root]; const arr=[b,b+4,b+7]; if(type==='7') arr.push(b+10); return arr.map(m=>Tone.Frequency(m,'midi').toNote()); }
function bassNote(root){ return Tone.Frequency(36+SEMI[root],'midi').toNote(); }
async function play(idx){
  const d=DATA[idx]; await Tone.start(); ensure();
  Tone.Transport.stop(); Tone.Transport.cancel();
  clearHi();
  Tone.Transport.bpm.value = Math.min(Math.max(d.bpm,60),220);
  const card=grid.querySelector(`.song[data-idx="${idx}"]`);
  d.cells.forEach((c,i)=>{
    const time=i+':0:0';
    Tone.Transport.schedule(t=>{
      synth.triggerAttackRelease(notes(c[0],c[1]),'0:3:2',t);
      bass.triggerAttackRelease(bassNote(c[0]),'0:3:2',t);
      Tone.Draw.schedule(()=>{ if(card){ card.querySelectorAll('.bar').forEach(b=>b.classList.remove('playing')); const bb=card.querySelector(`.bar[data-bar="${i}"]`); if(bb) bb.classList.add('playing'); }},t);
    },time);
  });
  Tone.Transport.schedule(()=>{ Tone.Draw.schedule(()=>{ stop(); }); }, '12:0:0');
  Tone.Transport.position='0:0:0'; Tone.Transport.start(); playingIdx=idx;
  if(card) card.querySelector('.play').innerHTML='&#9632; Stop';
}
function clearHi(){ grid.querySelectorAll('.bar.playing').forEach(b=>b.classList.remove('playing')); }
function stop(){ Tone.Transport.stop(); Tone.Transport.cancel(); clearHi();
  if(playingIdx!=null){ const c=grid.querySelector(`.song[data-idx="${playingIdx}"] .play`); if(c) c.innerHTML='&#9654; Play'; }
  playingIdx=null;
}
grid.addEventListener('click',e=>{ const btn=e.target.closest('.play'); if(!btn) return; const idx=+btn.dataset.idx; if(playingIdx===idx) stop(); else { stop(); play(idx); } });
render();
</script>
</body></html>"""

out = DOC.replace('__DATA__', json.dumps(data))
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blues.html')
open(path, 'w').write(out)
print(f'wrote {path}: {len(data)} sections, {n_songs} songs')
