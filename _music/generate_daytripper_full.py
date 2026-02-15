#!/usr/bin/env python3
"""
Generate Day Tripper MIDI - Full arrangement with intro + verse
- Guitar riff (layered intro, continues through verse)
- Vocal melody
- Chord pads
- Bass
- Drums
"""

import struct
import json
import zipfile

# MIDI helper functions
def var_length(value):
    result = []
    result.append(value & 0x7F)
    value >>= 7
    while value:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(result))

def write_midi_file(filename, tracks, ticks_per_beat=480):
    with open(filename, 'wb') as f:
        f.write(b'MThd')
        f.write(struct.pack('>I', 6))
        f.write(struct.pack('>H', 1))
        f.write(struct.pack('>H', len(tracks)))
        f.write(struct.pack('>H', ticks_per_beat))
        for track_data in tracks:
            f.write(b'MTrk')
            f.write(struct.pack('>I', len(track_data)))
            f.write(track_data)

def build_track(events, channel=0):
    data = bytearray()
    for delta, event_type, event_data in events:
        data.extend(var_length(delta))
        if event_type == 'note_on':
            note, velocity = event_data
            data.append(0x90 | channel)
            data.append(note)
            data.append(velocity)
        elif event_type == 'note_off':
            note = event_data
            data.append(0x80 | channel)
            data.append(note)
            data.append(0)
        elif event_type == 'program':
            data.append(0xC0 | channel)
            data.append(event_data)
        elif event_type == 'tempo':
            data.append(0xFF)
            data.append(0x51)
            data.append(0x03)
            data.extend(struct.pack('>I', event_data)[1:])
        elif event_type == 'time_sig':
            num, denom_power = event_data
            data.append(0xFF)
            data.append(0x58)
            data.append(0x04)
            data.append(num)
            data.append(denom_power)
            data.append(24)
            data.append(8)
        elif event_type == 'track_name':
            name = event_data.encode('utf-8')
            data.append(0xFF)
            data.append(0x03)
            data.extend(var_length(len(name)))
            data.extend(name)
        elif event_type == 'end':
            data.append(0xFF)
            data.append(0x2F)
            data.append(0x00)
    return bytes(data)

# Scale degree to semitone offset in major scale
SCALE_DEGREES = {
    '1': 0, '#1': 1, 'b2': 1, '2': 2, '#2': 3, 'b3': 3, '3': 4,
    '4': 5, '#4': 6, 'b5': 6, '5': 7, '#5': 8, 'b6': 8, '6': 9,
    '#6': 10, 'b7': 10, '7': 11
}

# Chord root (1-7) to semitones in major scale
CHORD_ROOTS = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}

# Chord type to intervals
CHORD_TYPES = {
    5: [0, 4, 7],           # Major triad (type 5 in Hookpad)
    6: [0, 3, 7],           # Minor triad
    7: [0, 4, 7, 10],       # Dominant 7th
    8: [0, 4, 7, 11],       # Major 7th
    9: [0, 3, 7, 10],       # Minor 7th
}

TICKS = 480

def sd_to_midi(sd, octave, tonic=64):
    semitones = SCALE_DEGREES.get(sd, 0)
    return tonic + semitones + (octave * 12)

def beats_to_ticks(beats, ticks_per_beat=480):
    return int(beats * ticks_per_beat)

def chord_to_midi_notes(root, chord_type, tonic=52, inversion=0):
    """Convert chord root and type to MIDI notes. tonic=52 is E3"""
    root_semitone = CHORD_ROOTS.get(root, 0)
    intervals = CHORD_TYPES.get(chord_type, [0, 4, 7])
    notes = [tonic + root_semitone + interval for interval in intervals]
    # Handle inversion
    for i in range(inversion):
        if notes:
            notes[i % len(notes)] += 12
    return notes

# Load the Hookpad project
with zipfile.ZipFile('/Users/robert/Desktop/daytripper.zip', 'r') as z:
    with z.open('project.json') as f:
        project = json.load(f)

tempo_bpm = project['tempos'][0]['bpm']
microseconds_per_beat = int(60_000_000 / tempo_bpm)

# Get all the musical data
riff_notes = [n for n in project['notes'] if not n.get('isRest', False)]
vocal_notes = [n for n in project['inactiveNotes'][0] if not n.get('isRest', False)]
chords = [c for c in project['chords'] if not c.get('isRest', False)]

# Separate riff by section
intro_riff = [n for n in riff_notes if n['beat'] < 41]
verse_riff = [n for n in riff_notes if 41 <= n['beat'] < 73]

# Get the 2-measure pattern for repeating
pattern_notes = [n for n in riff_notes if n['beat'] <= 8]

