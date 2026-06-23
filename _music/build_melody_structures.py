"""Build _music/melody-structures.html from parcels.melodies in Supabase.

For each curated melody, pulls the actual chord + note data from
parcels.songs.hookpad_json so the page can render a per-melody piano roll.

Source of truth: parcels.melodies table.
Edit via ~/Desktop/melodies_curated.xlsx + run sync_melodies_to_supabase.py
to push changes, then run this script to rebuild the page.

melodies schema:
  slug, section, patterns, chord_shape, notes
`patterns` is a comma-separated list of pattern strings like
  "8-2222-ABBC", "4-112", "16-4444-AABA"
"""
import os, json, re
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'melody-structures.html')

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])


def parse_pattern(p):
    parts = p.strip().split('-')
    if len(parts) < 2: return None
    try: bars = int(parts[0])
    except ValueError: return None
    return (bars, parts[1], parts[2] if len(parts) >= 3 else '')


def norm_name(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())


def fetch_section_data(slug, section_name, pickup_beats=0):
    """Return {chords, notes, start, end, bpm, key, pickup_beats, pickup_note_count}
    for the named section, or None. Pickup notes (those starting in
    [start - pickup_beats, start)) are included with NEGATIVE beat offsets."""
    rows = sb.schema('parcels').table('songs').select(
        'slug,hookpad_json'
    ).eq('slug', slug).limit(1).execute().data
    if not rows: return None
    d = rows[0]['hookpad_json'] or {}
    sections = sorted(d.get('sections') or [], key=lambda s: s.get('beat', 0))
    if not sections: return None
    target = norm_name(section_name)
    end_beat = d.get('endBeat') or 0
    bpb = ((d.get('meters') or [{}])[0].get('numBeats')) or 4
    keys = d.get('keys') or [{}]
    tonic = keys[0].get('tonic') or 'C'
    scale = keys[0].get('scale') or 'major'
    tempos = d.get('tempos') or [{}]
    bpm = tempos[0].get('bpm') or 120
    def section_matches(name):
        n = norm_name(name)
        if n == target: return True
        stripped = re.sub(r'(?:[0-9]+|i+|iv|v|vi+)$', '', n)
        if stripped == target: return True
        return False
    for i, s in enumerate(sections):
        if section_matches(s.get('name') or s.get('label')):
            start = s.get('beat', 0)
            end = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
            fetch_start = start - (pickup_beats or 0)
            chs = [c for c in (d.get('chords') or [])
                   if c.get('beat') is not None and fetch_start <= c['beat'] < end]
            nts = [n for n in (d.get('notes') or [])
                   if n.get('beat') is not None and fetch_start <= n['beat'] < end]
            pickup_note_count = sum(1 for n in nts if n.get('beat', 0) < start)
            return {
                'start': start, 'end': end, 'bpb': bpb, 'bpm': bpm,
                'key': tonic, 'scale': scale,
                'pickup_beats': pickup_beats or 0,
                'pickup_note_count': pickup_note_count,
                'chords': [{'r': c.get('root'), 't': c.get('type', 0),
                            'b': round(c['beat'] - start, 3),
                            'd': round(c.get('duration', 1), 3),
                            'app': c.get('applied') or 0,
                            'bor': c.get('borrowed') or ''}
                           for c in chs],
                'notes': [{'sd': n.get('sd'), 'o': n.get('octave', 0),
                           'b': round(n['beat'] - start, 3),
                           'd': round(n.get('duration', 0.5), 3),
                           'r': bool(n.get('isRest'))}
                          for n in nts],
            }
    return None


