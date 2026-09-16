"""Combine MIDI + UG chord-text → Hookpad paste-JSON per matched song.

Inputs (per match):
  ~/Desktop/midi_files3/{basename}.mid   - MIDI for tempo + melody
  ~/Desktop/music/ug_tabs/{basename}.txt  - UG chord text for section structure

Outputs:
  ~/Desktop/midi_hookpads/{basename}.txt  - Hookpad paste JSON
  ~/Desktop/midi_hookpads_summary.csv     - per-song status

Usage:
    python midi_ug_to_hookpad.py            # all 290 matched songs
    python midi_ug_to_hookpad.py 10         # first 10
"""
import os, sys, csv, json, re, mido, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ug import parse_tab, build_paste

MIDI_DIR = os.path.expanduser('~/Desktop/midi_files3')
UG_DIR   = os.path.expanduser('~/Desktop/music/ug_tabs')
OUT_DIR  = os.path.expanduser('~/Desktop/midi_hookpads')
MATCHES  = os.path.expanduser('~/Desktop/guitar550_midi_matches.csv')
SUMMARY  = os.path.expanduser('~/Desktop/midi_hookpads_summary.csv')
os.makedirs(OUT_DIR, exist_ok=True)

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
INTERVALS = [0,2,4,5,7,9,11]   # C major


def midi_tempo(path):
    try:
        m = mido.MidiFile(path)
        for tk in m.tracks:
            for msg in tk:
                if msg.type == 'set_tempo': return round(mido.tempo2bpm(msg.tempo), 1)
    except Exception: pass
    return None


def midi_pitch_distribution(path):
    """Return Counter of pitch classes across all non-drum tracks."""
    try:
        m = mido.MidiFile(path)
        pcs = collections.Counter()
        for tk in m.tracks:
            channel = 0; is_drum = False
            for msg in tk:
                if msg.type == 'program_change':
                    channel = msg.channel
                    if channel == 9: is_drum = True
                if msg.type == 'note_on' and msg.velocity > 0 and not is_drum:
                    pcs[msg.note % 12] += 1
        return pcs
    except Exception: return collections.Counter()


def infer_key_tonic(pcs):
    """Major-scale fit; return tonic pitch class (0-11)."""
    if not pcs: return 0
    best = (0, -1)
    for tonic in range(12):
        scale = {(tonic+iv)%12 for iv in INTERVALS}
        score = sum(pcs.get(pc, 0) for pc in scale) + 0.3*pcs.get(tonic, 0)
        if score > best[1]: best = (tonic, score)
    return best[0]


