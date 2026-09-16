"""Generate changes.html — section-to-section chord transitions across the library.

Each row = one transition (e.g. V → I or G → F).
Click a row to filter to all songs that have that change.
Toggle between roman-numeral view (key-relative) and chord-letter view (key-absolute).
"""
import os, glob, json, re, sys
from collections import defaultdict, Counter

sys.path.insert(0, '/Users/robert/Desktop/glowinggardens_claude/_music')
from build_sections_page import (
    parse_fname, HOOKPAD_DIR,
)
from rebuild_studied_songs import USER_LIST, best_match

HERE = os.path.dirname(os.path.abspath(__file__))

# Resolve Guitar50 paths so we can tag those as a distinct subset
_ALL_FILES = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
GUITAR50_PATHS = set()
for title, artist in USER_LIST:
    p, _ = best_match(title, artist, _ALL_FILES)
    if p: GUITAR50_PATHS.add(p)

def categorize_for_changes(full_path, file_basename):
    """beatles | guitar50 | other. (We're focusing on the first 50 + Beatles per user.)"""
    if file_basename.startswith('beatles_'):
        return 'beatles'
    if full_path in GUITAR50_PATHS:
        return 'guitar50'
    return 'other'

ROMAN_UP = ['','I','II','III','IV','V','VI','VII']
MODE_QUALITIES = {
    'major':           ['M','m','m','M','M','m','d'],
    'minor':           ['m','d','M','m','m','M','M'],
    'harmonicMinor':   ['m','d','M','m','M','M','d'],
    'dorian':          ['m','m','M','M','m','d','M'],
    'mixolydian':      ['M','m','d','M','m','m','M'],
    'phrygian':        ['m','M','M','m','d','M','m'],
    'lydian':          ['M','M','m','d','M','m','m'],
    'phrygianDominant':['M','M','d','m','d','M','m'],
}

def to_roman(root, type_str, borrowed='', key_scale='major'):
    rs = str(root or '')
    if not rs: return None
    acc = ''
    while rs and rs[0] in 'b#': acc += rs[0]; rs = rs[1:]
    if not rs.isdigit(): return None
    deg = int(rs)
    if not 1 <= deg <= 7: return None
    base = ROMAN_UP[deg]; ts = str(type_str or '')
    em = ts.lower().startswith('m') and not ts.lower().startswith('maj')
    if em: is_minor=True; suffix=ts[1:]
    elif ts.lower().startswith('maj'): is_minor=False; suffix=ts
    elif borrowed and isinstance(borrowed,str) and borrowed in MODE_QUALITIES:
        q=MODE_QUALITIES[borrowed][deg-1]; is_minor=(q in ('m','d')); suffix=ts
    else:
        q=MODE_QUALITIES.get(key_scale,MODE_QUALITIES['major'])[deg-1]
        is_minor=(q in ('m','d')); suffix=ts
    if is_minor: base = base.lower()
    if suffix == '5': suffix = ''
    return f'{acc}{base}{suffix}'

NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
NOTES_FLAT  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
MAJOR_INT = [0, 2, 4, 5, 7, 9, 11]
MINOR_INT = [0, 2, 3, 5, 7, 8, 10]

def tonic_semis(t):
    for i, n in enumerate(NOTES_SHARP):
        if n == t: return i
    for i, n in enumerate(NOTES_FLAT):
        if n == t: return i
    return None

def roman_to_chord(roman, tonic, scale):
    """Convert 'V7' or 'iv' or 'bVII' in a given key to actual chord letter."""
    if not roman: return None
    m = re.match(r'^([b#]*)(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(.*)$', roman)
    if not m: return roman
    acc, deg_str, suf = m.group(1), m.group(2), m.group(3)
    is_minor = deg_str == deg_str.lower()
    deg_idx = {'I':0,'II':1,'III':2,'IV':3,'V':4,'VI':5,'VII':6}[deg_str.upper()]
    ti = tonic_semis(tonic)
    if ti is None: return roman
    intervals = MINOR_INT if scale == 'minor' else MAJOR_INT
    semis = (ti + intervals[deg_idx]) % 12
    for a in acc: semis = (semis + (-1 if a == 'b' else 1)) % 12
    use_flats = ('b' in (tonic or '')) or tonic == 'F'
    note = (NOTES_FLAT if use_flats else NOTES_SHARP)[semis]
    return note + ('m' if is_minor else '') + suf

