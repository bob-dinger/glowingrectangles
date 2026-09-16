"""Phase 1 (track classification) + Phase 2 (quantized chord extraction).

Per-song single-file analyzer. Picks the best track for each role using:
  - Drums:   MIDI channel 9, or wide-rapid-low-pitch heuristic
  - Bass:    GM program 33-40 OR median pitch < 50
  - Melody:  narrow pitch range + vocal register (55-80 median) + note count near UG lyric word count
  - Chords:  polyphonic (notes overlap) + mid register, NOT one of the above

Then extracts the chord track's chord events with 1/8-beat onset quantization (default).

Usage:
    python analyze_song_v2.py <midi_path> [ug_chord_text_path]
"""
import os, sys, re, mido, collections

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def lyric_word_count(ug_path):
    """Count words across all lyric lines in a UG chord text file (rough syllable proxy)."""
    if not os.path.exists(ug_path): return None
    text = open(ug_path).read()
    # Strip the # URL line and metadata
    lines = [l for l in text.split('\n')
             if not l.startswith('#') and not re.match(r'^\s*(Tuning|Key|Capo):', l)]
    n_words = 0
    chord_re = re.compile(r'^[A-G][#b]?[a-z0-9]*(/[A-G][#b]?)?$')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('['): continue
        tokens = line.split()
        # Skip pure-chord lines (every token looks like a chord)
        if tokens and all(chord_re.match(t) for t in tokens): continue
        # Count word-ish tokens (no chord symbols)
        for t in tokens:
            if t.isalpha() or "'" in t: n_words += 1
    return n_words


def track_notes(track):
    notes = []; abs_t = 0; starts = {}
    channel = 0; program = None; is_drum_chan = False; name = ''
    for msg in track:
        abs_t += msg.time
        if msg.type == 'track_name': name = msg.name
        if msg.type == 'program_change':
            program = msg.program; channel = msg.channel
            if channel == 9: is_drum_chan = True
        if msg.type == 'note_on' and msg.velocity > 0:
            starts[msg.note] = abs_t
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in starts: notes.append((starts.pop(msg.note), msg.note, abs_t))
    return {'name': name, 'program': program, 'channel': channel,
            'is_drum_chan': is_drum_chan, 'notes': notes}


def polyphony_ratio(notes):
    """Fraction of total note-time where 2+ notes overlap."""
    if len(notes) < 2: return 0.0
    events = []
    for s, _, e in notes:
        events.append((s, +1)); events.append((e, -1))
    events.sort()
    poly_time = total = 0; active = 0; prev = events[0][0]
    for t, delta in events:
        if active >= 1: total += t - prev
        if active >= 2: poly_time += t - prev
        active += delta; prev = t
    return poly_time / total if total else 0.0