print(f"Tempo: {tempo_bpm} BPM")
print(f"Intro riff notes: {len(intro_riff)}")
print(f"Verse riff notes: {len(verse_riff)}")
print(f"Vocal melody notes: {len(vocal_notes)}")
print(f"Chords: {len(chords)}")

# === TRACK CREATION FUNCTIONS ===

def create_melody_track(name, program, channel, notes, velocity=100, octave_offset=0, tonic=64):
    """Create a melody track from note data"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for note in notes:
        if note.get('isRest', False):
            continue
        beat = note['beat'] - 1  # Convert to 0-indexed
        tick = beats_to_ticks(beat, TICKS)
        duration_ticks = beats_to_ticks(note['duration'], TICKS)
        midi_note = sd_to_midi(note['sd'], note['octave'] + octave_offset, tonic)

        note_events.append((tick, 'on', midi_note, velocity))
        note_events.append((tick + duration_ticks, 'off', midi_note))

    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    last_tick = 0
    for event in note_events:
        delta = event[0] - last_tick
        last_tick = event[0]
        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, channel)

def create_guitar_track_layered(name, program, channel, pattern, start_measure, end_measure, octave_offset=0, velocity=100):
    """Create guitar track with repeating pattern from start to end measure"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    start_beat = (start_measure - 1) * 4
    end_beat = (end_measure) * 4
    pattern_length = 8  # 2 measures

    current_beat = start_beat
    while current_beat < end_beat:
        for note in pattern:
            note_beat = current_beat + (note['beat'] - 1)
            if note_beat >= end_beat:
                break
            tick = beats_to_ticks(note_beat, TICKS)
            duration_ticks = beats_to_ticks(note['duration'], TICKS)
            midi_note = sd_to_midi(note['sd'], note['octave'] + octave_offset, tonic=64)

            note_events.append((tick, 'on', midi_note, velocity))
            note_events.append((tick + duration_ticks, 'off', midi_note))
        current_beat += pattern_length

    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    last_tick = 0
    for event in note_events:
        delta = event[0] - last_tick
        last_tick = event[0]
        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, channel)

def create_chord_track(name, program, channel, chords, velocity=70, tonic=52):
    """Create a chord pad track"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for chord in chords:
        if chord.get('isRest', False):
            continue
        beat = chord['beat'] - 1
        tick = beats_to_ticks(beat, TICKS)
        duration_ticks = beats_to_ticks(chord['duration'], TICKS)

        midi_notes = chord_to_midi_notes(chord['root'], chord['type'], tonic, chord.get('inversion', 0))

        for midi_note in midi_notes:
            note_events.append((tick, 'on', midi_note, velocity))
            note_events.append((tick + duration_ticks, 'off', midi_note))

    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    last_tick = 0
    for event in note_events:
        delta = event[0] - last_tick
        last_tick = event[0]
        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, channel)

def create_bass_track(name, program, channel, chords, velocity=90, tonic=40):
    """Create bass track following chord roots. tonic=40 is E2"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for chord in chords:
        if chord.get('isRest', False):
            continue
        beat = chord['beat'] - 1
        tick = beats_to_ticks(beat, TICKS)
        duration_ticks = beats_to_ticks(chord['duration'], TICKS)

        root_semitone = CHORD_ROOTS.get(chord['root'], 0)
        midi_note = tonic + root_semitone

        note_events.append((tick, 'on', midi_note, velocity))
        note_events.append((tick + duration_ticks, 'off', midi_note))

    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    last_tick = 0
    for event in note_events:
        delta = event[0] - last_tick
        last_tick = event[0]
        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, channel)

