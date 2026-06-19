"""Generate pattern-browser HTML pages. Defaults to 8-bar; pass --bars=16 for the
16-bar page. Reads `{n}_bar_patterns.json` (output of detect_patterns*.py), groups
matched sections by pattern, click-to-play with the same chord-block + melody-bar
viz as the section-explorer pages.
"""
import json, os, sys
from collections import defaultdict

PATTERN_ORDER_8 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    'full 4+4 repeat',
    '2+2+2+2 repeat',
    'AABA (2-bar phrases)',
    'AAAB (2-bar phrases)',
    'ABAB (2-bar phrases)',
    'ABAD (2-bar phrases)',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'ABCD (2-bar phrases)',
    '2+2+4 phrase',
    'ABC blocks (2+2+4 bars)',
    '4+4 question/answer',
    '224 groove (2+2+4 bts)',
    '422 groove (4+2+2 bts)',
    '1.5+.5+2 groove (4-bar)',
    'one-chord drone',
    'two-chord vamp',
    'walking (6+ changes)',
]

PATTERN_ORDER_14 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    '7+7 repeat',
    '8+6 phrase',
    '6+8 phrase',
    '12+2 phrase',
    '4+4+6 phrase',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'one-chord drone',
    'two-chord vamp',
    'walking (10+ changes)',
]

PATTERN_ORDER_16 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    'full 8+8 repeat',
    '4+4+4+4 repeat',
    'AABA (4-bar phrases)',
    'AAAB (4-bar phrases)',
    'ABAB (4-bar phrases)',
    'ABAD (4-bar phrases)',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'ABCD (4-bar phrases)',
    '4+4+8 phrase',
    'ABC blocks (4+4+8 bars)',
    '112 groove (1+1+2 bars)',
    '8+8 question/answer',
    'one-chord drone',
    'two-chord vamp',
    'walking (12+ changes)',
]

PATTERN_ORDER_10 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    '5+5 repeat',
    '4+4+2 phrase',
    '2-bar x5 repeat',
    'ABABA (2-bar phrases)',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'one-chord drone',
    'two-chord vamp',
    'walking (8+ changes)',
]

PATTERN_ORDER_12 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    '12-bar blues',
    'full 6+6 repeat',
    'AAA (4-bar phrases)',
    'AAB (4-bar phrases)',
    'AAB loose (4-bar)',
    'ABA (4-bar phrases)',
    'ABC (4-bar phrases)',
    '8+4 phrase',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'one-chord drone',
    'two-chord vamp',
    'walking (9+ changes)',
]

PATTERN_ORDER_24 = [
    'axis (I-V-vi-IV)',
    'doo-wop (I-vi-IV-V)',
    'pachelbel/8-chord',
    'ii-V-I',
    'andalusian (i-bVII-bVI-V)',
    'mixolydian (bVII-IV)',
    'stepwise descent (4+)',
    'full 12+12 repeat',
    '8+8+8 repeat',
    'AAB (8-bar phrases)',
    '6+6+6+6 repeat',
    'AABA (6-bar phrases)',
    'AAAB (6-bar phrases)',
    'ABAB (6-bar phrases)',
    'ABAD (6-bar phrases)',
    'ends on I (arrival)',
    '1 chord/bar, no repeats',
    'ABCD (6-bar phrases)',
    'one-chord drone',
    'two-chord vamp',
    'walking (18+ changes)',
]

CONFIGS = {
    8:  dict(src='eight_bar_patterns.json',         out='eight-bar-patterns.html',
             order=PATTERN_ORDER_8, title='8-bar', bars=8),
    10: dict(src='ten_bar_patterns.json',           out='ten-bar-patterns.html',
             order=PATTERN_ORDER_10, title='10-bar', bars=10),
    12: dict(src='twelve_bar_patterns.json',        out='twelve-bar-patterns.html',
             order=PATTERN_ORDER_12, title='12-bar', bars=12),
    14: dict(src='fourteen_bar_patterns.json',      out='fourteen-bar-patterns.html',
             order=PATTERN_ORDER_14, title='14-bar', bars=14),
    16: dict(src='sixteen_bar_patterns.json',       out='sixteen-bar-patterns.html',
             order=PATTERN_ORDER_16, title='16-bar', bars=16),
    24: dict(src='twenty_four_bar_patterns.json',   out='twenty-four-bar-patterns.html',
             order=PATTERN_ORDER_24, title='24-bar', bars=24),
}

