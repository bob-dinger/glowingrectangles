"""Full MIDI + UG → Hookpad paste pipeline (v3 with self-similarity detection).

Layers:
  1. Track classification (drums/bass/melody/chords) with UG lyric-count hint
  2. Quantized half-measure harmonic chord detection + secondary-track fallback
  3. Same-root chord collapse, drop phantom first chord
  4. Melody self-similarity → find dominant section length
  5. Chord pattern matching to align UG section labels
  6. Snap section lengths to common values {4, 8, 12, 16, 24, 32}
  7. Measure-aligned chord splitting (every chord ≤ 1 measure)

Usage:
    python midi_ug_pipeline_v3.py <midi_path> [ug_path] [out.txt]
"""
import os, sys, json, re, copy, mido, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_song_v2 import classify, harmonic_chord_track, lyric_word_count
from parse_ug import parse_tab, chord_to_root_degree

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
FLATS = {'Db':1,'Eb':3,'Gb':6,'Ab':8,'Bb':10}
MAJOR_INT = [0, 2, 4, 5, 7, 9, 11]
BPB = 4
COMMON_LENGTHS = [4, 6, 8, 10, 12, 14, 16, 20, 24, 32]


def note_pc(s):
    return NAMES.index(s) if s in NAMES else FLATS.get(s)


def infer_tonic(pcs):
    best = (0, -1)
    for t in range(12):
        scale = {(t+iv)%12 for iv in MAJOR_INT}
        sc = sum(pcs.get(pc, 0) for pc in scale) + 0.3 * pcs.get(t, 0)
        if sc > best[1]: best = (t, sc)
    return best[0]


def chord_to_root_local(chord_label, tonic_pc):
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


# ---------- Self-similarity ----------

def melody_repetition_intervals(notes, phrase_len=6):
    """For every phrase-length window of melody notes, hash it. Inter-occurrence beat distance
    of repeated phrases → candidate section length (rounded to nearest measure)."""
    sigs = collections.defaultdict(list)
    for i in range(len(notes) - phrase_len + 1):
        phrase = notes[i:i+phrase_len]
        sig = tuple((n['sd'], n['octave']) for n in phrase)
        sigs[sig].append(phrase[0]['beat'])
    intervals = collections.Counter()
    for beats in sigs.values():
        if len(beats) < 2: continue
        beats = sorted(beats)
        for i in range(len(beats) - 1):
            d = beats[i+1] - beats[i]
            rounded = round(d / BPB) * BPB  # snap to measure
            if 8 <= rounded <= 128: intervals[rounded] += 1
    return intervals


def chord_repetition_intervals(chord_events, pattern_len=4):
    roots = [c['root'] for c in chord_events]
    intervals = collections.Counter()
    for i in range(len(roots) - pattern_len):
        for j in range(i+1, len(roots) - pattern_len + 1):
            if roots[i:i+pattern_len] == roots[j:j+pattern_len]:
                d = chord_events[j]['beat'] - chord_events[i]['beat']
                rounded = round(d / BPB) * BPB
                if 8 <= rounded <= 128: intervals[rounded] += 1
                break
    return intervals


def find_dominant_length(melody_notes, chord_events):
    """Combine melody + chord repetition signals → most likely verse/chorus length in bars."""
    mel_iv = melody_repetition_intervals(melody_notes) if melody_notes else collections.Counter()
    chd_iv = chord_repetition_intervals(chord_events) if chord_events else collections.Counter()
    combined = collections.Counter()
    for d, c in mel_iv.items(): combined[d] += c * 2   # melody is more reliable
    for d, c in chd_iv.items(): combined[d] += c
    if not combined: return 16  # default
    # Prefer common multiples (8/12/16/24/32)
    boosted = {d: c * (1.3 if (d/BPB) in COMMON_LENGTHS else 1) for d, c in combined.items()}
    best = max(boosted.items(), key=lambda kv: kv[1])
    return int(best[0] / BPB)  # convert beats → bars


def snap_to_common(bars, dominant=16):
    """Round detected bar count to a common-length value, preferring the dominant section length."""
    if bars <= 0: return dominant
    # Test each common length + dominant
    candidates = sorted(set(COMMON_LENGTHS + [dominant]))
    return min(candidates, key=lambda c: abs(c - bars))


# ---------- Chord cleanup ----------

def drop_phantom_first(chord_events):
    """Drop the leading chord event if it looks like a pickup/artifact:
      - short (<2 beats) with different root from next, OR
      - first event on a non-tonic root (2 or 7) when song has 10+ events
        and that root doesn't recur in the next 4 events
    """
    if len(chord_events) < 2: return chord_events
    first, second = chord_events[0], chord_events[1]
    # Short + different root
    if first['duration'] < 2.0 and first['root'] != second['root']:
        return chord_events[1:]
    # Non-tonic opener that doesn't recur immediately
    if len(chord_events) >= 10 and first['root'] in (2, 7):
        next_roots = [c['root'] for c in chord_events[1:5]]
        if first['root'] not in next_roots:
            return chord_events[1:]
    return chord_events


