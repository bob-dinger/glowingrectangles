"""Parse an Ultimate Guitar tab text file → Hookpad paste-compatible JSON.

Drop tabs at ~/Desktop/music/ug_tabs/{basename}.txt (basename matches a Hookpad filename).

Usage:
    python parse_ug.py <basename>            # e.g. 'alan-jackson_small-town-southern-man'
    python parse_ug.py --all                 # parse every tab in the folder
    python parse_ug.py --paste <basename>    # also copy to clipboard

Outputs a paste-JSON next to the tab file: {basename}_paste.json.

Heuristics (v1):
  - Sections detected by [SectionName] headers
  - Chord lines: lines where every non-whitespace token matches CHORD_RE
  - Lyric lines: any line directly following a chord line (chord positions snap to that lyric's columns)
  - Key inferred from the most-common-as-root chord (Capo IGNORED — capo only shifts sounding key, scale degrees are invariant)
  - bars_per_line ≈ tempo / 80  (from user's heuristic; tempo from DB if slug exists, else default 100)
  - Melody: chord root note at chord position (placeholder — user will refine in Hookpad)
"""
import os, re, sys, json, subprocess
from collections import Counter

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')

NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
NOTES_FLAT  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
MAJOR_INT = [0, 2, 4, 5, 7, 9, 11]
MINOR_INT = [0, 2, 3, 5, 7, 8, 10]
# Mode quality at each scale degree (1-7)
MODE_QUALITIES = {
    'major':       ['M','m','m','M','M','m','d'],
    'minor':       ['m','d','M','m','m','M','M'],
    'dorian':      ['m','m','M','M','m','d','M'],
    'mixolydian':  ['M','m','d','M','m','m','M'],
    'lydian':      ['M','M','m','d','M','m','m'],
}

CHORD_RE = re.compile(r'^([A-G])([#b])?(m|maj|min|aug|dim|sus[24]?)?(\d+)?(?:add\d+)?(?:/([A-G][#b]?))?$')
SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$')


def parse_chord_name(s):
    """'F#m7' → {'note':'F#', 'quality':'m', 'extra': '7', 'bass': None}."""
    m = CHORD_RE.match(s.strip())
    if not m: return None
    note = m.group(1) + (m.group(2) or '')
    q = m.group(3) or ''
    extra = m.group(4) or ''
    bass = m.group(5)
    return {'note': note, 'quality': q, 'extra': extra, 'bass': bass, 'raw': s.strip()}


def is_chord_line(line):
    toks = line.split()
    if not toks: return False
    chord_toks = 0
    for t in toks:
        # Strip leading punctuation/quotes (some tabs prefix chord lines)
        t = t.strip('()')
        if parse_chord_name(t): chord_toks += 1
    # All tokens must be chord-like (allow some non-chord tokens like "x4" repeat markers if rare)
    return chord_toks >= max(1, len(toks) - 1) and chord_toks >= 1


def parse_chord_line(line):
    """Return list of (chord_name, col) for each chord token, preserving column position."""
    out = []
    i = 0
    while i < len(line):
        if line[i].isspace():
            i += 1; continue
        j = i
        while j < len(line) and not line[j].isspace(): j += 1
        tok = line[i:j].strip('()')
        if parse_chord_name(tok):
            out.append((tok, i))
        i = j
    return out


def note_to_pc(note):
    if note in NOTES_SHARP: return NOTES_SHARP.index(note)
    if note in NOTES_FLAT:  return NOTES_FLAT.index(note)
    return None


def parse_metadata(lines):
    """Parse metadata. Handles both line-prefix style and inline 'Tuning: X  Key: Y  Capo: Z' style."""
    meta = {}
    head = '\n'.join(lines[:15])
    # Find each label anywhere in the head section (mid-line allowed)
    for label, key in [('Capo','capo'), ('Key','key'), ('Tempo','bpm'), ('BPM','bpm'), ('Tuning','tuning')]:
        m = re.search(rf'\b{label}\s*[:=]\s*([^\n]+?)(?=\s{{2,}}\b(?:Capo|Key|Tempo|BPM|Tuning)\b|\s*$)',
                      head, re.IGNORECASE)
        if not m: continue
        v = m.group(1).strip()
        if key == 'capo':
            m2 = re.search(r'(\d+)', v)
            meta['capo'] = int(m2.group(1)) if m2 else 0
        elif key == 'key':
            # Key value is something like "G", "Em", "Bb"
            m2 = re.match(r'([A-G][#b]?)(m|min|maj)?', v)
            if m2:
                meta['key'] = m2.group(1)
                meta['scale'] = 'minor' if m2.group(2) and m2.group(2).startswith('m') and m2.group(2) != 'maj' else 'major'
        elif key == 'bpm':
            m2 = re.search(r'(\d+)', v)
            if m2: meta['bpm'] = int(m2.group(1))
        elif key == 'tuning':
            meta['tuning'] = v
    return meta


