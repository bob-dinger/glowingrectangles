"""Convert a GM MIDI file to a Hookpad paste-JSON .txt.

Picks the lead/melody track by name + monophony + range, infers per-bar
chord roots from the bass track, snaps everything to the song's detected
tonic.  Diatonic-only output for now — chromatic events get snapped to
their nearest diatonic degree (user can refine in Hookpad).

Usage:
    python midi_to_hookpad_paste.py <input.mid> [<output.txt>]
"""
import os, sys, json, hashlib
from collections import Counter
import mido


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR_INT  = [0, 2, 4, 5, 7, 9, 11]


def extract_notes(track, ticks_per_beat):
    """Walk a single track, pairing note_on/note_off events into (beat, pitch, dur_beats)."""
    out = []
    abs_t = 0
    pending = {}  # pitch -> abs_ticks
    for msg in track:
        abs_t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            pending[msg.note] = abs_t
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in pending:
                start = pending.pop(msg.note)
                out.append({'pitch': msg.note,
                            'beat': 1 + start / ticks_per_beat,
                            'duration': (abs_t - start) / ticks_per_beat})
    return out


def detect_tonic(notes):
    """Pick the most common pitch class — fine for songs that sit on the tonic."""
    if not notes: return 0
    pcs = Counter(n['pitch'] % 12 for n in notes)
    return pcs.most_common(1)[0][0]


def pc_to_scale_degree(pc, tonic_pc):
    """Diatonic snap — returns (root_int_1to7, accidental_str)."""
    diff = (pc - tonic_pc) % 12
    if diff in MAJOR_INT:
        return MAJOR_INT.index(diff) + 1, ''
    # snap chromatic down to nearest diatonic (flat)
    if diff - 1 in MAJOR_INT: return MAJOR_INT.index(diff - 1) + 1, ''
    if diff + 1 in MAJOR_INT: return MAJOR_INT.index(diff + 1) + 1, ''
    return 1, ''


def melody_sd_octave(pitch, tonic_pc):
    """Return (sd_str, hookpad_octave) for a MIDI pitch in the song's key."""
    pc = pitch % 12
    diff = (pc - tonic_pc) % 12
    if diff in MAJOR_INT:
        sd_str = str(MAJOR_INT.index(diff) + 1)
    else:
        # b-prefix accidental relative to next diatonic UP
        nearest_up = next((iv for iv in MAJOR_INT if iv > diff), MAJOR_INT[0] + 12)
        sd_str = 'b' + str((MAJOR_INT.index(nearest_up) if nearest_up <= 11 else 0) + 1)
    # MIDI 60 = C4 = Hookpad octave 0; MIDI 72 = octave 1, etc.
    # but we need to account for tonic placement in that octave (rough enough)
    hp_octave = (pitch - 60) // 12
    return sd_str, hp_octave


def make_chord(beat, root, duration=4):
    return {
        'root': root, 'beat': beat, 'duration': duration, 'type': 5,
        'inversion': 0, 'applied': 0,
        'adds': [], 'omits': [], 'alterations': [], 'suspensions': [], 'substitutions': [],
        'pedal': None, 'alternate': '', 'borrowed': '',
        'isRest': False, 'recordingEndBeat': None,
    }


def make_note(beat, sd, octave, duration):
    return {
        'sd': sd, 'beat': beat, 'isRest': False, 'octave': octave,
        'duration': round(duration * 4) / 4,  # quantize to 1/16
        'recordingEndBeat': None,
    }


