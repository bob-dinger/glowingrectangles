"""Extract just the melody track from each MIDI for Hookpad import.

Picks the most-melody-like track per file: monophonic, mid-to-high register, drum-channel excluded.
Writes a new <name>_melody.mid that Hookpad can import without you having to mute other tracks.

Run: python extract_melody.py
"""
import os, glob
import mido

MIDI_DIR = '/Users/robert/Desktop/midis'

# General MIDI program names (0-indexed, just the families that matter for melody detection)
GM_FAMILIES = {
    range(0, 8):   'Piano',
    range(8, 16):  'Chromatic Percussion',
    range(16, 24): 'Organ',
    range(24, 32): 'Guitar',
    range(32, 40): 'Bass',
    range(40, 48): 'Strings',
    range(48, 56): 'Ensemble',
    range(56, 64): 'Brass',
    range(64, 72): 'Reed',
    range(72, 80): 'Pipe',
    range(80, 88): 'Synth Lead',
    range(88, 96): 'Synth Pad',
    range(96, 104): 'Synth Effects',
    range(104, 112): 'Ethnic',
    range(112, 120): 'Percussive',
    range(120, 128): 'Sound Effects',
}
def gm_family(p):
    for r, n in GM_FAMILIES.items():
        if p in r: return n
    return '?'


def analyze_track(track):
    """Return dict of track stats."""
    name = next((m.name for m in track if m.type == 'track_name'), '')
    program = next((m.program for m in track if m.type == 'program_change'), None)
    channels = set()
    notes = []  # (abs_tick, note, velocity)
    abs_tick = 0
    active = {}  # note -> start_tick
    for msg in track:
        abs_tick += msg.time
        if hasattr(msg, 'channel'):
            channels.add(msg.channel)
        if msg.type == 'note_on' and msg.velocity > 0:
            active[msg.note] = abs_tick
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active:
                start = active.pop(msg.note)
                notes.append((start, msg.note, abs_tick - start))
    is_drums = 9 in channels  # channel 10 in GM = drums (0-indexed = 9)
    pitches = [n[1] for n in notes]
    avg = sum(pitches) / len(pitches) if pitches else 0
    # Monophonic-ness: count how many notes overlap with any other note
    notes_sorted = sorted(notes)
    overlaps = 0
    for i, (s, _, d) in enumerate(notes_sorted):
        end = s + d
        for j in range(i+1, len(notes_sorted)):
            s2 = notes_sorted[j][0]
            if s2 >= end: break
            overlaps += 1
    mono_ratio = 1.0 - (overlaps / max(len(notes), 1))  # 1.0 = perfectly mono
    return {
        'name': name, 'program': program, 'family': gm_family(program or 0),
        'is_drums': is_drums, 'note_count': len(notes),
        'avg_pitch': avg, 'mono_ratio': mono_ratio,
        'pitch_min': min(pitches) if pitches else 0,
        'pitch_max': max(pitches) if pitches else 0,
    }


MELODY_NAME_HINTS = ['vocal', 'voice', 'vox', 'melody', 'lead vocal', 'lead vox', 'singer', 'main melody']
NON_MELODY_HINTS = ['bass', 'drum', 'percuss', 'kick', 'snare', 'hi-hat', 'cymbal',
                    'guitar', 'organ', 'string', 'pad', 'piano', 'effects', 'tempo',
                    'click', 'reset', 'fx', 'rhythm']

def melody_score(stats):
    """Higher = more melody-like."""
    if stats['is_drums']: return -1000
    if stats['note_count'] < 10: return -1000
    name_lower = stats['name'].lower()
    score = 0
    # Strong bonus for melody-suggesting names
    for hint in MELODY_NAME_HINTS:
        if hint in name_lower:
            score += 500
            break
    # Strong penalty for non-melody names — but only if no melody hint matched
    if score == 0:
        for hint in NON_MELODY_HINTS:
            if hint in name_lower:
                score -= 100
                break
    score += stats['mono_ratio'] * 100     # prefer monophonic
    score += min(stats['avg_pitch'], 80)   # prefer mid/high register
    score += min(stats['note_count'] / 10, 30)  # prefer dense
    return score


def write_track(mid, track_idx, out_path):
    new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    new_mid.tracks.append(mid.tracks[0])  # tempo/key meta
    if track_idx != 0:
        new_mid.tracks.append(mid.tracks[track_idx])
    new_mid.save(out_path)


def extract(midi_path):
    mid = mido.MidiFile(midi_path)
    base = os.path.basename(midi_path).replace('.mid', '')
    print(f'\n{"="*70}\n{os.path.basename(midi_path)} — {len(mid.tracks)} tracks')

    # Format 0 = single track with everything mashed together — can't extract
    if len(mid.tracks) == 1:
        print(f'  ⚠ single-track (Format 0) — can\'t separate melody automatically.')
        print(f'    Use GarageBand "Split by Channel" or a DAW to demix.')
        return

    stats_per_track = []
    for i, t in enumerate(mid.tracks):
        s = analyze_track(t)
        stats_per_track.append((i, s))
        flag = 'DRUMS' if s['is_drums'] else ''
        print(f'  [{i:>2}] {s["name"][:25]:25} {s["family"][:13]:13} '
              f'notes={s["note_count"]:>4} pitch={s["pitch_min"]:>3}-{s["pitch_max"]:>3} '
              f'avg={s["avg_pitch"]:>4.1f} mono={s["mono_ratio"]:.2f} {flag}')

    scored = sorted([(melody_score(s), i, s) for i, s in stats_per_track], reverse=True)
    best_score, best_i, best_s = scored[0]
    confident = best_score >= 500   # strong name match
    label = '(name match)' if confident else '(best-guess)'
    print(f'  → picked track {best_i}: {best_s["name"]!r} ({best_s["family"]}, score {best_score:.1f}) {label}')

    write_track(mid, best_i, midi_path.replace('.mid', '_melody.mid'))
    print(f'  saved → {base}_melody.mid')

    # If we're not confident, also split every non-drum track for manual auditioning
    if not confident:
        print(f'  ⚠ no track named voice/melody/vocal — also splitting candidates:')
        for i, s in stats_per_track:
            if s['is_drums'] or s['note_count'] < 10: continue
            safe_name = (s['name'] or f'track{i}').lower().replace(' ', '_').replace('/', '_')
            safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')[:30]
            out = midi_path.replace('.mid', f'_t{i}_{safe_name}.mid')
            write_track(mid, i, out)
            print(f'    → {os.path.basename(out)}')


for f in sorted(glob.glob(os.path.join(MIDI_DIR, '*.mid'))):
    if '_melody' in f: continue
    extract(f)
