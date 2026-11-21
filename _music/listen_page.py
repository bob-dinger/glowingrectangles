"""A local listening page for every song downloaded from YouTube.

    listen_page.py        # writes ~/Desktop/music/listen.html (rerun to pick up new downloads)

Reads the download manifests in ~/Desktop/music/audio_work (library + Hot 100),
joins each song to its Billboard Hot 100 run (peak, weeks, first year), its
tempo (measured from the record when we have it, else songbpm) and key, and
writes one self-contained page that plays the files straight from audio_work.
The page and the audio stay on this machine, never in the repo or on the site.
"""
import csv, html, json, os, re

M = os.path.expanduser('~/Desktop/music')
YT, BB = f'{M}/audio_work/youtube', f'{M}/audio_work/billboard'
OUT = f'{M}/listen.html'
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower().replace('&', 'and'))
tnorm = lambda t: norm(re.sub(r'^(the|a) ', '', re.sub(r'\(.*?\)|\[.*?\]', '', (t or '').lower().replace('’', "'")).strip()).replace("in'", 'ing'))
anorm = lambda a: norm(re.sub(r'^the ', '', (a or '').lower().strip()))
FULL = {'rhcp': 'redhotchilipeppers', 'ccr': 'creedenceclearwaterrevival', 'hootie': 'hootieandtheblowfish', 'elo': 'electriclightorchestra',
        'hallandoates': 'darylhalljohnoates', 'jimihendrix': 'jimihendrixexperience'}
load = lambda f: json.load(open(f)) if os.path.exists(f) else []


def chart():
    songs = {}
    for r in csv.DictReader(open(f'{M}/billboard/hot-100-current.csv')):
        d = songs.setdefault((r['title'], r['performer']), dict(peak=101, weeks=0, year=9999))
        d['peak'] = min(d['peak'], int(r['current_week'])); d['weeks'] += 1; d['year'] = min(d['year'], int(r['chart_week'][:4]))
    idx = {}
    for (t, p), d in songs.items():
        for side in t.split('/'):
            idx.setdefault(tnorm(side), []).append((anorm(p), d))
    return idx


def title_case(s):
    if any(c.isupper() for c in s): return s
    small = {'a', 'an', 'and', 'the', 'of', 'in', 'on', 'to', 'for', 'at', 'by', 'or'}
    return ' '.join(w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(s.split()))


