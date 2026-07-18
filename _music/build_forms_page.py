"""Build _music/forms.html — every Beatles song's SONG-LEVEL structure, side by side.

One level above the chord/section work: just the sequence of sections
(intro, verse, verse, bridge, verse, outro). Alan Pollack is the source of truth —
both the form line and the album/session are parsed out of his notes.

NOTE: read the full `Form:` block from each note's HTML, never _index.json's `form`
field — that one is truncated at the first line break.
"""
import os, re, json, html
from collections import Counter

NOTES = os.path.expanduser('~/Desktop/music/pollack_beatles_notes')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms.html')

# Pollack's CD line -> the user's numbered recording sessions
SESSION = [
    (1, 'Please Please Me'), (2, 'With The Beatles'), (3, "A Hard Day's Night"),
    (4, 'Beatles For Sale'), (5, 'Help!'), (6, 'Rubber Soul'), (7, 'Revolver'),
    (8, "Sgt. Pepper's Lonely Hearts Club Band"), (9, 'Magical Mystery Tour'),
    (10, 'White Album'), (11, 'Let It Be'), (12, 'Abbey Road'),
    (13, 'Yellow Submarine'), (14, 'Past Masters'),
]
SHORT = {8: "Sgt. Pepper's", 14: 'Past Masters (singles)'}

KINDS = [('intro', 'intro'), ('outro', 'outro'), ('coda', 'outro'), ('verse', 'verse'),
         ('bridge', 'bridge'), ('middle', 'bridge'), ('refrain', 'refrain'), ('chorus', 'refrain'),
         ('solo', 'solo'), ('instrumental', 'solo'), ('break', 'solo'),
         ('connector', 'link'), ('link', 'link'), ('transition', 'link'), ('interlude', 'link')]

def text(path):
    t = open(path, errors='ignore').read()
    t = re.sub(r'<[^>]+>', ' ', t); t = html.unescape(t)
    return re.sub(r'[ \t]+', ' ', t)

def kind(tok):
    for k, v in KINDS:
        if k in tok: return v
    if re.fullmatch(r'[-\s]*\d+\s*x[-\s]*', tok): return 'repeat'
    return 'other'

def load():
    idx = json.load(open(os.path.join(NOTES, '_index.json')))
    rows = []
    for slug, v in idx.items():
        if not isinstance(v, dict) or not v.get('title'): continue
        p = os.path.join(NOTES, slug + '.html')
        if not os.path.exists(p): continue
        t = text(p)
        mf = re.search(r'Form:(.*?)(?:CD:|Recorded:|UK-release)', t, re.S)
        if not mf: continue
        form = re.sub(r'\s+', ' ', mf.group(1)).strip()
        toks = [re.sub(r'\s+', ' ', re.sub(r'\(.*?\)', '', x).strip().lower())
                for x in form.split('|')]
        toks = [x for x in toks if x]
        mc = re.search(r'CD:\s*(.{0,60})', t)
        alb = mc.group(1).split(',')[0].strip().strip('"') if mc else ''
        sn = next((n for n, a in SESSION if a.lower().startswith(alb.lower()[:12]) and alb), 99)
        rows.append({'slug': slug, 'title': v['title'], 'key': v.get('key', ''),
                     'meter': v.get('meter', ''), 'album': alb, 'session': sn,
                     'raw': toks, 'kinds': [kind(x) for x in toks]})
    return sorted(rows, key=lambda r: (r['session'], r['title'].lower()))

