"""Full MIDI + UG → Hookpad paste pipeline (Phase 1 + 2 + 3).

  1. Classify tracks (drums/bass/melody/chords) using UG lyric count hint
  2. Half-measure harmonic chord detection with secondary-track fallback
  3. Collapse same-root extensions, split at measure boundaries
  4. Align UG section labels to MIDI chord sequence via roman-numeral matching
  5. Extract melody, transpose to C-encoding
  6. Output Hookpad paste JSON

Usage:
    python midi_ug_full_pipeline.py <midi_path> [ug_text_path] [out.txt]
"""
import os, sys, json, re, copy, mido, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_song_v2 import classify, harmonic_chord_track, lyric_word_count, simplify_chord
from parse_ug import parse_tab, chord_to_root_degree, parse_chord_name

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
FLATS = {'Db':1,'Eb':3,'Gb':6,'Ab':8,'Bb':10}
MAJOR_INT = [0, 2, 4, 5, 7, 9, 11]
BPB = 4


def note_pc(s):
    if s in NAMES: return NAMES.index(s)
    return FLATS.get(s)


def chord_to_root_local(chord_label, tonic_pc):
    """Convert 'F#m' → (degree, quality_suffix, borrowed)."""
    m = re.match(r'^([A-G][#b]?)(m|dim|aug)?$', chord_label or '')
    if not m: return None
    cpc = note_pc(m.group(1))
    if cpc is None: return None
    q = m.group(2) or ''
    semis = (cpc - tonic_pc) % 12
    for d, iv in enumerate(MAJOR_INT, 1):
        if iv == semis: return (d, q, '')
    for d, iv in enumerate(MAJOR_INT, 1):
        if (iv - 1) % 12 == semis:
            if q == '':  return (d, '', 'minor')
            if q == 'm': return (d, 'm', 'phrygian')
    return None


def infer_tonic(pcs):
    best = (0, -1)
    for t in range(12):
        scale = {(t+iv)%12 for iv in MAJOR_INT}
        sc = sum(pcs.get(pc, 0) for pc in scale) + 0.3 * pcs.get(t, 0)
        if sc > best[1]: best = (t, sc)
    return best[0]


def extract_melody(notes, ppq, shift):
    out = []
    for st, p, en in notes:
        sp = p - shift; rel = sp - 60
        octave = rel // 12; rem = rel - octave * 12
        sd = None
        for d, iv in enumerate(MAJOR_INT, 1):
            if iv == rem: sd = str(d); break
        if sd is None:
            for d, iv in enumerate(MAJOR_INT, 1):
                if (iv+1) % 12 == rem: sd = f'#{d}'; break
        if sd is None:
            for d, iv in enumerate(MAJOR_INT, 1):
                if (iv-1) % 12 == rem: sd = f'b{d}'; break
        if sd is None: continue
        beat = round(st/ppq + 1, 3)
        dur = round((en - st) / ppq, 3)
        if dur < 0.05 or beat < 1: continue
        out.append({'sd': sd, 'octave': octave, 'beat': beat, 'duration': dur, 'isRest': False, 'recordingEndBeat': None})
    out.sort(key=lambda n: n['beat'])
    for i in range(len(out) - 1):
        gap = out[i+1]['beat'] - (out[i]['beat'] + out[i]['duration'])
        if 0 < gap < 2.5:
            out[i]['duration'] = round(out[i+1]['beat'] - out[i]['beat'], 3)
    return out


def split_at_measure(chord_event):
    """Yield chord segments that all start AND end on measure boundaries (except possibly the first)."""
    beat = chord_event['beat']; remaining = chord_event['duration']
    while remaining > 0.001:
        offset = (beat - 1) % BPB
        if offset < 0.001:
            seg = min(BPB, remaining)
        else:
            seg = min(BPB - offset, remaining)
        out = copy.deepcopy(chord_event)
        out['beat'] = round(beat, 3); out['duration'] = round(seg, 3)
        yield out
        beat += seg; remaining -= seg


