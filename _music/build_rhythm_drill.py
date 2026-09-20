#!/usr/bin/env python3
"""Build _music/rhythm-slots.html - a drill page for the 16-slot part types.

Data comes from window_types.py's census. Everything is inlined: Chromium
refuses fetch() on file:// so a page opened off disk would come up blank.
"""
import json, os, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'window_types.py')).read().split('ranked = sorted')[0]
ns = {}
exec(compile(src, 'window_types.py', 'exec'), ns)
pat_songs = ns['pat_songs']

NAMES = {
    (0, 8): "one per bar", (0,): "one, held", (0, 4, 8, 12): "two per bar",
    (0, 4, 8): "half half whole", (0, 8, 12): "whole half half",
    (0, 3, 8, 11): "two per bar, pushed", (0, 12): "three-one",
    (0, 7): "one per bar, pushed", (0, 8, 11): "whole, half, pushed half",
    (0, 4): "half, then held", (0, 4, 12): "half, whole, half",
    (0, 6, 8): "three-one, then whole", (0, 14): "held, late flick",
    (0, 4, 8, 12, 14): "two per bar + a flick",
}

def pretty(n):
    a, _, t = n.partition('_')
    return f"{t.title()} — {a.title()}" if t else n.title()

rows = sorted(pat_songs.items(), key=lambda kv: -len(kv[1]))[:18]
data = []
for k, ss in rows:
    data.append({
        "onsets": list(k),
        "name": NAMES.get(k, ""),
        "n": len(ss),
        "pushed": [o for o in k if o % 2],
        "songs": sorted(pretty(s) for s in ss)[:60],
    })

DEG = [1, 5, 6, 4]           # a plain axis so the ear hears rhythm, not harmony
def paste(onsets, windows=4):
    chords, i = [], 0
    for w in range(windows):
        for j, o in enumerate(onsets):
            nxt = onsets[j+1] if j+1 < len(onsets) else 16
            chords.append({
                "root": DEG[i % 4], "beat": w*8 + o/2, "duration": (nxt-o)/2,
                "type": 5, "inversion": 0, "applied": 0, "adds": [], "omits": [],
                "alterations": [], "suspensions": [], "substitutions": [],
                "pedal": 0, "alternate": 0, "borrowed": "", "isRest": False,
                "recordingEndBeat": 0})
            i += 1
    return {"notes": [], "chords": chords, "audioTracks": [], "version": 1}

for d in data:
    d["paste"] = json.dumps(paste(d["onsets"]), separators=(',', ':'))

