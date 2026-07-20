"""Build _music/forms.html — every Beatles song's SONG-LEVEL structure, side by side.

Source of truth is the user's own Hookpad data (parcels.songs), NOT Pollack. Pollack's
form lines switch between two notations without marking which: most songs enumerate every
section, but "flat" repetitive ones give a single representative cycle (Help! is written
"Intro | Verse | Refrain | Outro" though the prose says three verses). Hookpad has the
real sequence, and it has bar counts.

Bar math walks the METER MAP — 36 of 209 Beatles songs change meter mid-song, and taking
numBeats from meters[0] silently corrupts every one of them.
"""
import os, re, json, html
from collections import Counter, defaultdict
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms.html')
NOTES = os.path.expanduser('~/Desktop/music/pollack_beatles_notes')
SESSION = [(1, 'Please Please Me'), (2, 'With The Beatles'), (3, "A Hard Day's Night"),
           (4, 'Beatles For Sale'), (5, 'Help!'), (6, 'Rubber Soul'), (7, 'Revolver'),
           (8, "Sgt. Pepper's Lonely Hearts Club Band"), (9, 'Magical Mystery Tour'),
           (10, 'White Album'), (11, 'Let It Be'), (12, 'Abbey Road'),
           (13, 'Yellow Submarine'), (14, 'Past Masters')]
SHORT = {8: "Sgt. Pepper's", 14: 'Past Masters (singles)'}
VARIANT = re.compile(r'[-_](simple|hooktab|right|wrong|double|half|\d+|[A-G]b?|mixolydian|ly_o_COMPLETED)$', re.I)
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def albums():
    """title -> session number, taken from Pollack's CD: line (covers included)"""
    idx = json.load(open(os.path.join(NOTES, '_index.json')))
    out = {}
    for slug, v in idx.items():
        if not isinstance(v, dict) or not v.get('title'): continue
        p = os.path.join(NOTES, slug + '.html')
        if not os.path.exists(p): continue
        t = re.sub(r'<[^>]+>', ' ', open(p, errors='ignore').read())
        t = html.unescape(t)
        m = re.search(r'CD:\s*(.{0,60})', t)
        a = m.group(1).split(',')[0].strip().strip('"') if m else ''
        n = next((n for n, nm in SESSION if a and nm.lower().startswith(a.lower()[:12])), None)
        if n: out[norm(v['title'])] = n
    # covers have no CD: line in Pollack, and some titles are spelled differently here than
    # there — beatles_proj.json (slug -> [session, album]) fills both gaps
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beatles_proj.json')
    if os.path.exists(p):
        for slug, v in json.load(open(p)).items():
            t = norm(slug.split('_', 1)[1] if '_' in slug else slug)
            t = re.sub(r'\d+$', '', t)
            if t and t not in out and isinstance(v, list) and v: out[t] = v[0]
    return out

# Pollack's cover notes carry no CD: line and beatles_proj.json omits covers, so the
# album for each cover is hardcoded here.
COVERS = {
    'anna': 1, 'chains': 1, 'boys': 1, 'babyitsyou': 1, 'atasteofhoney': 1, 'twistandshout': 1,
    'tilltherewasyou': 2, 'pleasemisterpostman': 2, 'pleasemrpostman': 2, 'rolloverbeethoven': 2,
    'youreallygotaholdonme': 2, 'devilinherheart': 2, 'money': 2, 'moneythatswhatiwant': 2,
    'rockandrollmusic': 4, 'mrmoonlight': 4, 'kansascity': 4, 'kansascityheyheyheyhey': 4,
    'wordsoflove': 4, 'honeydont': 4, 'everybodystryingtobemybaby': 4,
    'actnaturally': 5, 'dizzymisslizzy': 5,
    'longtallsally': 14, 'slowdown': 14, 'matchbox': 14, 'badboy': 14,
    # late/Anthology singles and a few titles spelled differently from Pollack
    'freeasabird': 14, 'reallove': 14, 'nowandthen': 14,
    'goodmorning': 8, 'drrobert': 7, 'allivegottado': 2, 'benefitofmrkite': 8,
}