BASE = '/Users/robert/Desktop/glowinggardens_claude/_music'


SECTIONS_NAV = [('eight', 8), ('ten', 10), ('twelve', 12), ('sixteen', 16)]
PATTERNS_NAV = [('eight', 8), ('ten', 10), ('twelve', 12), ('fourteen', 14), ('sixteen', 16), ('twenty-four', 24)]


def build_bar_nav(current_n):
    parts = ['<div class="bar-nav">', '<span class="label">Sections</span>']
    for w, n in SECTIONS_NAV:
        parts.append(f'<a href="{w}-bar-sections.html" class="nav-pill">{n}</a>')
    parts.append('<span class="sep"></span>')
    parts.append('<span class="label">Patterns</span>')
    for w, n in PATTERNS_NAV:
        cls = 'nav-pill current' if n == current_n else 'nav-pill'
        parts.append(f'<a href="{w}-bar-patterns.html" class="{cls}">{n}</a>')
    parts.append('</div>')
    return '\n'.join(parts)


def build(cfg):
    src = os.path.join(BASE, cfg['src'])
    out = os.path.join(BASE, cfg['out'])
    bars = cfg['bars']
    pattern_order = cfg['order']
    title = cfg['title']
    bar_nav_html = build_bar_nav(bars)

    sections = json.load(open(src))
    counts = defaultdict(int)
    for s in sections:
        for p in s.get('patterns', []):
            counts[p] += 1
    matched_total = sum(1 for s in sections if s.get('patterns'))

    runtime = []
    for s in sections:
        if not s.get('patterns'): continue
        runtime.append({k: v for k, v in s.items() if k != 'pmc'})
    data_json = json.dumps(runtime, separators=(',', ':'))

    pill_html = [
        f'<div class="pill pattern-pill active" data-pat="__all__">all<span class="count">{matched_total}</span></div>'
    ]
    for p in pattern_order:
        n = counts.get(p, 0)
        if n == 0: continue
        pill_html.append(
            f'<div class="pill pattern-pill" data-pat="{p}">{p}<span class="count">{n}</span></div>'
        )
    pills_block = '\n  '.join(pill_html)

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} sections by pattern</title>
<style>
  body {{ background:#1a1a2e; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,sans-serif;
         margin:0; padding:14px 18px; }}
  h1 {{ font-size:16px; margin:0 0 6px; font-weight:500; letter-spacing:.02em; }}
  .meta {{ color:#6a6a8a; font-size:11px; margin-bottom:10px; }}
  .filter-row {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; }}
  .filter-input {{ flex:1; max-width:420px; background:#22223e; border:1px solid #2a2a4a;
                  color:#e0e0e0; padding:6px 10px; border-radius:4px; font-size:12px;
                  outline:none; transition:border-color .15s; }}
  .filter-input:focus {{ border-color:#5060a0; }}
  .filter-input::placeholder {{ color:#5a5a7a; }}
  .filter-clear {{ color:#6a6a8a; cursor:pointer; font-size:11px; user-select:none;
                  padding:4px 6px; display:none; }}
  .filter-clear:hover {{ color:#e0e0e0; }}
  .filter-clear.shown {{ display:inline; }}
  .pattern-pills, .page-pills {{ display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;
           padding:8px 0; background:#1a1a2e; }}
  .pattern-pills {{ position:sticky; top:0; z-index:11; border-bottom:1px solid #2a2a4a; }}
  .page-pills {{ position:sticky; top:46px; z-index:10; border-bottom:1px solid #1a1a2e; margin-bottom:14px; }}
  .pill {{ padding:4px 9px; background:#2a2a4a; border-radius:12px; cursor:pointer;
          font-size:11px; color:#a0a0c0; user-select:none; }}
  .pill:hover {{ background:#3a3a5a; }}
  .pill.active {{ background:#5060a0; color:#fff; }}
  .pill .count {{ color:#7a7a9a; margin-left:4px; font-size:10px; }}
  .pill.active .count {{ color:#c0d0f0; }}
  .section {{ background:#22223e; border-radius:5px; padding:9px 11px; margin-bottom:7px;
             cursor:pointer; transition:background .12s; }}
  .section:hover {{ background:#2a2a48; }}
  .section.playing {{ background:#2a3050; outline:1px solid #5060a0; }}
  .playhead {{ position:absolute; top:0; bottom:0; width:1.5px; background:#fff;
              pointer-events:none; opacity:.85; z-index:5; }}
  .section-head {{ display:flex; justify-content:space-between; align-items:baseline;
                  font-size:12px; margin-bottom:4px; gap:10px; }}
  .song-name {{ font-weight:500; color:#e0e0e0; flex:1; min-width:0; overflow:hidden;
               text-overflow:ellipsis; white-space:nowrap; }}
  .sec-name {{ color:#a0a0c0; }}
  .key-bpm {{ color:#6a6a8a; font-size:10px; }}
  .pat-tags {{ color:#7080b0; font-size:10px; margin-top:2px; }}
  .pat-tag {{ display:inline-block; background:#2a2a4a; padding:1px 6px; border-radius:8px;
             margin-right:3px; }}
  .viz {{ position:relative; width:100%; height:88px; background:#1a1a2e; border-radius:3px;
         overflow:hidden; margin-top:3px; }}
  .chord-row, .melody-row {{ position:absolute; left:0; right:0; }}
  .chord-row {{ top:0; height:26px; }}
  .melody-row {{ top:28px; bottom:0; }}
  .chord {{ position:absolute; height:100%; border-radius:2px; display:flex; align-items:center;
           justify-content:center; font-size:10px; padding:0 3px; box-sizing:border-box;
           overflow:hidden; white-space:nowrap; }}
  .bar-line {{ position:absolute; top:0; bottom:0; width:1px; background:#3a3a5a; pointer-events:none; }}
  .bar-line.strong {{ background:#4a4a6a; }}
  .melody-note {{ position:absolute; height:5px; border-radius:2px; }}
  .n-1 {{ background:#e84545; }} .n-2 {{ background:#f0a040; }} .n-3 {{ background:#f0d840; }}
  .n-4 {{ background:#50c878; }} .n-5 {{ background:#5090f0; }} .n-6 {{ background:#b870f0; }}
  .n-7 {{ background:#e070b0; }}
  .n-s1 {{ background:linear-gradient(135deg,#e84545 50%,#f0a040 50%); }}
  .n-s2 {{ background:linear-gradient(135deg,#f0a040 50%,#f0d840 50%); }}
  .n-s4 {{ background:linear-gradient(135deg,#50c878 50%,#5090f0 50%); }}
  .n-s5 {{ background:linear-gradient(135deg,#5090f0 50%,#b870f0 50%); }}
  .n-s6 {{ background:linear-gradient(135deg,#b870f0 50%,#e070b0 50%); }}
  .deg-1 {{ background: rgba(220, 60, 60, 0.35); color: #ffa0a0; }}
  .deg-2 {{ background: rgba(230, 140, 40, 0.35); color: #ffc888; }}
  .deg-3 {{ background: rgba(220, 200, 40, 0.35); color: #f0e888; }}
  .deg-4 {{ background: rgba(50, 180, 80, 0.35); color: #88e8a0; }}
  .deg-5 {{ background: rgba(60, 120, 220, 0.35); color: #90b8f8; }}
  .deg-6 {{ background: rgba(160, 80, 220, 0.35); color: #d0a0f8; }}
  .deg-7 {{ background: rgba(224, 112, 176, 0.35); color: #f0a8d0; }}
  .deg-other {{ background: rgba(80, 80, 100, 0.35); color: #a0a0c0; }}
  .bar-nav {{ display:flex; align-items:center; gap:6px; margin-bottom:12px; font-size:11px; flex-wrap:wrap; }}
  .bar-nav .label {{ color:#6a6a8a; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; margin-right:2px; }}
  .bar-nav .nav-pill {{ padding:4px 10px; background:#22223e; color:#a0a0c0; border:1px solid #2a2a4a; border-radius:11px; text-decoration:none; font-size:11px; font-weight:600; }}
  .bar-nav .nav-pill:hover {{ background:#3a3a5a; color:#e0e0e0; }}
  .bar-nav .nav-pill.current {{ background:#3050d0; color:#fff; border-color:#3050d0; }}
  .bar-nav .sep {{ width:1px; height:14px; background:#2a2a4a; margin:0 6px; }}
</style>
</head>
<body>
{bar_nav_html}
<h1>{title} sections by pattern <span style="color:#6a6a8a;font-weight:400;font-size:11px;">— click a section to play</span></h1>
<div class="meta" id="meta">loading…</div>
<div class="filter-row">
  <input class="filter-input" id="filter" type="text" placeholder="filter by artist, title, or section…">
  <span class="filter-clear" id="clear">clear</span>
</div>
<div class="pattern-pills" id="patternPills">
  {pills_block}
</div>
<div class="page-pills" id="pagePills"></div>
<div id="list"></div>

<script src="https://cdn.jsdelivr.net/npm/tone@14.8.49/build/Tone.js"></script>
<script>
const BARS_PER_SECTION = {bars};
let synthChord = null, synthMelody = null;
let playingEl = null;
let playTimeouts = [];
let playRaf = null;

function initAudio() {{
  if (synthChord) return;
  synthChord = new Tone.PolySynth(Tone.Synth, {{
    oscillator: {{ type: 'triangle' }},
    envelope: {{ attack: 0.02, decay: 0.1, sustain: 0.6, release: 0.4 }}
  }}).toDestination();
  synthChord.volume.value = -16;
  synthMelody = new Tone.Synth({{
    oscillator: {{ type: 'triangle' }},
    envelope: {{ attack: 0.01, decay: 0.05, sustain: 0.7, release: 0.2 }}
  }}).toDestination();
  synthMelody.volume.value = -8;
}}

const TONIC_PC = {{'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
                  'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}};
const MAJOR_SCALE = [0,2,4,5,7,9,11];
const MINOR_SCALE = [0,2,3,5,7,8,10];

function scaleDegreeOffset(sd) {{
  if (!sd) return null;
  let alter = 0, n = sd;
  if (sd[0] === '#') {{ alter = 1; n = sd.slice(1); }}
  else if (sd[0] === 'b') {{ alter = -1; n = sd.slice(1); }}
  const num = parseInt(n);
  if (!num || num < 1 || num > 7) return null;
  return MAJOR_SCALE[num - 1] + alter;
}}
function melodyMidi(note, keyPc) {{
  const off = scaleDegreeOffset(note.sd);
  if (off === null) return null;
  return keyPc + off + (note.o + 5) * 12;
}}
function chordRootMidi(c, keyPc, scale) {{
  const sc = scale === 'minor' ? MINOR_SCALE : MAJOR_SCALE;
  let root = keyPc + sc[c.r - 1];
  if (c.bor === 'minor' && scale === 'major' && (c.r === 3 || c.r === 6 || c.r === 7)) root -= 1;
  root = 36 + ((root - 36) % 12 + 12) % 12;
  return root;
}}
function chordNotesMidi(c, keyPc, scale) {{
  const root = chordRootMidi(c, keyPc, scale);
  let isMinor;
  if (scale === 'major') {{
    isMinor = (c.r === 2 || c.r === 3 || c.r === 6) && !c.app && c.bor !== 'minor';
  }} else {{
    isMinor = (c.r === 1 || c.r === 4 || c.r === 5);
  }}
  if (c.bor === 'minor') isMinor = false;
  const third = isMinor ? 3 : 4;
  const notes = [root, root + third, root + 7];
  if (c.t === 7) {{
    let seventh = 10;
    if (scale === 'major' && (c.r === 1 || c.r === 4) && !c.bor) seventh = 11;
    notes.push(root + seventh);
  }}
  if (c.sus && c.sus.length) {{
    notes[1] = root + (c.sus[0] === 2 ? 2 : 5);
  }}
  return notes;
}}
function midiToFreq(m) {{ return 440 * Math.pow(2, (m - 69) / 12); }}

function stopPlayback() {{
  if (playingEl) playingEl.classList.remove('playing');
  playingEl = null;
  playTimeouts.forEach(clearTimeout);
  playTimeouts = [];
  if (playRaf) cancelAnimationFrame(playRaf);
  playRaf = null;
  if (synthChord) synthChord.releaseAll();
  if (synthMelody) synthMelody.triggerRelease();
  document.querySelectorAll('.playhead').forEach(p => p.remove());
}}

async function playSection(section, el) {{
  if (playingEl === el) {{ stopPlayback(); return; }}
  stopPlayback();
  await Tone.start();
  initAudio();
  const keyPc = TONIC_PC[section.key] ?? 0;
  const scale = section.scale === 'minor' ? 'minor' : 'major';
  const bpm = parseFloat(section.bpm) || 120;
  const secPerBeat = 60.0 / bpm;
  const spanBeats = section.end - section.start;
  playingEl = el;
  el.classList.add('playing');
  const now = Tone.now() + 0.1;
  section.chords.forEach(c => {{
    const notes = chordNotesMidi(c, keyPc, scale).map(midiToFreq);
    const t = now + c.b * secPerBeat;
    const dur = Math.max(0.05, c.d * secPerBeat * 0.95);
    synthChord.triggerAttackRelease(notes, dur, t);
  }});
  section.notes.forEach(n => {{
    if (n.r) return;
    const m = melodyMidi(n, keyPc);
    if (m === null) return;
    const t = now + n.b * secPerBeat;
    const dur = Math.max(0.05, n.d * secPerBeat * 0.9);
    synthMelody.triggerAttackRelease(midiToFreq(m), dur, t);
  }});
  const viz = el.querySelector('.viz');
  const ph = document.createElement('div');
  ph.className = 'playhead';
  viz.appendChild(ph);
  const startMs = performance.now() + 100;
  const totalMs = spanBeats * secPerBeat * 1000;
  function animate() {{
    const elapsed = performance.now() - startMs;
    if (elapsed >= totalMs) {{ stopPlayback(); return; }}
    ph.style.left = (Math.max(0, elapsed) / totalMs * 100) + '%';
    playRaf = requestAnimationFrame(animate);
  }}
  playRaf = requestAnimationFrame(animate);
}}
</script>

<script>
const PAGE_SIZE = 50;
let DATA = [];
let VIEW = [];
let page = 0;
let activePattern = '__all__';
let filterText = '';

const NUMERALS = ['I','II','III','IV','V','VI','VII'];

function romanLabel(c, scale) {{
  const root = c.r;
  if (!root || root < 1 || root > 7) return '?';
  let base = NUMERALS[root - 1];
  if (scale === 'major' && (root === 2 || root === 3 || root === 6) && !c.bor && c.t !== 7) {{
    base = base.toLowerCase();
  }} else if (scale === 'minor' && (root === 1 || root === 4 || root === 5)) {{
    base = base.toLowerCase();
  }}
  if (c.t === 7) base += '7';
  if (c.app) base = 'V/' + (NUMERALS[c.app - 1] || '?');
  if (c.bor) {{
    if (c.bor === 'minor' && (root === 3 || root === 6 || root === 7)) base = 'b' + base;
  }}
  if (c.adds && c.adds.length) base += '+' + c.adds.join(',');
  if (c.sus && c.sus.length) base += 'sus' + c.sus.join('');
  return base;
}}

function renderSection(s) {{
  const spanBeats = s.end - s.start;
  const sdNum = sd => {{
    if (!sd) return 0;
    if (sd[0] === '#') return parseInt(sd.slice(1)) + 0.5;
    if (sd[0] === 'b') return parseInt(sd.slice(1)) - 0.5;
    return parseInt(sd);
  }};
  const pitches = s.notes.filter(n => !n.r).map(n => n.o * 7 + sdNum(n.sd));
  let lo = 0, hi = 0, range = 1;
  if (pitches.length) {{
    lo = Math.min(...pitches); hi = Math.max(...pitches);
    range = Math.max(1, hi - lo);
  }}
  let html = '<div class="chord-row">';
  s.chords.forEach(c => {{
    const left = (c.b / spanBeats) * 100;
    const w = (c.d / spanBeats) * 100;
    const root = c.r;
    let cls = 'chord deg-other';
    if (root >= 1 && root <= 7) cls = 'chord deg-' + root;
    const lbl = romanLabel(c, s.scale);
    html += `<div class="${{cls}}" style="left:${{left}}%;width:${{w}}%;">${{lbl}}</div>`;
  }});
  html += '</div><div class="melody-row">';
  for (let i = 0; i <= BARS_PER_SECTION; i++) {{
    const left = (i * 4 / spanBeats) * 100;
    const cls = (i === 0 || i === BARS_PER_SECTION) ? 'bar-line strong' : 'bar-line';
    html += `<div class="${{cls}}" style="left:${{left}}%;"></div>`;
  }}
  const noteClass = sd => {{
    if (!sd) return 'n-other';
    if (sd[0] === '#') return 'n-s' + sd.slice(1);
    if (sd[0] === 'b') return 'n-s' + (parseInt(sd.slice(1)) - 1);
    return 'n-' + sd;
  }};
  s.notes.forEach(n => {{
    if (n.r) return;
    const p = n.o * 7 + sdNum(n.sd);
    const yPct = ((hi - p) / range) * 100;
    const left = (n.b / spanBeats) * 100;
    const w = (n.d / spanBeats) * 100;
    html += `<div class="melody-note ${{noteClass(n.sd)}}" style="left:${{left}}%;width:${{w}}%;top:${{yPct}}%;"></div>`;
  }});
  html += '</div>';
  return html;
}}

function render() {{
  const start = page * PAGE_SIZE;
  const slice = VIEW.slice(start, start + PAGE_SIZE);
  const list = document.getElementById('list');
  list.innerHTML = slice.map((s, i) => {{
    const tags = (s.patterns || []).map(p => `<span class="pat-tag">${{p}}</span>`).join('');
    return `
    <div class="section" data-idx="${{i}}">
      <div class="section-head">
        <div class="song-name">${{s.artist}} — ${{s.title}} <span class="sec-name">[${{s.sec}}]</span></div>
        <div class="key-bpm">${{s.key}} ${{s.scale}} · ${{s.bpm}} BPM</div>
      </div>
      <div class="pat-tags">${{tags}}</div>
      <div class="viz">${{renderSection(s)}}</div>
    </div>`;
  }}).join('');
  list.querySelectorAll('.section').forEach(el => {{
    el.addEventListener('click', () => {{
      const idx = parseInt(el.dataset.idx);
      playSection(slice[idx], el);
    }});
  }});
  document.querySelectorAll('#pagePills .pill').forEach((el, i) =>
    el.classList.toggle('active', i === page));
  window.scrollTo(0, 0);
}}

function buildPagePills() {{
  const n_pages = Math.ceil(VIEW.length / PAGE_SIZE);
  const pills = document.getElementById('pagePills');
  pills.innerHTML = '';
  if (VIEW.length === 0) {{
    pills.innerHTML = '<span style="color:#6a6a8a;font-size:11px;padding:4px 0;">no matches</span>';
    return;
  }}
  if (n_pages <= 1) return;
  for (let i = 0; i < n_pages; i++) {{
    const start = i * PAGE_SIZE + 1;
    const end = Math.min((i + 1) * PAGE_SIZE, VIEW.length);
    const pill = document.createElement('div');
    pill.className = 'pill';
    pill.innerHTML = `${{start}}–${{end}}`;
    pill.onclick = () => {{ stopPlayback(); page = i; render(); }};
    pills.appendChild(pill);
  }}
}}

function rebuildView() {{
  const q = filterText.trim().toLowerCase();
  const terms = q ? q.split(/\\s+/) : [];
  VIEW = DATA.filter(s => {{
    if (activePattern !== '__all__' && !(s.patterns || []).includes(activePattern)) return false;
    if (terms.length) {{
      const hay = (s.artist + ' ' + s.title + ' ' + s.sec).toLowerCase();
      if (!terms.every(t => hay.includes(t))) return false;
    }}
    return true;
  }});
  page = 0;
  const songs = new Set(VIEW.map(s => s.slug)).size;
  document.getElementById('meta').textContent =
    `${{VIEW.length}} sections from ${{songs}} songs · ${{DATA.length}} total matched (of all sections)`;
  stopPlayback();
  buildPagePills();
  render();
}}

(function(){{
  document.querySelectorAll('.pattern-pill').forEach(el => {{
    el.addEventListener('click', () => {{
      document.querySelectorAll('.pattern-pill').forEach(p => p.classList.remove('active'));
      el.classList.add('active');
      activePattern = el.dataset.pat;
      rebuildView();
    }});
  }});
  const inp = document.getElementById('filter');
  let t = null;
  inp.addEventListener('input', () => {{
    clearTimeout(t);
    t = setTimeout(() => {{ filterText = inp.value; rebuildView(); }}, 60);
  }});
  document.getElementById('clear').addEventListener('click', () => {{
    inp.value = ''; filterText = ''; rebuildView();
    inp.focus();
  }});
  const data = __DATA__;
  DATA = data;
  rebuildView();
}})();
</script>
</body>
</html>'''

    html = html.replace('__DATA__', data_json)
    with open(out, 'w') as f: f.write(html)
    print(f'wrote {out}  ({os.path.getsize(out)/1024:.0f} KB)  '
          f'{matched_total} sections matched, {sum(1 for p in pattern_order if counts.get(p,0)>0)} patterns shown')


def main():
    # CLI: --bars=8|16|all (default all)
    target = 'all'
    for a in sys.argv[1:]:
        if a.startswith('--bars='): target = a.split('=',1)[1]
    keys = [int(target)] if target.isdigit() else list(CONFIGS.keys())
    for k in keys:
        build(CONFIGS[k])


if __name__ == '__main__': main()
