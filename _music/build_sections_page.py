"""Generate sections pages: interactive viewers for chord-progression sections.

Three views written each run:
    sections-beatles.html   - just the 106 Beatles JSONs
    sections-studied.html   - just the 50 studied non-Beatles
    sections-other.html     - everything else
    sections.html           - the full corpus (default landing)

Walks every JSON, extracts each section's bar-by-bar (half-measure resolution)
chord layout, dedupes by (song, section name, pattern), inlines as JSON, and
renders interactive filters. Re-run after any Hookpad sync to refresh.
"""
import os, glob, json, re
from collections import defaultdict

from rebuild_studied_songs import USER_LIST, best_match
from rebuild_study_2 import USER_LIST_2
from rebuild_guitar150 import USER_LIST_3
from rebuild_guitar200 import USER_LIST_4
from rebuild_guitar250 import USER_LIST_5
from rebuild_guitar300 import USER_LIST_6
from rebuild_guitar350 import USER_LIST_7
from rebuild_guitar400 import USER_LIST_8
from rebuild_guitar450 import USER_LIST_9
from rebuild_guitar500 import USER_LIST_10
from rebuild_guitar550 import USER_LIST_11

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
HERE = os.path.dirname(os.path.abspath(__file__))

_ALL_FILES = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
STUDIED_PATHS = set()
ALL_STUDIED = (USER_LIST + USER_LIST_2 + USER_LIST_3 + USER_LIST_4
               + USER_LIST_5 + USER_LIST_6 + USER_LIST_7 + USER_LIST_8
               + USER_LIST_9 + USER_LIST_10 + USER_LIST_11)
for title, artist in ALL_STUDIED:
    path, _ = best_match(title, artist, _ALL_FILES)
    if path:
        STUDIED_PATHS.add(path)

def categorize(full_path, file_basename):
    """Return 'beatles' | 'studied' | 'other'."""
    if file_basename.startswith('beatles_'):
        return 'beatles'
    if full_path in STUDIED_PATHS:
        return 'studied'
    return 'other'

ROMAN = re.compile(r'^(?P<acc>[b#]*)(?P<deg>VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(?P<suf>.*)$')
NATURAL_MINOR = {'II','III','VI','VII'}
ROMAN_UP = ['','I','II','III','IV','V','VI','VII']
CELLS_PER_BAR = 2


MODE_QUALITIES = {  # triad quality at each scale degree per mode
    'major':           ['major','minor','minor','major','major','minor','dim'],
    'minor':           ['minor','dim','major','minor','minor','major','major'],
    'harmonicMinor':   ['minor','dim','major','minor','major','major','dim'],
    'melodicMinor':    ['minor','minor','major','major','major','dim','dim'],
    'dorian':          ['minor','minor','major','major','minor','dim','major'],
    'mixolydian':      ['major','minor','dim','major','minor','minor','major'],
    'phrygian':        ['minor','major','major','minor','dim','major','minor'],
    'lydian':          ['major','major','minor','dim','major','minor','minor'],
    'phrygianDominant':['major','major','dim','minor','dim','major','minor'],
    'locrian':         ['dim','major','minor','minor','major','major','minor'],
}

def quality_at(deg, mode):
    q = MODE_QUALITIES.get(mode, MODE_QUALITIES['major'])
    return q[deg-1] if 1 <= deg <= 7 else 'major'

def to_roman(root, type_str, borrowed='', key_scale='major'):
    """Render a Hookpad chord as a Roman numeral with correct casing.
    Quality decided by (in priority): explicit type 'm'/'maj' > borrowed mode > key's natural mode."""
    rs = str(root or '')
    if not rs: return None
    acc = ''
    while rs and rs[0] in 'b#':
        acc += rs[0]; rs = rs[1:]
    if not rs.isdigit(): return None
    deg = int(rs)
    if not 1 <= deg <= 7: return None
    base = ROMAN_UP[deg]
    ts = str(type_str or '')

    # Quality decision tree
    explicit_minor = ts.lower().startswith('m') and not ts.lower().startswith('maj')
    is_minor = None
    suffix = ts
    if explicit_minor:
        is_minor = True
        suffix = ts[1:]
    elif ts.lower().startswith('maj'):
        is_minor = False
    elif borrowed and isinstance(borrowed, str) and borrowed in MODE_QUALITIES:
        q = quality_at(deg, borrowed)
        is_minor = (q == 'minor')
    else:
        q = quality_at(deg, key_scale)
        is_minor = (q == 'minor')

    if is_minor:
        base = base.lower()
    return f'{acc}{base}{suffix}'