def place(k, alb):
    """covers table, then exact, then prefix, then containment — titles differ across sources"""
    if k in COVERS: return COVERS[k]
    if k in alb: return alb[k]
    for a in alb:
        if a.startswith(k) or k.startswith(a):
            if abs(len(a) - len(k)) <= 6: return alb[a]
    cands = [a for a in alb if len(a) > 7 and (a in k or k in a)]
    return alb[cands[0]] if len(cands) == 1 else 99

def bars(hj, b0, b1):
    """measures between two beats, honouring every meter change in the range"""
    ms = sorted(hj.get('meters') or [{'beat': 1, 'numBeats': 4}], key=lambda m: m.get('beat', 1))
    total, pos = 0.0, b0
    while pos < b1:
        cur = ms[0]
        for m in ms:
            if m.get('beat', 1) <= pos: cur = m
        nxt = min([m['beat'] for m in ms if m.get('beat', 1) > pos] + [b1])
        npb = cur.get('numBeats') or 4
        total += (min(nxt, b1) - pos) / npb
        pos = min(nxt, b1)
    return round(total, 3)

def kind(nm):
    n = nm.lower()
    for k, v in (('intro', 'intro'), ('outro', 'outro'), ('coda', 'outro'), ('pickup', 'intro'),
                 ('pre', 'pre'), ('verse', 'verse'), ('bridge', 'bridge'), ('middle', 'bridge'),
                 ('refrain', 'refrain'), ('chorus', 'chorus'), ('solo', 'solo'), ('instrumental', 'solo'),
                 ('break', 'solo'), ('interlude', 'link'), ('link', 'link'), ('connector', 'link')):
        if k in n: return v
    return 'other'

