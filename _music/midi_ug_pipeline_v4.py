"""V4 pipeline: section lengths from UG (lyric + chord weights × total song bars), snap to common values.

Replaces chord-pattern matching for section boundaries — that was unreliable because
chord progressions repeat WITHIN sections, not just across them.

Per-section weight = (lyric_words × 1) + (chord_changes × 2)
  - Instrumental sections (no lyrics): use chord-change weight + min floor
  - Verses + choruses: lyrics carry the weight
Total weights sum → allocate bars proportionally → snap each to common-length set.

Usage: python midi_ug_pipeline_v4.py <midi> [ug] [out.txt]
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
                if (iv+1)%12 == rem: sd = f'#{d}'; break
        if sd is None:
            for d, iv in enumerate(MAJOR_INT, 1):
                if (iv-1)%12 == rem: sd = f'b{d}'; break
        if sd is None: continue
        beat = round(st/ppq + 1, 3)
        dur = round((en - st)/ppq, 3)
        if dur < 0.05 or beat < 1: continue
        out.append({'sd': sd, 'octave': octave, 'beat': beat, 'duration': dur, 'isRest': False, 'recordingEndBeat': None})
    out.sort(key=lambda n: n['beat'])
    for i in range(len(out) - 1):
        gap = out[i+1]['beat'] - (out[i]['beat'] + out[i]['duration'])
        if 0 < gap < 2.5: out[i]['duration'] = round(out[i+1]['beat'] - out[i]['beat'], 3)
    return out


def drop_phantom_first(chord_events):
    if len(chord_events) < 2: return chord_events
    first, second = chord_events[0], chord_events[1]
    if first['duration'] < 2.0 and first['root'] != second['root']:
        return chord_events[1:]
    if len(chord_events) >= 10 and first['root'] in (2, 7):
        next_roots = [c['root'] for c in chord_events[1:5]]
        if first['root'] not in next_roots: return chord_events[1:]
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


def snap_common(bars):
    return min(COMMON_LENGTHS, key=lambda c: abs(c - bars))


# ---------- V4: proportional section allocation from UG metadata ----------

def _word_at_or_after_col(lyric, col):
    """Return the word index (0-based) that the chord at column `col` lands on.
    A word is any contiguous run of non-whitespace, non-punctuation chars."""
    word_count = 0; in_word = False; word_start_col = None
    for i, ch in enumerate(lyric):
        is_word_char = ch.isalpha() or ch == "'"
        if is_word_char:
            if not in_word:
                word_start_col = i
                in_word = True
        else:
            if in_word:
                # Word just ended at position i; if chord col was within this word, return word_count
                if word_start_col <= col < i: return word_count
                word_count += 1
                in_word = False
    # End of string while in word
    if in_word and word_start_col <= col: return word_count
    return word_count   # chord falls after end of lyric line


def _count_words(lyric):
    return sum(1 for t in lyric.split() if any(c.isalpha() for c in t))


def extract_chord_timing(ug_sections, ug_tonic_pc):
    """For each section: return chord events with syllable-position-in-section.
    Each entry: (root_deg, syllable_idx_in_section, chord_name, original_column)."""
    out = []
    last_root = None
    for sec in ug_sections:
        chord_positions = []
        total_words = 0
        pending = []
        first_event_kind = None
        for kind, payload in sec.get('events', []):
            if first_event_kind is None: first_event_kind = kind
            if kind == 'chord_line':
                pending = payload
            elif kind == 'lyric_line':
                for cname, col in pending:
                    info = chord_to_root_degree(cname, NAMES[ug_tonic_pc], 'major')
                    if info:
                        w_idx = _word_at_or_after_col(payload, col)
                        chord_positions.append((info['deg'], total_words + w_idx, cname, col))
                total_words += _count_words(payload)
                pending = []
        # Trailing chord-only content (instrumental section)
        for cname, col in pending:
            info = chord_to_root_degree(cname, NAMES[ug_tonic_pc], 'major')
            if info:
                chord_positions.append((info['deg'], total_words, cname, col))
        # Sustain prepend: if first chord's column > 0 OR section starts with lyric line, prepend last_root
        if chord_positions and last_root is not None:
            if chord_positions[0][3] > 0 or first_event_kind == 'lyric_line':
                chord_positions = [(last_root, 0, '(sustain)', 0)] + chord_positions
        if chord_positions:
            last_root = chord_positions[-1][0]
        out.append({'name': sec.get('name', '?'),
                    'chords': chord_positions,
                    'total_words': total_words})
    return out


def section_metadata(ug_sections, ug_tonic_pc=0):
    """For each UG section: extract name, lyric word count, chord change count, and roots.
    Applies sustain rules:
      - If section's first chord is at column > 0 (pickup), prepend previous section's last chord
      - If section starts with a lyric line (no chord line first), prepend previous last chord
    """
    out = []
    last_root = None
    for sec in ug_sections:
        n_words = 0
        chord_events_with_col = []   # [(root_deg, col)]
        first_event_kind = None
        for kind, payload in sec.get('events', []):
            if first_event_kind is None: first_event_kind = kind
            if kind == 'chord_line':
                for cname, col in payload:
                    info = chord_to_root_degree(cname, NAMES[ug_tonic_pc], 'major')
                    if info: chord_events_with_col.append((info['deg'], col))
            elif kind == 'lyric_line':
                for tok in payload.split():
                    if tok.isalpha() or "'" in tok: n_words += 1

        roots = [r for r, _ in chord_events_with_col]
        # Sustain rules
        has_pickup = False
        if last_root is not None:
            if chord_events_with_col and chord_events_with_col[0][1] > 0:
                # First chord is indented → pickup, previous chord sustains in
                has_pickup = True
                roots = [last_root] + roots
            elif first_event_kind == 'lyric_line':
                # Section opens with lyrics, no chord — previous chord sustains in
                roots = [last_root] + roots
        # Dedupe consecutive duplicates
        deduped = []
        for r in roots:
            if not deduped or deduped[-1] != r: deduped.append(r)
        if not deduped and not n_words: continue
        if deduped: last_root = deduped[-1]
        # chord_changes = number of unique roots after dedup
        out.append({'name': sec.get('name', '?'),
                    'lyric_words': n_words,
                    'chord_changes': len(deduped),
                    'roots': deduped,
                    'has_pickup': has_pickup})
    return out


def melody_by_measure(notes, bpb=BPB):
    """Group melody-note (sd, octave) pairs by measure index (0-based from beat 1)."""
    out = collections.defaultdict(list)
    for n in notes:
        m = int((n['beat'] - 1) // bpb)
        out[m].append((n['sd'], n['octave']))
    return out


def measure_similarity(a, b):
    if not a or not b: return 0
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(len(sa | sb), 1)


def melody_dominant_length(per_measure, candidates=(4, 6, 8, 10, 12, 14, 16, 20, 24, 32), min_overlap=4):
    """For each candidate section length k, score by total measure-similarity at offset k.
    Returns (best_k, scores_dict)."""
    if not per_measure: return None, {}
    max_m = max(per_measure.keys())
    scores = {}
    for k in candidates:
        s = 0; n = 0
        for m in range(max_m - k + 1):
            a, b = per_measure.get(m, []), per_measure.get(m + k, [])
            if len(a) < min_overlap or len(b) < min_overlap: continue
            sim = measure_similarity(a, b)
            if sim > 0.4: s += sim; n += 1   # only count real matches
        scores[k] = s
    if not scores or max(scores.values()) == 0: return None, scores
    # Slight boost for common lengths
    for k in scores:
        if k in (8, 12, 16): scores[k] *= 1.1
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0], scores


def allocate_sections_by_melody(ug_meta, melody_notes, total_bars):
    """Walk melody notes in order: each lyric section claims a proportional share of the
    note sequence (weighted by its lyric word count). Instrumental sections fill the gaps."""
    if not melody_notes: return None   # caller falls back to proportional
    lyric_words = [s['lyric_words'] for s in ug_meta]
    total_words = sum(lyric_words)
    if total_words == 0: return None   # no lyrics → fall back

    n_melody = len(melody_notes)
    # Per-section melody-note allocation (proportional to lyric word count)
    note_alloc = []
    for i, s in enumerate(ug_meta):
        if lyric_words[i] == 0:
            note_alloc.append(0)   # instrumental, claims a gap
        else:
            note_alloc.append(round(n_melody * lyric_words[i] / total_words))

    # Walk melody notes, assigning ranges
    out = []
    note_i = 0
    for i, (s, n_alloc) in enumerate(zip(ug_meta, note_alloc)):
        if n_alloc == 0:
            out.append({'name': s['name'], 'start_beat': None, 'end_beat': None})
            continue
        start_note = note_i
        end_note = min(start_note + n_alloc, n_melody)
        note_i = end_note
        out.append({
            'name': s['name'],
            'start_beat': melody_notes[start_note]['beat'],
            'end_beat': (melody_notes[end_note]['beat'] if end_note < n_melody
                        else melody_notes[-1]['beat'] + melody_notes[-1]['duration']),
            'n_notes': end_note - start_note,
        })

    # Fill instrumental gaps: previous_end → next_lyric_start (or song boundaries)
    for i, s in enumerate(out):
        if s['start_beat'] is not None: continue
        prev_end = out[i-1]['end_beat'] if i > 0 and out[i-1].get('end_beat') else 1
        next_start = next((out[j]['start_beat'] for j in range(i+1, len(out))
                           if out[j].get('start_beat') is not None), total_bars * BPB + 1)
        s['start_beat'] = prev_end
        s['end_beat']   = next_start

    # Snap each start to nearest measure boundary
    for s in out:
        sb = round(s['start_beat'])
        offset = (sb - 1) % BPB
        if offset != 0:
            sb = sb - offset if offset < BPB/2 else sb + (BPB - offset)
        eb_raw = s['end_beat']
        eb = round(eb_raw)
        offset = (eb - 1) % BPB
        if offset != 0:
            eb = eb - offset if offset < BPB/2 else eb + (BPB - offset)
        bars = max(1, (eb - sb) // BPB)
        s['start_beat'] = max(1, sb)
        s['end_beat'] = s['start_beat'] + bars * BPB
        s['bars'] = bars
        s['bars_raw'] = round((eb_raw - sb) / BPB, 2)

    return [(s['name'], s['bars'], s['bars_raw'], s['start_beat'], s['end_beat']) for s in out]


def allocate_sections(ug_meta, total_bars, melody_length_hint=None):
    """Distribute total_bars across UG sections by weight, snap to common, prefer melody_length_hint."""
    def weight(s):
        n = s['name'].lower()
        c = s['chord_changes']; l = s['lyric_words']
        if 'intro' in n or 'outro' in n or 'interlude' in n or 'solo' in n or 'break' in n or 'bridge' in n:
            return max(c * 2, 6)
        return max(l + c, 8)

    weights = [weight(s) for s in ug_meta]
    total_w = sum(weights) or 1
    raw_alloc = [total_bars * w / total_w for w in weights]
    # Snap with a strong pull toward the melody-detected length for verse/chorus types
    snapped = []
    for s, a in zip(ug_meta, raw_alloc):
        n = s['name'].lower()
        if melody_length_hint and ('verse' in n or 'chorus' in n) and abs(a - melody_length_hint) < melody_length_hint * 0.4:
            snapped.append(melody_length_hint)
        else:
            snapped.append(snap_common(round(a)))
    diff = sum(snapped) - total_bars
    if diff != 0 and ug_meta:
        idx = max(range(len(snapped)), key=lambda i: snapped[i])
        snapped[idx] = max(4, snapped[idx] - diff)
    return list(zip([s['name'] for s in ug_meta], snapped, raw_alloc))


def hookpad_tempo_for(title, artist):
    """Look up the Hookpad-stored tempo for this song from Supabase. Lenient matching."""
    try:
        from dotenv import load_dotenv
        load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
        from supabase import create_client
        sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
        # Match by the longest word in the title (skirts apostrophe issues like Don't → Don'T)
        words = [w for w in re.sub(r"[^\w\s]", " ", title).split() if len(w) >= 4]
        if not words: words = title.split()
        longest = max(words, key=len)
        artist_first = (artist.replace('The ','').split() or [artist])[0]
        r = sb.schema('parcels').table('songs').select('title,artist,hookpad_json,bpm').ilike('title', f'%{longest}%').ilike('artist', f'%{artist_first}%').limit(5).execute()
        for row in r.data:
            if row.get('bpm'): return row['bpm']
            d = row.get('hookpad_json') or {}
            tempos = d.get('tempos') or []
            if tempos: return tempos[0].get('bpm')
    except Exception as e:
        print(f'  (Hookpad lookup error: {e})')
    return None


def build_paste(midi_path, ug_path, out_path, hookpad_bpm=None):
    mid = mido.MidiFile(midi_path); ppq = mid.ticks_per_beat
    tempo = next((round(mido.tempo2bpm(m.tempo)) for tk in mid.tracks for m in tk if m.type=='set_tempo'), 120)
    # Half-time detection: if Hookpad has this song at ~2x the MIDI tempo, MIDI is half-time
    bar_multiplier = 1
    if hookpad_bpm and 1.7 < (hookpad_bpm / tempo) < 2.3:
        bar_multiplier = 2
        tempo = hookpad_bpm   # use the "real" tempo
    ug_words = lyric_word_count(ug_path)
    roles, tracks = classify(mid, ug_words)

    pcs = collections.Counter()
    for t in tracks:
        if t['i'] == roles.get('drums'): continue
        for _, p, _ in t['notes']: pcs[p%12] += 1
    midi_tonic = infer_tonic(pcs)

    primary = next(t for t in tracks if t['i'] == roles['chords'])['notes']
    secondary = [next(t for t in tracks if t['i'] == i)['notes'] for i in roles.get('chords_alts', [])]
    raw_chords = harmonic_chord_track(primary, secondary, ppq, window_beats=2.0)
    hp_chords = []
    for beat, label, hm in raw_chords:
        enc = chord_to_root_local(label, midi_tonic)
        if not enc: continue
        root, q, borrowed = enc
        hp_chords.append({
            'root': root, 'beat': beat, 'duration': hm*2.0, 'type': 5,
            'inversion': 0, 'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': borrowed, 'isRest': False, 'recordingEndBeat': None,
        })
    hp_chords = drop_phantom_first(hp_chords)
    end_beat = max((c['beat'] + c['duration']) for c in hp_chords) if hp_chords else 1
    total_bars = round((end_beat - 1) / BPB) * bar_multiplier

    mel_notes = []
    if 'melody' in roles:
        mel_notes = extract_melody(next(t for t in tracks if t['i'] == roles['melody'])['notes'], ppq, midi_tonic)

    # If MIDI is in half-time relative to Hookpad, stretch beats + durations by bar_multiplier
    if bar_multiplier > 1:
        for c in hp_chords:
            c['beat'] = round((c['beat'] - 1) * bar_multiplier + 1, 3)
            c['duration'] = round(c['duration'] * bar_multiplier, 3)
        for n in mel_notes:
            n['beat'] = round((n['beat'] - 1) * bar_multiplier + 1, 3)
            n['duration'] = round(n['duration'] * bar_multiplier, 3)
        end_beat = end_beat * bar_multiplier

    # Melody-driven section length detection (kept as fallback hint)
    per_meas = melody_by_measure(mel_notes)
    dom_len, dom_scores = melody_dominant_length(per_meas)

    # UG: parse + section metadata (with sustain rules)
    ug_meta_obj, ug_sections = parse_tab(open(ug_path).read())
    # Extract UG-declared tonic for accurate chord-degree conversion
    ug_key_raw = ug_meta_obj.get('key', NAMES[midi_tonic])
    m_key = re.match(r'^([A-G][#b]?)', ug_key_raw)
    ug_tonic_pc = note_pc(m_key.group(1)) if m_key and note_pc(m_key.group(1)) is not None else midi_tonic
    ug_meta = section_metadata(ug_sections, ug_tonic_pc)

    # PRIMARY: walk melody notes, assigning each lyric section proportional notes (by word count).
    # Instrumental sections fill the gaps. Falls back to proportional if no melody/lyrics.
    melody_layout = allocate_sections_by_melody(ug_meta, mel_notes, total_bars)
    if melody_layout:
        section_layout = [(n, b, raw) for (n, b, raw, _sb, _eb) in melody_layout]
    else:
        section_layout = allocate_sections(ug_meta, total_bars, melody_length_hint=dom_len)
    # Build start_beat for each
    sections_out = []
    cur_beat = hp_chords[0]['beat'] if hp_chords else 1
    # Snap first start to measure
    m_offset = (cur_beat - 1) % BPB
    if m_offset != 0:
        cur_beat = cur_beat - m_offset if m_offset < BPB/2 else cur_beat + (BPB - m_offset)
    for name, bars, raw in section_layout:
        sections_out.append({'name': name, 'start_beat': round(cur_beat, 3),
                             'end_beat': round(cur_beat + bars*BPB, 3),
                             'bars': bars, 'bars_raw': round(raw, 2)})
        cur_beat += bars * BPB

    final_end = sections_out[-1]['end_beat'] if sections_out else end_beat
    hp_chords = [c for c in hp_chords if c['beat'] < final_end]
    for c in hp_chords:
        if c['beat'] + c['duration'] > final_end:
            c['duration'] = max(0.5, final_end - c['beat'])
    split_chords = []
    for c in hp_chords: split_chords.extend(split_at_measure(c))
    mel_notes = [n for n in mel_notes if n['beat'] < final_end]

    hp_sections = [{'beat': max(1, int(s['start_beat'])), 'name': s['name']} for s in sections_out]
    seen = set(); hp_sections = [s for s in hp_sections if not (s['beat'] in seen or seen.add(s['beat']))]

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
        'tempo': tempo, 'midi_key': NAMES[midi_tonic],
        'total_bars': total_bars, 'sections': sections_out,
        'chord_events': len(split_chords), 'melody_notes': len(mel_notes),
        'end_beat': int(final_end), 'dom_length': dom_len,
    }


if __name__ == '__main__':
    args = sys.argv[1:]
    midi = args[0]; bn = os.path.splitext(os.path.basename(midi))[0]
    ug   = args[1] if len(args) > 1 else os.path.expanduser(f'~/Desktop/music/ug_tabs/{bn}.txt')
    out  = args[2] if len(args) > 2 else os.path.expanduser(f'~/Desktop/{bn}_v4_paste.txt')
    # Try to infer title/artist from basename, look up Hookpad tempo
    parts = bn.split('_', 1)
    artist_g = parts[0].replace('-', ' ') if len(parts) > 1 else ''
    title_g = (parts[1] if len(parts) > 1 else bn).replace('-', ' ')
    hp_bpm = hookpad_tempo_for(title_g, artist_g)
    if hp_bpm: print(f'  (Hookpad tempo for "{title_g}" / "{artist_g}": {hp_bpm})')
    info = build_paste(midi, ug, out, hookpad_bpm=hp_bpm)
    print(f'tempo {info["tempo"]}  MIDI key {info["midi_key"]}  total bars {info["total_bars"]}\n')
    print(f'{"section":18s}  start    end    bars  (raw)')
    for s in info['sections']:
        print(f"  {s['name']:16s}  {s['start_beat']:>6}  {s['end_beat']:>6}  {s['bars']:>3}    ({s['bars_raw']})")
    print(f'\n{info["chord_events"]} chord events, {info["melody_notes"]} melody notes')
    print(f'wrote → {out}')