def normalize(tok, key_is_major):
    """Just strip the cosmetic '5' (power-chord) suffix. Casing now handled in to_roman."""
    m = ROMAN.match(tok)
    if not m: return tok
    acc, deg, suf = m.group('acc'), m.group('deg'), m.group('suf')
    if suf == '5': suf = ''
    return acc + deg + suf


def key_at_beat(keys, beat):
    """Return the key entry active at this beat (the last one whose beat is <= the query)."""
    active = keys[0] if keys else {'beat': 1, 'scale': 'major', 'tonic': 'C'}
    for k in keys:
        if k.get('beat', 1) <= beat:
            active = k
    return active


def parse_fname(fname):
    name = os.path.basename(fname).removesuffix('.json')
    name = re.sub(r'-(right|Right|RIGHT)$', '', name)
    parts = name.split('_', 1)
    if len(parts) != 2:
        return None, name
    artist, rest = parts
    toks = rest.split('_')
    while len(toks) > 1 and len(toks[-1]) <= 3:
        toks.pop()
    return artist.strip(), '_'.join(toks).strip()


def deg_of(tok):
    m = ROMAN.match(tok or '')
    if not m: return None
    deg = m.group('deg').upper()
    return {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7}.get(deg)


def extract_lyrics_by_tag(lyrics_field):
    """Hookpad stores lyrics tagged like [v]..., [ch]..., [b].... Return dict tag -> joined text."""
    if not lyrics_field: return {}
    if isinstance(lyrics_field, dict):
        values = lyrics_field.get('values', [])
        text = '\n'.join(v for v in values if isinstance(v, str))
    elif isinstance(lyrics_field, str):
        text = lyrics_field
    else:
        return {}

    blocks = {}
    current_tag = None
    current_lines = []
    for line in text.split('\n'):
        line = line.rstrip()
        m = re.match(r'^\[(\w+)\](.*)', line)
        if m:
            if current_tag is not None:
                blocks.setdefault(current_tag, []).extend(current_lines)
            current_tag = m.group(1)
            rest = m.group(2).strip()
            current_lines = [rest] if rest else []
        elif current_tag is not None:
            # Skip placeholder lines (just ~ + spaces) and empty lines
            if not line.strip() or re.match(r'^[~\s]+$', line):
                continue
            current_lines.append(line)
    if current_tag is not None:
        blocks.setdefault(current_tag, []).extend(current_lines)

    out = {}
    for tag, lines in blocks.items():
        cleaned = [ln.replace('/', '').strip() for ln in lines]
        cleaned = [ln for ln in cleaned if ln]
        if cleaned:
            out[tag] = ' / '.join(cleaned)
    return out


# Map a section name to the lyric tag Hookpad would use.
# Hookpad bundles pre-chorus + chorus lyrics under [ch], so pre-chorus sections get 'ch' lyrics
# (the leading line of [ch] is typically the pre-chorus line).
def lyric_tag_for_section(section_name):
    s = (section_name or '').lower()
    if 'verse' in s: return 'v'
    if 'chorus' in s or 'refrain' in s: return 'ch'   # matches "chorus" and "pre-chorus" both
    if 'bridge' in s: return 'b'
    return None