def key_at_beat(keys, beat):
    if not keys: return {'tonic':'C','scale':'major'}
    a = keys[0]
    for k in keys:
        if k.get('beat',1) <= beat: a = k
    return a


def collect_changes():
    """Return list of transition records: (from_roman, to_roman, from_letter, to_letter, song, sections).
    Only includes beatles + Guitar50 songs to keep the initial dataset focused."""
    records = []
    all_files = sorted(glob.glob(os.path.join(HOOKPAD_DIR, '*.json')))
    for f in all_files:
        bn = os.path.basename(f)
        # Limit to Beatles + Guitar50
        if not (bn.startswith('beatles_') or f in GUITAR50_PATHS): continue
        try: d = json.load(open(f, encoding='utf-8-sig'))
        except: continue
        sections = d.get('sections') or []
        chords = d.get('chords') or []
        keys = d.get('keys') or []
        if len(sections) < 2 or not chords: continue
        artist, title = parse_fname(f)
        for i in range(len(sections)-1):
            cur, nxt = sections[i], sections[i+1]
            end_next = sections[i+2]['beat'] if i+2 < len(sections) else (d.get('endBeat') or 9e9)
            cur_chds = sorted([c for c in chords if not c.get('isRest') and c.get('beat') is not None
                               and cur['beat'] <= c['beat'] < nxt['beat']], key=lambda c: c['beat'])
            nxt_chds = sorted([c for c in chords if not c.get('isRest') and c.get('beat') is not None
                               and nxt['beat'] <= c['beat'] < end_next], key=lambda c: c['beat'])
            if not cur_chds or not nxt_chds: continue
            lc, fn = cur_chds[-1], nxt_chds[0]
            lk = key_at_beat(keys, lc['beat'])
            fk = key_at_beat(keys, fn['beat'])
            from_roman = to_roman(lc.get('root'), lc.get('type',''),
                                  lc.get('borrowed',''), lk.get('scale','major'))
            to_roman_  = to_roman(fn.get('root'), fn.get('type',''),
                                  fn.get('borrowed',''), fk.get('scale','major'))
            if not from_roman or not to_roman_: continue
            from_letter = roman_to_chord(from_roman, lk.get('tonic','C'), lk.get('scale','major'))
            to_letter   = roman_to_chord(to_roman_,  fk.get('tonic','C'), fk.get('scale','major'))
            records.append({
                'title': title, 'artist': artist,
                'from_section': cur.get('name','?'), 'to_section': nxt.get('name','?'),
                'from_roman': from_roman, 'to_roman': to_roman_,
                'from_letter': from_letter, 'to_letter': to_letter,
                'key_change': '' if (lk.get('tonic') == fk.get('tonic') and lk.get('scale') == fk.get('scale'))
                               else f'{fk.get("tonic","?")}{"m" if fk.get("scale")=="minor" else ""}',
                'set': categorize_for_changes(f, os.path.basename(f)),
            })
    return records


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Section-to-Section Changes</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }
.app { display: flex; flex-direction: column; height: 100vh; }
.nav { display: flex; gap: 4px; padding: 8px 16px 0; background: #20203a; border-bottom: 1px solid #2a2a44; }
.nav a { color: #8a8ab0; padding: 4px 10px; border-radius: 4px 4px 0 0; text-decoration: none; font-size: 12px; }
.nav a.active { background: #1a1a2e; color: #e0e0e0; }
.nav a:hover { color: #e0e0e0; }
.topbar { display: flex; gap: 10px; padding: 10px 16px; background: #20203a; border-bottom: 1px solid #333; align-items: center; flex-wrap: wrap; }
.topbar label { color: #8a8ab0; font-size: 11px; }
.topbar select, .topbar input { background: #1a1a2e; color: #e0e0e0; border: 1px solid #44446a; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-family: inherit; }
.topbar input { width: 200px; }
.count { margin-left: auto; color: #8a8ab0; font-size: 11px; }
.body { flex: 1; display: flex; overflow: hidden; }
.left {
  width: 360px; border-right: 1px solid #2a2a44; overflow-y: auto;
}
.right { flex: 1; overflow-y: auto; padding: 12px 16px; }
.change-row {
  display: flex; align-items: center; padding: 5px 12px; cursor: pointer;
  border-bottom: 1px solid #2a2a44; border-left: 3px solid transparent;
}
.change-row:hover { background: #20203a; }
.change-row.active { background: #20203a; border-left-color: #6366f1; }
.change-arrow {
  font-family: monospace; font-size: 13px; color: #e0e0e0;
  display: flex; align-items: center; gap: 6px; flex: 1;
}
.change-arrow .from, .change-arrow .to { padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.change-count { color: #8a8ab0; font-size: 11px; }
.empty { color: #6a6a8a; text-align: center; padding: 40px; }
.song-list h2 { font-size: 14px; color: #e0e0e0; margin-bottom: 10px; }
.song-list ul { list-style: none; padding: 0; margin: 0; }
.song-list li {
  padding: 6px 0; border-bottom: 1px solid #2a2a44; font-size: 12px;
  display: flex; gap: 10px; align-items: baseline;
}
.song-list .title { font-weight: 600; color: #e0e0e0; min-width: 220px; }
.song-list .artist { color: #8a8ab0; min-width: 140px; font-size: 11px; }
.song-list .sections { color: #6a8aa8; font-size: 10px; font-family: monospace; }
.song-list .key-change { color: #f4c898; font-size: 10px; }
/* degree colors */
.deg-1 { background: #f4a8a8; color: #1a1a2e; }
.deg-2 { background: #f4c898; color: #1a1a2e; }
.deg-3 { background: #f0e898; color: #1a1a2e; }
.deg-4 { background: #a8e0b0; color: #1a1a2e; }
.deg-5 { background: #a8c8f0; color: #1a1a2e; }
.deg-6 { background: #d0b0f0; color: #1a1a2e; }
.deg-7 { background: #b890e0; color: #1a1a2e; }
</style>
</head><body>
<div class="app">
  <div class="nav" id="nav"></div>
  <div class="topbar">
    <label>set</label><select id="set">
      <option value="" selected>beatles + guitar50</option>
      <option value="beatles">beatles only</option>
      <option value="guitar50">guitar50 only</option>
    </select>
    <label>view</label><select id="view">
      <option value="roman">roman (V→I)</option>
      <option value="letter">chord letters (C→F)</option>
    </select>
    <label>sort</label><select id="sort">
      <option value="count">by frequency</option>
      <option value="alpha">alphabetical</option>
    </select>
    <input id="search" placeholder="filter changes (e.g. V→I)" spellcheck="false">
    <span class="count" id="count"></span>
  </div>
  <div class="body">
    <div class="left" id="changesList"></div>
    <div class="right" id="songList"><div class="empty">click a change on the left to see all songs</div></div>
  </div>
</div>
<script>
const PAGE_LINKS = [
  ['sections.html',          'all sections'],
  ['sections-studied.html',  'studied sections'],
  ['breaks.html',            'phrase breaks'],
  ['changes.html',           'changes ↗'],
  ['Guitar50.html',          '← study pages'],
];
const here = (location.pathname.split('/').pop() || 'changes.html');
document.getElementById('nav').innerHTML = PAGE_LINKS.map(([h,l]) =>
  `<a href="${h}" class="${h===here?'active':''}">${l}</a>`).join('');

const DATA = __DATA__;

function chordDeg(s) {
  // pull leading digit from roman or letter — for color
  const r = (s || '').match(/^[b#]*(I{1,3}|IV|V|VI{0,2}|VII|i{1,3}|iv|v|vi{0,2}|vii)/);
  if (r) {
    return {I:1,II:2,III:3,IV:4,V:5,VI:6,VII:7,i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7}[r[1]];
  }
  // letter: derive from note alphabetical position — fallback to no color
  return null;
}

let selectedChange = null;

function render() {
  const setF = document.getElementById('set').value;
  const view = document.getElementById('view').value;
  const sortBy = document.getElementById('sort').value;
  const q = document.getElementById('search').value.trim().toLowerCase();

  // Filter the dataset
  const rows = DATA.filter(r => !setF || r.set === setF);

  // Aggregate by (from, to) using the selected view
  const keyOf = r => view === 'letter'
    ? `${r.from_letter} → ${r.to_letter}`
    : `${r.from_roman} → ${r.to_roman}`;
  const groups = new Map();
  rows.forEach(r => {
    const k = keyOf(r);
    if (q && !k.toLowerCase().includes(q)) return;
    if (!groups.has(k)) groups.set(k, { key: k, from: view==='letter' ? r.from_letter : r.from_roman,
                                          to: view==='letter' ? r.to_letter : r.to_roman,
                                          songs: new Set(), records: [] });
    const g = groups.get(k);
    g.songs.add(r.artist + '|' + r.title);
    g.records.push(r);
  });

  // Sort
  let entries = [...groups.values()];
  if (sortBy === 'count') entries.sort((a,b) => b.songs.size - a.songs.size);
  else entries.sort((a,b) => a.key.localeCompare(b.key));

  document.getElementById('count').textContent =
    `${entries.length} unique changes from ${rows.length} transitions`;

  const list = document.getElementById('changesList');
  list.innerHTML = entries.map(e => {
    const fromDeg = chordDeg(e.from);
    const toDeg = chordDeg(e.to);
    const isActive = (selectedChange === e.key);
    return `<div class="change-row ${isActive?'active':''}" data-key="${e.key}">
      <div class="change-arrow">
        <span class="from ${fromDeg?'deg-'+fromDeg:''}">${e.from}</span>
        <span style="color:#6a6a8a">→</span>
        <span class="to ${toDeg?'deg-'+toDeg:''}">${e.to}</span>
      </div>
      <div class="change-count">${e.songs.size}</div>
    </div>`;
  }).join('');

  // Render the song list for selected change
  if (selectedChange) {
    const g = groups.get(selectedChange);
    if (g) {
      const seen = new Set();
      // De-dupe by (artist, title) — keep first occurrence
      const unique = [];
      g.records.forEach(r => {
        const k = r.artist + '|' + r.title;
        if (!seen.has(k)) { seen.add(k); unique.push(r); }
      });
      const right = document.getElementById('songList');
      right.innerHTML = `<div class="song-list">
        <h2>${g.key} — ${unique.length} songs</h2>
        <ul>
          ${unique.map(r => `<li>
            <span class="title">${r.title}</span>
            <span class="artist">${r.artist}</span>
            <span class="sections">${r.from_section} → ${r.to_section}</span>
            ${r.key_change ? `<span class="key-change">→ ${r.key_change}</span>` : ''}
          </li>`).join('')}
        </ul>
      </div>`;
    }
  }
}

document.addEventListener('change', e => { if (e.target.closest('.topbar')) render(); });
document.getElementById('search').addEventListener('input', render);
document.addEventListener('click', e => {
  const row = e.target.closest('.change-row');
  if (row) {
    selectedChange = row.dataset.key;
    render();
  }
});
render();
</script>
</body></html>
"""


def main():
    records = collect_changes()
    inlined = json.dumps(records, separators=(',',':'))
    html = TEMPLATE.replace('__DATA__', inlined)
    out = os.path.join(HERE, 'changes.html')
    open(out, 'w').write(html)
    print(f'wrote {len(records)} transitions → {out}')


if __name__ == '__main__':
    main()
