"""Build _music/song-structures.html — 2-pane scanner.

Left sidebar: pool-grouped song lists (Beatles / G50 / G100 / G150).
Right pane: the selected song's sections laid out vertically.
"""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'song-structures.html')
PAGES = [
    ('Beatles', 'Beatles-Study.html'),
    ('G50', 'Guitar50.html'),
    ('G100', 'Guitar100.html'),
    ('G150', 'Guitar150.html'),
]


def slugs_from_page(fn):
    html = open(os.path.join(HERE, fn)).read()
    m = re.search(r'const SONGS\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    if not m: return []
    return [(s['slug'], s.get('title',''), s.get('artist',''))
            for s in json.loads(m.group(1)) if s.get('slug')]


def section_breakdown(d):
    sections = sorted(d.get('sections') or [], key=lambda s: s.get('beat', 0))
    bpb = ((d.get('meters') or [{}])[0].get('numBeats')) or 4
    end_beat = d.get('endBeat') or 0
    out = []
    for i, s in enumerate(sections):
        name = (s.get('name') or '').strip()
        if not name: continue
        start = s.get('beat', 0)
        end = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
        bars = round((end - start) / bpb)
        if bars < 1: continue
        out.append({'name': name, 'bars': bars})
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

    html = HTML_TEMPLATE.replace('__SIDEBAR__', '\n'.join(sidebar_html))
    html = html.replace('__DATA__', json.dumps(songs_json, ensure_ascii=False, separators=(',', ':')))
    open(OUT, 'w').write(html)
    print(f"wrote {OUT}")
    counts = {f: sum(1 for s in song_meta.values() if s['flag']==f) for f in ('no-data','no-sections','only-generic','few-sections','ok')}
    print(f"  flag counts: {counts}")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Song Structures — Glowing Gardens</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#1a1a2e; color:#e0e0e0; margin:0; padding:0; height:100vh; overflow:hidden; display:flex; flex-direction:column; }
  .back-link { position:fixed; top:18px; left:20px; color:#6a6a8a; text-decoration:none; font-size:13px; z-index:50; }
  .back-link:hover { color:#e0e0e0; }
  header { padding:18px 24px 12px 60px; border-bottom:1px solid #2a2a4a; }
  header h1 { font-size:18px; font-weight:700; margin:0; }
  header p { font-size:11px; color:#8a8ab0; margin:3px 0 0; }

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

  .main { flex:1; overflow-y:auto; padding:24px 36px; }
  .placeholder { color:#6a6a8a; text-align:center; margin-top:120px; font-size:14px; }
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

  .sections { display:flex; flex-direction:column; gap:6px; max-width:520px; }
  .section { display:flex; align-items:center; padding:10px 16px; border-radius:6px; }
  .section .name { flex:1; font-size:14px; color:#fff; font-weight:600; }
  .section .bars { font-family: ui-monospace, Menlo, monospace; font-size:13px; color:#fff; background:rgba(0,0,0,0.3); padding:2px 10px; border-radius:11px; font-weight:700; }
  .sec-intro { background:#3a3a5a; }
  .sec-verse { background:#1e4a73; }
  .sec-prechorus { background:#3a5a4a; }
  .sec-chorus { background:#a01e1e; }
  .sec-bridge { background:#6e16a5; }
  .sec-solo { background:#957e0c; }
  .sec-outro { background:#3a3a5a; }
  .sec-interlude { background:#44446a; }
  .sec-generic { background:#a01b6b; }
  .sec-other { background:#44446a; }

  .totals { margin-top:18px; font-size:12px; color:#8a8ab0; max-width:520px; display:flex; justify-content:space-between; padding:0 6px; }
</style>
</head>
<body>
<a href="index.html" class="back-link">&larr; Music</a>
<header>
  <h1>Song Structures</h1>
  <p>Click a song on the left to see its sections. Dots = flag (red=no sections, orange=only generic, amber=few sections, gray=OK).</p>
</header>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="pool-pills">
      <a class="pool-pill" data-pool="Beatles">Beatles</a>
      <a class="pool-pill" data-pool="G50">G50</a>
      <a class="pool-pill" data-pool="G100">G100</a>
      <a class="pool-pill" data-pool="G150">G150</a>
    </div>
    __SIDEBAR__
  </aside>
  <main class="main" id="main">
    <div class="placeholder">Click a song from the left to see its sections.</div>
  </main>
</div>

<script>
const SONGS = __DATA__;

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

function render(slug) {
  const s = SONGS[slug];
  if (!s) return;
  const main = document.getElementById('main');
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
    body = `<div class="sections">${s.sections.map(sec => `
      <div class="section sec-${classOf(sec.name)}">
        <span class="name">${escapeHtml(sec.name)}</span>
        <span class="bars">${sec.bars}</span>
      </div>
    `).join('')}</div>
    <div class="totals"><span>${s.sections.length} sections</span><span>${totalBars} bars</span></div>`;
  }
  main.innerHTML = `
    <div class="song-head">
      <div class="title">${escapeHtml(s.title)}</div>
      <div class="artist">${escapeHtml(s.artist)}</div>
      <div class="pools">${s.pools.map(p => `<span class="pool-tag">${p}</span>`).join('')}</div>
      <div class="flag flag-${s.flag}">${flagLabels[s.flag] || s.flag}</div>
    </div>
    ${body}
  `;
}

document.querySelectorAll('.pool-pill').forEach(p => {
  p.addEventListener('click', () => {
    const target = document.querySelector(`.pool-group[data-pool="${p.dataset.pool}"]`);
    if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
  });
});

document.querySelectorAll('.song-item').forEach(li => {
  li.addEventListener('click', () => {
    document.querySelectorAll('.song-item.active').forEach(x => x.classList.remove('active'));
    li.classList.add('active');
    render(li.dataset.slug);
    li.scrollIntoView({block: 'nearest'});
  });
});

// auto-select first item
const first = document.querySelector('.song-item');
if (first) first.click();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