def slim_section_paste(d, section_start, section_end, section_name):
    """Per-section paste payload: chord+note events inside the section, beats shifted to start at 1."""
    bpb = (d.get('meters') or [{'numBeats':4}])[0].get('numBeats', 4) or 4
    # Use the key active at section_start (so paste preserves modulations)
    key = key_at_beat(d.get('keys') or [{}], section_start)
    tempo = (d.get('tempos') or [{}])[0]
    meter = (d.get('meters') or [{'numBeats':4}])[0]
    offset = section_start - 1  # so section_start maps to beat 1

    chords = []
    for c in d.get('chords', []):
        if c.get('isRest'): continue
        b = c.get('beat')
        if b is None or not (section_start <= b < section_end): continue
        # Clip duration so it doesn't extend beyond section
        dur = min(c.get('duration', bpb), section_end - b)
        ch = {'r': c.get('root'), 'b': b - offset, 'd': dur, 't': c.get('type')}
        if c.get('borrowed'): ch['bw'] = c['borrowed']
        if c.get('applied'): ch['ap'] = c['applied']
        chords.append(ch)

    raw_notes = d.get('notes') or []
    notes = []
    for n in raw_notes:
        if n.get('isRest'): continue
        b = n.get('beat')
        if b is None or not (section_start <= b < section_end): continue
        dur = min(n.get('duration', 0.25), section_end - b)
        notes.append({'sd': n.get('sd'), 'oct': n.get('octave', 0),
                      'b': b - offset, 'd': dur})

    end_beat = section_end - offset  # length of section in beats + 1
    return {
        'key': {'beat': 1, 'scale': key.get('scale','major'), 'tonic': key.get('tonic','C')},
        'tempo': {'beat': 1, 'bpm': tempo.get('bpm', 120),
                  'swingFactor': tempo.get('swingFactor', 0), 'swingBeat': tempo.get('swingBeat', 0.5)},
        'meter': {'beat': 1, 'numBeats': meter.get('numBeats', 4), 'beatUnit': meter.get('beatUnit', 1)},
        'section_name': section_name,
        'endBeat': end_beat,
        'chords': chords,
        'notes': notes,
    }


def phrase_endings(notes, section_start, section_end, ioi_threshold=2.0, dur_threshold=1.0):
    """Return tuple of phrase-ending local beat positions.
    Refined rule: phrase ending = note that BOTH
      (a) has IOI to next sounding note (or to section end) >= ioi_threshold, AND
      (b) is held for >= dur_threshold beats (filters out quick passing notes).
    Quick stab-and-pause patterns (IOI≥2 but dur<1) are micro-breaths, not phrases."""
    sec_notes = sorted([n for n in notes
                        if not n.get('isRest') and n.get('beat') is not None
                        and section_start <= n['beat'] < section_end], key=lambda n: n['beat'])
    endings = []
    for j, n in enumerate(sec_notes):
        next_beat = sec_notes[j+1]['beat'] if j+1 < len(sec_notes) else section_end
        ioi = next_beat - n['beat']
        dur = n.get('duration', 0) or 0
        if ioi >= ioi_threshold and dur >= dur_threshold:
            local = round(n['beat'] - section_start + 1, 2)
            endings.append(local)
    return tuple(endings)


def get_voice_1_notes(d):
    """Always return voice 1 (the lead/vocal melody by convention).
    Top-level `notes` holds the currently-active voice; voice 1 lives in `inactiveNotes[0]`
    when a later voice is active. If voice 1 is empty for a song, return empty — user will fix it."""
    active_idx = d.get('activeMelodyIndex', 0)
    if active_idx == 0:
        return d.get('notes') or []
    inactive = d.get('inactiveNotes') or []
    return inactive[0] if inactive else []


