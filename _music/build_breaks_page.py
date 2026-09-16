"""Generate breaks.html — dedicated visualization of phrase-break structure across sections.

Each section row gets a horizontal phrase timeline showing the bars + break points + phrase segments.
Sortable by macro pattern (e.g., '2-2-4'), section type, bar count.
Click a macro pattern to filter to all sections sharing it.

Reuses phrase_endings detector from build_sections_page.
"""
import os, glob, json, re, sys
from collections import defaultdict

sys.path.insert(0, '/Users/robert/Desktop/glowinggardens_claude/_music')
from build_sections_page import (
    phrase_endings, get_voice_1_notes, parse_fname, categorize,
    STUDIED_PATHS, HOOKPAD_DIR
)

HERE = os.path.dirname(os.path.abspath(__file__))


def macro_pattern(fp, gaps, bars, bpb=4):
    """Collapse micro phrase endings into macro phrases by gap size.
    A macro boundary = gap >= 6 beats (or it's the last phrase ending).
    Returns the macro phrase lengths in MEASURES."""
    if not fp: return []
    macros = []
    cur_start = 0  # in beats; section starts at "beat 1" → start of macro 1 = beat 1
    # For each phrase ending, decide if it's a macro boundary
    for i, end in enumerate(fp):
        next_gap = gaps[i] if i < len(gaps) else None  # gap to next ending
        # End is a macro boundary if next gap is large OR it's the last
        if next_gap is None or next_gap >= 6:
            macro_len_beats = end - cur_start
            macros.append(round(macro_len_beats / bpb, 1))
            cur_start = end
    # Trailing silence after last phrase ending up to section end (bars * bpb)
    # We treat the last macro as ending at the last phrase ending, ignoring trailing rests
    return macros


def chord_deg(root_str):
    """Return the diatonic scale degree (1-7) from chord root, ignoring accidentals."""
    rs = str(root_str or '')
    while rs and rs[0] in 'b#': rs = rs[1:]
    if rs.isdigit():
        n = int(rs)
        if 1 <= n <= 7: return n
    return None

def collect_breaks():
    records = []
    all_files = sorted(glob.glob(os.path.join(HOOKPAD_DIR, '*.json')))
    for f in all_files:
        try: d = json.load(open(f, encoding='utf-8-sig'))
        except: continue
        sections = d.get('sections') or []
        all_chords = d.get('chords') or []
        notes = get_voice_1_notes(d)
        if not sections: continue
        bpb = (d.get('meters') or [{'numBeats':4}])[0].get('numBeats', 4) or 4
        end_beat = d.get('endBeat') or 0
        artist, title = parse_fname(f)
        for i, s in enumerate(sections):
            end = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
            bars = round((end - s['beat']) / bpb)
            if bars < 1: continue
            fp = phrase_endings(notes, s['beat'], end)
            if not fp: continue
            gaps = tuple(round(fp[k+1]-fp[k], 1) for k in range(len(fp)-1))
            macros = macro_pattern(list(fp), list(gaps), bars, bpb)

            # Chord blocks: [{b, d, deg}] in section-local beats
            sec_chords = []
            for c in all_chords:
                if c.get('isRest'): continue
                cb = c.get('beat')
                if cb is None or cb < s['beat'] or cb >= end: continue
                # Clip duration to section end
                cd = min(c.get('duration', bpb), end - cb)
                deg = chord_deg(c.get('root'))
                sec_chords.append({
                    'b': round(cb - s['beat'] + 1, 2),
                    'd': round(cd, 2),
                    'deg': deg,
                })

            # Phrase-ending notes with pitch info for piano-roll rendering
            fp_notes = []
            sec_notes = sorted([n for n in notes
                                if not n.get('isRest') and n.get('beat') is not None
                                and s['beat'] <= n['beat'] < end], key=lambda n: n['beat'])
            ends_set = set(round(x, 2) for x in fp)
            for n in sec_notes:
                local = round(n['beat'] - s['beat'] + 1, 2)
                if local in ends_set:
                    sd = str(n.get('sd', '?'))
                    # Get scale degree number for color
                    sd_clean = sd
                    while sd_clean and sd_clean[0] in 'b#':
                        sd_clean = sd_clean[1:]
                    deg = int(sd_clean) if sd_clean.isdigit() else None
                    fp_notes.append({
                        'b': local,
                        'sd': sd,
                        'deg': deg,
                        'oct': n.get('octave', 0),
                    })

            records.append({
                'title': title, 'artist': artist,
                'section': s.get('name','?'),
                'bars': bars, 'bpb': bpb,
                'fp': list(fp), 'gaps': list(gaps),
                'macros': macros,
                'chords': sec_chords,
                'fp_notes': fp_notes,
                'set': categorize(f, os.path.basename(f)),
            })
    return records


