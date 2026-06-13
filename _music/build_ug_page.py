"""Build _music/ug.html — mobile page: pool selector + alphabetical song list with UG links + per-section Hookpad screenshots."""
import os, re, json, glob
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'ug.html')
IMG_ROOT = os.path.join(os.path.dirname(HERE), 'hookpad_images')   # repo-root /hookpad_images/
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


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or '').lower())


# Map our internal pool labels (Beatles / G50 / G100 / …) to folder names
# under hookpad_images/ that the user actually uses (beatles / guitar50 / guitar100 / …).
POOL_FOLDER = {
    'Beatles': 'beatles',
    'G50': 'guitar50', 'G100': 'guitar100', 'G150': 'guitar150',
    'G200': 'guitar200', 'G250': 'guitar250', 'G300': 'guitar300',
    'G350': 'guitar350', 'G400': 'guitar400', 'G450': 'guitar450',
    'G500': 'guitar500', 'G550': 'guitar550',
}


def find_images(pool_label, artist, title):
    """Look under hookpad_images/<folder>/* for a folder matching artist_title.
    Return list of {name, path} for any .png/.jpg files inside."""
    pool_dir = os.path.join(IMG_ROOT, POOL_FOLDER.get(pool_label, pool_label.lower()))
    if not os.path.isdir(pool_dir):
        return []
    target_key = norm(artist) + norm(title)
    for entry in os.listdir(pool_dir):
        full = os.path.join(pool_dir, entry)
        if not os.path.isdir(full): continue
        if norm(entry.replace('_', ' ')) != target_key: continue
        files = []
        for img in sorted(glob.glob(os.path.join(full, '*.png')) + glob.glob(os.path.join(full, '*.jpg'))):
            name = os.path.splitext(os.path.basename(img))[0]
            # path relative to repo root (so the served URL works on GH Pages)
            rel = os.path.relpath(img, os.path.dirname(HERE))
            files.append({'name': name, 'path': '../' + rel.replace(os.sep, '/')})
        return files
    return []


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
        r = sb.schema('parcels').table('songs').select('slug,artist,title,ug_url,bpm,key_tonic,key_scale,hookpad_url').in_('slug', chunk).execute().data
        for row in r:
            rows[row['slug']] = row
    pool_data = {}
    total_with_url = 0
    total_with_images = 0
    for label, slugs in pools.items():
        items = []
        for slug in slugs:
            r = rows.get(slug)
            if not r: continue
            imgs = find_images(label, r.get('artist'), r.get('title'))
            if imgs: total_with_images += 1
            bpm = r.get('bpm')
            key = (r.get('key_tonic') or '') + (' min' if r.get('key_scale') == 'minor' else '')
            items.append({
                'title': r.get('title') or '',
                'artist': r.get('artist') or '',
                'ug_url': r.get('ug_url'),
                'hookpad_url': r.get('hookpad_url'),
                'bpm': round(bpm) if bpm else None,
                'key': key.strip() or None,
                'images': imgs,
            })
        items.sort(key=lambda s: s['title'].lower())
        pool_data[label] = items
        n_url = sum(1 for x in items if x['ug_url'])
        total_with_url += n_url
        n_img = sum(1 for x in items if x['images'])
        print(f"  {label}: {len(items)} songs, {n_url} with ug_url, {n_img} with images")
    print(f"total UG links: {total_with_url}, songs with images: {total_with_images}")

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
  ul.songs li { padding:12px 16px; display:flex; align-items:center; gap:10px; border-bottom:1px solid #1e1e3a; }
  ul.songs li .song-meta { flex:1; min-width:0; }
  ul.songs li .title { font-size:15px; font-weight:600; color:#e0e0e0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  ul.songs li .artist { font-size:12px; color:#8a8ab0; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .btn { display:inline-flex; align-items:center; justify-content:center; padding:8px 12px; border-radius:8px; font-size:12px; font-weight:700; text-decoration:none; min-width:48px; height:36px; box-sizing:border-box; flex-shrink:0; user-select:none; }
  .btn-hp { background:#3050d0; color:#fff; }
  .btn-hp.disabled { background:#1e1e3a; color:#5a5a7a; pointer-events:none; }
  .btn-ug { background:#a01e1e; color:#fff; }
  .btn-ug.disabled { background:#1e1e3a; color:#5a5a7a; pointer-events:none; }

  /* Song-detail view (per-song image page) */
  .detail-view { display:none; }
  .detail-view.active { display:block; }
  .list-view.hidden { display:none; }
  .detail-header { padding:14px 16px; display:flex; align-items:center; gap:12px; border-bottom:1px solid #2a2a4a; position:sticky; top:0; background:#0f0f1f; z-index:5; }
  .back-btn { background:transparent; border:none; color:#a5b4fc; font-size:15px; font-weight:600; cursor:pointer; padding:0; }
  .detail-title { font-size:16px; font-weight:700; color:#e0e0e0; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .detail-meta { padding:10px 16px; background:#16162a; border-bottom:1px solid #2a2a4a; display:flex; gap:14px; align-items:center; flex-wrap:wrap; font-size:13px; color:#8a8ab0; }
  .detail-meta .chip { background:#20203a; color:#e0e0e0; padding:4px 10px; border-radius:11px; font-size:12px; font-weight:600; }
  .detail-meta .key { background:#3050d0; color:#fff; font-family:ui-monospace,monospace; }
  .detail-meta .bpm { background:#a01e1e; color:#fff; }
  .detail-meta a { color:#a5b4fc; text-decoration:none; font-weight:700; margin-left:auto; }
  .detail-images { padding:12px; display:flex; flex-direction:column; gap:14px; }
  .detail-images .section { background:#16162a; border:1px solid #2a2a4a; border-radius:8px; overflow:hidden; }
  .detail-images .section .label { padding:8px 12px; font-size:13px; font-weight:600; color:#a5b4fc; text-transform:capitalize; border-bottom:1px solid #2a2a4a; }
  .detail-images .section img { display:block; width:100%; height:auto; }
  .detail-images .empty { color:#6a6a8a; text-align:center; padding:40px 16px; font-size:13px; }
</style>
</head>
<body>
<div class="list-view" id="listView">
  <header>
    <h1>Songs</h1>
    <div class="pool-pills" id="pillBar"></div>
    <div class="count" id="count"></div>
  </header>
  <ul class="songs" id="songs"></ul>
</div>
<div class="detail-view" id="detailView">
  <div class="detail-header">
    <button class="back-btn" id="backBtn">← Back</button>
    <div class="detail-title" id="detailTitle"></div>
    <a id="detailUg" class="btn btn-ug" target="_blank" rel="noopener">UG ↗</a>
  </div>
  <div class="detail-meta" id="detailMeta"></div>
  <div class="detail-images" id="detailImages"></div>
</div>

<script>
const DATA = __DATA__;
const POOLS = __POOLS__;

let currentPool = null;
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function pickPool(label) {
  currentPool = label;
  localStorage.setItem('ugPool', label);
  document.querySelectorAll('#pillBar .pill').forEach(p => {
    p.classList.toggle('active', p.dataset.pool === label);
  });
  const items = DATA[label] || [];
  const withUrl = items.filter(x => x.ug_url).length;
  const withImg = items.filter(x => x.images && x.images.length).length;
  document.getElementById('count').textContent = `${items.length} songs · ${withUrl} UG · ${withImg} HP`;
  document.getElementById('songs').innerHTML = items.map((s, i) => {
    const hpBtn = (s.images && s.images.length)
      ? `<a class="btn btn-hp" href="#${encodeURIComponent(label)}/${i}">HP</a>`
      : `<span class="btn btn-hp disabled">HP</span>`;
    const ugBtn = s.ug_url
      ? `<a class="btn btn-ug" href="${s.ug_url}" target="_blank" rel="noopener">UG</a>`
      : `<span class="btn btn-ug disabled">UG</span>`;
    return `<li>
      <div class="song-meta">
        <div class="title">${escapeHtml(s.title)}</div>
        <div class="artist">${escapeHtml(s.artist)}</div>
      </div>
      ${hpBtn}${ugBtn}
    </li>`;
  }).join('');
  window.scrollTo(0, 0);
}

function showDetail(poolLabel, idx) {
  const items = DATA[poolLabel] || [];
  const s = items[idx];
  if (!s) { goHome(); return; }
  document.getElementById('listView').classList.add('hidden');
  document.getElementById('detailView').classList.add('active');
  document.getElementById('detailTitle').innerHTML = `${escapeHtml(s.title)} <span style="font-weight:400;color:#8a8ab0;font-size:13px"> — ${escapeHtml(s.artist)}</span>`;
  const ugA = document.getElementById('detailUg');
  if (s.ug_url) { ugA.href = s.ug_url; ugA.classList.remove('disabled'); }
  else { ugA.removeAttribute('href'); ugA.classList.add('disabled'); }
  const meta = document.getElementById('detailMeta');
  const bits = [];
  if (s.key) bits.push(`<span class="chip key">${escapeHtml(s.key)}</span>`);
  if (s.bpm) bits.push(`<span class="chip bpm">${s.bpm} BPM</span>`);
  if (s.hookpad_url) bits.push(`<a href="${s.hookpad_url}" target="_blank" rel="noopener">Open in Hookpad ↗</a>`);
  meta.innerHTML = bits.join('');
  meta.style.display = bits.length ? '' : 'none';
  const div = document.getElementById('detailImages');
  if (!s.images || !s.images.length) {
    div.innerHTML = `<div class="empty">No Hookpad screenshots yet.</div>`;
  } else {
    div.innerHTML = s.images.map(img => `<div class="section"><img src="${escapeHtml(img.path)}" loading="lazy" alt=""></div>`).join('');
  }
  window.scrollTo(0, 0);
}

function goHome() {
  document.getElementById('listView').classList.remove('hidden');
  document.getElementById('detailView').classList.remove('active');
}

function handleHash() {
  const h = decodeURIComponent(location.hash.replace(/^#/, ''));
  if (!h) { goHome(); return; }
  const parts = h.split('/');
  if (parts.length === 2) {
    const pool = parts[0];
    const idx = parseInt(parts[1], 10);
    if (DATA[pool] && !isNaN(idx)) {
      if (currentPool !== pool) pickPool(pool);
      showDetail(pool, idx);
      return;
    }
  }
  goHome();
}

document.getElementById('pillBar').innerHTML = POOLS.map(p => `<div class="pill" data-pool="${p}">${p}</div>`).join('');
document.querySelectorAll('#pillBar .pill').forEach(p => p.addEventListener('click', () => {
  pickPool(p.dataset.pool);
  if (location.hash) history.pushState(null, '', location.pathname);
  goHome();
}));
document.getElementById('backBtn').addEventListener('click', () => history.back());
window.addEventListener('hashchange', handleHash);
window.addEventListener('popstate', handleHash);

pickPool(localStorage.getItem('ugPool') || POOLS[0]);
handleHash();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