def classify(mid, ug_lyric_count=None):
    tracks_info = []
    for i, tk in enumerate(mid.tracks):
        info = track_notes(tk); info['i'] = i
        if not info['notes']: continue
        pitches = [p for _, p, _ in info['notes']]
        info['pitch_min'] = min(pitches); info['pitch_max'] = max(pitches)
        info['pitch_range'] = info['pitch_max'] - info['pitch_min']
        info['median'] = sorted(pitches)[len(pitches)//2]
        info['n_notes'] = len(info['notes'])
        info['poly_ratio'] = polyphony_ratio(info['notes'])
        # Role hints
        info['is_drum'] = info['is_drum_chan']
        info['is_bass'] = (info['program'] is not None and 33 <= info['program'] <= 40) or info['median'] < 50
        tracks_info.append(info)

    # Pick best per role with scores
    roles = {}
    # Drums: any drum-channel track with the most notes
    drums = [t for t in tracks_info if t['is_drum']]
    if drums: roles['drums'] = max(drums, key=lambda t: t['n_notes'])['i']

    # Bass: lowest median pitch among bass-program-or-low-pitch tracks
    bass_cands = [t for t in tracks_info if t['is_bass'] and not t['is_drum'] and t['median'] < 55]
    if bass_cands: roles['bass'] = min(bass_cands, key=lambda t: t['median'])['i']

    # Melody: monophonic, narrow range, vocal register, optionally matches lyric count
    melody_cands = []
    for t in tracks_info:
        if t['is_drum'] or t['i'] == roles.get('bass'): continue
        if not (50 <= t['median'] <= 84): continue
        if t['pitch_range'] > 28: continue
        if t['poly_ratio'] > 0.20: continue   # mostly monophonic
        if t['n_notes'] < 20 or t['n_notes'] > 2000: continue
        score = -t['pitch_range'] * 2 + (5 if t['poly_ratio'] < 0.05 else 0)
        if ug_lyric_count:
            # Bonus when note count is within ±30% of lyric word count
            ratio = t['n_notes'] / ug_lyric_count
            if 0.7 <= ratio <= 1.5: score += 10
        melody_cands.append((score, t))
    if melody_cands:
        roles['melody'] = max(melody_cands, key=lambda x: x[0])[1]['i']

    # Chords: highly polyphonic, mid register, not already assigned. Return primary + alts in order.
    chord_cands = []
    used = set(roles.values())
    for t in tracks_info:
        if t['i'] in used or t['is_drum']: continue
        if t['poly_ratio'] < 0.20: continue
        if not (40 <= t['median'] <= 80): continue
        score = t['poly_ratio'] * 10 + min(t['n_notes'], 1000) / 100
        chord_cands.append((score, t))
    chord_cands.sort(reverse=True)
    if chord_cands:
        roles['chords'] = chord_cands[0][1]['i']
        roles['chords_alts'] = [c[1]['i'] for c in chord_cands[1:]]

    return roles, tracks_info


def identify_chord_weighted(pc_weights):
    """Score every (root, quality) candidate by total weight of chord tones vs non-chord."""
    if not pc_weights: return None
    total = sum(pc_weights.values())
    best = (None, -1)
    for root in range(12):
        for q, ivs in QUAL.items():
            chord_pcs = {(root + iv) % 12 for iv in ivs}
            in_chord = sum(pc_weights.get(p, 0) for p in chord_pcs)
            out_chord = sum(pc_weights.get(p, 0) for p in pc_weights if p not in chord_pcs)
            # Weight: fraction of chord-tone weight, minus penalty for non-chord
            score = in_chord - 0.4 * out_chord
            # Bonus if root is heavily weighted
            score += 0.3 * pc_weights.get(root, 0)
            # Slight preference for triads (3 notes) over 7ths
            if len(ivs) == 3: score *= 1.05
            if score > best[1]: best = (NAMES[root] + q, score)
    return best[0]


def simplify_chord(label):
    """Strip 7th/sus/add/etc. to just root + basic-triad-quality.
       'F#m7' -> 'F#m'  'Aadd9' -> 'A'  'Esus4' -> 'E'  'C#dim' -> 'C#dim'  'Gaug' -> 'Gaug'"""
    if not label: return None
    m = re.match(r'^([A-G][#b]?)(.*)$', label)
    if not m: return label
    root, rest = m.group(1), m.group(2)
    # Determine basic quality
    if rest.startswith('m') and not rest.startswith('maj'): q = 'm'
    elif rest.startswith('dim'): q = 'dim'
    elif rest.startswith('aug'): q = 'aug'
    else: q = ''
    return root + q


def harmonic_chord_track(primary_notes, secondary_notes_lists, ppq, window_beats=2.0, end_beat=None):
    """Sample one chord per window_beats window (default = half-measure in 4/4).
    For each window: gather weighted pitch classes from primary; if primary has no notes,
    fall back to secondary tracks. Returns [(beat, chord_label, duration_in_half_measures)]."""
    # Determine end beat
    all_notes_for_end = primary_notes + [n for sec in secondary_notes_lists for n in sec]
    if not all_notes_for_end: return []
    end_tick = max(e for _, _, e in all_notes_for_end)
    end_beat_calc = end_tick / ppq + 1
    if end_beat is None or end_beat > end_beat_calc:
        end_beat = end_beat_calc

    # Per-window chord
    samples = []
    beat = 1.0
    while beat < end_beat:
        win_end = beat + window_beats
        # Build weighted pc profile from primary
        weights = collections.Counter()
        for st, p, en in primary_notes:
            sb, eb = st/ppq + 1, en/ppq + 1
            if sb < win_end and eb > beat:
                weights[p % 12] += min(eb, win_end) - max(sb, beat)
        # Fall back to secondaries if primary empty
        if not weights:
            for sec in secondary_notes_lists:
                for st, p, en in sec:
                    sb, eb = st/ppq + 1, en/ppq + 1
                    if sb < win_end and eb > beat:
                        weights[p % 12] += min(eb, win_end) - max(sb, beat)
                if weights: break
        chord = identify_chord_weighted(weights) if weights else None
        samples.append((round(beat, 3), chord))
        beat = win_end

    # Simplify each chord (drop 7th/sus/add9 etc.), then collapse consecutive same-root same-quality
    collapsed = []
    for b, c in samples:
        simp = simplify_chord(c)
        if collapsed and collapsed[-1][1] == simp:
            collapsed[-1] = [collapsed[-1][0], simp, collapsed[-1][2] + 1]
        else:
            collapsed.append([b, simp, 1])
    return collapsed


QUAL = {'':(0,4,7),'m':(0,3,7),'7':(0,4,7,10),'m7':(0,3,7,10),'maj7':(0,4,7,11),
        'dim':(0,3,6),'sus2':(0,2,7),'sus4':(0,5,7),'5':(0,7),'add9':(0,2,4,7)}


def identify_chord(pcs):
    if not pcs: return None
    pcset = set(pcs)
    best = (None, -1)
    for root in range(12):
        for q, ivs in QUAL.items():
            chord_pcs = {(root + iv) % 12 for iv in ivs}
            score = len(chord_pcs & pcset) - 0.5 * len(pcset - chord_pcs)
            # Bonus if root is the lowest pitch class
            if min(pcs) == root: score += 0.3
            if len(ivs) == 3: score *= 1.05
            if score > best[1]: best = (NAMES[root] + q, score)
    return best[0]


def main():
    args = sys.argv[1:]
    if not args: print('usage: analyze_song_v2.py <midi_path> [ug_text_path]'); sys.exit(1)
    midi_path = args[0]
    ug_path = args[1] if len(args) > 1 else None
    if not ug_path:
        # Auto-find
        bn = os.path.splitext(os.path.basename(midi_path))[0]
        guess = os.path.expanduser(f'~/Desktop/music/ug_tabs/{bn}.txt')
        if os.path.exists(guess): ug_path = guess

    mid = mido.MidiFile(midi_path)
    ppq = mid.ticks_per_beat
    ug_words = lyric_word_count(ug_path) if ug_path else None
    print(f'MIDI: {os.path.basename(midi_path)}  ({mid.length:.1f}s, {len(mid.tracks)} tracks)')
    print(f'UG:   {os.path.basename(ug_path) if ug_path else "(none)"}  lyric words: {ug_words}')

    roles, tracks = classify(mid, ug_words)
    print(f'\n--- Track summary ---')
    print(f'{"#":>3}  {"name":24s}  {"prog":>4}  {"ch":>2}  {"notes":>5}  {"pitch":>9}  {"poly":>5}  role')
    for t in tracks:
        role = next((r for r, ix in roles.items() if ix == t['i']), '')
        print(f'{t["i"]:>3}  {t["name"][:24]:24s}  {str(t["program"]):>4}  {t["channel"]:>2}  '
              f'{t["n_notes"]:>5}  {t["pitch_min"]:>3}-{t["pitch_max"]:>3}  '
              f'{t["poly_ratio"]:>5.2f}  {role}')

    if 'chords' in roles:
        primary_notes = next(t for t in tracks if t['i'] == roles['chords'])['notes']
        alt_idxs = roles.get('chords_alts', [])
        secondary_notes = [next(t for t in tracks if t['i'] == ai)['notes'] for ai in alt_idxs]
        ch = harmonic_chord_track(primary_notes, secondary_notes, ppq, window_beats=2.0)
        print(f'\n--- Harmonic chord track  (half-measure windows; primary=tk{roles["chords"]}, fallbacks={alt_idxs}) ---')
        print(f'  {len(ch)} chord changes over {sum(e[2] for e in ch)} half-measures (~{sum(e[2] for e in ch) * 0.5:.0f} bars)\n')
        for beat, chord, hm in ch[:60]:
            measure = int((beat - 1) // 4 + 1)
            bars = hm * 0.5
            print(f'  m{measure:>3}  beat {beat:>7.2f}  {bars:>4.1f}b  {chord}')
        # Skip the rest of the legacy printer
        return
        # legacy below (unused)
        seen = []
        for ev in []:
            beat, pcs, _, _, src = ev
            chord = identify_chord(pcs)
            if seen and seen[-1]['chord'] == chord:
                seen[-1]['end_beat'] = beat
            else:
                seen.append({'beat': beat, 'chord': chord, 'src': src, 'end_beat': beat})
        n_fb = sum(1 for s in seen if s['src'] == 'fallback')
        print(f'  ({len(seen)} unique chord changes, {n_fb} from fallback tracks)\n')
        last_end = None
        for s in seen[:60]:
            dur = max(0.5, s['end_beat'] - s['beat'])
            tag = '[F]' if s['src'] == 'fallback' else '   '
            print(f'  {tag} beat {s["beat"]:7.2f}  dur~{dur:5.2f}  {s["chord"]}')
    else:
        print('\nno chord track identified.')


if __name__ == '__main__':
    main()