tot = len(set().union(*pat_songs.values()))
OUT = os.path.join(HERE, 'rhythm-slots.html')
open(OUT, 'w').write("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Part Types — 16 Slots</title><style>
*{box-sizing:border-box}
body{margin:0;height:100vh;display:flex;font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
 background:#12121a;color:#e8e8f0;overflow:hidden}
aside{width:330px;flex:none;overflow-y:auto;border-right:1px solid #2a2a38;padding:14px 0}
main{flex:1;padding:26px 34px;overflow-y:auto}
h1{font-size:15px;margin:0 0 4px 22px;letter-spacing:.02em}
.sub{font-size:11px;color:#7b7b90;margin:0 0 14px 22px}
.item{padding:9px 22px;cursor:pointer;border-left:3px solid transparent;display:flex;
 align-items:center;gap:10px}
.item:hover{background:#1b1b26}
.item.on{background:#1f1f2e;border-left-color:#f0a040}
.item .nm{flex:1;font-size:12px}
.item .ct{font-size:11px;color:#7b7b90;font-variant-numeric:tabular-nums}
.mini{display:flex;gap:1px}
.mini i{width:5px;height:12px;background:#2a2a38;border-radius:1px}
.mini i.on{background:#5090f0}
.mini i.push{background:#f0a040}
.grid{display:flex;gap:3px;margin:18px 0 6px}
.grid b{width:30px;height:46px;background:#1c1c28;border-radius:3px;display:flex;
 align-items:flex-end;justify-content:center;font-size:9px;color:#54546a;padding-bottom:3px;font-weight:400}
.grid b.on{background:#5090f0;color:#fff}
.grid b.push{background:#f0a040;color:#1a1a2e}
.grid b.bar{box-shadow:inset 2px 0 0 #3a3a4c}
.ruler{display:flex;gap:3px;font-size:10px;color:#54546a;margin-bottom:20px}
.ruler span{width:30px;text-align:center}
h2{font-size:20px;margin:0 0 2px;font-weight:600}
.meta{color:#8a8aa0;font-size:12px;margin-bottom:4px}
.note{color:#f0a040;font-size:12px;margin:14px 0 0}
button{background:#2a2a3c;color:#e8e8f0;border:1px solid #3a3a50;border-radius:5px;
 padding:7px 13px;font:inherit;cursor:pointer;margin:18px 0 6px}
button:hover{background:#34344a}
.songs{columns:3;column-gap:26px;margin-top:18px;font-size:12px;color:#a8a8c0;
 border-top:1px solid #2a2a38;padding-top:14px}
.songs div{break-inside:avoid;padding:1px 0}
</style></head><body>
<aside><h1>Part types</h1><p class="sub">where the chords land in 2 bars<br>
blue = on the beat &middot; orange = pushed</p><div id="list"></div></aside>
<main id="detail"></main>
<script>
const DATA = """ + json.dumps(data) + """;
const TOTAL = """ + str(tot) + """;
const list = document.getElementById('list'), detail = document.getElementById('detail');
DATA.forEach((d,i)=>{
  const el = document.createElement('div'); el.className='item'; el.dataset.i=i;
  const mini = d.onsets.map(o=>o).reduce((a,o)=>a,0);
  let m = '<div class="mini">';
  for(let s=0;s<16;s++){
    const on = d.onsets.includes(s);
    m += `<i class="${on?(s%2?'on push':'on'):''}"></i>`;
  }
  m += '</div>';
  el.innerHTML = m + `<span class="nm">${d.name||'['+d.onsets.join(' ')+']'}</span>`
               + `<span class="ct">${d.n}</span>`;
  el.onclick = ()=>show(i); list.appendChild(el);
});
function show(i){
  const d = DATA[i];
  [...list.children].forEach(c=>c.classList.toggle('on', +c.dataset.i===i));
  let g='<div class="grid">', r='<div class="ruler">';
  for(let s=0;s<16;s++){
    const on=d.onsets.includes(s), cls=(on?(s%2?'on push':'on'):'')+(s%8===0?' bar':'');
    g += `<b class="${cls}">${s}</b>`;
    r += `<span>${s%2===0?(s/2+1):''}</span>`;
  }
  g+='</div>'; r+='</div>';
  const pushed = d.pushed.length
    ? `<p class="note">pushed: slot ${d.pushed.join(', ')} &mdash; an eighth early.
       Unpushed this is [${d.onsets.map(o=>o%2?o+1:o).join(', ')}].</p>` : '';
  detail.innerHTML = `<h2>${d.name||'['+d.onsets.join(' ')+']'}</h2>
    <div class="meta">[${d.onsets.join(', ')}] &middot; ${d.onsets.length} chord${d.onsets.length>1?'s':''}
      per 2 bars &middot; <b>${d.n}</b> songs (${(100*d.n/TOTAL).toFixed(0)}% of the library)</div>
    ${g}${r}${pushed}
    <button onclick='copyPaste(${i})'>Copy 8 bars as Hookpad paste</button>
    <div class="songs">${d.songs.map(s=>'<div>'+s+'</div>').join('')}</div>`;
}
function copyPaste(i){
  navigator.clipboard.writeText(DATA[i].paste).then(()=>{
    const b=document.querySelector('button'); const t=b.textContent;
    b.textContent='copied \\u2014 paste into Hookpad'; setTimeout(()=>b.textContent=t,1800);
  });
}
show(0);
</script></body></html>""")
print(f"  {OUT}")
print(f"  {len(data)} patterns, {tot:,} songs")