def main():
    idx = chart()
    def fold(v, ref):                       # put a measured tempo in the same half/double counting as the sheet, else 60-185
        if ref: return min((v * m for m in (.5, 1, 2)), key=lambda x: abs(x - ref))
        while v > 185: v /= 2
        while v < 60: v *= 2
        return v
    measured = {norm(v['title']): fold(v['best'], v.get('sheet') or v.get('file')) for v in load(f'{YT}/batch1_verify.json') + load(f'{YT}/pilot_verify.json')}
    back = {k: v for k, v in (load(f'{YT}/songbpm_backfill.json') or {}).items()} if os.path.exists(f'{YT}/songbpm_backfill.json') else {}
    rows, seen = [], set()
    for f, kind in [(f'{YT}/fixes_manifest.json', None), (f'{YT}/pilot_manifest.json', 'list'), (f'{YT}/batch1_manifest.json', 'list'), (f'{YT}/library_manifest.json', None),
                    (f'{BB}/manifest.json', 'hot100')]:
        for r in load(f):
            p = r.get('file')
            if not p or not os.path.exists(p) or p in seen or r.get('url') in seen: continue   # same video under two spellings (BØRNS / Borns)
            seen.update({p, r.get('url')})
            src = r.get('src') or (f"Guitar{r['list']}" if r.get('list') else 'Guitar50' if 'pilot' in f else '')
            k = kind or ('list' if src.startswith('Guitar') else 'library')
            a = anorm(r['artist']); a = FULL.get(a, a)
            hit = next((d for pa, d in idx.get(tnorm(r['title']), []) if a[:5] and (a[:5] in pa or pa[:5] in a)), None)
            bf = back.get(f"{r['artist']}|{r['title']}", {})
            bpm = measured.get(norm(r['title'])) or r.get('songbpm_bpm') or bf.get('bpm')
            key = r.get('songbpm_key') or bf.get('key') or r.get('sheet_key')
            rows.append(dict(t=title_case(r['title']), a=title_case(r['artist']), k=k, s=src.replace('hot100 peak ', '#'),
                             y=hit['year'] if hit else None, p=hit['peak'] if hit else None, w=hit['weeks'] if hit else None,
                             b=round(bpm) if bpm else None, m=bool(measured.get(norm(r['title']))), key=key,
                             f=os.path.relpath(p, M), len=r.get('yt_len')))
    data = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
    open(OUT, 'w').write(PAGE.replace('__DATA__', data).replace('__N__', str(len(rows))))
    print(f'{len(rows)} songs -> file://{OUT}')


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Listening Room</title>
<style>
:root{--bg:#f6f4ef;--panel:#fffdf8;--ink:#1d1b18;--mute:#7a746a;--line:#e4dfd4;--acc:#b5542c;--acc2:#2f6f5e;--hl:#fbe9dd;--chip:#efe9dd}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141311;--panel:#1c1a17;--ink:#ece7dd;--mute:#9a9284;--line:#2e2b26;--acc:#e07a4c;--acc2:#5fb39c;--hl:#3a2a20;--chip:#2a2722}}
:root[data-theme="dark"]{--bg:#141311;--panel:#1c1a17;--ink:#ece7dd;--mute:#9a9284;--line:#2e2b26;--acc:#e07a4c;--acc2:#5fb39c;--hl:#3a2a20;--chip:#2a2722}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.35 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;flex-direction:column}
header{padding:14px 20px 10px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;border-bottom:1px solid var(--line);background:var(--panel)}
h1{font-size:18px;margin:0 8px 0 0;letter-spacing:.2px}h1 small{color:var(--mute);font-weight:400;font-size:13px;margin-left:6px}
input[type=search]{flex:1 1 220px;max-width:340px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
.seg{display:flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}.seg button{border:0;background:transparent;color:var(--ink);padding:6px 10px;font:inherit;cursor:pointer}
.seg button+button{border-left:1px solid var(--line)}.seg button.on{background:var(--acc);color:#fff}
.chips{display:flex;gap:4px;flex-wrap:wrap}.chips button{border:0;background:var(--chip);color:var(--ink);border-radius:999px;padding:4px 9px;font:inherit;font-size:12px;cursor:pointer}
.chips button.on{background:var(--acc2);color:#fff}
select{padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
main{flex:1;overflow:auto}
table{width:100%;border-collapse:collapse}th,td{padding:6px 10px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:var(--panel);font-size:12px;color:var(--mute);font-weight:600;cursor:pointer;user-select:none;z-index:1}
td.t{white-space:normal;font-weight:500}td.n{text-align:right;font-variant-numeric:tabular-nums;color:var(--mute)}
tr{cursor:pointer}tr:hover td{background:var(--hl)}tr.playing td{background:var(--hl)}tr.playing td.t{color:var(--acc)}
.tag{font-size:11px;padding:1px 7px;border-radius:999px;background:var(--chip);color:var(--mute)}.tag.list{background:var(--acc2);color:#fff}.tag.no1{background:var(--acc);color:#fff}
footer{border-top:1px solid var(--line);background:var(--panel);padding:10px 20px;display:flex;gap:14px;align-items:center}
footer button{border:0;background:var(--chip);color:var(--ink);width:36px;height:36px;border-radius:50%;font-size:15px;cursor:pointer}
footer button.big{background:var(--acc);color:#fff;width:44px;height:44px}
#now{min-width:0;flex:0 1 340px}#now b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#now span{color:var(--mute);font-size:12px}
#bar{flex:1;height:6px;background:var(--chip);border-radius:3px;cursor:pointer;position:relative}#bar i{position:absolute;left:0;top:0;bottom:0;background:var(--acc);border-radius:3px}
#time{color:var(--mute);font-size:12px;font-variant-numeric:tabular-nums;min-width:84px;text-align:right}
.off{opacity:.45}.sa{display:none}
@media (max-width:700px){header{padding:10px 16px}footer{padding:8px 16px;flex-wrap:wrap}#bar{flex-basis:100%;order:9}.hide-s{display:none}.sa{display:block;font-weight:400;font-size:12px;color:var(--mute)}td.t{width:100%}}
</style></head><body>
<header>
  <h1>Listening Room<small id="count"></small></h1>
  <input type="search" id="q" placeholder="Search song or artist">
  <div class="seg" id="kind"><button data-k="all" class="on">All</button><button data-k="list">My lists</button><button data-k="library">Library</button><button data-k="hot100">Hot 100 · new to me</button></div>
  <div class="chips" id="dec"></div>
  <select id="sort"><option value="p">Peak</option><option value="w">Weeks on chart</option><option value="y">Year</option><option value="b">Tempo</option><option value="t">Title</option><option value="a">Artist</option></select>
  <div class="seg"><button id="shuf">Shuffle</button></div>
</header>
<main><table><thead><tr><th data-s="t">Song</th><th data-s="a" class="hide-s">Artist</th><th data-s="y" class="hide-s">Year</th><th data-s="p">Peak</th><th data-s="w" class="hide-s">Weeks</th><th data-s="b">BPM</th><th class="hide-s">Key</th><th class="hide-s">From</th></tr></thead><tbody id="rows"></tbody></table></main>
<footer>
  <button id="prev" title="Previous (p)">⏮</button><button id="play" class="big" title="Play/pause (space)">▶</button><button id="next" title="Next (n)">⏭</button>
  <div id="now"><b>Pick a song</b><span>__N__ songs downloaded so far</span></div>
  <div id="bar"><i></i></div><div id="time"></div>
</footer>
<audio id="au" preload="none"></audio>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s),au=$('#au');
let kind='all',dec=null,sort='p',dir=1,shuffle=false,view=[],cur=-1;
const decs=[...new Set(D.map(r=>r.y?Math.floor(r.y/10)*10:null).filter(x=>x))].sort();
$('#dec').innerHTML=decs.map(d=>`<button data-d="${d}">${String(d).slice(2)}s</button>`).join('');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function key(r){const v=r[sort];return v==null?(sort==='t'||sort==='a'?'':Infinity):v}
function build(){
  const q=$('#q').value.trim().toLowerCase();
  view=D.filter(r=>(kind==='all'||r.k===kind)&&(!dec||(r.y&&Math.floor(r.y/10)*10==dec))&&(!q||(r.t+' '+r.a).toLowerCase().includes(q)));
  if(shuffle){for(let i=view.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[view[i],view[j]]=[view[j],view[i]]}}
  else view.sort((x,y)=>{const a=key(x),b=key(y);if(typeof a==='string')return a.localeCompare(b)*dir;return((a>b)-(a<b))*dir||(y.w||0)-(x.w||0)});
  const playing=cur>=0?D[cur]:null;
  $('#rows').innerHTML=view.map((r,i)=>`<tr data-i="${i}" class="${r===playing?'playing':''}"><td class="t">${esc(r.t)}<span class="sa">${esc(r.a)}</span></td><td class="hide-s">${esc(r.a)}</td><td class="n hide-s">${r.y??''}</td>`+
    `<td class="n">${r.p?(r.p===1?'<span class="tag no1">#1</span>':r.p):'<span class="off">—</span>'}</td><td class="n hide-s">${r.w??''}</td>`+
    `<td class="n" title="${r.m?'measured from the record':'songbpm'}">${r.b??''}${r.m?' ·':''}</td><td class="hide-s">${esc(r.key||'')}</td>`+
    `<td class="hide-s"><span class="tag ${r.k==='list'?'list':''}">${esc(r.k==='hot100'?'Hot 100':r.k==='list'?r.s:'library')}</span></td></tr>`).join('');
  $('#count').textContent=`${view.length} of ${D.length}`;
}
function play(i){if(i<0||i>=view.length)return;const r=view[i];cur=D.indexOf(r);au.src=encodeURI(r.f);au.play();
  $('#now').innerHTML=`<b>${esc(r.t)}</b><span>${esc(r.a)}${r.y?' · '+r.y:''}${r.p?' · peak '+r.p:''}${r.b?' · '+r.b+' bpm':''}</span>`;
  document.querySelectorAll('tr.playing').forEach(t=>t.classList.remove('playing'));const tr=document.querySelector(`tr[data-i="${i}"]`);if(tr){tr.classList.add('playing');tr.scrollIntoView({block:'nearest'})}}
const pos=()=>view.indexOf(D[cur]);
$('#rows').onclick=e=>{const tr=e.target.closest('tr');if(tr)play(+tr.dataset.i)};
$('#play').onclick=()=>{if(cur<0)return play(0);au.paused?au.play():au.pause()};
$('#next').onclick=()=>play(pos()+1);$('#prev').onclick=()=>play(Math.max(0,pos()-1));
au.onended=()=>play(pos()+1);au.onplay=()=>$('#play').textContent='❚❚';au.onpause=()=>$('#play').textContent='▶';
au.onerror=()=>{$('#now span').textContent='could not play this file';setTimeout(()=>play(pos()+1),1200)};
const fmt=s=>isFinite(s)?Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'):'0:00';
au.ontimeupdate=()=>{$('#bar i').style.width=(au.currentTime/au.duration*100||0)+'%';$('#time').textContent=fmt(au.currentTime)+' / '+fmt(au.duration)};
$('#bar').onclick=e=>{const b=e.currentTarget.getBoundingClientRect();if(au.duration)au.currentTime=(e.clientX-b.left)/b.width*au.duration};
$('#kind').onclick=e=>{const b=e.target.closest('button');if(!b)return;kind=b.dataset.k;document.querySelectorAll('#kind button').forEach(x=>x.classList.toggle('on',x===b));build()};
$('#dec').onclick=e=>{const b=e.target.closest('button');if(!b)return;dec=dec==b.dataset.d?null:b.dataset.d;document.querySelectorAll('#dec button').forEach(x=>x.classList.toggle('on',x.dataset.d==dec));build()};
$('#sort').onchange=e=>{sort=e.target.value;dir=(sort==='w')?-1:1;shuffle=false;$('#shuf').classList.remove('on');build()};
document.querySelector('thead').onclick=e=>{const s=e.target.dataset.s;if(!s)return;dir=sort===s?-dir:(s==='w'?-1:1);sort=s;$('#sort').value=s;shuffle=false;$('#shuf').classList.remove('on');build()};
$('#shuf').onclick=e=>{shuffle=!shuffle;e.target.classList.toggle('on',shuffle);build()};
$('#q').oninput=build;
document.onkeydown=e=>{if(e.target.tagName==='INPUT')return;if(e.code==='Space'){e.preventDefault();$('#play').click()}if(e.key==='n')$('#next').click();if(e.key==='p')$('#prev').click()};
try{const t=localStorage.getItem('lr-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}
build();
</script></body></html>'''

if __name__ == '__main__':
    main()