def align_sections(ug_sections, midi_chord_events, key_tonic_pc, ug_key_tonic_pc):
    """Walk MIDI chord events, snapping each UG section's chord pattern to its best matching subsequence.
    Returns [{name, start_beat, end_beat, bars, n_matched}]."""
    # Roots for UG sections (in UG's own key). Drop empty sections + dedupe consecutive same-root
    # (MIDI compresses held chords into single events; UG often lists every strum).
    ug_section_roots = []
    for sec in ug_sections:
        roots = []
        for kind, payload in sec.get('events', []):
            if kind != 'chord_line': continue
            for cname, _col in payload:
                info = chord_to_root_degree(cname, NAMES[ug_key_tonic_pc], 'major')
                if info: roots.append(info['deg'])
        # Dedupe consecutive duplicates
        deduped = []
        for r in roots:
            if not deduped or deduped[-1] != r: deduped.append(r)
        if deduped:
            ug_section_roots.append((sec.get('name', '?'), deduped))

    midi_roots = [c['root'] for c in midi_chord_events]
    midi_beats = [c['beat'] for c in midi_chord_events]

    out = []
    pos = 0
    SEARCH_AHEAD = 50   # how far to look for each section's match
    for name, ug_roots in ug_section_roots:
        if not ug_roots:
            # Empty section (no chord events in UG) — give it a placeholder spot
            out.append({'name': name, 'start_beat': None, 'end_beat': None, 'bars': 0, 'n_matched': 0})
            continue
        # Slide a window starting from pos forward, score match against ug_roots.
        # Prefer earlier positions (small penalty per offset) to avoid drifting into repetitions.
        best = (pos, -1e9, len(ug_roots))
        max_start = min(len(midi_roots) - 1, pos + SEARCH_AHEAD)
        for start in range(pos, max_start + 1):
            score = 0; matched = 0
            for j, ur in enumerate(ug_roots):
                if start + j >= len(midi_roots): break
                if midi_roots[start + j] == ur:
                    score += 1; matched += 1
                else:
                    score -= 0.4
            score += 0.1 * matched
            score -= 0.05 * (start - pos)   # earliness bonus
            if score > best[1]: best = (start, score, matched)
        start = best[0]
        # Determine end: walk until UG sequence is "consumed"
        end = min(start + len(ug_roots), len(midi_roots))
        if end < len(midi_chord_events):
            end_beat = midi_chord_events[end]['beat']
        else:
            end_beat = midi_chord_events[-1]['beat'] + midi_chord_events[-1]['duration']
        start_beat = midi_chord_events[start]['beat'] if start < len(midi_chord_events) else end_beat
        # Snap start to nearest measure boundary
        m_offset = (start_beat - 1) % BPB
        if m_offset > 0.5 and m_offset < BPB - 0.5:
            start_beat = start_beat - m_offset   # snap back to measure boundary
        out.append({'name': name, 'start_beat': round(start_beat, 3), 'end_beat': round(end_beat, 3),
                    'bars': round((end_beat - start_beat) / BPB, 2), 'n_matched': best[2]})
        pos = end
    # Now fix sections with no chord data: use surrounding sections' beats
    for i, s in enumerate(out):
        if s['start_beat'] is None:
            prev_end = out[i-1]['end_beat'] if i > 0 and out[i-1]['end_beat'] else 1
            next_start = next((out[j]['start_beat'] for j in range(i+1, len(out)) if out[j].get('start_beat')), prev_end + 16)
            s['start_beat'] = prev_end
            s['end_beat'] = next_start
            s['bars'] = round((next_start - prev_end) / BPB, 2)
    return out