def extract_melody(path, shift):
    """Pick the most melody-like track and return a list of Hookpad-style notes (transposed by -shift)."""
    try:
        m = mido.MidiFile(path)
    except Exception: return []
    ppq = m.ticks_per_beat
    # Per-track stats to pick melody
    candidates = []
    for i, tk in enumerate(m.tracks):
        channel = 0; is_drum = False; program = None
        for msg in tk:
            if msg.type == 'program_change':
                channel = msg.channel; program = msg.program
                if channel == 9: is_drum = True
        if is_drum: continue
        notes = []
        abs_t = 0; starts = {}
        for msg in tk:
            abs_t += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                starts[msg.note] = abs_t
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in starts: notes.append((starts.pop(msg.note), msg.note, abs_t))
        if not notes: continue
        pitches = [p for _,p,_ in notes]
        pmin, pmax = min(pitches), max(pitches); med = sorted(pitches)[len(pitches)//2]
        rng = pmax - pmin
        # Vocal-melody-like: narrow range, vocal register, monophonic-ish
        if 50 <= med <= 84 and rng <= 28 and 30 <= len(notes) <= 1500:
            # Score: prefer narrow + vocal register + moderate density
            score = -rng + (1 if 55 <= med <= 76 else 0)
            candidates.append((score, i, notes))
    if not candidates: return []
    candidates.sort(reverse=True)
    _, _, best_notes = candidates[0]
    # Convert to Hookpad notes (transposed)
    out = []
    for st, p, en in best_notes:
        shifted = p - shift
        rel = shifted - 60
        octave = rel // 12
        rem = rel - octave * 12
        sd = None; acc = ''
        for d, iv in enumerate(INTERVALS, 1):
            if iv == rem: sd = str(d); break
        if sd is None:
            for d, iv in enumerate(INTERVALS, 1):
                if (iv+1) % 12 == rem: sd = f'#{d}'; break
        if sd is None:
            for d, iv in enumerate(INTERVALS, 1):
                if (iv-1) % 12 == rem: sd = f'b{d}'; break
        if sd is None: continue
        beat = round(st/ppq + 1, 3)
        dur = round((en - st)/ppq, 3)
        if dur < 0.05 or beat < 1: continue
        out.append({'sd': sd, 'octave': octave, 'beat': beat, 'duration': dur,
                    'isRest': False, 'recordingEndBeat': None})
    out.sort(key=lambda n: n['beat'])
    # Gap fill (< 2.5 beats)
    for i in range(len(out) - 1):
        gap = out[i+1]['beat'] - (out[i]['beat'] + out[i]['duration'])
        if 0 < gap < 2.5:
            out[i]['duration'] = round(out[i+1]['beat'] - out[i]['beat'], 3)
    return out


def process(midi_path, ug_path):
    # 1. Parse UG → sections + chord events
    meta, sections = parse_tab(open(ug_path).read())
    # 2. Use MIDI tempo if present
    bpm = midi_tempo(midi_path) or meta.get('bpm') or 100
    meta['bpm'] = bpm
    # 3. Build paste from UG
    paste, summary = build_paste(meta, sections)
    paste['tempos'][0]['bpm'] = bpm
    # 4. Inject MIDI-derived melody (transposed to C)
    pcs = midi_pitch_distribution(midi_path)
    midi_tonic = infer_key_tonic(pcs)
    melody = extract_melody(midi_path, midi_tonic)
    if melody:
        paste['notes'] = melody
    return paste, {
        'bpm': bpm,
        'midi_key': NAMES[midi_tonic],
        'melody_notes': len(melody),
        'sections': len(paste['sections']),
        'chords': len(paste['chords']),
        'end_beat': paste['endBeat'],
    }


def main():
    args = sys.argv[1:]
    limit = int(args[0]) if args and args[0].isdigit() else None

    matches = list(csv.DictReader(open(MATCHES)))
    # dedupe by midi_file
    seen = set(); unique = []
    for r in matches:
        if r['midi_file'] in seen: continue
        seen.add(r['midi_file']); unique.append(r)
    if limit: unique = unique[:limit]
    print(f'processing {len(unique)} matched songs…')

    def kebab(s):
        s = (s or '').lower().strip()
        s = re.sub(r"[''`]", '', s)
        s = re.sub(r'\s+', '-', s)
        s = re.sub(r'[^a-z0-9_-]', '-', s)
        return re.sub(r'-+', '-', s).strip('-_')
    def candidate_ug_basenames(midi_file, title, artist):
        bn = midi_file[:-4]
        # Strip _N dedupe suffix
        bn_clean = re.sub(r'_\d+$', '', bn)
        a = kebab(artist)
        if a.startswith('the-'): a = a[4:]
        canon = f'{a}_{kebab(title)}'
        # Also try stripping "-the-X-Y" subtitle from artist segment
        m = re.match(r'^(.+?)-the-[a-z0-9-]+(_.+)$', bn_clean)
        bn_short = m.group(1) + m.group(2) if m else None
        names = [bn, bn_clean, canon, bn_short]
        return [n for n in names if n]

    rows = []
    for i, r in enumerate(unique, 1):
        bn = r['midi_file'][:-4]
        midi_path = os.path.join(MIDI_DIR, r['midi_file'])
        out_path  = os.path.join(OUT_DIR, bn + '.txt')
        ug_path = None
        for cand in candidate_ug_basenames(r['midi_file'], r['title'], r['artist']):
            p = os.path.join(UG_DIR, cand + '.txt')
            if os.path.exists(p):
                ug_path = p; break
        if not ug_path:
            rows.append({'midi_file': r['midi_file'], 'status': 'no_ug', 'title': r['title'], 'artist': r['artist']})
            continue
        try:
            paste, info = process(midi_path, ug_path)
            open(out_path, 'w').write(json.dumps(paste, separators=(',',':')))
            rows.append({'midi_file': r['midi_file'], 'status': 'ok', 'title': r['title'], 'artist': r['artist'], **info})
            if i <= 3 or i % 25 == 0:
                print(f'  [{i:3}/{len(unique)}] ✓ {bn}: bpm={info["bpm"]} mel={info["melody_notes"]} secs={info["sections"]} chords={info["chords"]}')
        except Exception as e:
            rows.append({'midi_file': r['midi_file'], 'status': f'error:{str(e)[:80]}', 'title': r['title'], 'artist': r['artist']})
            print(f'  [{i:3}/{len(unique)}] ✗ {bn}: {e}')

    # Summary
    fields = ['midi_file','title','artist','status','bpm','midi_key','melody_notes','sections','chords','end_beat']
    with open(SUMMARY, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows: w.writerow({k: r.get(k,'') for k in fields})
    n_ok = sum(1 for r in rows if r.get('status') == 'ok')
    n_noug = sum(1 for r in rows if r.get('status') == 'no_ug')
    n_err = sum(1 for r in rows if r.get('status','').startswith('error'))
    print(f'\nok: {n_ok}, no_ug: {n_noug}, errors: {n_err}')
    print(f'pastes → {OUT_DIR}')
    print(f'summary → {SUMMARY}')


if __name__ == '__main__':
    main()
