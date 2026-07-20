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
from chord_label import chord_label

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
    """title -> (session number, track number), from Pollack's CD: line"""
    idx = json.load(open(os.path.join(NOTES, '_index.json')))
    out, trk = {}, {}
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
        mt = re.search(r'CD:.{0,60}?Track\s+(\d+)', t)
        if mt: trk[norm(v['title'])] = int(mt.group(1))
    # covers have no CD: line in Pollack, and some titles are spelled differently here than
    # there — beatles_proj.json (slug -> [session, album]) fills both gaps
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beatles_proj.json')
    if os.path.exists(p):
        for slug, v in json.load(open(p)).items():
            t = norm(slug.split('_', 1)[1] if '_' in slug else slug)
            t = re.sub(r'\d+$', '', t)
            if t and t not in out and isinstance(v, list) and v: out[t] = v[0]
    return out, trk

# UK album track numbers for the covers, which Pollack's cov_ notes don't carry.
# Past Masters is a compilation, so its entries stay unnumbered.
COVER_TRACK = {
    'anna': 3, 'chains': 4, 'boys': 5, 'babyitsyou': 10, 'atasteofhoney': 12, 'twistandshout': 14,
    'tilltherewasyou': 6, 'pleasemisterpostman': 7, 'pleasemrpostman': 7, 'rolloverbeethoven': 8,
    'youreallygotaholdonme': 10, 'devilinherheart': 12, 'money': 14, 'moneythatswhatiwant': 14,
    'rockandrollmusic': 4, 'mrmoonlight': 6, 'kansascity': 7, 'kansascityheyheyheyhey': 7,
    'wordsoflove': 9, 'honeydont': 10, 'everybodystryingtobemybaby': 14,
    'actnaturally': 8, 'dizzymisslizzy': 14,
}

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

def _match(k, d):
    """exact, then prefix, then containment — titles differ across sources"""
    if k in d: return d[k]
    for a in d:
        if (a.startswith(k) or k.startswith(a)) and abs(len(a) - len(k)) <= 6: return d[a]
    cands = [a for a in d if len(a) > 7 and (a in k or k in a)]
    return d[cands[0]] if len(cands) == 1 else None

def place(k, alb):
    if k in COVERS: return COVERS[k]
    return _match(k, alb) or 99

def track(k, trk):
    if k in COVER_TRACK: return COVER_TRACK[k]
    return _match(k, trk) or 99

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

SEMI = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
PCNAME = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
PCIDX = {n: i for i, n in enumerate(PCNAME)}
for _a, _b in [('C#', 1), ('D#', 3), ('F#', 6), ('G#', 8), ('A#', 10)]: PCIDX[_a] = _b

def tonic_pc(k):
    """key entry -> pitch class of the tonic, with Hookpad's relative-major convention"""
    t = k.get('tonic', 0)
    pc = PCIDX.get(str(t), t if isinstance(t, int) else 0)
    return (pc + 3) % 12 if k.get('scale') == 'minor' else pc

def sd_semis(sd):
    """scale-degree string ('1', 'b3', '#4') -> semitones above the tonic"""
    m = re.match(r'^([b#]*)(\d)$', str(sd))
    if not m: return None
    acc = sum(-1 if c == 'b' else 1 for c in m.group(1))
    d = int(m.group(2))
    return SEMI.get(d, 0) + acc if d in SEMI else None

def key_at(hj, beat):
    ks = sorted(hj.get('keys') or [{'beat': 1}], key=lambda k: k.get('beat', 0))
    cur = ks[0]
    for k in ks:
        if k.get('beat', 0) <= beat: cur = k
    return cur

def section_body(hj, b0, b1, scale):
    """melody notes and chords inside a section, positioned relative to its start"""
    notes = []
    for n in hj.get('notes') or []:
        nb = n.get('beat', 0)
        if not (b0 <= nb < b1) or n.get('isRest'): continue
        sem = sd_semis(n.get('sd'))
        if sem is None: continue
        notes.append({'sd': str(n.get('sd')), 'sem': sem, 'o': int(n.get('octave', 0)),
                      'b': round(nb - b0, 3), 'd': round(n.get('duration', 1), 3)})
    chords = []
    for c in hj.get('chords') or []:
        cb, cd = c.get('beat', 0), c.get('duration', 1)
        if not c.get('root') or not 1 <= c['root'] <= 7: continue
        st, en = max(cb, b0), min(cb + cd, b1)
        if en <= st: continue
        chords.append({'n': chord_label(c, scale), 'b': round(st - b0, 3), 'd': round(en - st, 3)})
    return notes, sorted(chords, key=lambda c: c['b'])