def main():
    args = sys.argv[1:]
    if not args: print('usage: midi_ug_full_pipeline.py <midi> [ug] [out]'); sys.exit(1)
    midi_path = args[0]
    bn = os.path.splitext(os.path.basename(midi_path))[0]
    ug_path = args[1] if len(args) > 1 else os.path.expanduser(f'~/Desktop/music/ug_tabs/{bn}.txt')
    if not os.path.exists(ug_path):
        print(f'no UG file at {ug_path}'); sys.exit(1)
    out_path = args[2] if len(args) > 2 else os.path.expanduser(f'~/Desktop/{bn}_full_paste.txt')

    mid = mido.MidiFile(midi_path)
    ppq = mid.ticks_per_beat

    # Tempo
    tempo = None
    for tk in mid.tracks:
        for msg in tk:
            if msg.type == 'set_tempo': tempo = round(mido.tempo2bpm(msg.tempo)); break
        if tempo: break
    if not tempo: tempo = 120

    # Track classification
    ug_words = lyric_word_count(ug_path)
    roles, tracks = classify(mid, ug_words)
    print(f'tempo {tempo}  roles: {roles}')

    # Pitch distribution → key tonic
    pcs = collections.Counter()
    for t in tracks:
        if t['i'] == roles.get('drums'): continue
        for _, p, _ in t['notes']: pcs[p % 12] += 1
    midi_tonic_pc = infer_tonic(pcs)
    print(f'inferred MIDI key: {NAMES[midi_tonic_pc]} major')

    # Harmonic chord track
    primary = next(t for t in tracks if t['i'] == roles['chords'])['notes']
    secondary = [next(t for t in tracks if t['i'] == ai)['notes'] for ai in roles.get('chords_alts', [])]
    raw_chords = harmonic_chord_track(primary, secondary, ppq, window_beats=2.0)
    print(f'detected {len(raw_chords)} chord events (half-measure resolution)')

    # Convert raw chord labels → Hookpad chord events (in C-encoding via tonic shift)
    hp_chord_events = []
    for beat, label, hm in raw_chords:
        enc = chord_to_root_local(label, midi_tonic_pc)
        if not enc: continue
        root, q, borrowed = enc
        dur = hm * 2.0
        hp_chord_events.append({
            'root': root, 'beat': beat, 'duration': dur, 'type': 5,
            'inversion': 0, 'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': borrowed, 'isRest': False, 'recordingEndBeat': None,
        })

    # UG parse for section alignment
    ug_meta, ug_sections = parse_tab(open(ug_path).read())
    ug_key = ug_meta.get('key', NAMES[midi_tonic_pc])
    # Extract just root letter from UG key string ('E', 'Am', 'F#m', 'No capo' etc.)
    m_key = re.match(r'^([A-G][#b]?)', ug_key)
    ug_key_tonic_pc = note_pc(m_key.group(1)) if m_key else midi_tonic_pc
    print(f'UG key: {ug_key} → tonic pc {ug_key_tonic_pc}')

    # Section alignment
    sections = align_sections(ug_sections, hp_chord_events, midi_tonic_pc, ug_key_tonic_pc)
    print(f'\nUG sections aligned to MIDI:')
    for s in sections:
        print(f"  {s['name']:18s} beats {s['start_beat']:>6}-{s['end_beat']:>6}  ({s['bars']:>4} bars, {s['n_matched']} matched)")

    # Split chord events at measure boundaries
    split_chords = []
    for c in hp_chord_events: split_chords.extend(split_at_measure(c))

    # Melody
    mel_notes = []
    if 'melody' in roles:
        mel_notes = extract_melody(next(t for t in tracks if t['i'] == roles['melody'])['notes'], ppq, midi_tonic_pc)

    # Build sections list for Hookpad
    hp_sections = []
    for s in sections:
        if s.get('start_beat') is None: continue
        hp_sections.append({'beat': max(1, int(s['start_beat'])), 'name': s['name']})
    if not hp_sections:
        hp_sections.append({'beat': 1, 'name': 'Song'})
    # Drop duplicates at same beat
    seen_beats = set(); hp_sections = [s for s in hp_sections if not (s['beat'] in seen_beats or seen_beats.add(s['beat']))]

    end_beat = max(int(c['beat'] + c['duration']) for c in split_chords) if split_chords else 1
    song = {
        'notes': mel_notes,
        'chords': split_chords,
        'keys':   [{'beat':1,'scale':'major','tonic':'C'}],
        'tempos': [{'beat':1,'bpm':tempo,'swingBeat':0.5,'swingFactor':0}],
        'meters': [{'beat':1,'beatUnit':1,'numBeats':BPB}],
        'breaks': [],
        'sections': hp_sections,
        'endBeat': end_beat,
        'audioTracks': [], 'version': 1,
    }
    open(out_path, 'w').write(json.dumps(song, separators=(',', ':')))
    print(f'\n{len(split_chords)} chord events, {len(mel_notes)} melody notes, {len(hp_sections)} sections')
    print(f'wrote → {out_path}')


if __name__ == '__main__':
    main()
