"""Build _music/song-structures.html — 2-pane scanner.

Left sidebar: pool-grouped song lists (Beatles / G50 / G100 / G150).
Right pane: the selected song's sections laid out vertically.
"""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'songs.html')
PAGES = [
    ('Beatles', 'Beatles-Study.html'),
    ('G50', 'Guitar50.html'),
    ('G100', 'Guitar100.html'),
    ('G150', 'Guitar150.html'),
    ('G200', 'Guitar200.html'),
    ('G250', 'Guitar250.html'),
    ('G300', 'Guitar300.html'),
    ('G350', 'Guitar350.html'),
    ('G400', 'Guitar400.html'),
    ('G450', 'Guitar450.html'),
    ('G500', 'Guitar500.html'),
    ('G550', 'Guitar550.html'),
]


def slugs_from_page(fn):
    html = open(os.path.join(HERE, fn)).read()
    m = re.search(r'const SONGS\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    if not m: return []
    return [(s['slug'], s.get('title',''), s.get('artist',''))
            for s in json.loads(m.group(1)) if s.get('slug')]


MAJOR_INT = [0,2,4,5,7,9,11]
MODE_INT = {
    'major':[0,2,4,5,7,9,11], 'minor':[0,2,3,5,7,8,10],
    'dorian':[0,2,3,5,7,9,10], 'mixolydian':[0,2,4,5,7,9,10],
    'lydian':[0,2,4,6,7,9,11], 'phrygian':[0,1,3,5,7,8,10],
    'locrian':[0,1,3,5,6,8,10], 'harmonicMinor':[0,2,3,5,7,8,11],
    'phrygianDominant':[0,1,4,5,7,8,10],
}
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def strip_acc(s):
    s = str(s or ''); acc = 0
    while s and s[0] in 'b#':
        acc += -1 if s[0]=='b' else 1; s = s[1:]
    return acc, s


def tonic_semis(t):
    t = (t or 'C')
    for i, n in enumerate(NOTES):
        if n == t: return i
    flats = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
    for i, n in enumerate(flats):
        if n == t: return i
    return 0


def deg_to_pc(root, tonic, mode):
    acc, rs = strip_acc(root)
    if not rs.isdigit(): return None
    deg = int(rs)
    if deg < 1 or deg > 7: return None
    intervals = MODE_INT.get(mode, MAJOR_INT)
    return ((tonic_semis(tonic) + intervals[deg-1] + acc) % 12 + 12) % 12


MODE_QUALITIES = {
    'major':            ['M','m','m','M','M','m','d'],
    'minor':            ['m','d','M','m','m','M','M'],
    'dorian':           ['m','m','M','M','m','d','M'],
    'mixolydian':       ['M','m','d','M','m','m','M'],
    'lydian':           ['M','M','m','d','M','m','m'],
    'phrygian':         ['m','M','M','m','d','M','m'],
    'locrian':          ['d','M','m','m','M','M','m'],
    'harmonicMinor':    ['m','d','a','m','M','M','d'],
    'phrygianDominant': ['M','M','d','m','d','M','m'],
}


def chord_quality(c, scale):
    if c.get('applied'): return 'M'
    typ = c.get('type', '')
    if typ in ('m', 'min'): return 'm'
    borrowed = c.get('borrowed') if isinstance(c.get('borrowed'), str) else ''
    mode = borrowed if borrowed in MODE_QUALITIES else scale
    acc, rs = strip_acc(c.get('root', ''))
    if not rs.isdigit(): return 'M'
    deg = int(rs)
    return MODE_QUALITIES.get(mode, MODE_QUALITIES['major'])[deg-1]


def effective_pc(c, tonic, scale):
    """Pitch class of the chord's actual root (handles applied + borrowed)."""
    if c.get('applied'):
        tgt_pc = deg_to_pc(str(c['applied']), tonic, scale)
        if tgt_pc is None: return None
        return deg_to_pc(str(c.get('root', '1')), NOTES[tgt_pc], 'major')
    borrowed = c.get('borrowed') if isinstance(c.get('borrowed'), str) else ''
    mode = borrowed if borrowed in MODE_INT else scale
    return deg_to_pc(str(c.get('root', '1')), tonic, mode)


def chord_name(c, tonic, scale):
    """Return absolute chord name like 'C', 'Am', 'G7', 'Bb', 'F#dim'."""
    pc = effective_pc(c, tonic, scale)
    if pc is None: return '?'
    name = NOTES[pc]
    q = chord_quality(c, scale)
    if q == 'm':   name += 'm'
    elif q == 'd': name += '°'
    elif q == 'a': name += '+'
    if c.get('type') in (7, '7'): name += '7'
    return name


def chord_color_class(c, tonic, scale):
    if not c: return 'pc-unknown'
    acc, rs = strip_acc(c.get('root', ''))
    if not rs.isdigit(): return 'pc-unknown'
    deg = int(rs)
    if deg < 1 or deg > 7: return 'pc-unknown'
    borrowed = c.get('borrowed') if isinstance(c.get('borrowed'), str) else ''
    is_diatonic = not c.get('applied') and not borrowed and acc == 0
    if is_diatonic:
        color_deg = ((deg + 4) % 7) + 1 if scale == 'minor' else deg
        return f'deg-{color_deg}'
    pc = effective_pc(c, tonic, scale)
    return f'pc-{pc}' if pc is not None else 'pc-unknown'


def per_measure_chord_data(chords, start, end, bpb, tonic, scale):
    """Return list of {cls, name} per measure in [start, end)."""
    n_bars = round((end - start) / bpb)
    measures = [None] * n_bars
    for c in sorted(chords, key=lambda x: x.get('beat', 0)):
        if c.get('isRest'): continue
        cb = c.get('beat', 0); cd = c.get('duration', 0)
        if cb + cd <= start or cb >= end: continue
        first_m = max(0, int((cb - start) / bpb))
        last_m = min(n_bars - 1, int((cb + cd - 1e-9 - start) / bpb))
        for m in range(first_m, last_m + 1):
            if measures[m] is None:
                measures[m] = {'cls': chord_color_class(c, tonic, scale),
                               'name': chord_name(c, tonic, scale)}
    last = {'cls': 'pc-unknown', 'name': ''}
    for i in range(n_bars):
        if measures[i] is None: measures[i] = last
        else: last = measures[i]
    return measures


def section_breakdown(d):
    sections = sorted(d.get('sections') or [], key=lambda s: s.get('beat', 0))
    bpb = ((d.get('meters') or [{}])[0].get('numBeats')) or 4
    end_beat = d.get('endBeat') or 0
    key0 = (d.get('keys') or [{}])[0]
    tonic = key0.get('tonic') or 'C'
    scale = key0.get('scale') or 'major'
    chords = d.get('chords') or []
    out = []
    for i, s in enumerate(sections):
        name = (s.get('name') or '').strip()
        if not name: continue
        start = s.get('beat', 0)
        end = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
        bars = round((end - start) / bpb)
        if bars < 1: continue
        cells = per_measure_chord_data(chords, start, end, bpb, tonic, scale)
        out.append({'name': name, 'bars': bars, 'cells': cells})
    return out


def section_class(name):
    n = name.lower()
    if 'chorus' in n and 'pre' not in n: return 'chorus'
    if 'pre' in n and 'chorus' in n: return 'prechorus'
    if 'verse' in n: return 'verse'
    if 'bridge' in n: return 'bridge'
    if 'intro' in n: return 'intro'
    if 'outro' in n: return 'outro'
    if 'solo' in n: return 'solo'
    if 'interlude' in n: return 'interlude'
    if 'section' == n.strip() or n.strip().startswith('section '): return 'generic'
    return 'other'


def main():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

    # Track each song's pool memberships, preserving page order
    pool_lists = {label: [] for label, _ in PAGES}
    song_meta = {}  # slug -> {title, artist, pools:[...]}
    for label, fn in PAGES:
        for slug, title, artist in slugs_from_page(fn):
            if slug not in song_meta:
                song_meta[slug] = {'title': title, 'artist': artist, 'pools': []}
            if label not in song_meta[slug]['pools']:
                song_meta[slug]['pools'].append(label)
            if slug not in pool_lists[label]:
                pool_lists[label].append(slug)

    # Fetch hookpad_json for every slug, batched
    all_slugs = list(song_meta.keys())
    print(f"loading {len(all_slugs)} songs...")
    for i in range(0, len(all_slugs), 100):
        chunk = all_slugs[i:i+100]
        rows = (sb.schema('parcels').table('songs')
                .select('slug,hookpad_json').in_('slug', chunk).execute().data)
        for r in rows:
            secs = section_breakdown(r['hookpad_json']) if r.get('hookpad_json') else None
            song_meta[r['slug']]['sections'] = secs

    # Flag computation
    def flag(secs):
        if secs is None: return 'no-data'
        if not secs: return 'no-sections'
        real = [s for s in secs if section_class(s['name']) not in ('generic','other')]
        if not real: return 'only-generic'
        if len(real) <= 2: return 'few-sections'
        return 'ok'
    for s in song_meta.values():
        s['flag'] = flag(s.get('sections'))

    # Sort each pool list: flagged first, then alphabetical by artist+title
    flag_order = {'no-data':0,'no-sections':1,'only-generic':2,'few-sections':3,'ok':4}
    for label in pool_lists:
        pool_lists[label].sort(key=lambda slug: (
            flag_order.get(song_meta[slug]['flag'], 99),
            song_meta[slug]['artist'].lower(),
            song_meta[slug]['title'].lower(),
        ))

    # Build the inline data
    songs_json = {slug: {
        'title': m['title'], 'artist': m['artist'], 'pools': m['pools'],
        'flag': m['flag'], 'sections': m.get('sections') or [],
    } for slug, m in song_meta.items()}
    pool_json = {label: pool_lists[label] for label, _ in PAGES}

    # Sidebar HTML — pool groups with song lists
    sidebar_html = []
    for label, _ in PAGES:
        items = ''.join(
            f'<li class="song-item" data-slug="{slug}" data-flag="{song_meta[slug]["flag"]}">'
            f'<span class="dot dot-{song_meta[slug]["flag"]}"></span>'
            f'<span class="song-title">{song_meta[slug]["title"]}</span>'
            f'<span class="song-artist">{song_meta[slug]["artist"]}</span>'
            f'</li>'
            for slug in pool_lists[label]
        )
        sidebar_html.append(
            f'<div class="pool-group" data-pool="{label}">'
            f'<div class="pool-header">{label} <span class="pool-count">{len(pool_lists[label])}</span></div>'
            f'<ul class="song-list">{items}</ul>'
            f'</div>'
        )

    pills_html = ''.join(f'<a class="pool-pill" data-pool="{label}">{label}</a>' for label, _ in PAGES)
    html = HTML_TEMPLATE.replace('__SIDEBAR__', '\n'.join(sidebar_html))
    html = html.replace('__PILLS__', pills_html)
    html = html.replace('__DATA__', json.dumps(songs_json, ensure_ascii=False, separators=(',', ':')))
    open(OUT, 'w').write(html)
    print(f"wrote {OUT}")
    counts = {f: sum(1 for s in song_meta.values() if s['flag']==f) for f in ('no-data','no-sections','only-generic','few-sections','ok')}
    print(f"  flag counts: {counts}")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Songs — Glowing Gardens</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#1a1a2e; color:#e0e0e0; margin:0; padding:0; height:100vh; overflow:hidden; display:flex; flex-direction:column; }
  .back-link { position:fixed; top:18px; left:20px; color:#6a6a8a; text-decoration:none; font-size:13px; z-index:50; }
  .back-link:hover { color:#e0e0e0; }
  header { padding:14px 24px 12px 60px; border-bottom:1px solid #2a2a4a; display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
  header h1 { font-size:18px; font-weight:700; margin:0; }
  .view-toggle { display:flex; gap:4px; background:#16162a; padding:3px; border:1px solid #2a2a4a; border-radius:18px; }
  .view-toggle button { background:transparent; border:none; color:#8a8ab0; padding:5px 14px; border-radius:14px; cursor:pointer; font-size:12px; font-weight:600; }
  .view-toggle button.active { background:#3050d0; color:#fff; }
  .view-toggle button:hover:not(.active) { color:#e0e0e0; }

  .layout { flex:1; display:flex; min-height:0; }
  .sidebar { width:340px; min-width:340px; background:#16162a; border-right:1px solid #2a2a4a; overflow-y:auto; }
  .pool-pills { position:sticky; top:0; z-index:3; padding:8px 12px; background:#16162a; border-bottom:1px solid #2a2a4a; display:flex; gap:6px; flex-wrap:wrap; }
  .pool-pill { padding:5px 12px; background:#20203a; color:#e0e0e0; border:1px solid #2a2a4a; border-radius:14px; font-size:11px; font-weight:600; cursor:pointer; text-decoration:none; }
  .pool-pill:hover { background:#3050d0; border-color:#3050d0; }
  .pool-group { border-bottom:1px solid #20203a; }
  .pool-header { padding:10px 16px; background:#20203a; font-size:11px; color:#a5a8fc; text-transform:uppercase; letter-spacing:1.2px; font-weight:700; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:2; }
  .pool-count { color:#6a6a8a; font-weight:400; font-size:10px; }
  .song-list { list-style:none; margin:0; padding:4px 0; }
  .song-item { padding:6px 16px 6px 28px; cursor:pointer; display:grid; grid-template-columns:auto 1fr; gap:2px 8px; align-items:baseline; position:relative; }
  .song-item:hover { background:#20203a; }
  .song-item.active { background:#1e3a8a; }
  .song-item.active .song-title, .song-item.active .song-artist { color:#fff; }
  .song-item .dot { position:absolute; left:12px; top:13px; width:8px; height:8px; border-radius:50%; }
  .dot-ok { background:#3a3a5a; }
  .dot-no-data { background:#4a4a6a; }
  .dot-no-sections { background:#dc2626; }
  .dot-only-generic { background:#ea580c; }
  .dot-few-sections { background:#d97706; }
  .song-item .song-title { font-size:13px; color:#e0e0e0; font-weight:500; grid-column:1 / -1; }
  .song-item .song-artist { font-size:10px; color:#8a8ab0; grid-column:1 / -1; }

  .main { flex:1; overflow-y:auto; padding:0; display:flex; flex-direction:column; }
  .structure-pane, .expanded-pane { display:none; flex:1; }
  .structure-pane.active, .expanded-pane.active { display:flex; flex-direction:column; }
  .structure-pane { padding:24px 36px; }
  .placeholder { color:#6a6a8a; text-align:center; margin-top:120px; font-size:14px; padding:0 36px; }
  .filter-box { padding:8px 12px; border-bottom:1px solid #2a2a4a; background:#16162a; }
  .filter-box input { width:100%; padding:7px 10px; background:#1e1e3a; border:1px solid #2a2a4a; border-radius:6px; color:#e0e0e0; outline:none; font-size:12px; box-sizing:border-box; }
  .filter-box input:focus { border-color:#6366f1; }

  /* Expanded (song_viewer.js) DOM mirroring the Guitar*.html pages */
  .exp-song-header { display:flex; gap:18px; align-items:baseline; padding:14px 24px 10px; border-bottom:1px solid #2a2a4a; flex-wrap:wrap; }
  .exp-song-header h1 { font-size:20px; font-weight:700; margin:0; }
  .exp-song-header .artist { font-size:13px; color:#8a8ab0; }
  .exp-song-header .meta { font-size:12px; color:#8a8ab0; }
  .exp-song-header .meta b { color:#e0e0e0; }
  .exp-song-header .transport { display:flex; gap:6px; align-items:center; margin-left:auto; }
  .exp-song-header .transport button { background:#2a2a4a; color:#e0e0e0; border:1px solid #3a3a5a; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:600; }
  .exp-song-header .transport button:hover { background:#3a3a5a; }
  .exp-song-header .transport button.playing { background:#6e16a5; border-color:#8e26c5; }
  .exp-song-header .transport .tempo-input { width:50px; background:#16162a; color:#e0e0e0; border:1px solid #3a3a5a; border-radius:4px; padding:4px; text-align:center; font-size:12px; }
  .exp-song-header .transport label { font-size:11px; color:#8a8ab0; display:flex; align-items:center; gap:4px; }
  .exp-canvas-host { flex:1; overflow:auto; padding:12px; }
  .song-head { margin-bottom:24px; }
  .song-head .title { font-size:24px; font-weight:700; color:#e0e0e0; margin-bottom:4px; }
  .song-head .artist { font-size:14px; color:#8a8ab0; }
  .song-head .pools { margin-top:8px; display:flex; gap:6px; }
  .pool-tag { background:#3050d0; color:#fff; padding:3px 10px; border-radius:11px; font-size:11px; font-weight:600; }
  .song-head .flag { font-size:10px; color:#fff; padding:3px 10px; border-radius:11px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700; margin-top:8px; display:inline-block; }
  .flag-ok { background:#16a34a; }
  .flag-no-data { background:#4a4a6a; }
  .flag-no-sections { background:#dc2626; }
  .flag-only-generic { background:#ea580c; }
  .flag-few-sections { background:#d97706; }

  .sections { display:flex; flex-direction:column; gap:8px; }
  .section-row { display:flex; align-items:center; gap:10px; }
  .section-row .label { width:140px; flex-shrink:0; padding:0 12px; border-radius:6px; display:flex; flex-direction:column; align-items:center; justify-content:center; height:42px; box-sizing:border-box; }
  .section-row .label .name { font-size:15px; color:#fff; font-weight:700; text-transform:capitalize; letter-spacing:0.3px; line-height:1.1; }
  .section-row .label .bars { font-size:11px; color:rgba(255,255,255,0.75); font-family: ui-monospace, Menlo, monospace; margin-top:2px; }
  .label-intro     { background:#0ea5e9; }
  .label-verse     { background:#2563eb; }
  .label-prechorus { background:#14b8a6; }
  .label-chorus    { background:#dc2626; }
  .label-bridge    { background:#9333ea; }
  .label-solo      { background:#f59e0b; }
  .label-outro     { background:#475569; }
  .label-interlude { background:#6366f1; }
  .label-generic   { background:#ec4899; }
  .label-other     { background:#64748b; }
  .measures-strip { display:flex; gap:1px; height:42px; border-radius:3px; overflow:hidden; }
  .mc { height:42px; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:13px; text-shadow:0 1px 0 rgba(0,0,0,0.6), 1px 0 0 rgba(0,0,0,0.4); font-family: ui-monospace, Menlo, monospace; }
  .deg-1 { background:#a01e1e; } .deg-2 { background:#b35610; } .deg-3 { background:#957e0c; }
  .deg-4 { background:#25a838; } .deg-5 { background:#3050d0; } .deg-6 { background:#6e16a5; }
  .deg-7 { background:#a01b6b; }
  .pc-0 { background:#a01e1e; } .pc-1 { background:repeating-linear-gradient(135deg,#a01e1e 0 5px,#b35610 5px 10px); }
  .pc-2 { background:#b35610; } .pc-3 { background:repeating-linear-gradient(135deg,#b35610 0 5px,#957e0c 5px 10px); }
  .pc-4 { background:#957e0c; } .pc-5 { background:#25a838; }
  .pc-6 { background:repeating-linear-gradient(135deg,#25a838 0 5px,#3050d0 5px 10px); }
  .pc-7 { background:#3050d0; } .pc-8 { background:repeating-linear-gradient(135deg,#3050d0 0 5px,#6e16a5 5px 10px); }
  .pc-9 { background:#6e16a5; } .pc-10 { background:repeating-linear-gradient(135deg,#6e16a5 0 5px,#a01b6b 5px 10px); }
  .pc-11 { background:#a01b6b; }
  .pc-unknown { background:#44446a; }

  .totals { margin-top:18px; font-size:12px; color:#8a8ab0; max-width:520px; display:flex; justify-content:space-between; padding:0 6px; }
</style>
</head>
<body>
<a href="index.html" class="back-link">&larr; Music</a>
<header>
  <h1>Songs</h1>
  <div class="view-toggle">
    <button data-mode="structure">Structure</button>
    <button data-mode="expanded">Expanded</button>
  </div>
</header>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="filter-box"><input id="filter" placeholder="Filter songs…" spellcheck="false"></div>
    <div class="pool-pills">__PILLS__</div>
    __SIDEBAR__
  </aside>
  <main class="main">
    <div class="structure-pane" id="structurePane">
      <div class="placeholder">Click a song from the left to see its sections.</div>
    </div>
    <div class="expanded-pane" id="expandedPane">
      <div class="exp-song-header">
        <h1 id="expTitle">select a song</h1>
        <div class="artist" id="expArtist"></div>
        <div class="meta" id="expMeta"></div>
        <div class="transport">
          <button id="expPlayBtn">▶ Play</button>
          <button id="expStopBtn">■ Stop</button>
          <label>BPM <input type="number" id="expTempoInput" class="tempo-input" min="40" max="240"></label>
          <label>show
            <select id="expDisplaySelect" class="tempo-input" style="width:auto">
              <option value="chord">chord names</option>
              <option value="roman">roman</option>
            </select>
          </label>
        </div>
      </div>
      <div class="exp-canvas-host" id="expMain"><div class="placeholder">Click a song to load it.</div></div>
    </div>
  </main>
</div>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>

<script>
const SONGS = __DATA__;
const SUPABASE_URL = 'https://eazzqlyfcnnlplobgaas.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVhenpxbHlmY25ubHBsb2JnYWFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTI4MTkxMzAsImV4cCI6MjAwODM5NTEzMH0.3SUQeAewAyOzlNCUGTLx8E1hnDg7oD2CwymuK3s4wxE';
const sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
const viewer = new SongViewer({
  supabase: sb,
  mainEl: '#expMain',
  headerEls: { title: '#expTitle', artist: '#expArtist', meta: '#expMeta' },
  transport: { playBtn: '#expPlayBtn', stopBtn: '#expStopBtn', tempoInput: '#expTempoInput', displaySelect: '#expDisplaySelect' },
});

function classOf(name) {
  const n = name.toLowerCase().trim();
  if (n.includes('chorus') && !n.includes('pre')) return 'chorus';
  if (n.includes('pre') && n.includes('chorus')) return 'prechorus';
  if (n.includes('verse')) return 'verse';
  if (n.includes('bridge')) return 'bridge';
  if (n.includes('intro')) return 'intro';
  if (n.includes('outro')) return 'outro';
  if (n.includes('solo')) return 'solo';
  if (n.includes('interlude')) return 'interlude';
  if (n === 'section' || n.startsWith('section ')) return 'generic';
  return 'other';
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

let currentSlug = null;
let currentMode = localStorage.getItem('songsViewMode') || 'structure';

function renderStructure(slug) {
  const s = SONGS[slug];
  if (!s) return;
  const pane = document.getElementById('structurePane');
  const flagLabels = {
    'ok': 'OK', 'no-data': 'NO HOOKPAD DATA',
    'no-sections': 'NO SECTIONS', 'only-generic': 'ONLY GENERIC',
    'few-sections': 'FEW SECTIONS',
  };
  let body;
  if (!s.sections || !s.sections.length) {
    body = `<div class="placeholder" style="margin-top:40px">— no sections found —</div>`;
  } else {
    const totalBars = s.sections.reduce((a, b) => a + b.bars, 0);
    const pxPerBar = 48;
    body = `<div class="sections">${s.sections.map(sec => {
      const cellsHtml = (sec.cells || []).map(cell =>
        `<div class="mc ${cell.cls}" style="width:${pxPerBar - 1}px">${escapeHtml(cell.name || '')}</div>`
      ).join('');
      const cls = classOf(sec.name);
      return `<div class="section-row">
        <div class="label label-${cls}"><span class="name">${escapeHtml(sec.name)}</span><span class="bars">${sec.bars} bars</span></div>
        <div class="measures-strip" style="width:${sec.bars * pxPerBar}px">${cellsHtml}</div>
      </div>`;
    }).join('')}</div>
    <div class="totals" style="margin-left:152px;max-width:${Math.max(...s.sections.map(x=>x.bars)) * pxPerBar}px"><span>${s.sections.length} sections</span><span>${totalBars} bars</span></div>`;
  }
  pane.innerHTML = `
    <div class="song-head">
      <div class="title">${escapeHtml(s.title)}</div>
      <div class="artist">${escapeHtml(s.artist)}</div>
      <div class="pools">${s.pools.map(p => `<span class="pool-tag">${p}</span>`).join('')}</div>
      <div class="flag flag-${s.flag}">${flagLabels[s.flag] || s.flag}</div>
    </div>
    ${body}
  `;
}

function showMode(mode) {
  currentMode = mode;
  localStorage.setItem('songsViewMode', mode);
  document.querySelectorAll('.view-toggle button').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  document.getElementById('structurePane').classList.toggle('active', mode === 'structure');
  document.getElementById('expandedPane').classList.toggle('active', mode === 'expanded');
}

function selectSong(slug) {
  currentSlug = slug;
  document.querySelectorAll('.song-item.active').forEach(x => x.classList.remove('active'));
  const item = document.querySelector(`.song-item[data-slug="${slug}"]`);
  if (item) { item.classList.add('active'); item.scrollIntoView({block:'nearest'}); }
  if (currentMode === 'structure') renderStructure(slug);
  else viewer.load(slug);
}

document.querySelectorAll('.view-toggle button').forEach(b => {
  b.addEventListener('click', () => {
    showMode(b.dataset.mode);
    if (currentSlug) {
      if (b.dataset.mode === 'structure') renderStructure(currentSlug);
      else viewer.load(currentSlug);
    }
  });
});
document.querySelectorAll('.pool-pill').forEach(p => {
  p.addEventListener('click', () => {
    const target = document.querySelector(`.pool-group[data-pool="${p.dataset.pool}"]`);
    if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
  });
});
document.querySelectorAll('.song-item').forEach(li => {
  li.addEventListener('click', () => selectSong(li.dataset.slug));
});

// Filter songs
document.getElementById('filter').addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('.song-item').forEach(li => {
    const s = SONGS[li.dataset.slug];
    const text = `${s.title} ${s.artist}`.toLowerCase();
    li.style.display = (!q || text.includes(q)) ? '' : 'none';
  });
});

showMode(currentMode);
const first = document.querySelector('.song-item');
if (first) selectSong(first.dataset.slug);
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