# Map a section name to a coarse type for filter
def section_type(name):
    s = (name or '').lower().strip()
    if 'pre' in s and ('chorus' in s or 'cho' in s): return 'pre-chorus'
    if 'chorus' in s or 'refrain' in s: return 'chorus'
    if 'verse' in s: return 'verse'
    if 'bridge' in s: return 'bridge'
    if 'intro' in s or 'pickup' in s: return 'intro'
    if 'outro' in s or 'tag' in s or 'coda' in s: return 'outro'
    if 'solo' in s or 'instrumental' in s or 'interlude' in s: return 'solo/inst'
    return 'other'


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Phrase Breaks — Studied Sections</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }
.app { display: flex; flex-direction: column; height: 100vh; }
.topbar { display: flex; gap: 10px; padding: 10px 16px; background: #20203a; border-bottom: 1px solid #333; align-items: center; flex-wrap: wrap; }
.topbar label { color: #8a8ab0; font-size: 11px; }
.topbar select, .topbar input { background: #1a1a2e; color: #e0e0e0; border: 1px solid #44446a; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-family: inherit; }
.topbar input { width: 240px; }
.count { margin-left: auto; color: #8a8ab0; font-size: 11px; }
.nav { display: flex; gap: 4px; padding: 8px 16px 0; background: #20203a; border-bottom: 1px solid #2a2a44; }
.nav a { color: #8a8ab0; padding: 4px 10px; border-radius: 4px 4px 0 0; text-decoration: none; font-size: 12px; }
.nav a.active { background: #1a1a2e; color: #e0e0e0; }
.nav a:hover { color: #e0e0e0; }
.list { flex: 1; overflow-y: auto; padding: 0 16px 16px; }
.row { display: flex; align-items: center; gap: 14px; padding: 8px 0; border-bottom: 1px solid #2a2a44; }
.row:hover { background: #20203a; }
.meta { width: 260px; flex-shrink: 0; }
.meta .title { font-weight: 600; font-size: 12px; color: #e0e0e0; }
.meta .sub { font-size: 10px; color: #8a8ab0; margin-top: 2px; }
.macro {
  display: inline-block; font-family: monospace; font-size: 11px; color: #a8c8f0;
  background: #20203a; border: 1px solid #44446a; border-radius: 4px;
  padding: 2px 6px; cursor: pointer;
}
.macro:hover { background: #2a3a5a; color: #c8e0ff; }
.timeline {
  position: relative; flex: 1; height: 56px; background: #16162a;
  border: 1px solid #2a2a44; border-radius: 3px; overflow: hidden;
}
/* Chord blocks: bottom half, full-width per chord */
.chord-block {
  position: absolute; bottom: 0; height: 18px;
  border-right: 1px solid rgba(0,0,0,0.4);
}
/* Notes: top portion, piano-roll style — y = pitch, x = beat, w = ~half measure */
.pr-note {
  position: absolute; height: 4px; border-radius: 2px;
}
.bar-tick { position: absolute; top: 0; bottom: 0; width: 1px; background: #2a2a44; pointer-events:none; }
.bar-tick.major { background: #44446a; }
/* Degree colors (matches chord-color memory) */
.deg-1 { background: #f4a8a8; }   /* I  red */
.deg-2 { background: #f4c898; }   /* ii orange */
.deg-3 { background: #f0e898; }   /* iii yellow */
.deg-4 { background: #a8e0b0; }   /* IV green */
.deg-5 { background: #a8c8f0; }   /* V  blue */
.deg-6 { background: #d0b0f0; }   /* vi purple */
.deg-7 { background: #b890e0; }   /* vii deeper purple */
.deg-unknown { background: #44446a; }
.fp-text {
  width: 240px; flex-shrink: 0; color: #6a8aa8;
  font-family: monospace; font-size: 10px;
}
.fp-text .gaps { color: #44446a; }
</style>
</head><body>
<div class="app">
  <div class="nav" id="nav"></div>
  <div class="topbar">
    <label>set</label><select id="set">
      <option value="">all</option>
      <option value="beatles">beatles</option>
      <option value="studied" selected>studied 550</option>
      <option value="other">other</option>
    </select>
    <label>section</label><select id="type"></select>
    <label>bars</label><select id="bars"></select>
    <label>macro</label><select id="macro"></select>
    <label>sort</label><select id="sort">
      <option value="macro">by macro pattern</option>
      <option value="bars">by length</option>
      <option value="title">by title</option>
      <option value="type">by section type</option>
    </select>
    <input id="search" placeholder="search title / macro (e.g. 2-2-4)" spellcheck="false">
    <span class="count" id="count"></span>
  </div>
  <div class="list" id="list"></div>
</div>
<script>
const PAGE_LINKS = [
  ['sections.html',          'all sections'],
  ['sections-beatles.html',  'beatles sections'],
  ['sections-studied.html',  'studied sections'],
  ['breaks.html',            'phrase breaks ↗'],
  ['Guitar50.html',          '← study pages'],
];
const here = (location.pathname.split('/').pop() || 'breaks.html');
document.getElementById('nav').innerHTML = PAGE_LINKS.map(([h, l]) =>
  `<a href="${h}" class="${h === here ? 'active' : ''}">${l}</a>`).join('');

const DATA = __DATA__;

function sectionType(name) {
  const s = (name || '').toLowerCase().trim();
  if (s.includes('pre') && (s.includes('chorus') || s.includes('cho'))) return 'pre-chorus';
  if (s.includes('chorus') || s.includes('refrain')) return 'chorus';
  if (s.includes('verse')) return 'verse';
  if (s.includes('bridge')) return 'bridge';
  if (s.includes('intro') || s.includes('pickup')) return 'intro';
  if (s.includes('outro') || s.includes('tag') || s.includes('coda')) return 'outro';
  if (s.includes('solo') || s.includes('instrumental') || s.includes('interlude')) return 'solo/inst';
  return 'other';
}

// Populate dropdowns
const types = [...new Set(DATA.map(r => sectionType(r.section)))].sort();
const sel_type = document.getElementById('type');
sel_type.innerHTML = '<option value="">all</option>' + types.map(t => `<option value="${t}">${t}</option>`).join('');
const bars_list = [...new Set(DATA.map(r => r.bars))].sort((a,b)=>a-b);
const sel_bars = document.getElementById('bars');
sel_bars.innerHTML = '<option value="">all</option>' + bars_list.map(b => `<option value="${b}">${b}</option>`).join('');
const macros = [...new Set(DATA.map(r => r.macros.join('-')))].sort((a,b) => {
  const aa = a.split('-').reduce((s,x) => s + parseFloat(x), 0);
  const bb = b.split('-').reduce((s,x) => s + parseFloat(x), 0);
  return aa - bb || a.localeCompare(b);
});
const sel_macro = document.getElementById('macro');
sel_macro.innerHTML = '<option value="">all</option>' + macros.map(m => `<option value="${m}">${m}</option>`).join('');

const PIXELS_PER_BAR = 28;   // each measure = 28px wide

function render() {
  const setF = document.getElementById('set').value;
  const typeF = document.getElementById('type').value;
  const barsF = document.getElementById('bars').value;
  const macroF = document.getElementById('macro').value;
  const q = document.getElementById('search').value.trim().toLowerCase();
  const sortBy = document.getElementById('sort').value;

  let rows = DATA.filter(r => {
    if (setF && r.set !== setF) return false;
    if (typeF && sectionType(r.section) !== typeF) return false;
    if (barsF && r.bars != barsF) return false;
    if (macroF && r.macros.join('-') !== macroF) return false;
    if (q) {
      const macro = r.macros.join('-');
      const hay = (r.title + ' ' + r.artist + ' ' + macro).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  rows.sort((a, b) => {
    if (sortBy === 'title') return a.title.localeCompare(b.title);
    if (sortBy === 'bars') return a.bars - b.bars || a.title.localeCompare(b.title);
    if (sortBy === 'type') return sectionType(a.section).localeCompare(sectionType(b.section)) || a.title.localeCompare(b.title);
    // macro
    const aMacroSum = a.macros.reduce((s,x)=>s+x,0);
    const bMacroSum = b.macros.reduce((s,x)=>s+x,0);
    return a.bars - b.bars
      || a.macros.join('-').localeCompare(b.macros.join('-'))
      || a.title.localeCompare(b.title);
  });

  document.getElementById('count').textContent = `${rows.length} sections`;

  const list = document.getElementById('list');
  const html = rows.map(r => {
    const bpb = r.bpb || 4;
    const sectionBeats = r.bars * bpb;
    const widthPx = r.bars * PIXELS_PER_BAR;

    // Chord blocks: span the full section length
    let chords = '';
    (r.chords || []).forEach(c => {
      // c.b = section-local beat (1-indexed); c.d = duration in beats
      const left = ((c.b - 1) / sectionBeats) * widthPx;
      const w = Math.max(2, (c.d / sectionBeats) * widthPx);
      const cls = c.deg ? `deg-${c.deg}` : 'deg-unknown';
      chords += `<div class="chord-block ${cls}" style="left:${left}px;width:${w}px" title="chord at b${c.b}"></div>`;
    });

    // Piano-roll notes for phrase endings.
    // Vertical layout: sd 1 lowest, sd 7 highest. Top 32px reserved for note range.
    const NOTE_AREA_H = 32;            // pixels at top of timeline for notes
    const NOTE_H = 4;
    const PITCH_SLOTS = 7;             // sd 1..7
    const SLOT_H = (NOTE_AREA_H - NOTE_H) / (PITCH_SLOTS - 1);
    let prNotes = '';
    (r.fp_notes || []).forEach(n => {
      const left = ((n.b - 1) / sectionBeats) * widthPx;
      // half measure wide
      const w = ((bpb / 2) / sectionBeats) * widthPx;
      // y: sd 1 at bottom of note area (y = NOTE_AREA_H - NOTE_H), sd 7 at top (y = 0)
      let deg = n.deg;
      if (!deg || deg < 1 || deg > 7) deg = 1;
      const top = (PITCH_SLOTS - deg) * SLOT_H + (n.oct || 0) * -2;  // tiny octave nudge
      const cls = n.deg ? `deg-${n.deg}` : 'deg-unknown';
      prNotes += `<div class="pr-note ${cls}" style="left:${left}px;width:${w}px;top:${Math.max(0,top)}px"
                       title="sd ${n.sd} oct ${n.oct} at b${n.b}"></div>`;
    });

    // Bar ticks
    let ticks = '';
    for (let m = 1; m <= r.bars; m++) {
      const left = (m * bpb / sectionBeats) * widthPx;
      const isMajor = (m === r.bars / 2 || m === r.bars);
      ticks += `<div class="bar-tick ${isMajor ? 'major' : ''}" style="left:${left}px"></div>`;
    }

    const macroStr = r.macros.join('-');
    const fpStr = r.fp.join(' ');
    const gapsStr = r.gaps.join(' ');
    const macroChip = `<span class="macro" data-macro="${macroStr}" title="click to filter">${macroStr || '—'}</span>`;

    return `<div class="row">
      <div class="meta">
        <div class="title">${r.title}</div>
        <div class="sub">${r.artist} · ${r.section} · ${r.bars}b</div>
      </div>
      <div style="flex-shrink:0; width:80px">${macroChip}</div>
      <div class="timeline" style="width:${widthPx}px; flex-shrink:0">
        ${chords}${prNotes}${ticks}
      </div>
      <div class="fp-text">(${fpStr})<br><span class="gaps">gaps [${gapsStr}]</span></div>
    </div>`;
  }).join('');
  list.innerHTML = html;
}

document.addEventListener('change', e => { if (e.target.closest('.topbar')) render(); });
document.getElementById('search').addEventListener('input', render);
document.addEventListener('click', e => {
  const m = e.target.closest('.macro');
  if (m && m.dataset.macro) {
    document.getElementById('macro').value = m.dataset.macro;
    render();
  }
});
render();
</script>
</body></html>
"""


def main():
    records = collect_breaks()
    inlined = json.dumps(records, separators=(',',':'))
    html = TEMPLATE.replace('__DATA__', inlined)
    out = os.path.join(HERE, 'breaks.html')
    open(out, 'w').write(html)
    print(f'wrote {len(records)} sections with phrase data → {out}')


if __name__ == '__main__':
    main()