def build():
    # Pull curated melodies from Supabase
    mel_rows = sb.schema('parcels').table('melodies').select('*').execute().data
    # Join with songs for artist/title/hookpad_url
    slugs = list({r['slug'] for r in mel_rows})
    song_meta = {}
    for i in range(0, len(slugs), 100):
        chunk = slugs[i:i+100]
        sr = sb.schema('parcels').table('songs').select('slug,artist,title,hookpad_url').in_('slug', chunk).execute().data
        for s in sr: song_meta[s['slug']] = s
    rows = []
    for r in mel_rows:
        s = song_meta.get(r['slug']) or {}
        rows.append({
            'slug': r['slug'], 'section': r['section'],
            'patterns': r.get('patterns') or '',
            'chord_shape': r.get('chord_shape') or '',
            'notes': r.get('notes') or '',
            'pickup_beats': float(r.get('pickup_beats') or 0),
            'artist': s.get('artist') or '?',
            'title': s.get('title') or '?',
            'hookpad_url': s.get('hookpad_url') or '',
        })
    print(f"loaded {len(rows)} curated melodies; fetching section data…")

    # Pull section data for each row (cache by (slug, section, pickup))
    cache = {}
    for r in rows:
        key = (r['slug'], r['section'], r['pickup_beats'])
        if key not in cache:
            cache[key] = fetch_section_data(r['slug'], r['section'], r['pickup_beats'])
        if cache[key] is None:
            print(f"  ! no section data for {r['slug']} / {r['section']}")
        r['_section_data'] = cache[key]

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

    def pat_sort_key(p):
        parsed = parse_pattern(p)
        if not parsed: return (999, '', '')
        return parsed
    sorted_patterns = sorted(pat_to_rows.keys(), key=pat_sort_key)

    # Named chord-set groups. Frozenset of scale-degree roots (1-7) → group name.
    # Order: longest-set names first so a 4-chord match takes priority over a 3-chord subset.
    NAMED_GROUPS = [
        (frozenset({1, 4, 5, 6}),    'axis'),         # I-V-vi-IV "axis of awesome"
        (frozenset({1, 2, 4, 5}),    'I-ii-IV-V'),    # doo-wop without the vi
        (frozenset({1, 3, 4, 6}),    '50s'),          # I-vi-IV-iii vicinity
        (frozenset({1, 4, 5, 2}),    'I-ii-IV-V'),    # duplicate, kept for clarity
        (frozenset({1, 5, 6}),       'I-V-vi'),
        (frozenset({1, 4, 5}),       'I-IV-V'),
        (frozenset({1, 4, 6}),       'I-IV-vi'),
        (frozenset({1, 5, 4, 2}),    'I-ii-IV-V'),
        (frozenset({1, 6, 4}),       'I-IV-vi'),
        (frozenset({6, 4, 1, 5}),    'axis'),
    ]
    # Dedupe + canonical name per chord-set
    chord_set_name = {}
    for s, n in NAMED_GROUPS:
        chord_set_name.setdefault(s, n)

    def detect_chord_set(section_data):
        if not section_data: return None, None
        roots = set()
        for c in section_data.get('chords', []):
            r = c.get('r')
            # Skip chromatic chords (applied or borrowed) when computing the set
            if c.get('app') or c.get('bor'): continue
            if r and 1 <= r <= 7:
                roots.add(r)
        if not roots: return None, None
        fs = frozenset(roots)
        name = chord_set_name.get(fs)
        # Letter-form for display, e.g. {1,4,5,6} → "I-IV-V-vi"
        DEG_LABEL = {1:'I', 2:'ii', 3:'iii', 4:'IV', 5:'V', 6:'vi', 7:'vii°'}
        letters = '-'.join(DEG_LABEL[d] for d in sorted(roots))
        return name, letters

    def render_row_data(r):
        cs_name, cs_letters = detect_chord_set(r.get('_section_data'))
        # Determine primary pattern: smallest bar count
        parsed_pats = [(p, parsed) for p, parsed in r.get('_pats_parsed', [])]
        primary = min(parsed_pats, key=lambda x: x[1][0])[0] if parsed_pats else None
        return {
            'title': r['title'], 'artist': r['artist'], 'section': r['section'],
            'slug': r['slug'], 'hookpad_url': r.get('hookpad_url') or '',
            'chord_shape': r.get('chord_shape') or '',
            'notes_text': r.get('notes') or '',
            'patterns': [{'str': p, 'bars': parsed[0], 'split': parsed[1], 'letter': parsed[2]}
                         for p, parsed in r.get('_pats_parsed', [])],
            'data': r.get('_section_data'),
            'chord_set_name': cs_name,
            'chord_set_letters': cs_letters,
            'primary': primary,
        }
    data = {p: [render_row_data(r) for r in pat_to_rows[p]] for p in sorted_patterns}

    sidebar = []
    cur_bars = None
    for p in sorted_patterns:
        bars = parse_pattern(p)[0]
        if bars != cur_bars:
            sidebar.append(f'<div class="bars-header">{bars} bars</div>')
            cur_bars = bars
        sidebar.append(f'<div class="pat-link" data-pat="{p}">{p}<span class="ct">{len(pat_to_rows[p])}</span></div>')

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
  .sidebar {{ width:200px; flex-shrink:0; background:#16162a; border-right:1px solid #2a2a4a; overflow-y:auto; padding:6px 0 20px; }}
  .bars-header {{ padding:8px 14px 4px; color:#a5a8fc; font-size:10px; text-transform:uppercase; letter-spacing:1.2px; font-weight:700; background:#1a1a30; margin-top:4px; }}
  .pat-link {{ padding:6px 16px; cursor:pointer; font-family:ui-monospace,Menlo,monospace; font-size:12px; color:#a0a0c0; border-left:3px solid transparent; display:flex; align-items:baseline; }}
  .pat-link:hover {{ background:#22223e; color:#e0e0e0; }}
  .pat-link.active {{ background:#22223e; color:#fff; border-left-color:#3050d0; }}
  .pat-link .ct {{ margin-left:auto; color:#5a5a7a; font-size:10px; }}
  .right {{ flex:1; overflow-y:auto; padding:14px 22px; }}
  .right h2 {{ font-size:14px; color:#e0e0e0; margin:0 0 4px; font-family:ui-monospace,Menlo,monospace; }}
  .right .meta {{ color:#6a6a8a; font-size:11px; margin-bottom:14px; }}
  .include-pills {{ display:flex; gap:6px; flex-wrap:wrap; margin:8px 0 14px; font-size:11px; }}
  .include-pills .lbl {{ color:#6a6a8a; padding:3px 0; }}
  .include-pills .pill {{ padding:3px 9px; background:#22223e; color:#a0a0c0; border:1px solid #2a2a4a; border-radius:11px; cursor:pointer; font-family:ui-monospace,Menlo,monospace; }}
  .include-pills .pill:hover {{ background:#3a3a5a; color:#e0e0e0; }}
  .include-pills .pill.on {{ background:#3050d0; color:#fff; border-color:#3050d0; }}
  .include-pills .pill .ct {{ color:rgba(255,255,255,0.6); margin-left:5px; font-size:10px; }}
  .pat-blocks {{ display:flex; gap:3px; height:32px; margin-bottom:18px; max-width:540px; }}
  .pat-blocks .ph {{ position:relative; display:flex; align-items:center; justify-content:flex-start; padding-left:8px; border-radius:4px; }}
  .pat-blocks .ph .lt {{ font-weight:700; font-size:12px; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,0.5); }}
  .ph-A {{ background:rgba(60,120,220,0.85); }}
  .ph-B {{ background:rgba(220,90,80,0.85); }}
  .ph-C {{ background:rgba(50,180,80,0.85); }}
  .ph-D {{ background:rgba(230,170,40,0.85); }}
  .ph-E {{ background:rgba(160,80,220,0.85); }}
  .ph-F {{ background:rgba(220,70,200,0.85); }}
  .ph-X {{ background:#3a3a5a; }}
  .card {{ background:#16162a; border:1px solid #2a2a4a; border-radius:6px; padding:10px 14px; margin-bottom:14px; }}
  .card-head {{ display:flex; align-items:baseline; gap:10px; margin-bottom:8px; font-size:13px; flex-wrap:wrap; }}
  .card-head .title {{ font-weight:700; color:#e0e0e0; }}
  .card-head .artist {{ color:#8a8ab0; font-size:12px; }}
  .card-head .section {{ color:#6a6a8a; font-size:11px; }}
  .card-head .key {{ color:#fbbf24; font-size:11px; font-weight:600; }}
  .card-head .chord-set {{ font-family:ui-monospace,Menlo,monospace; font-size:10px; padding:1px 7px; border-radius:9px; }}
  .card-head .chord-set.named {{ background:rgba(99,102,241,0.25); color:#a5b4fc; font-weight:700; text-transform:uppercase; letter-spacing:0.4px; }}
  .card-head .chord-set.unnamed {{ background:#22223e; color:#8a8ab0; }}
  .card-head .pickup-chip {{ font-size:10px; padding:1px 7px; border-radius:9px; background:rgba(99,102,241,0.18); color:#a5b4fc; font-weight:600; font-family:ui-monospace,Menlo,monospace; }}
  .card-head .hp {{ color:#a5b4fc; text-decoration:none; font-size:11px; font-weight:700; margin-left:auto; padding:2px 8px; background:rgba(99,102,241,0.15); border-radius:4px; }}
  .card-head .hp:hover {{ background:rgba(99,102,241,0.3); }}
  /* piano roll */
  .roll {{ position:relative; height:80px; background:#0d0d1d; border-radius:4px; border:1px solid #2a2a4a; overflow:hidden; }}
  .bar-line {{ position:absolute; top:0; bottom:0; width:1px; background:rgba(140,140,180,0.18); }}
  .bar-line.strong {{ background:rgba(140,140,180,0.45); width:1px; }}
  .pickup-zone {{ position:absolute; top:0; bottom:0; background:repeating-linear-gradient(45deg,rgba(99,102,241,0.06) 0 4px,rgba(99,102,241,0.12) 4px 8px); border-right:1px dashed rgba(165,180,252,0.5); }}
  .note.pickup {{ opacity:0.7; outline:1px solid rgba(165,180,252,0.4); }}
  .chord-bar {{ position:absolute; top:0; height:12px; font-size:9px; color:rgba(255,255,255,0.85); font-family:ui-monospace,Menlo,monospace; padding:0 4px; display:flex; align-items:center; border-radius:2px; }}
  .note {{ position:absolute; height:5px; border-radius:2px; }}
  .n-1 {{ background:#a01e1e; }} .n-2 {{ background:#b35610; }} .n-3 {{ background:#957e0c; }}
  .n-4 {{ background:#25a838; }} .n-5 {{ background:#3050d0; }} .n-6 {{ background:#6e16a5; }}
  .n-7 {{ background:#a01b6b; }}
  .n-s1 {{ background:repeating-linear-gradient(135deg,#a01e1e 0 4px,#b35610 4px 8px); }}
  .n-s2 {{ background:repeating-linear-gradient(135deg,#b35610 0 4px,#957e0c 4px 8px); }}
  .n-s4 {{ background:repeating-linear-gradient(135deg,#25a838 0 4px,#3050d0 4px 8px); }}
  .n-s5 {{ background:repeating-linear-gradient(135deg,#3050d0 0 4px,#6e16a5 4px 8px); }}
  .n-s6 {{ background:repeating-linear-gradient(135deg,#6e16a5 0 4px,#a01b6b 4px 8px); }}
  .n-other {{ background:#888; }}
  .all-patterns {{ font-family:ui-monospace,Menlo,monospace; font-size:10px; color:#8a8ab0; margin-top:8px; }}
  .all-patterns .pat {{ background:#22223e; padding:1px 6px; border-radius:3px; margin-right:5px; cursor:pointer; }}
  .all-patterns .pat:hover {{ background:#3050d0; color:#fff; }}
  .sub-meta {{ font-size:11px; color:#8a8ab0; margin-top:6px; display:flex; gap:14px; flex-wrap:wrap; }}
  .sub-meta .chord {{ color:#fbbf24; font-weight:600; }}
  .sub-meta .notes {{ color:#8a8ab0; font-style:italic; }}
  .placeholder {{ color:#5a5a7a; text-align:center; margin-top:80px; font-size:13px; }}
  .no-data {{ color:#5a5a7a; font-size:11px; font-style:italic; padding:14px; text-align:center; }}
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
    {chr(10).join(sidebar)}
  </aside>
  <main class="right" id="right">
    <div class="placeholder">— pick a pattern on the left —</div>
  </main>
</div>

<script>
const DATA = {json.dumps(data, ensure_ascii=False)};

function splitToWidths(split) {{
  if (split.includes('/')) return split.split('/').filter(s => /^\\d*\\.?\\d+$/.test(s)).map(parseFloat);
  if (split.includes('+')) return split.split('+').filter(s => /^\\d*\\.?\\d+$/.test(s)).map(parseFloat);
  // 2222 → [2,2,2,2]; .5.5.5.5 → [.5,.5,.5,.5]; 1.5.5 → [1,.5,.5]
  const nums = split.match(/\\.\\d+|\\d+\\.?\\d*/g) || [];
  return nums.map(parseFloat);
}}

function escapeHtml(s) {{
  return String(s || '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
}}

function renderPatBlocks(pattern) {{
  const widths = splitToWidths(pattern.split);
  const letters = (pattern.letter || '').split('');
  return '<div class="pat-blocks">' + widths.map((w, i) => {{
    const lt = letters[i] || '';
    const lt_norm = lt.toUpperCase().replace(/[^A-F]/g, '').slice(0,1) || 'X';
    return `<div class="ph ph-${{lt_norm}}" style="flex:${{w}}">` +
           (lt ? `<span class="lt">${{escapeHtml(lt)}}</span>` : '') +
           `</div>`;
  }}).join('') + '</div>';
}}

const NUMERALS = ['I','II','III','IV','V','VI','VII'];
function chordLetterShort(c) {{
  const r = c.r;
  if (r < 1 || r > 7) return '?';
  let s = NUMERALS[r-1];
  if (c.app) s = 'V/' + (NUMERALS[c.app-1] || '?');
  if (c.bor) s = 'b' + s;
  if (c.t === 7) s += '7';
  return s;
}}

function sdNum(sd) {{
  if (!sd) return 0;
  if (sd[0] === '#') return parseInt(sd.slice(1)) + 0.5;
  if (sd[0] === 'b') return parseInt(sd.slice(1)) - 0.5;
  return parseInt(sd);
}}
function noteClass(sd) {{
  if (!sd) return 'n-other';
  if (sd[0] === '#') return 'n-s' + sd.slice(1);
  if (sd[0] === 'b') return 'n-s' + (parseInt(sd.slice(1)) - 1);
  return 'n-' + sd;
}}

function renderRoll(d, pattern) {{
  if (!d) return '<div class="no-data">no melody data — slug or section may not match</div>';
  const sectionSpan = d.end - d.start;
  const pickup = d.pickup_beats || 0;
  const totalSpan = sectionSpan + pickup;
  const bars = Math.round(sectionSpan / d.bpb);
  // Pitch range from non-rest notes
  const pitches = d.notes.filter(n => !n.r).map(n => n.o * 7 + sdNum(n.sd));
  if (pitches.length === 0) return '<div class="no-data">no notes in this section</div>';
  const lo = Math.min(...pitches), hi = Math.max(...pitches);
  const range = Math.max(1, hi - lo);
  // Map a beat offset (relative to section start; negative = pickup) to left %
  const toLeft = (b) => ((b + pickup) / totalSpan) * 100;
  const toWidth = (w) => (w / totalSpan) * 100;
  let html = '<div class="roll">';
  // Pickup zone background
  if (pickup > 0) {{
    const w = (pickup / totalSpan) * 100;
    html += `<div class="pickup-zone" style="left:0;width:${{w}}%"></div>`;
  }}
  // Bar lines (only across the section proper)
  for (let i = 0; i <= bars; i++) {{
    const left = toLeft(i * d.bpb);
    const cls = (i === 0 || i === bars) ? 'bar-line strong' : 'bar-line';
    html += `<div class="${{cls}}" style="left:${{left}}%"></div>`;
  }}
  // Chord bars across the top
  d.chords.forEach(c => {{
    const left = toLeft(c.b);
    const w = toWidth(c.d);
    const lbl = chordLetterShort(c);
    let bg = c.r >=1 && c.r <=7 ? `rgba(${{[null,'160,30,30','179,86,16','149,126,12','37,168,56','48,80,208','110,22,165','160,27,107'][c.r]}}, 0.6)` : 'rgba(80,80,100,0.6)';
    html += `<div class="chord-bar" style="left:${{left}}%;width:${{w}}%;background:${{bg}}">${{lbl}}</div>`;
  }});
  // Notes
  d.notes.forEach(n => {{
    if (n.r) return;
    const p = n.o * 7 + sdNum(n.sd);
    const yPct = 18 + ((hi - p) / range) * 70;
    const left = toLeft(n.b);
    const w = Math.max(0.5, toWidth(n.d));
    const isPickup = n.b < 0;
    html += `<div class="note ${{noteClass(n.sd)}}${{isPickup ? ' pickup' : ''}}" style="left:${{left}}%;width:${{w}}%;top:${{yPct}}%"></div>`;
  }});
  html += '</div>';
  return html;
}}

// Per-pattern include-set state: which "other primary" patterns are toggled on.
const INCLUDES = {{}};   // patStr → Set of primary patterns to include in addition to default

function show(patStr) {{
  const allItems = DATA[patStr] || [];
  const right = document.getElementById('right');
  // Default: only melodies whose primary is patStr.
  // Plus: any whose primary is in INCLUDES[patStr].
  const includes = INCLUDES[patStr] || new Set();
  const items = allItems.filter(r => r.primary === patStr || includes.has(r.primary));
  // Other primaries available to toggle (for melodies tagged with patStr but smaller primary)
  const otherPrimaries = new Map();   // primary → count
  for (const r of allItems) {{
    if (r.primary !== patStr) {{
      otherPrimaries.set(r.primary, (otherPrimaries.get(r.primary) || 0) + 1);
    }}
  }}
  const headerPattern = (items[0] && items[0].patterns.find(p => p.str === patStr))
                       || (allItems[0] && allItems[0].patterns.find(p => p.str === patStr));
  const headerBlocks = headerPattern ? renderPatBlocks(headerPattern) : '';
  // Build pills row
  let pillsHtml = '';
  if (otherPrimaries.size) {{
    const pills = Array.from(otherPrimaries.entries())
      .sort((a, b) => (parseInt(a[0]) || 0) - (parseInt(b[0]) || 0))
      .map(([prim, ct]) => {{
        const on = includes.has(prim);
        return `<span class="pill ${{on ? 'on' : ''}}" data-prim="${{escapeHtml(prim)}}">+${{escapeHtml(prim)}}<span class="ct">${{ct}}</span></span>`;
      }}).join('');
    pillsHtml = `<div class="include-pills"><span class="lbl">also tagged here (whose primary is smaller):</span>${{pills}}</div>`;
  }}
  const head = `<h2>${{escapeHtml(patStr)}}</h2>` +
    `<div class="meta">${{items.length}} of ${{allItems.length}} melod${{allItems.length===1?'y':'ies'}}` +
    ` shown · default = primary tag only</div>${{headerBlocks}}${{pillsHtml}}`;
  if (!items.length) {{ right.innerHTML = head + '<div class="placeholder">no entries with this as primary tag</div>'; wirePills(patStr); return; }}
  const cards = items.map(r => {{
    const thisPat = r.patterns.find(p => p.str === patStr) || r.patterns[0];
    const roll = renderRoll(r.data, thisPat);
    const hp = r.hookpad_url ? `<a class="hp" href="${{r.hookpad_url}}" target="_blank" rel="noopener">HP↗</a>` : '';
    const keyStr = r.data ? `${{r.data.key}} ${{r.data.scale}} · ${{Math.round(r.data.bpm)}}bpm` : '';
    const otherPats = r.patterns.filter(p => p.str !== patStr);
    const allPats = otherPats.length
      ? `<div class="all-patterns">also: ${{otherPats.map(p => `<span class="pat" data-pat="${{escapeHtml(p.str)}}">${{escapeHtml(p.str)}}</span>`).join('')}}</div>`
      : '';
    const extras = [];
    if (r.chord_shape) extras.push(`<span class="chord">${{escapeHtml(r.chord_shape)}}</span>`);
    if (r.notes_text) extras.push(`<span class="notes">${{escapeHtml(r.notes_text)}}</span>`);
    const extraHtml = extras.length ? `<div class="sub-meta">${{extras.join(' · ')}}</div>` : '';
    let csChip = '';
    if (r.chord_set_name) csChip = `<span class="chord-set named" title="${{escapeHtml(r.chord_set_letters || '')}}">${{escapeHtml(r.chord_set_name)}}</span>`;
    else if (r.chord_set_letters) csChip = `<span class="chord-set unnamed">${{escapeHtml(r.chord_set_letters)}}</span>`;
    let pickupChip = '';
    if (r.data && r.data.pickup_beats > 0) {{
      const n = r.data.pickup_note_count;
      pickupChip = `<span class="pickup-chip" title="${{r.data.pickup_beats}}-beat pickup, ${{n}} note${{n===1?'':'s'}}">↪ pickup ${{r.data.pickup_beats}}b (${{n}}n)</span>`;
    }}
    return `<div class="card">
      <div class="card-head">
        <span class="title">${{escapeHtml(r.title)}}</span>
        <span class="artist">${{escapeHtml(r.artist)}}</span>
        <span class="section">[${{escapeHtml(r.section)}}]</span>
        ${{keyStr ? `<span class="key">${{keyStr}}</span>` : ''}}
        ${{csChip}}
        ${{pickupChip}}
        ${{hp}}
      </div>
      ${{roll}}
      ${{allPats}}
      ${{extraHtml}}
    </div>`;
  }}).join('');
  right.innerHTML = head + cards;
  document.querySelectorAll('.pat-link').forEach(p => p.classList.toggle('active', p.dataset.pat === patStr));
  right.querySelectorAll('.all-patterns .pat').forEach(el => {{
    el.addEventListener('click', () => show(el.dataset.pat));
  }});
  wirePills(patStr);
  localStorage.setItem('melodyPat', patStr);
}}

function wirePills(patStr) {{
  document.querySelectorAll('#right .include-pills .pill').forEach(el => {{
    el.addEventListener('click', () => {{
      if (!INCLUDES[patStr]) INCLUDES[patStr] = new Set();
      const prim = el.dataset.prim;
      if (INCLUDES[patStr].has(prim)) INCLUDES[patStr].delete(prim);
      else INCLUDES[patStr].add(prim);
      show(patStr);
    }});
  }});
}}

document.querySelectorAll('.pat-link').forEach(p => {{
  p.addEventListener('click', () => show(p.dataset.pat));
}});

const last = localStorage.getItem('melodyPat');
if (last && DATA[last]) show(last);
else {{
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
