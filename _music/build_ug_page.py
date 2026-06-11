"""Build _music/ug.html — mobile page: pool selector + alphabetical song list with UG links."""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'ug.html')
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
    return [s['slug'] for s in json.loads(m.group(1)) if s.get('slug')]


def main():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    pools = {}
    all_slugs = set()
    for label, fn in PAGES:
        ss = slugs_from_page(fn)
        pools[label] = ss
        all_slugs.update(ss)
    print(f"slugs: {len(all_slugs)} across {len(pools)} pools")
    rows = {}
    for i in range(0, len(all_slugs), 100):
        chunk = list(all_slugs)[i:i+100]
        r = sb.schema('parcels').table('songs').select('slug,artist,title,ug_url').in_('slug', chunk).execute().data
        for row in r:
            rows[row['slug']] = row
    pool_data = {}
    total_with_url = 0
    for label, slugs in pools.items():
        items = []
        for slug in slugs:
            r = rows.get(slug)
            if not r: continue
            items.append({'title': r.get('title') or '', 'artist': r.get('artist') or '', 'ug_url': r.get('ug_url')})
        items.sort(key=lambda s: s['title'].lower())
        pool_data[label] = items
        n_url = sum(1 for x in items if x['ug_url'])
        total_with_url += n_url
        print(f"  {label}: {len(items)} songs, {n_url} with ug_url")
    print(f"total UG links: {total_with_url}")

    html = HTML.replace('__DATA__', json.dumps(pool_data, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('__POOLS__', json.dumps(list(pool_data.keys())))
    open(OUT, 'w').write(html)
    print(f"wrote {OUT}")


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>UG — Glowing Gardens</title>
<style>
  :root { font-size:16px; }
  * { box-sizing:border-box; }
  body { margin:0; background:#0f0f1f; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; padding-bottom:40px; }
  header { padding:14px 16px; position:sticky; top:0; background:#0f0f1f; z-index:10; border-bottom:1px solid #2a2a4a; }
  h1 { margin:0 0 10px; font-size:18px; font-weight:700; }
  .pool-pills { display:flex; gap:6px; flex-wrap:wrap; }
  .pill { padding:6px 12px; background:#20203a; color:#e0e0e0; border:1px solid #2a2a4a; border-radius:14px; font-size:13px; font-weight:600; cursor:pointer; user-select:none; }
  .pill.active { background:#3050d0; border-color:#3050d0; color:#fff; }
  .count { font-size:12px; color:#8a8ab0; margin-top:8px; }
  ul.songs { list-style:none; margin:0; padding:0; }
  ul.songs li { border-bottom:1px solid #1e1e3a; }
  ul.songs li a { display:block; padding:14px 16px; color:#e0e0e0; text-decoration:none; }
  ul.songs li a:active { background:#1e1e3a; }
  ul.songs li.no-url { padding:14px 16px; color:#6a6a8a; }
  .title { font-size:16px; font-weight:600; color:#e0e0e0; }
  .artist { font-size:13px; color:#8a8ab0; margin-top:2px; }
  .no-url .artist { color:#5a5a7a; }
  .arrow { float:right; color:#6366f1; font-size:14px; }
</style>
</head>
<body>
<header>
  <h1>UG quick links</h1>
  <div class="pool-pills" id="pillBar"></div>
  <div class="count" id="count"></div>
</header>
<ul class="songs" id="songs"></ul>

<script>
const DATA = __DATA__;
const POOLS = __POOLS__;

function pickPool(label) {
  localStorage.setItem('ugPool', label);
  document.querySelectorAll('#pillBar .pill').forEach(p => {
    p.classList.toggle('active', p.dataset.pool === label);
  });
  const items = DATA[label] || [];
  const withUrl = items.filter(x => x.ug_url).length;
  document.getElementById('count').textContent = `${withUrl} of ${items.length} have a UG link`;
  const list = document.getElementById('songs');
  list.innerHTML = items.map(s => s.ug_url
    ? `<li><a href="${s.ug_url}" target="_blank" rel="noopener"><div class="title">${escapeHtml(s.title)} <span class="arrow">↗</span></div><div class="artist">${escapeHtml(s.artist)}</div></a></li>`
    : `<li class="no-url"><div class="title">${escapeHtml(s.title)}</div><div class="artist">${escapeHtml(s.artist)} · no UG link</div></li>`
  ).join('');
  window.scrollTo(0, 0);
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

document.getElementById('pillBar').innerHTML = POOLS.map(p => `<div class="pill" data-pool="${p}">${p}</div>`).join('');
document.querySelectorAll('#pillBar .pill').forEach(p => p.addEventListener('click', () => pickPool(p.dataset.pool)));
pickPool(localStorage.getItem('ugPool') || POOLS[0]);
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