def collect():
    records = []
    for f in sorted(glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8-sig'))
        except Exception:
            continue
        sections = d.get('sections') or []
        chords = d.get('chords') or []
        all_notes = get_voice_1_notes(d)
        if not sections or not chords: continue
        bpb = (d.get('meters') or [{'numBeats':4}])[0].get('numBeats', 4) or 4
        cell_beats = bpb / CELLS_PER_BAR
        keys_list = d.get('keys') or [{'beat': 1, 'scale': 'major', 'tonic': 'C'}]
        bpm = (d.get('tempos') or [{}])[0].get('bpm')
        end_beat = d.get('endBeat') or 999999
        bounds = list(sections) + [{'beat': end_beat, 'name': '<end>'}]
        artist, title = parse_fname(f)
        lyrics_by_tag = extract_lyrics_by_tag(d.get('lyrics'))

        for i in range(len(bounds)-1):
            s, e = bounds[i], bounds[i+1]
            bars = round((e['beat'] - s['beat']) / bpb)
            if bars < 1: continue
            sec_chords = [c for c in chords
                          if not c.get('isRest')
                          and c.get('beat') is not None
                          and s['beat'] <= c['beat'] < e['beat']]
            if not sec_chords: continue
            total_cells = bars * CELLS_PER_BAR

            # Active key at the start of this section (handles mid-song modulations)
            section_key = key_at_beat(keys_list, s['beat'])
            section_tonic = section_key.get('tonic', 'C')
            section_scale = section_key.get('scale', 'major')
            section_is_major = section_scale == 'major'

            cells = []
            for cell_idx in range(total_cells):
                cell_start = s['beat'] + cell_idx * cell_beats
                cur = None
                for c in sec_chords:
                    cb = c['beat']; cd = c.get('duration', bpb)
                    if cb <= cell_start < cb + cd:
                        cur = c; break
                if cur is None:
                    prior = [c for c in sec_chords if c['beat'] <= cell_start]
                    cur = prior[-1] if prior else sec_chords[0]
                tok = to_roman(cur.get('root'), cur.get('type',''),
                               borrowed=cur.get('borrowed',''), key_scale=section_scale)
                tok = normalize(tok, section_is_major) if tok else '?'
                cells.append(tok)

            tag = lyric_tag_for_section(s.get('name',''))
            lyrics = lyrics_by_tag.get(tag, '') if tag else ''
            paste = slim_section_paste(d, s['beat'], e['beat'], s.get('name','?'))
            fp = phrase_endings(all_notes, s['beat'], e['beat'])
            gaps = tuple(round(fp[k+1]-fp[k], 1) for k in range(len(fp)-1)) if len(fp) >= 2 else ()
            records.append({
                'pattern': ' '.join(cells),
                'cells': cells,
                'bars': bars,
                'unique': len(set(cells)),
                'title': title,
                'artist': artist or '',
                'section': s.get('name','?'),
                'key': f'{section_tonic}{"m" if section_scale=="minor" else ""}',
                'tonic': section_tonic,
                'scale': section_scale,
                'bpm': bpm,
                'lyrics': lyrics,
                'set': categorize(f, os.path.basename(f)),
                'paste': paste,
                'fp': list(fp),             # phrase-ending positions
                'gaps': list(gaps),         # gaps between endings
            })

    # Dedupe by (song, section name, pattern)
    grouped = defaultdict(list)
    for r in records:
        nt = re.sub(r'[^a-z0-9]', '', r['title'].lower())
        na = re.sub(r'[^a-z0-9]', '', r['artist'].lower())
        k = (na, nt, r['section'].strip().lower(), r['pattern'])
        grouped[k].append(r)

    out = []
    for k, group in grouped.items():
        base = dict(group[0])
        base['repeats'] = len(group)
        out.append(base)
    out.sort(key=lambda r: (r['bars'], r['pattern'], r['title']))
    return out


def main():
    data = collect()

    # Sort all data alphabetically by title (default for all views)
    data.sort(key=lambda r: (r['title'].lower(), r['section'].lower(), r['bars']))

    def write(subset, label, fname):
        inlined_data = json.dumps(subset, separators=(',',':'))
        title_html = f'Sections — {label}'
        html = (TEMPLATE.replace('__DATA__', inlined_data)
                        .replace('__TITLE__', title_html))
        path = os.path.join(HERE, fname)
        open(path, 'w').write(html)
        print(f'  {label:12} {len(subset):>5} sections / {len(set((r["artist"],r["title"]) for r in subset))} songs → {fname}')

    print('writing pages:')
    write(data, 'all', 'sections.html')
    write([r for r in data if r['set'] == 'beatles'], 'beatles', 'sections-beatles.html')
    write([r for r in data if r['set'] == 'studied'], 'studied 50', 'sections-studied.html')
    write([r for r in data if r['set'] == 'other'], 'other', 'sections-other.html')


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>__TITLE__</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }
.app { display: flex; flex-direction: column; height: 100vh; }
.nav { display: flex; gap: 4px; padding: 8px 16px 0; background: #20203a; border-bottom: 1px solid #2a2a44; }
.nav a { color: #8a8ab0; padding: 4px 10px; border-radius: 4px 4px 0 0; text-decoration: none; font-size: 12px; }
.nav a.active { background: #1a1a2e; color: #e0e0e0; }
.nav a:hover { color: #e0e0e0; }
.filters { display: flex; gap: 12px; padding: 10px 16px; background: #20203a; border-bottom: 1px solid #333; align-items: center; flex-wrap: wrap; }
.filters label { color: #8a8ab0; font-size: 11px; }
.filters select, .filters input { background: #1a1a2e; color: #e0e0e0; border: 1px solid #44446a; border-radius: 4px; padding: 4px 8px; font-size: 12px; font-family: inherit; }
.filters input { width: 200px; }
.count { margin-left: auto; color: #8a8ab0; font-size: 11px; }
.list { flex: 1; overflow-y: auto; padding: 0 16px 16px; }
.row { display: flex; align-items: flex-start; gap: 16px; padding: 6px 0; border-bottom: 1px solid #2a2a44; cursor: pointer; }
.row:hover { background: #20203a; }
.left { flex-shrink: 0; display: flex; align-items: center; gap: 8px; }
.strip { display: flex; gap: 4px; flex-shrink: 0; }
.measure { display: flex; gap: 0; padding: 2px; border: 1px solid #44446a; border-radius: 3px; background: #16162a; }
.cell { min-width: 22px; height: 22px; padding: 0 3px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: #1a1a2e; white-space: nowrap; }
.deg-1 { background: #f4a8a8; }   /* I  red */
.deg-2 { background: #f4c898; }   /* ii orange */
.deg-3 { background: #f0e898; }   /* iii yellow */
.deg-4 { background: #a8e0b0; }   /* IV green */
.deg-5 { background: #a8c8f0; }   /* V  blue */
.deg-6 { background: #d0b0f0; }   /* vi purple */
.deg-7 { background: #b890e0; }   /* vii deeper purple */
.cell.unknown { background: #44446a; color: #8a8ab0; }
.right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; padding-top: 2px; }
.meta-line { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.meta-line .title { font-weight: 600; color: #e0e0e0; font-size: 12px; }
.meta-line .meta { color: #8a8ab0; font-size: 10px; }
.meta-line .repeats { color: #6a6a8a; font-size: 10px; }
.lyrics { color: #b8b8d0; font-size: 11px; line-height: 1.4; font-family: monospace; word-break: break-word; }
.lyrics:empty { display: none; }
.fp { color: #6a8aa8; font-size: 10px; font-family: monospace; cursor: pointer; padding: 1px 4px; border-radius: 3px; }
.fp:hover { background: #2a3a5a; color: #a8c8f0; }
.fp .gaps { color: #44446a; }
.fp.empty { color: #44446a; }
.bars-badge { color: #8a8ab0; font-size: 10px; width: 30px; flex-shrink: 0; }
.copy-btn { background: #2a2a44; color: #8a8ab0; border: 1px solid #44446a; border-radius: 3px;
            padding: 1px 6px; font-size: 10px; cursor: pointer; font-family: inherit; }
.copy-btn:hover { background: #3a3a5a; color: #e0e0e0; }
.copy-btn.copied { background: #2d5a2d; color: #c8f0c8; border-color: #4a8a4a; }
.pattern { color: #6a6a8a; font-size: 10px; font-family: monospace; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
</head><body>
<div class="app">
  <div class="nav" id="nav"></div>
  <div class="filters">
    <label>length</label><select id="length"></select>
    <label>section</label><select id="section"></select>
    <label>#chords</label><select id="unique"></select>
    <label>sort</label><select id="sort">
      <option value="title">by title</option>
      <option value="pattern">by pattern</option>
      <option value="bars">by length</option>
      <option value="unique">by # chords</option>
      <option value="fp">by fingerprint</option>
      <option value="gaps">by gap pattern</option>
    </select>
    <label>show</label><select id="display">
      <option value="roman">roman</option>
      <option value="chord">chord names</option>
    </select>
    <label>in key</label><select id="transpose">
      <option value="native">native</option>
      <option value="C">C</option><option value="G">G</option><option value="D">D</option>
      <option value="A">A</option><option value="E">E</option><option value="B">B</option>
      <option value="F#">F#</option><option value="F">F</option><option value="Bb">Bb</option>
      <option value="Eb">Eb</option><option value="Ab">Ab</option><option value="Db">Db</option>
      <option value="Am">Am</option><option value="Em">Em</option><option value="Dm">Dm</option>
      <option value="Bm">Bm</option><option value="F#m">F#m</option><option value="C#m">C#m</option>
    </select>
    <input id="search" placeholder="search · or fp:5 12.5 20.5 · or gaps:8 8 8" spellcheck="false" style="width: 280px">
    <span class="count" id="count"></span>
  </div>
  <div class="list" id="list"></div>
</div>
<script>
// Cross-page nav
const PAGE_LINKS = [
  ['sections.html',          'all'],
  ['sections-beatles.html',  'beatles'],
  ['sections-studied.html',  'studied 50'],
  ['sections-other.html',    'other'],
];
const here = location.pathname.split('/').pop() || 'sections.html';
document.getElementById('nav').innerHTML = PAGE_LINKS.map(([href, label]) =>
  `<a href="${href}" class="${href === here ? 'active' : ''}">${label}</a>`
).join('');

const DATA = __DATA__;

// ===== Roman ↔ chord name conversion =====
const NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const NOTES_FLAT  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
const MAJOR_INT   = [0, 2, 4, 5, 7, 9, 11];
const MINOR_INT   = [0, 2, 3, 5, 7, 8, 10];
const DEG_IDX = {I:0,II:1,III:2,IV:3,V:4,VI:5,VII:6,i:0,ii:1,iii:2,iv:3,v:4,vi:5,vii:6};

function tonicSemis(tonic){
  let i = NOTES_SHARP.indexOf(tonic);
  if (i < 0) i = NOTES_FLAT.indexOf(tonic);
  return i;
}

function romanToChord(roman, tonic, scale){
  // Parse: [accidentals][degree][suffix]
  const m = roman.match(/^([b#]*)(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(.*)$/);
  if (!m) return roman;
  const acc = m[1];
  const deg = m[2];
  const suf = m[3];
  const isMinor = deg === deg.toLowerCase();
  const degIdx = DEG_IDX[deg];
  const ti = tonicSemis(tonic);
  if (ti < 0) return roman;
  const intervals = scale === 'minor' ? MINOR_INT : MAJOR_INT;
  let semis = ti + intervals[degIdx];
  for (const a of acc) semis += (a === 'b' ? -1 : 1);
  semis = ((semis % 12) + 12) % 12;
  const useFlats = tonic.includes('b') || tonic === 'F' || (scale === 'minor' && ['D','G','C'].includes(tonic));
  const noteName = (useFlats ? NOTES_FLAT : NOTES_SHARP)[semis];
  return noteName + (isMinor ? 'm' : '') + suf;
}

function expandChord(c){
  return {root:c.r, beat:c.b, duration:c.d, type:c.t,
    inversion:0, applied:c.ap||0,
    adds:[], omits:[], alterations:[], suspensions:[], substitutions:[],
    pedal:null, alternate:'', borrowed:c.bw||'',
    isRest:false, recordingEndBeat:null};
}
function expandNote(n){
  return {sd:n.sd, octave:n.oct, beat:n.b, duration:n.d,
    isRest:false, recordingEndBeat:null};
}

async function copySection(idx, btn){
  const p = _currentRows[idx] && _currentRows[idx].paste;
  if (!p){ btn.textContent = 'no data'; return; }
  const obj = {
    notes: (p.notes||[]).map(expandNote),
    chords: (p.chords||[]).map(expandChord),
    keys: [p.key],
    tempos: [p.tempo],
    meters: [p.meter],
    breaks: [],
    sections: [{beat: 1, name: p.section_name || 'Section'}],
    endBeat: p.endBeat,
    audioTracks: [],
    version: 1,   // skip fp validation
  };
  await navigator.clipboard.writeText(JSON.stringify(obj));
  btn.textContent = '✓ copied';
  btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'copy hookpad'; btn.classList.remove('copied'); }, 2500);
}

// Event delegation for copy buttons + fingerprint click-to-filter
document.addEventListener('click', e => {
  const btn = e.target.closest('.copy-btn');
  if (btn) {
    e.stopPropagation();
    copySection(parseInt(btn.dataset.idx, 10), btn);
    return;
  }
  const fp = e.target.closest('.fp');
  if (fp && fp.dataset.fp) {
    // Set search to "fp:<fingerprint>" so only matching sections show
    document.getElementById('search').value = 'fp:' + fp.dataset.fp;
    // Also set length filter to match
    if (fp.dataset.bars) document.getElementById('length').value = fp.dataset.bars;
    render();
  }
});
const DEG_OF = {I:1,II:2,III:3,IV:4,V:5,VI:6,VII:7,i:1,ii:2,iii:3,iv:4,v:5,vi:6,vii:7};
function degOf(tok){
  const m = tok && tok.match(/^[b#]*([IVivX]+)/);
  if (!m) return null;
  return DEG_OF[m[1]] || null;
}

// Populate length dropdown with present values
const lengths = [...new Set(DATA.map(r => r.bars))].sort((a,b)=>a-b);
const lenSel = document.getElementById('length');
lenSel.innerHTML = '<option value="">all</option>' + lengths.map(l => `<option value="${l}">${l}</option>`).join('');

// Section names dropdown
const sectionNames = [...new Set(DATA.map(r => r.section.trim().toLowerCase()))].sort();
const secSel = document.getElementById('section');
secSel.innerHTML = '<option value="">all</option>' + sectionNames.map(s => `<option value="${s}">${s}</option>`).join('');

// Unique chord count dropdown
const uniqueCounts = [...new Set(DATA.map(r => r.unique))].sort((a,b)=>a-b);
const uniSel = document.getElementById('unique');
uniSel.innerHTML = '<option value="">any</option>' + uniqueCounts.map(u => `<option value="${u}">${u}</option>`).join('');

let _currentRows = [];
function render(){
  const lenF = lenSel.value;
  const secF = secSel.value;
  const uniF = uniSel.value;
  const q = document.getElementById('search').value.trim().toLowerCase();
  const sortBy = document.getElementById('sort').value;

  let rows = DATA.filter(r => {
    if (lenF && r.bars != lenF) return false;
    if (secF && r.section.trim().toLowerCase() !== secF) return false;
    if (uniF && r.unique != uniF) return false;
    if (q){
      // Special prefix: "fp:<positions>" matches exact fingerprint
      if (q.startsWith('fp:')) {
        const needle = q.slice(3).trim();
        if ((r.fp||[]).join(' ') !== needle) return false;
      } else if (q.startsWith('gaps:')) {
        const needle = q.slice(5).trim();
        if ((r.gaps||[]).join(' ') !== needle) return false;
      } else {
        const hay = (r.title + ' ' + r.artist + ' ' + r.pattern).toLowerCase();
        if (!hay.includes(q)) return false;
      }
    }
    return true;
  });

  const fpKey = r => (r.fp||[]).join(' ');
  const gapsKey = r => (r.gaps||[]).join(' ');
  rows.sort((a,b) => {
    if (sortBy === 'title') return a.title.localeCompare(b.title);
    if (sortBy === 'bars') return a.bars - b.bars || a.pattern.localeCompare(b.pattern);
    if (sortBy === 'unique') return a.unique - b.unique || a.pattern.localeCompare(b.pattern);
    if (sortBy === 'fp') return a.bars - b.bars || fpKey(a).localeCompare(fpKey(b)) || a.title.localeCompare(b.title);
    if (sortBy === 'gaps') return a.bars - b.bars || gapsKey(a).localeCompare(gapsKey(b)) || a.title.localeCompare(b.title);
    return a.pattern.localeCompare(b.pattern) || a.title.localeCompare(b.title);
  });

  _currentRows = rows;
  document.getElementById('count').textContent = `${rows.length} sections`;

  const list = document.getElementById('list');
  // Build via array join (faster than appendChild for big lists)
  const html = rows.map((r, idx) => {
    // Decide what label to render for each cell
    const displayMode = document.getElementById('display').value;
    const transposeKey = document.getElementById('transpose').value;
    let tonic = r.tonic, scale = r.scale;
    if (transposeKey !== 'native') {
      // 'Am' / 'Em' etc. → minor; 'C' / 'F#' → major
      if (transposeKey.endsWith('m')) { tonic = transposeKey.slice(0, -1); scale = 'minor'; }
      else                            { tonic = transposeKey; scale = 'major'; }
    }
    const renderLabel = tok => displayMode === 'chord' ? romanToChord(tok, tonic, scale) : tok;

    const measures = [];
    for (let i = 0; i < r.cells.length; i += 2) {
      const halves = [r.cells[i], r.cells[i+1]].map(tok => {
        if (tok === undefined) return '';
        const d = degOf(tok);
        const cls = d ? `deg-${d}` : 'unknown';
        return `<div class="cell ${cls}">${renderLabel(tok)}</div>`;
      }).join('');
      measures.push(`<div class="measure">${halves}</div>`);
    }
    const cells = measures.join('');
    const rep = r.repeats > 1 ? `<span class="repeats">×${r.repeats}</span>` : '';
    const lyrics = (r.lyrics || '').replace(/&/g,'&amp;').replace(/</g,'&lt;');
    const copyBtn = r.paste ? `<button class="copy-btn" data-idx="${idx}">copy hookpad</button>` : '';
    const fpStr = (r.fp && r.fp.length) ? r.fp.join(' ') : '';
    const gapsStr = (r.gaps && r.gaps.length) ? r.gaps.join(' ') : '';
    const fpHtml = fpStr
      ? `<span class="fp" data-fp="${fpStr}" data-bars="${r.bars}" title="click to filter to this fingerprint">(${fpStr})${gapsStr ? ` <span class="gaps">gaps [${gapsStr}]</span>` : ''}</span>`
      : `<span class="fp empty">(no phrase endings)</span>`;
    return `<div class="row">
      <div class="left">
        <div class="bars-badge">${r.bars}b</div>
        <div class="strip">${cells}</div>
      </div>
      <div class="right">
        <div class="meta-line">
          <span class="title">${r.title}</span>
          <span class="meta">${r.artist} · ${r.section} · ${r.key} · ${r.bpm||'?'} BPM</span>
          ${rep}
          ${copyBtn}
          ${fpHtml}
        </div>
        <div class="lyrics">${lyrics}</div>
      </div>
    </div>`;
  }).join('');
  list.innerHTML = html;
}

['change', 'input'].forEach(ev => {
  document.querySelectorAll('.filters select, .filters input').forEach(el => {
    el.addEventListener(ev, render);
  });
});
render();
</script>
</body></html>
"""


if __name__ == '__main__':
    main()