def main():
    rows = load()
    sess = []
    for n, alb in SESSION + [(99, 'Other')]:
        songs = [r for r in rows if r['session'] == n]
        if songs: sess.append({'n': n, 'name': SHORT.get(n, alb), 'songs': songs})
    core = Counter(' '.join(c for c in r['kinds'] if c in ('verse', 'bridge', 'refrain', 'solo'))
                   for r in rows)
    for r in rows:
        r['core'] = ' '.join(c for c in r['kinds'] if c in ('verse', 'bridge', 'refrain', 'solo'))
        r['shared'] = core[r['core']]
    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps(sess)))
    print(f'wrote {OUT}  |  {len(rows)} songs across {len(sess)} sessions')
    for s in sess: print(f'   {s["n"]:>3}  {s["name"][:28]:<30} {len(s["songs"])}')

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Song Structures · Beatles</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:230px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:14px 16px 6px;margin:0}
.srow{padding:8px 16px;cursor:pointer;border-bottom:1px solid #f0f0f4;display:flex;justify-content:space-between;gap:8px}
.srow:hover{background:#eef}.srow.on{background:#2a2a44;color:#fff}
.srow .n{font-size:11px;color:#aaa}.srow.on .n{color:#dde}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}
.meta{color:#888;font-size:12px;margin-bottom:14px}
.opts{display:flex;gap:14px;align-items:center;margin-bottom:16px;font-size:12px;color:#556}
.opts label{cursor:pointer;user-select:none}
.song{display:flex;align-items:baseline;gap:10px;padding:5px 0;border-bottom:1px solid #ededf2}
.song .t{width:230px;flex:none;font-weight:600;font-size:13px}
.song .t .sub{display:block;font-weight:400;font-size:10px;color:#aaa}
.seq{display:flex;flex-wrap:wrap;gap:3px;align-items:center}
.sec{font-size:10px;font-weight:700;color:#fff;border-radius:4px;padding:2px 0;text-align:center;
  width:58px;text-shadow:0 1px 2px rgba(0,0,0,.35)}
.k-verse{background:#5090f0}.k-bridge{background:#e8734a}.k-refrain{background:#50c878}
.k-intro{background:#b8bcc8}.k-outro{background:#8c90a0}.k-solo{background:#a878d8}
.k-link{background:#d8c860}.k-repeat{background:#fff;color:#c60;border:1px dashed #c60;text-shadow:none}
.k-other{background:#fff;color:#889;border:1px solid #ccd;text-shadow:none}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.legend .sec{width:auto;padding:2px 8px}
.badge{font-size:10px;color:#8a2be2;background:#f3ecff;border-radius:4px;padding:1px 6px;margin-left:6px}
</style></head><body><div id=wrap>
<div id=side><h1>Sessions</h1><div id=list></div></div>
<div id=main>
  <h2 id=ttl></h2><div class=meta id=sub></div>
  <div class=opts>
    <label><input type=checkbox id=hideIO> hide intro / outro</label>
    <label><input type=checkbox id=sortShape> group by shape</label>
    <span id=cnt></span>
  </div>
  <div class=legend>
    <span class="sec k-verse">verse</span><span class="sec k-bridge">bridge</span>
    <span class="sec k-refrain">refrain</span><span class="sec k-solo">solo</span>
    <span class="sec k-intro">intro</span><span class="sec k-outro">outro</span>
    <span class="sec k-link">link</span>
  </div>
  <div id=body></div>
</div></div>
<script>
const D=__DATA__;
let SI=0;
const L=document.getElementById('list');
D.forEach((s,i)=>{const r=document.createElement('div');r.className='srow';r.dataset.i=i;
  r.innerHTML=`<span>${s.n===99?'Other':s.n+'. '+s.name}</span><span class=n>${s.songs.length}</span>`;
  r.onclick=()=>sel(i);L.appendChild(r);});
const hideIO=document.getElementById('hideIO'), sortShape=document.getElementById('sortShape');
hideIO.onchange=sortShape.onchange=()=>sel(SI);
function sel(i){SI=i;
  document.querySelectorAll('.srow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
  const s=D[i];
  document.getElementById('ttl').textContent=s.n===99?'Other':`${s.n}. ${s.name}`;
  document.getElementById('sub').textContent=`${s.songs.length} songs · structures from Alan Pollack's "Notes On…"`;
  let songs=s.songs.slice();
  if(sortShape.checked) songs.sort((a,b)=>a.core.localeCompare(b.core)||a.title.localeCompare(b.title));
  document.getElementById('body').innerHTML=songs.map(o=>{
    const pairs=o.kinds.map((k,j)=>[k,o.raw[j]]).filter(([k])=>!(hideIO.checked&&(k==='intro'||k==='outro')));
    const chips=pairs.map(([k,raw])=>`<span class="sec k-${k}" title="${raw}">${k==='repeat'?raw:k}</span>`).join('');
    const b=o.shared>1?`<span class=badge>${o.shared} share this shape</span>`:'';
    return `<div class=song><div class=t>${o.title}<span class=sub>${o.key||''} · ${o.meter||''}</span></div>
            <div class=seq>${chips}${b}</div></div>`;}).join('');
  document.getElementById('cnt').textContent='';}
sel(0);
</script></body></html>"""

if __name__ == '__main__':
    main()