def parse_tab(text):
    """Parse the full tab text → structured representation."""
    lines = text.split('\n')
    meta = parse_metadata(lines)
    sections = []  # list of {name, chord_lines: [(chord_name, col, line_idx)], lyric_lines: [(text, line_idx)]}
    current = None
    pending_chord_line = None   # (chord_events_list, line_idx)

    for i, line in enumerate(lines):
        # Section header?
        m = SECTION_RE.match(line)
        if m:
            if current: sections.append(current)
            name = m.group(1).strip()
            current = {'name': name, 'events': []}
            pending_chord_line = None
            continue
        # Skip everything before the first explicit [Section] header
        if not current: continue
        if not line.strip():
            pending_chord_line = None
            continue
        if is_chord_line(line):
            chords = parse_chord_line(line)
            pending_chord_line = chords
            current['events'].append(('chord_line', chords))
        else:
            # Lyric line — attach to most recent chord line
            current['events'].append(('lyric_line', line))
            pending_chord_line = None
    if current: sections.append(current)
    return meta, sections


def infer_key(sections):
    """Tally chord roots across all sections; tonic = most common (with a major-bias tiebreaker)."""
    roots = Counter()
    for sec in sections:
        for kind, payload in sec.get('events', []):
            if kind != 'chord_line': continue
            for cname, col in payload:
                c = parse_chord_name(cname)
                if c: roots[c['note']] += 1
    if not roots: return 'C', 'major'
    most = roots.most_common(1)[0][0]
    # Try to detect if it's minor by checking if the tonic chord is minor
    # (Rough heuristic — could be improved)
    is_minor_tonic = False
    for sec in sections:
        for kind, payload in sec.get('events', []):
            if kind != 'chord_line': continue
            for cname, _ in payload:
                c = parse_chord_name(cname)
                if c and c['note'] == most and c['quality'] in ('m', 'min'):
                    is_minor_tonic = True
                    break
    return most, ('minor' if is_minor_tonic else 'major')


def chord_to_root_degree(chord_name, key_tonic, key_scale='major'):
    """Convert chord name (e.g. 'G') to (root_degree, type, borrowed) in the song's key.
    Returns None if can't parse.
    Output is structured for Hookpad chord JSON."""
    c = parse_chord_name(chord_name)
    if not c: return None
    chord_pc = note_to_pc(c['note'])
    tonic_pc = note_to_pc(key_tonic)
    if chord_pc is None or tonic_pc is None: return None
    semis_from_tonic = (chord_pc - tonic_pc) % 12

    intervals = MAJOR_INT if key_scale == 'major' else MINOR_INT
    qualities = MODE_QUALITIES[key_scale]

    # Find degree where (intervals[d] mod 12) == semis_from_tonic; if not exact, allow accidental
    deg, acc = None, 0
    for d, iv in enumerate(intervals):
        if iv == semis_from_tonic:
            deg = d + 1; acc = 0; break
    if deg is None:
        # Try b accidental (chord is 1 semitone below natural degree)
        for d, iv in enumerate(intervals):
            if (iv - 1) % 12 == semis_from_tonic:
                deg = d + 1; acc = -1; break
    if deg is None:
        # Try # accidental
        for d, iv in enumerate(intervals):
            if (iv + 1) % 12 == semis_from_tonic:
                deg = d + 1; acc = 1; break
    if deg is None: return None

    # Determine quality. Explicit minor/dim from chord name wins.
    cq = c['quality']
    if cq in ('m', 'min'): quality = 'm'
    elif cq == 'dim': quality = 'd'
    elif cq == 'aug': quality = 'a'
    else: quality = 'M'

    # Determine borrowed mode if chord quality conflicts with diatonic
    diatonic = qualities[deg - 1]
    borrowed = ''
    if quality != diatonic and acc == 0:
        # Try modes
        for mode_name, qs in MODE_QUALITIES.items():
            if mode_name == key_scale: continue
            if qs[deg - 1] == quality:
                borrowed = mode_name; break

    # Type
    type_ = 5  # default triad
    if '7' in c['extra']: type_ = 7

    return {
        'deg': deg, 'acc': acc, 'quality': quality,
        'type': type_, 'borrowed': borrowed,
    }


def hookpad_chord(deg_info, beat, dur):
    return {
        'root': deg_info['deg'], 'beat': beat, 'duration': dur,
        'type': deg_info['type'], 'inversion': 0, 'applied': 0,
        'adds': [], 'omits': [], 'alterations': [], 'suspensions': [], 'substitutions': [],
        'pedal': None, 'alternate': '', 'borrowed': deg_info['borrowed'],
        'isRest': False, 'recordingEndBeat': None,
    }


def section_bars(events, bpm, bpb):
    """Estimate bars based on # lyric lines and tempo (user's heuristic: bars/line ≈ tempo/80)."""
    n_lyric = sum(1 for k, _ in events if k == 'lyric_line')
    if n_lyric == 0:
        # Instrumental section — base on # chord lines (1 line ≈ 1-2 bars at typical tempo)
        n_chord = sum(1 for k, _ in events if k == 'chord_line')
        return max(2, n_chord * max(1, int(round(bpm / 80))))
    bars_per_line = max(1, int(round(bpm / 80)))
    return max(1, n_lyric * bars_per_line)


