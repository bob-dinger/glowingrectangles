"""Build _music/melody-structures.html from ~/Desktop/melodies_curated.xlsx.

Schema (one row per melody):
  slug, artist, title, section, patterns, chord_shape, notes, hookpad_url

`patterns` is a comma-separated list of pattern strings like
  "8-2222-ABBC", "4-112", "16-4444-AABA"
A single melody can carry multiple patterns (e.g. outer + inner).
"""
import os, json, re
from collections import defaultdict
from openpyxl import load_workbook

XLSX = os.path.expanduser('~/Desktop/melodies_curated.xlsx')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'melody-structures.html')


def parse_pattern(p):
    """'8-2222-ABBC' → (8, '2222', 'ABBC'); '4-112' → (4, '112', '')"""
    parts = p.strip().split('-')
    if len(parts) < 2: return None
    try:
        bars = int(parts[0])
    except ValueError:
        return None
    split = parts[1]
    letter = parts[2] if len(parts) >= 3 else ''
    return (bars, split, letter)


def split_to_widths(split):
    """'2222' → [2,2,2,2]; '224' → [2,2,4]; '112' → [1,1,2]; '4+4' → [4,4]"""
    if '+' in split:
        return [int(s) for s in split.split('+') if s.isdigit()]
    if split.isdigit():
        return [int(c) for c in split]
    return []