def kind(nm):
    n = nm.lower()
    for k, v in (('intro', 'intro'), ('outro', 'outro'), ('coda', 'outro'), ('pickup', 'intro'),
                 ('pre', 'pre'), ('verse', 'verse'), ('bridge', 'bridge'), ('middle', 'bridge'),
                 ('refrain', 'refrain'), ('chorus', 'chorus'), ('solo', 'solo'), ('instrumental', 'solo'),
                 ('break', 'solo'), ('interlude', 'link'), ('link', 'link'), ('connector', 'link')):
        if k in n: return v
    return 'other'

def main():
    alb, trk = albums()
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
        bodies, bodyix = [], {}
        end = hj.get('endBeat', 0) + 1
        out = []
        for i, s in enumerate(secs):
            b0 = s.get('beat', 0)
            b1 = secs[i + 1]['beat'] if i + 1 < len(secs) else end
            m = bars(hj, b0, b1)
            nm = (s.get('name') or '').strip()
            if m < 0.75 and (not nm or nm.lower() == 'section'): continue   # trailing marker junk
            kd = kind(nm)
            ref = None
            if kd != 'outro':                       # outros aren't worth a roll
                kk2 = key_at(hj, b0)
                sc2 = kk2.get('scale', 'major'); sc2 = sc2 if sc2 in ('major', 'minor') else 'major'
                ns, cs = section_body(hj, b0, b1, sc2)
                if ns or cs:
                    sig = (kd, m, tuple((x['sem'], x['o'], x['b'], x['d']) for x in ns),
                           tuple((x['n'], x['b'], x['d']) for x in cs))
                    # two identical verses are one thing to look at, not two
                    if sig in bodyix:
                        ref = bodyix[sig]
                    else:
                        ref = len(bodies)
                        bodyix[sig] = ref
                        bodies.append({'kind': kd, 'name': nm or '—', 'bars': m,
                                       'tonic': tonic_pc(kk2), 'scale': sc2,
                                       'bpm': (hj.get('tempos') or [{}])[0].get('bpm') or bpm,
                                       'notes': ns, 'chords': cs})
            out.append({'name': nm or '—', 'kind': kd, 'bars': m, 'ref': ref})
        if not out: continue
        kk = (hj.get('keys') or [{}])[0]
        tempos = hj.get('tempos') or [{}]
        songs.append({'title': t, 'session': place(k, alb), 'track': track(k, trk), 'sections': out,
                      'bodies': bodies,
                      'key': f"{kk.get('tonic','?')} {kk.get('scale','')}".strip(),
                      'bpm': tempos[0].get('bpm') or bpm,
                      'total': round(sum(s['bars'] for s in out), 2),
                      'shape': ' '.join(s['kind'] for s in out
                                        if s['kind'] in ('verse', 'bridge', 'refrain', 'chorus', 'solo'))})
    for i, s in enumerate(songs): s['i'] = i        # stable id for the modal
    shapes = Counter(s['shape'] for s in songs)
    for s in songs: s['shared'] = shapes[s['shape']]
    sess = []
    for n, nm in SESSION + [(99, 'Unplaced')]:
        got = sorted([s for s in songs if s['session'] == n], key=lambda s: (s['track'], s['title'].lower()))
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
.song .t .tn{display:inline-block;width:20px;color:#bbb;font-weight:400;font-size:11px}
.song .t{width:230px;flex:none;font-weight:600;font-size:13px}
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
/* --- section modal --- */
.sec.hit{cursor:pointer}.sec.hit:hover{filter:brightness(1.12)}
#ov{position:fixed;inset:0;background:rgba(20,20,35,.55);display:none;align-items:center;justify-content:center;z-index:50}
#ov.on{display:flex}
#mod{background:#fff;border-radius:12px;padding:18px 20px;max-width:min(1100px,94vw);max-height:90vh;overflow:auto;
  box-shadow:0 18px 60px rgba(0,0,0,.3)}
