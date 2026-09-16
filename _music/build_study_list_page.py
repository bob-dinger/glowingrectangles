"""Build a study-list page (Guitar50.html, Guitar100.html, ...): top nav + sidebar of song slugs + the new viewer.

Each rebuild_guitarN.py imports this and calls build_page(out_path, title, song_list, active_tab).

`song_list` is a list of (title, artist) tuples. The builder resolves each to a slug
by querying Supabase, falling back to a "missing" marker if no match exists.
"""
import os, re, json, sys
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_KEY', '')

# Default top nav. Order matches the user's existing layout.
DEFAULT_TABS = [
    ('Beatles',    'Beatles-Study.html'),
    ('Guitar 50',  'Guitar50.html'),
    ('Guitar 100', 'Guitar100.html'),
    ('Guitar 150', 'Guitar150.html'),
    ('Guitar 200', 'Guitar200.html'),
    ('Guitar 250', 'Guitar250.html'),
    ('Guitar 300', 'Guitar300.html'),
    ('Guitar 350', 'Guitar350.html'),
    ('Guitar 400', 'Guitar400.html'),
    ('Guitar 450', 'Guitar450.html'),
    ('Guitar 500', 'Guitar500.html'),
    ('Guitar 550', 'Guitar550.html'),
    ('Studied',    'studied-songs.html'),
]


SUFFIX_RE = re.compile(r'_(?:ly|[jocC])$')


def _kebab(s):
    """'Cheap Trick' → 'cheap-trick'. Apostrophes dropped (not converted to hyphen)."""
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-_')
    return s


def _kebab_artist(s):
    """Same as _kebab but strips leading 'the-' (so 'the old 97s' ↔ 'old 97s')."""
    k = _kebab(s)
    if k.startswith('the-'): k = k[4:]
    return k


def _strip_suffixes(slug):
    """Strip trailing _j/_ly/_o/_c suffixes (possibly stacked: 'foo_o_c_ly' → 'foo')."""
    while True:
        m = SUFFIX_RE.search(slug)
        if not m: return slug
        slug = slug[:m.start()]


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


_sb_cache = None
def _get_supabase():
    global _sb_cache
    if _sb_cache is None:
        _sb_cache = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _sb_cache


_idx_cache = None
def _indexes():
    """Build cached lookup structures from Supabase:
       - by_base:  {suffix_stripped_slug: full_slug}   ← primary slug-pattern matcher
       - by_at:    {(norm_artist, norm_title): slug}   ← fallback for differing artist text
    """
    global _idx_cache
    if _idx_cache is not None:
        return _idx_cache
    sb = _get_supabase()
    by_base, by_at, page = {}, {}, 0
    while True:
        rng = sb.schema('parcels').table('songs').select('title,artist,slug').not_.is_('slug', 'null').range(page*1000, page*1000 + 999).execute()
        rows = rng.data or []
        for r in rows:
            base = _strip_suffixes(r['slug'])
            by_base[base] = r['slug']
            key = (_norm(r['artist']), _norm(r['title']))
            by_at[key] = r['slug']
            by_at.setdefault(('', _norm(r['title'])), r['slug'])
        if len(rows) < 1000: break
        page += 1
    _idx_cache = (by_base, by_at)
    return _idx_cache


def resolve_slug(title, artist):
    """Match (title, artist) → slug. Tries kebab pattern (suffix-agnostic) first;
    falls back to (artist, title) normalized text match."""
    by_base, by_at = _indexes()
    base = f'{_kebab_artist(artist)}_{_kebab(title)}'
    if base in by_base: return by_base[base]
    return by_at.get((_norm(artist), _norm(title))) or by_at.get(('', _norm(title)))