def build():
    wb = load_workbook(XLSX)
    ws = wb['melodies']
    headers = [c.value for c in ws[1]]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0]: continue
        rows.append(dict(zip(headers, r)))
    print(f"loaded {len(rows)} curated melodies")

    # Build pattern → list of rows index
    pat_to_rows = defaultdict(list)
    for r in rows:
        pats_str = (r.get('patterns') or '').strip()
        if not pats_str: continue
        pats = [p.strip() for p in pats_str.split(',') if p.strip()]
        r['_pats_parsed'] = []
        for p in pats:
            parsed = parse_pattern(p)
            if not parsed: continue
            pat_to_rows[p].append(r)
            r['_pats_parsed'].append((p, parsed))

    # Sort patterns: by bars asc, then by split, then letter
    def pat_sort_key(p):
        parsed = parse_pattern(p)
        if not parsed: return (999, '', '')
        bars, split, letter = parsed
        return (bars, split, letter)
    sorted_patterns = sorted(pat_to_rows.keys(), key=pat_sort_key)

    # Build pattern data for inline JSON (rows formatted for rendering)
    def render_row_data(r):
        return {
            'title': r['title'], 'artist': r['artist'], 'section': r['section'],
            'slug': r['slug'], 'hookpad_url': r.get('hookpad_url') or '',
            'chord_shape': r.get('chord_shape') or '',
            'notes': r.get('notes') or '',
            'patterns': [{'str': p, 'bars': parsed[0], 'split': parsed[1], 'letter': parsed[2]}
                         for p, parsed in r.get('_pats_parsed', [])],
        }
    data = {p: [render_row_data(r) for r in pat_to_rows[p]] for p in sorted_patterns}

    # Sidebar HTML
    sidebar = []
    cur_bars = None
    for p in sorted_patterns:
        parsed = parse_pattern(p)
        if not parsed: continue
        bars = parsed[0]
        if bars != cur_bars:
            sidebar.append(f'<div class="bars-header">{bars} bars</div>')
            cur_bars = bars
        n = len(pat_to_rows[p])
        sidebar.append(f'<div class="pat-link" data-pat="{p}">{p}<span class="ct">{n}</span></div>')
    sidebar_html = '\n'.join(sidebar)

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Melody Structures — Curated</title>
<style>
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; height:100%; background:#1a1a2e; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:13px; overflow:hidden; }}
  .topbar {{ display:flex; align-items:center; gap:14px; padding:10px 16px; border-bottom:1px solid #2a2a4a; background:#0f0f1f; }}
  .topbar a.back {{ color:#6a6a8a; text-decoration:none; font-size:12px; }}
  .topbar a.back:hover {{ color:#e0e0e0; }}
  .topbar h1 {{ font-size:14px; font-weight:700; margin:0; }}
  .topbar .sub {{ color:#6a6a8a; font-size:11px; margin-left:auto; }}
  .layout {{ display:flex; height:calc(100vh - 42px); }}
  .sidebar {{ width:240px; flex-shrink:0; background:#16162a; border-right:1px solid #2a2a4a; overflow-y:auto; padding:6px 0 20px; }}
  .bars-header {{ padding:8px 14px 4px; color:#a5a8fc; font-size:10px; text-transform:uppercase; letter-spacing:1.2px; font-weight:700; background:#1a1a30; margin-top:4px; }}
  .pat-link {{ padding:6px 16px; cursor:pointer; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:#a0a0c0; border-left:3px solid transparent; display:flex; align-items:baseline; }}
  .pat-link:hover {{ background:#22223e; color:#e0e0e0; }}
  .pat-link.active {{ background:#22223e; color:#fff; border-left-color:#3050d0; }}
  .pat-link .ct {{ margin-left:auto; color:#5a5a7a; font-size:10px; }}
  .right {{ flex:1; overflow-y:auto; padding:18px 24px; }}
  .right h2 {{ font-size:14px; color:#e0e0e0; margin:0 0 4px; font-family:ui-monospace,Menlo,monospace; }}
  .right .meta {{ color:#6a6a8a; font-size:11px; margin-bottom:14px; }}
  .card {{ background:#16162a; border:1px solid #2a2a4a; border-radius:6px; padding:10px 14px; margin-bottom:10px; }}
  .card-head {{ display:flex; align-items:baseline; gap:10px; margin-bottom:8px; font-size:13px; flex-wrap:wrap; }}
  .card-head .title {{ font-weight:700; color:#e0e0e0; }}
  .card-head .artist {{ color:#8a8ab0; font-size:12px; }}
  .card-head .section {{ color:#6a6a8a; font-size:11px; }}
  .card-head .hp {{ color:#a5b4fc; text-decoration:none; font-size:11px; font-weight:700; margin-left:auto; padding:2px 8px; background:rgba(99,102,241,0.15); border-radius:4px; }}
  .card-head .hp:hover {{ background:rgba(99,102,241,0.3); }}
  .blocks {{ display:flex; gap:3px; height:44px; }}
  .ph {{ position:relative; display:flex; align-items:stretch; border-radius:4px; overflow:hidden; min-width:30px; }}
  .ph .lt {{ position:absolute; top:3px; left:6px; font-weight:700; font-size:13px; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,0.5); z-index:2; }}
  .ph-A {{ background:rgba(60,120,220,0.85); }}
  .ph-B {{ background:rgba(220,90,80,0.85); }}
  .ph-C {{ background:rgba(50,180,80,0.85); }}
  .ph-D {{ background:rgba(230,170,40,0.85); }}
  .ph-E {{ background:rgba(160,80,220,0.85); }}
  .ph-F {{ background:rgba(220,70,200,0.85); }}
  .ph-X {{ background:#3a3a5a; }}
  .all-patterns {{ font-family:ui-monospace,Menlo,monospace; font-size:10px; color:#8a8ab0; margin-top:6px; }}
  .all-patterns .pat {{ background:#22223e; padding:1px 6px; border-radius:3px; margin-right:5px; }}
  .sub-meta {{ font-size:11px; color:#8a8ab0; margin-top:6px; display:flex; gap:14px; flex-wrap:wrap; }}
  .sub-meta .chord {{ color:#fbbf24; font-weight:600; }}
  .sub-meta .notes {{ color:#8a8ab0; font-style:italic; }}
  .placeholder {{ color:#5a5a7a; text-align:center; margin-top:80px; font-size:13px; }}
</style>
</head>
<body>
<div class="topbar">
  <a class="back" href="index.html">&larr; Music</a>
  <h1>Melody Structures (curated)</h1>
  <div class="sub">{len(rows)} melodies · {len(sorted_patterns)} unique patterns · source: <code>~/Desktop/melodies_curated.xlsx</code></div>
</div>
<div class="layout">
  <aside class="sidebar">
    {sidebar_html}
  </aside>
  <main class="right" id="right">
    <div class="placeholder">— pick a pattern on the left —</div>
  </main>
</div>

<script>
const DATA = {json.dumps(data, ensure_ascii=False)};

function splitToWidths(split) {{
  if (split.includes('+')) return split.split('+').filter(s => /^\\d+$/.test(s)).map(Number);
  if (/^\\d+$/.test(split)) return split.split('').map(Number);
  return [];
}}

function escapeHtml(s) {{
  return String(s || '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
}}

function renderBlocks(pattern) {{
  const widths = splitToWidths(pattern.split);
  const letters = (pattern.letter || '').split('');
  return '<div class="blocks">' + widths.map((w, i) => {{
    const lt = letters[i] || '';
    const lt_norm = lt.toUpperCase().replace(/[^A-F]/g, '').slice(0,1) || 'X';
    return `<div class="ph ph-${{lt_norm}}" style="flex:${{w}}">` +
           (lt ? `<span class="lt">${{escapeHtml(lt)}}</span>` : '') +
           `</div>`;
  }}).join('') + '</div>';
}}

function show(patStr) {{
  const items = DATA[patStr] || [];
  const right = document.getElementById('right');
  const head = `<h2>${{escapeHtml(patStr)}}</h2><div class="meta">${{items.length}} melod${{items.length===1?'y':'ies'}}</div>`;
  if (!items.length) {{ right.innerHTML = head + '<div class="placeholder">no entries</div>'; return; }}
  const cards = items.map(r => {{
    // Render blocks for THIS pattern specifically (find matching)
    const thisPat = r.patterns.find(p => p.str === patStr) || r.patterns[0];
    const blocks = renderBlocks(thisPat);
    const hp = r.hookpad_url ? `<a class="hp" href="${{r.hookpad_url}}" target="_blank" rel="noopener">HP↗</a>` : '';
    const allPats = r.patterns.length > 1
      ? `<div class="all-patterns">all: ${{r.patterns.map(p => `<span class="pat">${{escapeHtml(p.str)}}</span>`).join('')}}</div>`
      : '';
    const extras = [];
    if (r.chord_shape) extras.push(`<span class="chord">${{escapeHtml(r.chord_shape)}}</span>`);
    if (r.notes) extras.push(`<span class="notes">${{escapeHtml(r.notes)}}</span>`);
    const extraHtml = extras.length ? `<div class="sub-meta">${{extras.join(' · ')}}</div>` : '';
    return `<div class="card">
      <div class="card-head">
        <span class="title">${{escapeHtml(r.title)}}</span>
        <span class="artist">${{escapeHtml(r.artist)}}</span>
        <span class="section">[${{escapeHtml(r.section)}}]</span>
        ${{hp}}
      </div>
      ${{blocks}}
      ${{allPats}}
      ${{extraHtml}}
    </div>`;
  }}).join('');
  right.innerHTML = head + cards;
  document.querySelectorAll('.pat-link').forEach(p => p.classList.toggle('active', p.dataset.pat === patStr));
  localStorage.setItem('melodyPat', patStr);
}}

document.querySelectorAll('.pat-link').forEach(p => {{
  p.addEventListener('click', () => show(p.dataset.pat));
}});

// Restore last selected pattern
const last = localStorage.getItem('melodyPat');
if (last && DATA[last]) show(last);
else {{
  // pick first
  const first = document.querySelector('.pat-link');
  if (first) show(first.dataset.pat);
}}
</script>
</body>
</html>
'''
    with open(OUT, 'w') as f: f.write(html)
    print(f"wrote {OUT}")


if __name__ == '__main__':
    build()