def create_drum_track(start_measure, end_measure, pattern_changes=None):
    """Create drum track with pattern changes at specified measures"""
    if pattern_changes is None:
        pattern_changes = {}

    events = [(0, 'track_name', 'Drums')]

    KICK = 36
    SNARE = 38
    HI_HAT = 42
    CRASH = 49
    RIDE = 51

    note_events = []

    for measure in range(start_measure, end_measure + 1):
        measure_start = (measure - 1) * 4

        # Determine pattern for this measure
        pattern = 'basic'
        for change_measure, change_pattern in sorted(pattern_changes.items()):
            if measure >= change_measure:
                pattern = change_pattern

        for beat in range(4):
            beat_time = measure_start + beat
            tick = beats_to_ticks(beat_time, TICKS)

            if pattern == 'basic':
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 100))
                    note_events.append((tick + TICKS // 4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS // 4, 'off', SNARE))
                for eighth in range(2):
                    eighth_tick = tick + (eighth * TICKS // 2)
                    note_events.append((eighth_tick, 'on', HI_HAT, 80))
                    note_events.append((eighth_tick + TICKS // 4, 'off', HI_HAT))

            elif pattern == 'driving':
                if beat == 0 and measure in pattern_changes and pattern_changes[measure] == 'driving':
                    note_events.append((tick, 'on', CRASH, 110))
                    note_events.append((tick + TICKS, 'off', CRASH))
                note_events.append((tick, 'on', KICK, 105))
                note_events.append((tick + TICKS // 4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS // 4, 'off', SNARE))
                else:
                    ghost_tick = tick + TICKS // 2
                    note_events.append((ghost_tick, 'on', SNARE, 50))
                    note_events.append((ghost_tick + TICKS // 4, 'off', SNARE))
                for eighth in range(2):
                    eighth_tick = tick + (eighth * TICKS // 2)
                    note_events.append((eighth_tick, 'on', RIDE, 85))
                    note_events.append((eighth_tick + TICKS // 4, 'off', RIDE))

            elif pattern == 'verse':
                # Verse pattern - slightly more open
                if beat == 0:
                    note_events.append((tick, 'on', KICK, 100))
                    note_events.append((tick + TICKS // 4, 'off', KICK))
                if beat == 2:
                    note_events.append((tick, 'on', KICK, 90))
                    note_events.append((tick + TICKS // 4, 'off', KICK))
                    # Add kick on the "and" of 2 sometimes
                    note_events.append((tick + TICKS // 2, 'on', KICK, 80))
                    note_events.append((tick + TICKS // 2 + TICKS // 4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS // 4, 'off', SNARE))
                for eighth in range(2):
                    eighth_tick = tick + (eighth * TICKS // 2)
                    note_events.append((eighth_tick, 'on', HI_HAT, 75))
                    note_events.append((eighth_tick + TICKS // 4, 'off', HI_HAT))

    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    last_tick = 0
    for event in note_events:
        delta = event[0] - last_tick
        last_tick = event[0]
        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, 9)

# === BUILD THE TRACKS ===

# Tempo track
tempo_events = [
    (0, 'track_name', 'Day Tripper - Full'),
    (0, 'tempo', microseconds_per_beat),
    (0, 'time_sig', (4, 2)),
    (0, 'end', None)
]
tempo_track = build_track(tempo_events)

# Guitar 1: Full song (measures 1-18)
guitar1_track = create_guitar_track_layered(
    'Guitar 1 (Lead)', 25, 0,
    pattern_notes, start_measure=1, end_measure=18,
    octave_offset=0, velocity=100
)

# Guitar 2: Enters measure 3, continues through verse
guitar2_track = create_guitar_track_layered(
    'Guitar 2 (Rhythm)', 26, 1,
    pattern_notes, start_measure=3, end_measure=18,
    octave_offset=-1, velocity=90
)

# Guitar 3: Enters measure 5, continues through verse
guitar3_track = create_guitar_track_layered(
    'Guitar 3 (Power)', 29, 2,
    pattern_notes, start_measure=5, end_measure=18,
    octave_offset=1, velocity=85
)

# Vocal melody (starts at verse, measure 11)
verse_vocal = [n for n in vocal_notes if 41 <= n['beat'] < 73]
vocal_track = create_melody_track(
    'Vocal', 73, 3,  # 73 = Flute (bright, cuts through)
    verse_vocal, velocity=100, octave_offset=1, tonic=64
)

# Chords (start when chords begin in the data)
chord_track = create_chord_track(
    'Chords', 4, 4,  # 4 = Electric Piano
    chords, velocity=65, tonic=52
)

# Bass (follows chords)
bass_track = create_bass_track(
    'Bass', 33, 5,  # 33 = Fingered Bass
    chords, velocity=95, tonic=40
)

# Drums with pattern changes
drum_track = create_drum_track(
    start_measure=5, end_measure=18,
    pattern_changes={5: 'basic', 9: 'driving', 11: 'verse'}
)

# Write the file
output_path = '/Users/robert/Desktop/daytripper_full.mid'
write_midi_file(output_path, [
    tempo_track,
    guitar1_track,
    guitar2_track,
    guitar3_track,
    vocal_track,
    chord_track,
    bass_track,
    drum_track
])

print(f"\nCreated: {output_path}")
print("\n=== ARRANGEMENT ===")
print("INTRO (Measures 1-10):")
print("  1-2:   Guitar 1 alone")
print("  3-4:   + Guitar 2 (octave lower)")
print("  5-8:   + Guitar 3 + Drums (basic pattern)")
print("  9-10:  Drums switch to driving pattern")
print("\nVERSE (Measures 11-18):")
print("  All 3 guitars continue the riff")
print("  + Vocal melody")
print("  + Chord pads")
print("  + Bass following chord roots")
print("  + Drums (verse pattern)")
print("\nTracks: 8 total")