def main(in_path, out_path=None, force_tonic=None, force_scale='major'):
    if out_path is None:
        base = os.path.splitext(os.path.basename(in_path))[0].lower().replace("'", '').replace(' ', '-')
        out_path = os.path.expanduser(f'~/Desktop/{base}.txt')

    m = mido.MidiFile(in_path)
    tpb = m.ticks_per_beat
    # tempo
    tempo_us = 500000  # default 120 BPM
    for t in m.tracks:
        for msg in t:
            if msg.type == 'set_tempo':
                tempo_us = msg.tempo; break
        if tempo_us != 500000: break
    bpm = round(60_000_000 / tempo_us)

    # find tracks by name
    def track_by_name(*names):
        for t in m.tracks:
            tn = t.name.strip().lower()
            for n in names:
                if n in tn: return t
        return None

    melody_track = track_by_name('big top', 'lead vocal', 'melody', 'vocal', 'lead', 'synthe 1')
    bass_track   = track_by_name('synbass', 'bass')
    if not melody_track:
        # fallback: pick the track with highest median pitch and reasonable note count
        candidates = []
        for t in m.tracks:
            ns = extract_notes(t, tpb)
            if 50 < len(ns) < 2000:
                med = sorted(n['pitch'] for n in ns)[len(ns)//2]
                candidates.append((med, t))
        candidates.sort(reverse=True)
        if candidates: melody_track = candidates[0][1]
    if not melody_track or not bass_track:
        print(f"missing tracks: melody={bool(melody_track)} bass={bool(bass_track)}")
        sys.exit(1)
    print(f"melody track: {melody_track.name!r}")
    print(f"bass track:   {bass_track.name!r}")

    melody_notes = extract_notes(melody_track, tpb)
    bass_notes   = extract_notes(bass_track, tpb)

    if force_tonic:
        tonic_name = force_tonic
        tonic_pc = NOTE_NAMES.index(force_tonic) if force_tonic in NOTE_NAMES else 0
        print(f"forced key: {tonic_name} {force_scale}  ({bpm} BPM, tpb={tpb})")
    else:
        tonic_pc = detect_tonic(bass_notes)
        tonic_name = NOTE_NAMES[tonic_pc]
        print(f"detected key: {tonic_name} {force_scale}  ({bpm} BPM, tpb={tpb})")

    # Better chord inference: harmonic template match over chord-bearing tracks.
    # For each measure, collect pitch-classes (weighted by note duration) from any
    # tracks that look like chord-pads (piano / "cocottes" / strings), then pick the
    # diatonic root whose triad (root, 3rd, 5th) maximizes overlap with the cell.
    harmony_tracks = []
    for t in m.tracks:
        nm = t.name.strip().lower()
        if any(k in nm for k in ('piano', 'cocottes', 'staccato', 'guitar', 'strings', 'pad', 'organ')):
            harmony_tracks.append(t)
    print(f"harmony tracks: {[t.name for t in harmony_tracks]}")
    harmony_notes = []
    for t in harmony_tracks:
        harmony_notes.extend(extract_notes(t, tpb))

    # PC-weights per measure
    from collections import defaultdict
    measure_pc_weight = defaultdict(lambda: [0.0]*12)
    for n in harmony_notes:
        bar = int((n['beat'] - 1) // 4)
        measure_pc_weight[bar][n['pitch'] % 12] += n['duration']

    DIATONIC = [(deg, MAJOR_INT[deg-1]) for deg in range(1, 8)]
    def best_root_for_measure(pc_weights, tonic_pc):
        best_deg, best_score = 1, -1.0
        for deg, root_offset in DIATONIC:
            root_pc = (tonic_pc + root_offset) % 12
            # triad pitch classes: root + diatonic 3rd + diatonic 5th
            third_offset = (root_offset + 4) % 12  # major third try
            fifth_offset = (root_offset + 7) % 12
            triad_pcs = {root_pc, (tonic_pc + third_offset) % 12, (tonic_pc + fifth_offset) % 12}
            score = sum(pc_weights[pc] for pc in triad_pcs)
            # bias: weight root pc more heavily
            score += pc_weights[root_pc] * 0.5
            if score > best_score:
                best_score, best_deg = score, deg
        return best_deg

    # Determine bar range from bass timeline
    last_bar = max((int((n['beat'] - 1) // 4) for n in bass_notes), default=0)
    chords = []
    for bar_idx in range(last_bar + 1):
        pcw = measure_pc_weight.get(bar_idx, [0.0]*12)
        # if nothing in harmony, fall back to bass-derived root
        if sum(pcw) == 0:
            bass_here = [n for n in bass_notes if int((n['beat']-1)//4) == bar_idx]
            if not bass_here: continue
            root, _ = pc_to_scale_degree(bass_here[0]['pitch'] % 12, tonic_pc)
        else:
            root = best_root_for_measure(pcw, tonic_pc)
        chords.append(make_chord(1 + bar_idx * 4, root, 4))

    notes_out = []
    for n in melody_notes:
        sd, oct_ = melody_sd_octave(n['pitch'], tonic_pc)
        notes_out.append(make_note(round(n['beat'] * 4) / 4, sd, oct_, n['duration']))

    end_beat = max((c['beat'] + c['duration'] for c in chords), default=1)
    obj = {
        'version': 1,
        'chords': chords,
        'notes': notes_out,
        'keys':   [{'beat': 1, 'scale': force_scale, 'tonic': tonic_name}],
        'tempos': [{'beat': 1, 'bpm': bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
        'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
        'breaks': [],
        'sections': [{'beat': 1, 'name': 'Imported MIDI'}],
        'endBeat': end_beat,
        'audioTracks': [],
    }
    compact = json.dumps(obj, separators=(',', ':'))
    obj['fp'] = hashlib.sha1(compact.encode('utf-8')).hexdigest()

    with open(out_path, 'w') as f:
        json.dump(obj, f, separators=(',', ':'))
    print(f"\nwrote {out_path}")
    print(f"  {len(chords)} chords ({len(set(c['root'] for c in chords))} unique roots), "
          f"{len(notes_out)} notes, endBeat={end_beat}")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('output', nargs='?')
    p.add_argument('--tonic', help='Force tonic, e.g. E or G# (overrides detection)')
    p.add_argument('--scale', default='major', choices=['major','minor'])
    args = p.parse_args()
    main(args.input, args.output, args.tonic, args.scale)
