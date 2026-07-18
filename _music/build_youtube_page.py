#!/usr/bin/env python
"""Generate videos.html — every song that has entries in parcels.songs.youtube_urls.
Regenerate after adding URLs (via add_youtube.py). Client-side search + kind filter.
"""
import os, re, json, html
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_KEY'])
rows = sb.schema('parcels').table('songs').select('slug,title,artist,youtube_urls,hookpad_url,ug_url').execute().data

def clean(t):  # strip variant tags + parentheticals for dedup + display
    t = (t or '')
    t = re.sub(r'_(ly|o|completed|right|left|simple|hooktab)\b', '', t, flags=re.I)
    t = re.sub(r'-(right|left|simple|hooktab|\d+|[0-9a-f]{6})$', '', t, flags=re.I)
    t = re.sub(r'\([^)]*\)', '', t)
    t = re.sub(r'[_]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()
def norm(t): return re.sub(r'[^a-z0-9]', '', (t or '').lower())
def vid(u):
    m = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})', u or ''); return m.group(1) if m else None
def display(t):  # prefer proper-cased; title-case an all-lowercase title
    t = clean(t)
    return t.title() if t == t.lower() else t

# dedupe songs by cleaned (artist,title); merge video lists across variant rows
songs = {}
for r in rows:
    yt = r.get('youtube_urls') or []
    if not yt: continue
    akey = norm(re.sub(r'^the\s+', '', clean(r['artist']).lower()))
    key = (akey, norm(clean(r['title'])))
    s = songs.setdefault(key, {'title': display(r['title']), 'artist': display(r['artist']),
                               'hookpad': r.get('hookpad_url'), 'ug': r.get('ug_url'), 'vids': {}})
    # prefer a display title that already has mixed case (more likely correct)
    if r['title'] != r['title'].lower():
        s['title'] = display(r['title'])
    s['hookpad'] = s['hookpad'] or r.get('hookpad_url')
    s['ug'] = s['ug'] or r.get('ug_url')
    for e in yt:
        if not isinstance(e, dict): e = {'url': e}
        v = vid(e.get('url'))
        if v and v not in s['vids']:
            s['vids'][v] = {'id': v, 'kind': e.get('kind', 'other'), 'title': e.get('title', '')}

data = []
for s in songs.values():
    data.append({'title': s['title'], 'artist': s['artist'], 'hookpad': s['hookpad'], 'ug': s['ug'],
                 'vids': sorted(s['vids'].values(), key=lambda v: v['kind'])})
data.sort(key=lambda d: (d['artist'].lower(), d['title'].lower()))
total_vids = sum(len(d['vids']) for d in data)

KIND_LABEL = {'guitar-tab': 'Guitar', 'bass-tab': 'Bass', 'score-tab': 'Score', 'score': 'Score', 'lesson': 'Lesson', 'cover': 'Cover', 'performance': 'Live', 'other': 'Video'}
KIND_CLASS = {'guitar-tab': 'k-guitar', 'bass-tab': 'k-bass', 'score-tab': 'k-score', 'score': 'k-score', 'lesson': 'k-lesson', 'cover': 'k-cover', 'performance': 'k-perf', 'other': 'k-other'}