def build_paste(meta, sections):
    BPB = 4
    bpm = meta.get('bpm') or 100
    key_tonic, key_scale = infer_key(sections)

    out_sections = []
    out_chords = []
    out_notes = []
    beat = 1

    for sec in sections:
        name = sec['name']
        events = sec['events']
        bars = section_bars(events, bpm, BPB)
        out_sections.append({'beat': beat, 'name': name})
        section_start = beat
        section_end = beat + bars * BPB

        # Group chord/lyric events by line pair
        lines = []  # list of (chord_events_or_none, lyric_text_or_none)
        i = 0
        evs = events
        while i < len(evs):
            kind, payload = evs[i]
            if kind == 'chord_line':
                if i + 1 < len(evs) and evs[i+1][0] == 'lyric_line':
                    lines.append((payload, evs[i+1][1]))
                    i += 2
                else:
                    lines.append((payload, None))
                    i += 1
            elif kind == 'lyric_line':
                lines.append((None, payload))
                i += 1
            else:
                i += 1

        # Allocate bars to each line proportionally (all lines equal for now)
        if lines:
            bars_per_line_int = max(1, bars // len(lines))
            extra_bars = bars - bars_per_line_int * len(lines)
        else:
            bars_per_line_int = bars; extra_bars = 0

        cur_line_beat = beat
        last_chord_info = None
        for li, (chords, lyric) in enumerate(lines):
            line_bars = bars_per_line_int + (1 if li < extra_bars else 0)
            line_beats = line_bars * BPB
            line_end = cur_line_beat + line_beats
            if chords:
                # Distribute chord events across the line based on column position (proportional)
                ref = lyric if lyric else (chords[-1][0] + ' ' * 4)
                ref_len = max(len(ref), max(c[1] for c in chords) + 1)
                events_with_pos = []
                for cname, col in chords:
                    frac = min(col / ref_len, 0.99) if ref_len > 0 else 0
                    cb = cur_line_beat + frac * line_beats
                    info = chord_to_root_degree(cname, key_tonic, key_scale)
                    if info is None: continue
                    events_with_pos.append((cb, info))
                # Compute durations from inter-onset
                events_with_pos.sort(key=lambda x: x[0])
                for ci, (cb, info) in enumerate(events_with_pos):
                    next_b = events_with_pos[ci+1][0] if ci+1 < len(events_with_pos) else line_end
                    dur = max(0.5, round(next_b - cb, 2))
                    # Snap to grid (nearest beat)
                    cb = round(cb)
                    out_chords.append(hookpad_chord(info, cb, dur))
                    last_chord_info = info
                    # Placeholder melody: root note of chord
                    out_notes.append({
                        'sd': str(info['deg']), 'octave': 0,
                        'beat': cb, 'duration': dur,
                        'isRest': False, 'recordingEndBeat': None,
                    })
            cur_line_beat += line_beats
        beat = section_end

    return {
        'notes': out_notes,
        'chords': out_chords,
        'keys': [{'beat':1, 'scale':'major', 'tonic':'C'}],  # always encode in C
        'tempos': [{'beat':1, 'bpm':bpm, 'swingBeat':0.5, 'swingFactor':0}],
        'meters': [{'beat':1, 'beatUnit':1, 'numBeats':BPB}],
        'breaks': [],
        'sections': out_sections,
        'endBeat': beat,
        'audioTracks': [],
        'version': 1,
    }, {'inferred_key': (key_tonic, key_scale), 'bpm': bpm}


def parse_file(basename, paste=False):
    src_path = os.path.join(UG_DIR, basename + '.txt')
    if not os.path.exists(src_path):
        print(f'  no file: {src_path}'); return None
    text = open(src_path, encoding='utf-8').read()
    meta, sections = parse_tab(text)
    paste_json, summary = build_paste(meta, sections)
    out_path = os.path.join(UG_DIR, basename + '_paste.json')
    open(out_path, 'w').write(json.dumps(paste_json, separators=(',', ':')))
    print(f'  {basename}: {len(paste_json["sections"])} sections, {len(paste_json["chords"])} chords, '
          f'key {summary["inferred_key"][0]} {summary["inferred_key"][1]}, bpm {summary["bpm"]}')
    if paste:
        subprocess.run(['pbcopy'], input=open(out_path).read(), text=True)
        print(f'  copied to clipboard')
    return paste_json


def main():
    args = sys.argv[1:]
    paste = False
    if '--paste' in args:
        paste = True; args.remove('--paste')
    if '--all' in args:
        for f in sorted(os.listdir(UG_DIR)):
            if f.endswith('.txt'):
                parse_file(f[:-4], paste=False)
    elif args:
        parse_file(args[0], paste=paste)
    else:
        print('usage: parse_ug.py [--paste] <basename>  |  parse_ug.py --all')


if __name__ == '__main__':
    main()