def build_page(out_path, page_title, song_list, active_tab=None, tabs=None):
    """
    out_path: e.g. '/.../Guitar50.html'
    page_title: e.g. 'Guitar 50'
    song_list: list of (title, artist) tuples
    active_tab: name of the active tab (default: page_title)
    tabs: list of (name, href); defaults to DEFAULT_TABS
    """
    tabs = tabs or DEFAULT_TABS
    active_tab = active_tab or page_title

    songs = []
    for title, artist in song_list:
        slug = resolve_slug(title, artist)
        songs.append({'title': title, 'artist': artist, 'slug': slug})

    # Sort alphabetically by title (case-insensitive) for the sidebar
    songs.sort(key=lambda s: s['title'].lower())

    found = sum(1 for s in songs if s['slug'])
    print(f'  {found}/{len(songs)} songs resolved to slugs')

    tab_html = ''.join(
        f'<a href="{href}"{" class=\"active\"" if name == active_tab else ""}>{name}</a>'
        for name, href in tabs
    )

    html = TEMPLATE
    html = html.replace('__PAGE_TITLE__', page_title)
    html = html.replace('__TABS__', tab_html)
    html = html.replace('__SONGS__', json.dumps(songs, separators=(',', ':')))
    html = html.replace('__SUPABASE_URL__', SUPABASE_URL)
    html = html.replace('__SUPABASE_ANON_KEY__', SUPABASE_ANON_KEY)
    open(out_path, 'w').write(html)
    print(f'  wrote {out_path}')


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>__PAGE_TITLE__</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; overflow: hidden; }
.topnav { display: flex; gap: 2px; background: #0f0f1f; padding: 6px 10px; border-bottom: 1px solid #2a2a4a; flex-wrap: wrap; }
.topnav a { color: #8a8ab0; padding: 5px 12px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 500; }
.topnav a:hover { color: #e0e0e0; background: #1e1e3a; }
.topnav a.active { background: #1e1e3a; color: #e0e0e0; border-bottom: 2px solid #6366f1; border-radius: 4px 4px 0 0; }
.layout { display: flex; height: calc(100vh - 36px); }
.sidebar { width: 260px; min-width: 260px; background: #16162a; border-right: 1px solid #2a2a4a; display: flex; flex-direction: column; }
.search { padding: 10px; border-bottom: 1px solid #2a2a4a; }
.search input { width: 100%; padding: 8px; background: #1e1e3a; border: 1px solid #2a2a4a; border-radius: 4px; color: #e0e0e0; outline: none; font-size: 12px; }
.search input:focus { border-color: #6366f1; }
.songlist { overflow-y: auto; flex: 1; }
.song-item { padding: 7px 10px; cursor: pointer; border-bottom: 1px solid rgba(42,42,74,0.4); border-left: 3px solid transparent; }
.song-item:hover { background: #1e1e3a; }
.song-item.active { background: #1e1e3a; border-left-color: #6366f1; }
.song-item .title { font-weight: 600; color: #e0e0e0; font-size: 12px; }
.song-item .artist { font-size: 10px; color: #6a6a8a; }
.song-item.missing { opacity: 0.4; }

.center { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.song-header { display: flex; gap: 18px; align-items: baseline; padding: 14px 24px 10px; border-bottom: 1px solid #2a2a4a; flex-wrap: wrap; }
.song-header h1 { font-size: 20px; font-weight: 700; margin: 0; }
.song-header .artist { font-size: 13px; color: #8a8ab0; }
.song-header .meta { font-size: 12px; color: #8a8ab0; margin-left: auto; }
.song-header .meta b { color: #e0e0e0; }
.song-header .transport { display: flex; gap: 6px; align-items: center; margin-left: auto; }
.song-header .transport button { background: #2a2a4a; color: #e0e0e0; border: 1px solid #3a3a5a; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; }
.song-header .transport button:hover { background: #3a3a5a; }
.song-header .transport button.playing { background: #6e16a5; border-color: #8e26c5; }
.song-header .transport .tempo-input { width: 50px; background: #16162a; color: #e0e0e0; border: 1px solid #3a3a5a; border-radius: 4px; padding: 4px; text-align: center; font-size: 12px; }
.song-header .transport label { font-size: 11px; color: #8a8ab0; display: flex; align-items: center; gap: 4px; }

.main { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 12px; }
</style>
</head><body>
<div class="topnav">__TABS__</div>
<div class="layout">
  <div class="sidebar">
    <div class="search"><input id="search" placeholder="Filter songs..." spellcheck="false"></div>
    <div class="songlist" id="songlist"></div>
  </div>
  <div class="center">
    <div class="song-header">
      <h1 id="songTitle">select a song</h1>
      <div class="artist" id="songArtist"></div>
      <div class="meta" id="songMeta"></div>
      <div class="transport">
        <button id="playBtn">▶ Play</button>
        <button id="stopBtn">■ Stop</button>
        <label>BPM <input type="number" id="tempoInput" class="tempo-input" min="40" max="240"></label>
        <label>show
          <select id="displaySelect" class="tempo-input" style="width:auto">
            <option value="chord">chord names</option>
            <option value="roman">roman</option>
          </select>
        </label>
      </div>
    </div>
    <div class="main" id="main"><div class="status">select a song from the sidebar</div></div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>
<script>
const SONGS = __SONGS__;
const sb = window.supabase.createClient('__SUPABASE_URL__', '__SUPABASE_ANON_KEY__');
const viewer = new SongViewer({
  supabase: sb,
  mainEl: '#main',
  headerEls: { title: '#songTitle', artist: '#songArtist', meta: '#songMeta' },
  transport: { playBtn: '#playBtn', stopBtn: '#stopBtn', tempoInput: '#tempoInput', displaySelect: '#displaySelect' },
});

function renderList(filter) {
  const list = document.getElementById('songlist');
  const norm = filter ? filter.toLowerCase().trim() : '';
  list.innerHTML = SONGS.map((s, i) => {
    const text = `${s.title} ${s.artist}`.toLowerCase();
    if (norm && !text.includes(norm)) return '';
    return `<div class="song-item ${s.slug ? '' : 'missing'}" data-idx="${i}">
      <div class="title">${s.title}</div>
      <div class="artist">${s.artist}${s.slug ? '' : ' · missing'}</div>
    </div>`;
  }).join('');
}

document.getElementById('search').oninput = (e) => renderList(e.target.value);

document.getElementById('songlist').addEventListener('click', (e) => {
  const item = e.target.closest('.song-item');
  if (!item) return;
  const idx = parseInt(item.dataset.idx);
  const song = SONGS[idx];
  document.querySelectorAll('.song-item.active').forEach(el => el.classList.remove('active'));
  item.classList.add('active');
  if (!song.slug) {
    document.getElementById('main').innerHTML = `<div class="status"><b>${song.title}</b> by ${song.artist}<br><br>not in library yet.</div>`;
    document.getElementById('songTitle').textContent = song.title;
    document.getElementById('songArtist').textContent = song.artist;
    document.getElementById('songMeta').textContent = '';
    return;
  }
  viewer.load(song.slug);
});

renderList('');
// Auto-load first available song
const firstWithSlug = SONGS.findIndex(s => s.slug);
if (firstWithSlug >= 0) {
  document.querySelectorAll('.song-item')[firstWithSlug]?.click();
}
</script>
</body></html>
"""