DOC = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Song Videos — Glowing Gardens</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html,body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#1a1a2e; color:#e0e0e0; }
.back-link { position:fixed; top:20px; left:20px; color:#4a4a6a; text-decoration:none; font-size:13px; z-index:100; }
.back-link:hover { color:#e0e0e0; }
.wrap { max-width:1180px; margin:0 auto; padding:40px 28px 60px; }
.header { text-align:center; margin-bottom:22px; }
.header h1 { font-size:26px; font-weight:700; }
.header p { font-size:13px; color:#6a6a8a; margin-top:5px; }
.controls { display:flex; gap:10px; justify-content:center; align-items:center; flex-wrap:wrap; margin-bottom:26px; position:sticky; top:0; background:#1a1a2e; padding:12px 0; z-index:50; }
#q { background:#16162a; border:1px solid #2a2a4a; border-radius:8px; padding:9px 13px; color:#e0e0e0; font-size:14px; width:280px; }
#q:focus { outline:none; border-color:#5a5a8a; }
.filt { font-size:12px; font-weight:600; padding:6px 12px; border-radius:6px; border:1px solid #2a2a4a; background:#16162a; color:#8a8aaa; cursor:pointer; }
.filt.on { background:#26264a; color:#e0e0e0; border-color:#4a4a7a; }
.count { font-size:12px; color:#6a6a8a; margin-left:6px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }
.song { background:#16162a; border:1px solid #2a2a4a; border-radius:10px; padding:14px 15px; }
.song h3 { font-size:14.5px; font-weight:600; margin-bottom:2px; }
.song .art { font-size:11px; color:#6a6a8a; margin-bottom:10px; }
.vids { display:flex; flex-wrap:wrap; gap:6px; }
.vid { font-size:11px; font-weight:600; padding:4px 9px; border-radius:5px; text-decoration:none; border:1px solid transparent; }
.vid:hover { filter:brightness(1.25); }
.k-guitar { background:rgba(60,120,220,.2); color:#90b8f8; }
.k-bass { background:rgba(50,180,80,.2); color:#88e8a0; }
.k-score { background:rgba(230,140,40,.2); color:#ffc888; }
.k-lesson { background:rgba(220,60,60,.2); color:#ffa0a0; }
.k-cover { background:rgba(160,80,220,.2); color:#d0a0f8; }
.k-perf { background:rgba(220,200,40,.2); color:#f0e888; }
.k-other { background:rgba(99,102,241,.2); color:#a5a8fc; }
.links { margin-top:9px; display:flex; gap:10px; }
.links a { font-size:10.5px; color:#5a5a8a; text-decoration:none; }
.links a:hover { color:#a5a8fc; }
.empty { text-align:center; color:#6a6a8a; padding:40px; font-size:14px; }
</style></head><body>
<a href="index.html" class="back-link">&larr; Back</a>
<div class="wrap">
  <div class="header">
    <h1>&#127916; Song Videos</h1>
    <p>__NS__ songs &middot; __NV__ videos &mdash; guitar / bass / score tabs and lessons. Click a chip to open on YouTube.</p>
  </div>
  <div class="controls">
    <input id="q" type="text" placeholder="Search song or artist&hellip;" autocomplete="off">
    <button class="filt on" data-k="all">All</button>
    <button class="filt" data-k="guitar-tab">Guitar</button>
    <button class="filt" data-k="bass-tab">Bass</button>
    <button class="filt" data-k="score-tab">Score</button>
    <span class="count" id="count"></span>
  </div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">No songs match.</div>
</div>
<script>
const DATA = __DATA__;
const KLABEL = __KLABEL__, KCLASS = __KCLASS__;
const grid = document.getElementById('grid'), q = document.getElementById('q'), countEl = document.getElementById('count'), emptyEl = document.getElementById('empty');
let kind = 'all';
function render() {
  const term = q.value.trim().toLowerCase();
  grid.innerHTML = ''; let n = 0;
  for (const s of DATA) {
    const vids = kind === 'all' ? s.vids : s.vids.filter(v => v.kind === kind);
    if (!vids.length) continue;
    if (term && !(s.title.toLowerCase().includes(term) || s.artist.toLowerCase().includes(term))) continue;
    n++;
    const el = document.createElement('div'); el.className = 'song';
    const chips = vids.map(v => `<a class="vid ${KCLASS[v.kind]||'k-other'}" target="_blank" rel="noopener" href="https://www.youtube.com/watch?v=${v.id}" title="${(v.title||'').replace(/"/g,'&quot;')}">${KLABEL[v.kind]||'Video'}</a>`).join('');
    let links = '';
    if (s.hookpad) links += `<a target="_blank" rel="noopener" href="${s.hookpad}">Hookpad</a>`;
    if (s.ug) links += `<a target="_blank" rel="noopener" href="${s.ug}">UG</a>`;
    el.innerHTML = `<h3>${s.title}</h3><div class="art">${s.artist}</div><div class="vids">${chips}</div>`+(links?`<div class="links">${links}</div>`:'');
    grid.appendChild(el);
  }
  countEl.textContent = n + ' songs';
  emptyEl.style.display = n ? 'none' : 'block';
}
document.querySelectorAll('.filt').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.filt').forEach(x => x.classList.remove('on')); b.classList.add('on'); kind = b.dataset.k; render();
}));
q.addEventListener('input', render);
render();
</script>
</body></html>"""

out = (DOC.replace('__DATA__', json.dumps(data))
          .replace('__KLABEL__', json.dumps(KIND_LABEL))
          .replace('__KCLASS__', json.dumps(KIND_CLASS))
          .replace('__NS__', str(len(data)))
          .replace('__NV__', str(total_vids)))
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videos.html')
open(path, 'w').write(out)
print(f'wrote {path}: {len(data)} songs, {total_vids} videos')
