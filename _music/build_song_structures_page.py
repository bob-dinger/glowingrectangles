"""Build _music/song-structures.html — a scannable list of every song's
section structure (name + bar count per section), so it's easy to spot
songs that still need section work.
"""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'song-structures.html')
PAGES = ['Beatles-Study.html', 'Guitar50.html', 'Guitar100.html', 'Guitar150.html']


def slugs_from_page(fn):
    html = open(os.path.join(HERE, fn)).read()
    m = re.search(r'const SONGS\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    if not m: return []
    return [(s['slug'], s.get('title',''), s.get('artist',''))
            for s in json.loads(m.group(1)) if s.get('slug')]


def section_breakdown(d):
    """Return list of (name, bars) for each section."""
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
        out.append((name, bars))
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
    if n == 'section' or 'section' in n: return 'generic'
    return 'other'


def main():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    pool = {}
    for fn in PAGES:
        page_name = fn.replace('.html', '')
        for slug, title, artist in slugs_from_page(fn):
            pool.setdefault(slug, {'title': title, 'artist': artist, 'pages': []})
            pool[slug]['pages'].append(page_name)
    slugs = list(pool.keys())
    print(f"pool: {len(slugs)} unique songs across {PAGES}")

    songs = []
    for i in range(0, len(slugs), 100):
        chunk = slugs[i:i+100]
        rows = (sb.schema('parcels').table('songs')
                .select('slug,artist,title,hookpad_json')
                .in_('slug', chunk).execute().data)
        by_slug = {r['slug']: r for r in rows}
        for slug in chunk:
            meta = pool[slug]
            r = by_slug.get(slug)
            if not r or not r.get('hookpad_json'):
                songs.append({**meta, 'slug': slug, 'sections': None, 'flag': 'no-data'})
                continue
            secs = section_breakdown(r['hookpad_json'])
            flag = ''
            real_secs = [s for s in secs if section_class(s[0]) not in ('generic','other')]
            if not secs:
                flag = 'no-sections'
            elif not real_secs:
                flag = 'only-generic'
            elif len(real_secs) <= 2:
                flag = 'few-sections'
            songs.append({**meta, 'slug': slug, 'sections': secs, 'flag': flag})

    # Sort: flagged first, then by artist + title
    flag_order = {'no-data':0, 'no-sections':1, 'only-generic':2, 'few-sections':3, '':4}
    songs.sort(key=lambda s: (flag_order.get(s['flag'], 99), s['artist'].lower(), s['title'].lower()))
    print(f"  flagged: no-data={sum(1 for s in songs if s['flag']=='no-data')}, "
          f"no-sections={sum(1 for s in songs if s['flag']=='no-sections')}, "
          f"only-generic={sum(1 for s in songs if s['flag']=='only-generic')}, "
          f"few-sections={sum(1 for s in songs if s['flag']=='few-sections')}, "
          f"OK={sum(1 for s in songs if not s['flag'])}")

    rows_html = []
    for s in songs:
        flag_html = f'<span class="flag flag-{s["flag"]}">{s["flag"]}</span>' if s['flag'] else ''
        if s['sections'] is None:
            pills = '<span class="empty">— no Hookpad data —</span>'
        elif not s['sections']:
            pills = '<span class="empty">— no sections —</span>'
        else:
            pills = ''.join(
                f'<span class="pill cls-{section_class(name)}" title="{name} - {bars} bars">'
                f'<span class="pn">{name}</span><span class="pb">{bars}</span></span>'
                for name, bars in s['sections']
            )
        pool_str = ' · '.join(s['pages'])
        rows_html.append(f'''
        <tr class="row" data-flag="{s["flag"]}" data-pool="{pool_str}">
          <td class="meta"><div class="artist">{s["artist"]}</div><div class="title">{s["title"]}</div><div class="pool">{pool_str}</div></td>
          <td class="pills">{pills}</td>
          <td class="flag-col">{flag_html}</td>
        </tr>
        ''')

    html = HTML_TEMPLATE.replace('__ROWS__', '\n'.join(rows_html)).replace('__COUNT__', str(len(songs)))
    open(OUT, 'w').write(html)
    print(f"wrote {OUT}")


HTML_TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Song Structures — Glowing Gardens</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#1a1a2e; color:#e0e0e0; margin:0; padding:0; }
  .back-link { position:fixed; top:18px; left:20px; color:#6a6a8a; text-decoration:none; font-size:13px; z-index:10; }
  .back-link:hover { color:#e0e0e0; }
  header { padding:32px 24px 16px; text-align:center; }
  header h1 { font-size:22px; font-weight:700; margin:0 0 4px; }
  header p { font-size:12px; color:#8a8ab0; margin:0; }
  .filters { padding:12px 24px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; border-bottom:1px solid #2a2a4a; }
  .filters label { font-size:12px; color:#a5a8fc; cursor:pointer; padding:4px 10px; background:#16162a; border-radius:4px; border:1px solid #2a2a4a; }
  .filters input { display:none; }
  .filters input:checked + span { color:#e0e0e0; font-weight:700; }
  .filters label:has(input:checked) { background:#3050d0; border-color:#3050d0; }
  main { padding:0 24px 48px; }
  table { width:100%; border-collapse:collapse; }
  .row { border-bottom:1px solid #20203a; }
  .row:hover { background:#1c1c30; }
  .meta { padding:8px 12px 8px 0; min-width:260px; vertical-align:top; }
  .meta .artist { font-size:11px; color:#8a8ab0; text-transform:lowercase; }
  .meta .title { font-size:14px; color:#e0e0e0; font-weight:600; }
  .meta .pool { font-size:10px; color:#6a6a8a; text-transform:uppercase; letter-spacing:0.5px; }
  .pills { padding:8px 0; vertical-align:middle; }
  .pill { display:inline-flex; align-items:center; gap:4px; padding:3px 8px; margin:2px 3px 2px 0; border-radius:11px; font-size:11px; background:#2a2a4a; }
  .pill .pn { color:#e0e0e0; }
  .pill .pb { color:#a5a8fc; font-weight:700; font-family: ui-monospace, monospace; background:#16162a; border-radius:8px; padding:0 5px; }
  .cls-intro { background:#3a3a5a; }
  .cls-verse { background:#1e4a73; }
  .cls-prechorus { background:#3a5a4a; }
  .cls-chorus { background:#a01e1e; }
  .cls-bridge { background:#6e16a5; }
  .cls-solo { background:#957e0c; }
  .cls-outro { background:#3a3a5a; }
  .cls-interlude { background:#44446a; }
  .cls-generic { background:#a01b6b; }
  .cls-other { background:#444; }
  .flag-col { width:120px; padding:8px 4px; text-align:right; vertical-align:middle; }
  .flag { font-size:10px; color:#fff; padding:2px 7px; border-radius:3px; text-transform:uppercase; letter-spacing:0.5px; }
  .flag-no-data { background:#4a4a6a; }
  .flag-no-sections { background:#a01e1e; }
  .flag-only-generic { background:#b35610; }
  .flag-few-sections { background:#957e0c; }
  .empty { font-size:11px; color:#6a6a8a; }
  .summary { padding:14px 24px; background:#20203a; font-size:12px; color:#a5a8fc; border-bottom:1px solid #2a2a4a; }
</style>
</head>
<body>
<a href="index.html" class="back-link">&larr; Music</a>
<header>
  <h1>Song Structures</h1>
  <p>One row per song · section pills with bar counts · sorted by flag-needs-work first, then by artist</p>
</header>
<div class="filters" id="flagFilters">
  <span style="font-size:11px;color:#8a8ab0;">show:</span>
  <label><input type="checkbox" value="no-data" checked><span>no-data</span></label>
  <label><input type="checkbox" value="no-sections" checked><span>no-sections</span></label>
  <label><input type="checkbox" value="only-generic" checked><span>only-generic</span></label>
  <label><input type="checkbox" value="few-sections" checked><span>few-sections</span></label>
  <label><input type="checkbox" value="" checked><span>OK</span></label>
</div>
<div class="filters" id="poolFilters">
  <span style="font-size:11px;color:#8a8ab0;">pool:</span>
  <label><input type="checkbox" value="Beatles-Study" checked><span>Beatles</span></label>
  <label><input type="checkbox" value="Guitar50" checked><span>G50</span></label>
  <label><input type="checkbox" value="Guitar100" checked><span>G100</span></label>
  <label><input type="checkbox" value="Guitar150" checked><span>G150</span></label>
</div>
<div class="summary" id="summary"></div>
<main>
  <table>
    <tbody id="rows">
      __ROWS__
    </tbody>
  </table>
</main>
<script>
function applyFilters() {
  const flags = [...document.querySelectorAll('#flagFilters input:checked')].map(i=>i.value);
  const pools = [...document.querySelectorAll('#poolFilters input:checked')].map(i=>i.value);
  let visible = 0;
  document.querySelectorAll('#rows .row').forEach(row => {
    const flag = row.dataset.flag || '';
    const pool = row.dataset.pool || '';
    const flagOk = flags.includes(flag);
    const poolOk = pools.length === 0 || pools.some(p => pool.includes(p));
    const ok = flagOk && poolOk;
    row.style.display = ok ? '' : 'none';
    if (ok) visible++;
  });
  document.getElementById('summary').textContent = `${visible} songs visible (of __COUNT__ total)`;
}
document.querySelectorAll('#flagFilters input, #poolFilters input').forEach(i => i.addEventListener('change', applyFilters));
applyFilters();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