def split_at_measure(c):
    beat = c['beat']; remaining = c['duration']
    while remaining > 0.001:
        offset = (beat - 1) % BPB
        seg = min(BPB, remaining) if offset < 0.001 else min(BPB - offset, remaining)
        out = copy.deepcopy(c)
        out['beat'] = round(beat, 3); out['duration'] = round(seg, 3)
        yield out
        beat += seg; remaining -= seg


# ---------- Section alignment ----------

def section_type_length(name, dominant_bars):
    """Default bar length for a section type, given the dominant verse length."""
    n = (name or '').lower()
    if 'intro' in n or 'interlude' in n: return min(10, dominant_bars)
    if 'verse' in n: return dominant_bars
    if 'chorus' in n: return max(8, int(dominant_bars * 0.75))   # 12 if dominant=16
    if 'bridge' in n or 'break' in n: return max(8, dominant_bars // 2)
    if 'pre' in n: return 4
    if 'outro' in n or 'fade' in n: return dominant_bars
    return dominant_bars


def align_sections_v3(ug_sections, chord_events, ug_tonic_pc, dominant_bars, total_end_beat):
    """Walk through the song, assigning section lengths primarily from type + dominant prior.
    Chord matching is used to confirm/adjust the FIRST section start (intro length)."""
    # Build UG section list with default lengths
    ug_secs = []
    for sec in ug_sections:
        roots = []
        for kind, payload in sec.get('events', []):
            if kind != 'chord_line': continue
            for cname, _col in payload:
                info = chord_to_root_degree(cname, NAMES[ug_tonic_pc], 'major')
                if info: roots.append(info['deg'])
        deduped = []
        for r in roots:
            if not deduped or deduped[-1] != r: deduped.append(r)
        if deduped:
            ug_secs.append({'name': sec.get('name','?'), 'roots': deduped, 'chord_count': len(roots)})

    if not ug_secs: return []

    midi_roots = [c['root'] for c in chord_events]
    midi_beats = [c['beat'] for c in chord_events]

    # Step 1: find the FIRST section's start (intro). Match its pattern in early MIDI events.
    first = ug_secs[0]
    first_start = midi_beats[0] if midi_beats else 1
    # Try positions 0..5 for best match of first section roots
    best = (0, -1e9, 0)
    for start in range(min(6, len(midi_roots) - len(first['roots']) + 1)):
        score = 0; matched = 0
        for j, ur in enumerate(first['roots']):
            if start + j >= len(midi_roots): break
            if midi_roots[start + j] == ur: score += 1; matched += 1
            else: score -= 0.4
        if score > best[1]: best = (start, score, matched)
    intro_start_beat = midi_beats[best[0]] if best[0] < len(midi_beats) else first_start
    # Snap to measure boundary
    m_offset = (intro_start_beat - 1) % BPB
    if m_offset != 0:
        intro_start_beat = intro_start_beat - m_offset if m_offset < BPB/2 else intro_start_beat + (BPB - m_offset)

    # Step 2: walk through UG sections, assigning bar lengths based on type + dominant prior.
    # First-section length: try to detect from chord matching, else use type default.
    out = []
    cur_beat = max(1, intro_start_beat)
    for i, sec in enumerate(ug_secs):
        # Default length from type
        bars = section_type_length(sec['name'], dominant_bars)
        # For first section (usually Intro): try to use matched length from MIDI
        if i == 0 and best[2] >= 4:
            intro_raw = best[2]   # number of distinct chord events matched
            # Heuristic: each MIDI chord event ≈ 2 beats (since half-measure resolution + held chords)
            # but for intros with rapid chord changes, this can be off
            # Use the position of next-different-pattern as the true end
            # For now: use chord-event-count as a hint, snap to common
            bars = snap_to_common(intro_raw + 2, dominant=dominant_bars)   # +2 fudge for sustained chords
        out.append({'name': sec['name'], 'start_beat': round(cur_beat, 3),
                    'bars': bars, 'end_beat': round(cur_beat + bars * BPB, 3),
                    'bars_raw': bars, 'ug_chord_count': sec['chord_count']})
        cur_beat += bars * BPB

    # Step 3: if we overshot the song, trim the last section to fit
    if cur_beat > total_end_beat:
        overshoot = cur_beat - total_end_beat
        last = out[-1]
        new_bars = max(2, last['bars'] - int(overshoot / BPB))
        last['bars'] = new_bars
        last['end_beat'] = round(last['start_beat'] + new_bars * BPB, 3)
    # Or undershoot — extend the last section (outro)
    elif total_end_beat - cur_beat > BPB * 2:
        extra = int((total_end_beat - cur_beat) / BPB)
        last = out[-1]
        last['bars'] += extra
        last['end_beat'] = round(last['start_beat'] + last['bars'] * BPB, 3)
    return out


# ---------- Build paste ----------

def build_paste(midi_path, ug_path, out_path):
    mid = mido.MidiFile(midi_path); ppq = mid.ticks_per_beat
    tempo = next((round(mido.tempo2bpm(m.tempo)) for tk in mid.tracks for m in tk if m.type=='set_tempo'), 120)
    ug_words = lyric_word_count(ug_path)
    roles, tracks = classify(mid, ug_words)

    # Key
    pcs = collections.Counter()
    for t in tracks:
        if t['i'] == roles.get('drums'): continue
        for _, p, _ in t['notes']: pcs[p % 12] += 1
    midi_tonic = infer_tonic(pcs)

    # Chord events
    primary = next(t for t in tracks if t['i'] == roles['chords'])['notes']
    secondary = [next(t for t in tracks if t['i'] == i)['notes'] for i in roles.get('chords_alts', [])]
    raw_chords = harmonic_chord_track(primary, secondary, ppq, window_beats=2.0)

    # Build Hookpad chord events (in C-encoding)
    hp_chords = []
    for beat, label, hm in raw_chords:
        enc = chord_to_root_local(label, midi_tonic)
        if not enc: continue
        root, q, borrowed = enc
        hp_chords.append({
            'root': root, 'beat': beat, 'duration': hm * 2.0, 'type': 5,
            'inversion': 0, 'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': borrowed, 'isRest': False, 'recordingEndBeat': None,
        })
    hp_chords = drop_phantom_first(hp_chords)

    # Melody
    mel_notes = []
    if 'melody' in roles:
        mel_notes = extract_melody(next(t for t in tracks if t['i'] == roles['melody'])['notes'],
                                   ppq, midi_tonic)

    # Dominant section length via self-similarity
    dominant = find_dominant_length(mel_notes, hp_chords)
    end_beat = max((c['beat'] + c['duration']) for c in hp_chords) if hp_chords else 1

    # UG section alignment
    ug_meta, ug_sections = parse_tab(open(ug_path).read())
    ug_key = ug_meta.get('key', NAMES[midi_tonic])
    m_key = re.match(r'^([A-G][#b]?)', ug_key)
    ug_tonic = note_pc(m_key.group(1)) if m_key and note_pc(m_key.group(1)) is not None else midi_tonic
    sections = align_sections_v3(ug_sections, hp_chords, ug_tonic, dominant, end_beat)

    # Adjust chord events: trim chords that extend past the last section's end
    final_end = sections[-1]['end_beat'] if sections else end_beat
    hp_chords = [c for c in hp_chords if c['beat'] < final_end]
    for c in hp_chords:
        if c['beat'] + c['duration'] > final_end:
            c['duration'] = max(0.5, final_end - c['beat'])

    # Split chord events at measure boundaries
    split_chords = []
    for c in hp_chords: split_chords.extend(split_at_measure(c))

    # Trim melody to song range
    mel_notes = [n for n in mel_notes if n['beat'] < final_end]

    # Sections list
    hp_sections = [{'beat': max(1, int(s['start_beat'])), 'name': s['name']} for s in sections]
    if not hp_sections: hp_sections = [{'beat': 1, 'name': 'Song'}]
    # Dedupe by beat
    seen = set()
    hp_sections = [s for s in hp_sections if not (s['beat'] in seen or seen.add(s['beat']))]

    song = {
        'notes': mel_notes, 'chords': split_chords,
        'keys':   [{'beat':1,'scale':'major','tonic':'C'}],
        'tempos': [{'beat':1,'bpm':tempo,'swingBeat':0.5,'swingFactor':0}],
        'meters': [{'beat':1,'beatUnit':1,'numBeats':BPB}],
        'breaks': [], 'sections': hp_sections,
        'endBeat': int(final_end), 'audioTracks': [], 'version': 1,
    }
    open(out_path, 'w').write(json.dumps(song, separators=(',', ':')))
    return {
        'tempo': tempo, 'midi_key': NAMES[midi_tonic], 'ug_key': ug_key,
        'dominant_length_bars': dominant,
        'sections': sections, 'chord_events': len(split_chords),
        'melody_notes': len(mel_notes), 'end_beat': int(final_end),
    }


def main():
    args = sys.argv[1:]
    if not args: print('usage: midi_ug_pipeline_v3.py <midi> [ug] [out]'); sys.exit(1)
    midi_path = args[0]
    bn = os.path.splitext(os.path.basename(midi_path))[0]
    ug_path = args[1] if len(args) > 1 else os.path.expanduser(f'~/Desktop/music/ug_tabs/{bn}.txt')
    out_path = args[2] if len(args) > 2 else os.path.expanduser(f'~/Desktop/{bn}_v3_paste.txt')
    if not os.path.exists(ug_path):
        print(f'no UG file at {ug_path}'); sys.exit(1)
    info = build_paste(midi_path, ug_path, out_path)
    print(f'tempo {info["tempo"]}  MIDI key {info["midi_key"]}  UG key {info["ug_key"]}')
    print(f'dominant section length: {info["dominant_length_bars"]} bars\n')
    print(f'{"section":18s}  start    end    bars  (raw)')
    for s in info['sections']:
        print(f'  {s["name"]:16s}  {s["start_beat"]:>6}  {s["end_beat"]:>6}  {s["bars"]:>3}    ({s["bars_raw"]})')
    print(f'\n{info["chord_events"]} chord events, {info["melody_notes"]} melody notes, end {info["end_beat"]}')
    print(f'wrote → {out_path}')


if __name__ == '__main__':
    main()