#mod h3{margin:0 0 2px;font-size:17px}
#mod .mmeta{color:#888;font-size:12px;margin-bottom:12px}
#mod .close{float:right;cursor:pointer;color:#aaa;font-size:20px;line-height:1;padding:0 4px}
#mod .close:hover{color:#333}
.roll{position:relative;border:1px solid #e4e4ec;border-radius:8px;background:#fbfbfe;overflow-x:auto}
.rollin{position:relative}
.lane{position:absolute;left:0;right:0;height:1px;background:#ececf4}
.lane.tonic{background:#d8d8ea}
.barline{position:absolute;top:0;bottom:0;width:1px;background:#e8e8f0}
.barline.b4{background:#d4d4e2}
.nb{position:absolute;height:9px;border-radius:3px;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.cb{position:absolute;bottom:0;height:22px;border-radius:4px;color:#fff;font:700 10px/22px -apple-system,sans-serif;
  text-align:center;text-shadow:0 1px 2px rgba(0,0,0,.4);overflow:hidden;white-space:nowrap}
.mtools{display:flex;gap:10px;align-items:center;margin-top:10px;font-size:12px;color:#667}
.mtools button{padding:5px 12px;border:1px solid #ccd;background:#f6f6fb;border-radius:7px;cursor:pointer;font-weight:600}
.dupe{font-size:11px;color:#8a2be2;margin-left:8px}
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
<div id=ov><div id=mod>
  <span class=close onclick="closeMod()">&times;</span>
  <h3 id=mtitle></h3><div class=mmeta id=msub></div>
  <div class=roll id=mroll></div>
  <div class=mtools>
    <button id=mplay>▶ Play</button>
    <span id=mnote></span>
  </div>
</div></div>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
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
  if(sortShape.checked) songs.sort((a,b)=>a.shape.localeCompare(b.shape)||a.track-b.track);
  document.getElementById('body').innerHTML=songs.map(o=>{
    const secs=o.sections.filter(x=>!(hideIO.checked&&(x.kind==='intro'||x.kind==='outro')));
    const chips=secs.map(x=>{
      const odd=markOdd.checked&&(x.bars%2!==0)?' odd':'';   // odd-numbered or fractional
      const hit=x.ref!=null?' hit':'';
      const click=x.ref!=null?` onclick="openMod(${o.i},${x.ref})"`:'';
      return `<span class="sec k-${x.kind}${odd}${hit}" title="${x.name}"${click}>${x.kind}<span class=b> (${NICE(x.bars)})</span></span>`;
    }).join('');
    const b=o.shared>1?`<span class=badge>${o.shared} share this shape</span>`:'';
    return `<div class=song><div class=t><span class=tn>${o.track<99?o.track:'–'}</span>${o.title}<span class=sub>${o.key||''}${o.bpm?' · '+o.bpm+'bpm':''} · ${NICE(o.total)} bars</span></div>
            <div class=seq>${chips}${b}</div></div>`;}).join('');}
// ---------- section modal ----------
const PCN=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const DEGCOL={0:'#e84545',2:'#f0a040',4:'#e8c828',5:'#50c878',7:'#5090f0',9:'#7040b0',11:'#e070b0'};
let SONGIX={},CUR=null,synth=null,part=null;
D.forEach(s=>s.songs.forEach(o=>{SONGIX[o.i]=o;}));
const R2D={i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7}, D2S={1:0,2:2,3:4,4:5,5:7,6:9,7:11};
// diatonic degrees get a solid colour; chromatic ones a diagonal of their two neighbours
function degBg(semi){
  semi=((semi%12)+12)%12;
  return DEGCOL[semi]!==undefined?DEGCOL[semi]
    :`linear-gradient(135deg,${DEGCOL[(semi+11)%12]||'#889'} 0 50%,${DEGCOL[(semi+1)%12]||'#889'} 50%)`;
}
// roman numeral -> semitones above the tonic, quality, and whatever decoration trails it
function parseRoman(lbl){
  if(lbl.indexOf('/')>-1 && lbl.indexOf('\u00b0')===-1){
    const [l,r]=lbl.split('/'); const L=parseRoman(l), R=parseRoman(r);
    if(L&&R) return {semi:(L.semi+R.semi)%12, q:'maj', suf:L.suf};   // applied chords are always major
  }
  if(lbl.indexOf('\u00b0')>-1){                                      // vii°7/V etc.
    const tgt=lbl.indexOf('/')>-1?parseRoman(lbl.split('/')[1]):{semi:0};
    const suf=/7/.test(lbl.split('/')[0])?'7':'';
    return {semi:((tgt?tgt.semi:0)-1+12)%12, q:'dim', suf};
  }
  const m=lbl.match(/^([b#]*)([ivxIVX]+)(.*)$/); if(!m) return null;
  const d=R2D[m[2].toLowerCase()]; if(!d) return null;
  let acc=0; for(const c of m[1]) acc+= c==='b'?-1:1;
  return {semi:(D2S[d]+acc+12)%12, q:m[2]===m[2].toUpperCase()?'maj':'min', suf:m[3]||''};
}
function chordBg(name,tonic){const p=parseRoman(name); return p?degBg(p.semi):'#889';}
function chordName(lbl,tonic){
  const p=parseRoman(lbl); if(!p) return lbl;
  return PCN[(tonic+p.semi)%12]+(p.q==='min'?'m':p.q==='dim'?'\u00b0':'')+p.suf;
}
function openMod(si,ri){
  const o=SONGIX[si], b=o.bodies[ri]; CUR=b;
  document.getElementById('mtitle').textContent=`${o.title} — ${b.name}`;
  const dupes=o.sections.filter(x=>x.ref===ri).length;
  document.getElementById('msub').innerHTML=
    `${NICE(b.bars)} bars · ${PCN[b.tonic]} ${b.scale} · ${b.bpm||'?'}bpm · ${b.notes.length} notes, ${b.chords.length} chords`
    +(dupes>1?`<span class=dupe>appears ${dupes}× in the song — showing the one</span>`:'');
  drawRoll(b);
  document.getElementById('ov').classList.add('on');
}
function closeMod(){document.getElementById('ov').classList.remove('on');stopPlay();}
document.getElementById('ov').onclick=e=>{if(e.target.id==='ov')closeMod();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMod();});
function drawRoll(b){
  const beats=Math.max(b.bars*4, ...b.chords.map(c=>c.b+c.d), ...b.notes.map(n=>n.b+n.d), 4);
  const PX=Math.max(9,Math.min(20,900/beats)), H=190, CH=26;
  const vals=b.notes.map(n=>n.sem+12*n.o);
  const lo=vals.length?Math.min(...vals):0, hi=vals.length?Math.max(...vals):12;
  const span=Math.max(hi-lo,7), top=8, usable=H-CH-16;
  const y=v=>top+usable-((v-lo)/span)*usable;
  let h=`<div class=rollin style="width:${Math.ceil(beats*PX)}px;height:${H}px">`;
  for(let v=Math.floor(lo/12)*12; v<=hi+1; v+=12) h+=`<div class="lane tonic" style="top:${y(v)}px"></div>`;
  for(let bar=0;bar<=Math.ceil(beats/4);bar++)
    h+=`<div class="barline${bar%4===0?' b4':''}" style="left:${bar*4*PX}px"></div>`;
  b.chords.forEach(c=>{h+=`<div class=cb title="${c.n}" style="left:${c.b*PX}px;width:${Math.max(c.d*PX-2,14)}px;background:${chordBg(c.n,b.tonic)}">${chordName(c.n,b.tonic)}</div>`;});
  b.notes.forEach(n=>{const v=n.sem+12*n.o;
    h+=`<div class="nb" title="${n.sd} — ${PCN[(b.tonic+n.sem%12+12)%12]}" style="left:${n.b*PX}px;top:${y(v)}px;width:${Math.max(n.d*PX-2,4)}px;background:${degBg(n.sem)}"></div>`;});
  document.getElementById('mroll').innerHTML=h+'</div>';
}
// ---------- playback ----------
function midiOf(n,tonic){return 60+tonic+n.sem+12*n.o;}
function nameOf(m){return PCN[((m%12)+12)%12].replace('b','b')+(Math.floor(m/12)-1);}
async function play(){
  if(!CUR) return;
  if(typeof Tone==='undefined'){document.getElementById('mnote').textContent='audio unavailable offline';return;}
  await Tone.start(); stopPlay();
  synth=synth||new Tone.PolySynth(Tone.Synth,{oscillator:{type:'triangle'},
        envelope:{attack:.01,decay:.2,sustain:.3,release:.4}}).toDestination();
  const bpm=CUR.bpm||120; Tone.Transport.bpm.value=bpm; const spb=60/bpm;
  const ev=[];
  CUR.notes.forEach(n=>ev.push([n.b*spb,{n:[nameOf(midiOf(n,CUR.tonic))],d:Math.max(.05,n.d*spb*.95),v:.85}]));
  part=new Tone.Part((t,e)=>synth.triggerAttackRelease(e.n,e.d,t,e.v),ev);
  part.start(0); Tone.Transport.start();
  document.getElementById('mplay').textContent='■ Stop';
}
function stopPlay(){
  if(typeof Tone==='undefined')return;
  Tone.Transport.stop(); Tone.Transport.cancel(0);
  if(part){part.dispose();part=null;}
  document.getElementById('mplay').textContent='▶ Play';
}
document.getElementById('mplay').onclick=()=>{
  if(document.getElementById('mplay').textContent.startsWith('■')) stopPlay(); else play();
};
sel(0);
</script></body></html>"""

if __name__ == '__main__':
    main()