def main():
    alb = albums()
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select title,hookpad_json,bpm from parcels.songs where hookpad_json is not null "
                "and lower(artist) like %s", ('%beatle%',))
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -(len((r[1] or {}).get('sections') or []) * 1000
                              + len((r[1] or {}).get('chords') or [])))
    seen, songs = set(), []
    for t, hj, bpm in rows:
        t = (t or '').strip()
        if not t or VARIANT.search(t): continue
        k = norm(t)
        if k in seen: continue
        seen.add(k)
        secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
        if not secs: continue
        end = hj.get('endBeat', 0) + 1
        out = []
        for i, s in enumerate(secs):
            b0 = s.get('beat', 0)
            b1 = secs[i + 1]['beat'] if i + 1 < len(secs) else end
            m = bars(hj, b0, b1)
            nm = (s.get('name') or '').strip()
            if m < 0.75 and (not nm or nm.lower() == 'section'): continue   # trailing marker junk
            out.append({'name': nm or '—', 'kind': kind(nm), 'bars': m})
        if not out: continue
        kk = (hj.get('keys') or [{}])[0]
        tempos = hj.get('tempos') or [{}]
        songs.append({'title': t, 'session': place(k, alb), 'sections': out,
                      'key': f"{kk.get('tonic','?')} {kk.get('scale','')}".strip(),
                      'bpm': tempos[0].get('bpm') or bpm,
                      'total': round(sum(s['bars'] for s in out), 2),
                      'shape': ' '.join(s['kind'] for s in out
                                        if s['kind'] in ('verse', 'bridge', 'refrain', 'chorus', 'solo'))})
    shapes = Counter(s['shape'] for s in songs)
    for s in songs: s['shared'] = shapes[s['shape']]
    sess = []
    for n, nm in SESSION + [(99, 'Unplaced')]:
        got = sorted([s for s in songs if s['session'] == n], key=lambda s: s['title'].lower())
        if got: sess.append({'n': n, 'name': SHORT.get(n, nm), 'songs': got})
    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps(sess)))
    print(f'wrote {OUT}  |  {len(songs)} songs, {len(sess)} sessions')
    for s in sess: print(f'   {s["n"]:>3}  {s["name"][:28]:<30} {len(s["songs"])}')

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Song Structures · Beatles</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:225px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:14px 16px 6px;margin:0}
.srow{padding:8px 16px;cursor:pointer;border-bottom:1px solid #f0f0f4;display:flex;justify-content:space-between;gap:8px}
.srow:hover{background:#eef}.srow.on{background:#2a2a44;color:#fff}
.srow .n{font-size:11px;color:#aaa}.srow.on .n{color:#dde}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}
.meta{color:#888;font-size:12px;margin-bottom:12px}
.opts{display:flex;gap:16px;align-items:center;margin-bottom:14px;font-size:12px;color:#556}
.opts label{cursor:pointer;user-select:none}
.song{display:flex;align-items:baseline;gap:10px;padding:6px 0;border-bottom:1px solid #ededf2}
.song .t{width:210px;flex:none;font-weight:600;font-size:13px}
.song .t .sub{display:block;font-weight:400;font-size:10px;color:#aaa}
.seq{display:flex;flex-wrap:wrap;gap:3px;align-items:center}
.sec{font-size:10px;font-weight:700;color:#fff;border-radius:4px;padding:2px 7px;white-space:nowrap;
  text-shadow:0 1px 2px rgba(0,0,0,.35)}
.sec .b{opacity:.8;font-weight:400}
.k-verse{background:#5090f0}.k-bridge{background:#e8734a}.k-refrain{background:#50c878}
.k-chorus{background:#2e9e5b}.k-intro{background:#b8bcc8}.k-outro{background:#8c90a0}
.k-solo{background:#a878d8}.k-link{background:#d8c860}.k-pre{background:#7fb5e8}
.k-other{background:#fff;color:#889;border:1px solid #ccd;text-shadow:none}
.odd{outline:2px solid #c0392b;outline-offset:1px}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.badge{font-size:10px;color:#8a2be2;background:#f3ecff;border-radius:4px;padding:1px 6px;margin-left:6px}
</style></head><body><div id=wrap>
<div id=side><h1>Sessions</h1><div id=list></div></div>
<div id=main>
  <h2 id=ttl></h2><div class=meta id=sub></div>
  <div class=opts>
    <label><input type=checkbox id=hideIO> hide intro / outro</label>
    <label><input type=checkbox id=sortShape> group by shape</label>
    <label><input type=checkbox id=markOdd checked> flag odd / fractional</label>
  </div>
  <div class=legend>
    <span class="sec k-verse">verse</span><span class="sec k-bridge">bridge</span>
    <span class="sec k-refrain">refrain</span><span class="sec k-chorus">chorus</span>
    <span class="sec k-pre">pre</span><span class="sec k-solo">solo</span>
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
  r.innerHTML=`<span>${s.n===99?'Unplaced':s.n+'. '+s.name}</span><span class=n>${s.songs.length}</span>`;
  r.onclick=()=>sel(i);L.appendChild(r);});
const hideIO=document.getElementById('hideIO'),sortShape=document.getElementById('sortShape'),
      markOdd=document.getElementById('markOdd');
hideIO.onchange=sortShape.onchange=markOdd.onchange=()=>sel(SI);
const NICE=n=>Number.isInteger(n)?n:(Math.round(n*100)/100);
function sel(i){SI=i;
  document.querySelectorAll('.srow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
  const s=D[i];
  document.getElementById('ttl').textContent=s.n===99?'Unplaced':`${s.n}. ${s.name}`;
  document.getElementById('sub').textContent=`${s.songs.length} songs · sections and bar counts from your Hookpad files`;
  let songs=s.songs.slice();
  if(sortShape.checked) songs.sort((a,b)=>a.shape.localeCompare(b.shape)||a.title.localeCompare(b.title));
  document.getElementById('body').innerHTML=songs.map(o=>{
    const secs=o.sections.filter(x=>!(hideIO.checked&&(x.kind==='intro'||x.kind==='outro')));
    const chips=secs.map(x=>{
      const odd=markOdd.checked&&(x.bars%2!==0)?' odd':'';   // odd-numbered or fractional
      return `<span class="sec k-${x.kind}${odd}" title="${x.name}">${x.kind}<span class=b> (${NICE(x.bars)})</span></span>`;
    }).join('');
    const b=o.shared>1?`<span class=badge>${o.shared} share this shape</span>`:'';
    return `<div class=song><div class=t>${o.title}<span class=sub>${o.key||''}${o.bpm?' · '+o.bpm+'bpm':''} · ${NICE(o.total)} bars</span></div>
            <div class=seq>${chips}${b}</div></div>`;}).join('');}
sel(0);
</script></body></html>"""

if __name__ == '__main__':
    main()
