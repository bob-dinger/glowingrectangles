#!/usr/bin/env python3
"""
Generate Day Tripper MIDI with layered intro build-up:
- Measures 1-2: Guitar 1 alone
- Measures 3-4: Guitar 2 joins (octave lower)
- Measures 5+: Guitar 3 joins (harmony) + Drums at measure 5
"""

import struct
import json
import zipfile

# MIDI helper functions
def var_length(value):
    """Encode a value as MIDI variable-length quantity"""
    result = []
    result.append(value & 0x7F)
    value >>= 7
    while value:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(result))

def write_midi_file(filename, tracks, ticks_per_beat=480):
    """Write a multi-track MIDI file"""
    with open(filename, 'wb') as f:
        # Header chunk
        f.write(b'MThd')
        f.write(struct.pack('>I', 6))  # Header length
        f.write(struct.pack('>H', 1))  # Format 1 (multi-track)
        f.write(struct.pack('>H', len(tracks)))  # Number of tracks
        f.write(struct.pack('>H', ticks_per_beat))  # Ticks per beat

        # Track chunks
        for track_data in tracks:
            f.write(b'MTrk')
            f.write(struct.pack('>I', len(track_data)))
            f.write(track_data)

def build_track(events, channel=0):
    """Build track data from list of (delta_ticks, event_type, data) tuples"""
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
            program = event_data
            data.append(0xC0 | channel)
            data.append(program)
        elif event_type == 'tempo':
            microseconds = event_data
            data.append(0xFF)
            data.append(0x51)
            data.append(0x03)
            data.extend(struct.pack('>I', microseconds)[1:])
        elif event_type == 'time_sig':
            num, denom_power = event_data
            data.append(0xFF)
            data.append(0x58)
            data.append(0x04)
            data.append(num)
            data.append(denom_power)
            data.append(24)  # MIDI clocks per metronome click
            data.append(8)   # 32nd notes per quarter note
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

def sd_to_midi(sd, octave, tonic=64):
    """Convert scale degree + octave to MIDI note number
    tonic=64 is E4 (E major key)
    """
    semitones = SCALE_DEGREES.get(sd, 0)
    return tonic + semitones + (octave * 12)

def beats_to_ticks(beats, ticks_per_beat=480):
    return int(beats * ticks_per_beat)

# Load the Hookpad project
with zipfile.ZipFile('/Users/robert/Desktop/daytripper.zip', 'r') as z:
    with z.open('project.json') as f:
        project = json.load(f)

# Extract tempo and key
tempo_bpm = project['tempos'][0]['bpm']  # 138
microseconds_per_beat = int(60_000_000 / tempo_bpm)

# Get the riff notes (main melody track - the guitar riff)
# These are in the "notes" array for the intro section (beats 1-40)
riff_notes = [n for n in project['notes'] if n['beat'] < 41 and not n.get('isRest', False)]

# The riff is 8 beats (2 measures) and repeats 5 times in the intro
# Let's extract the first pattern (beats 1-8)
pattern_notes = [n for n in riff_notes if n['beat'] <= 8]

print(f"Found {len(pattern_notes)} notes in the 2-measure riff pattern")
print(f"Tempo: {tempo_bpm} BPM")

# Build the MIDI file
TICKS = 480
VELOCITY = 100
GUITAR_PROGRAM = 25  # Acoustic Guitar (steel)
GUITAR2_PROGRAM = 26  # Electric Guitar (jazz)
GUITAR3_PROGRAM = 29  # Overdriven Guitar

# Create tempo/conductor track
tempo_events = [
    (0, 'track_name', 'Day Tripper'),
    (0, 'tempo', microseconds_per_beat),
    (0, 'time_sig', (4, 2)),  # 4/4 time
    (0, 'end', None)
]
tempo_track = build_track(tempo_events)

def create_guitar_track(name, program, channel, start_measure, pattern, repetitions, octave_offset=0, velocity=100):
    """Create a guitar track that starts at a specific measure"""
    events = [(0, 'track_name', name), (0, 'program', program)]

    # Calculate start time
    start_beat = (start_measure - 1) * 4  # 4 beats per measure
    current_tick = beats_to_ticks(start_beat, TICKS)
    last_tick = 0

    # Collect all note on/off events
    note_events = []

    for rep in range(repetitions):
        pattern_offset = rep * 8  # Each pattern is 8 beats (2 measures)
        for note in pattern:
            note_beat = start_beat + pattern_offset + (note['beat'] - 1)  # Adjust beat
            note_tick = beats_to_ticks(note_beat, TICKS)
            duration_ticks = beats_to_ticks(note['duration'], TICKS)

            midi_note = sd_to_midi(note['sd'], note['octave'] + octave_offset, tonic=64)

            note_events.append((note_tick, 'on', midi_note, velocity))
            note_events.append((note_tick + duration_ticks, 'off', midi_note))

    # Sort by time
    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    # Convert to delta times
    last_tick = 0
    for event in note_events:
        tick = event[0]
        delta = tick - last_tick
        last_tick = tick

        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, channel)

def create_drum_track(start_measure, num_measures, pattern_change_measure=None):
    """Create a drum track with optional pattern change at a specific measure"""
    events = [(0, 'track_name', 'Drums')]

    # Drum notes (GM standard)
    KICK = 36
    SNARE = 38
    HI_HAT = 42
    CRASH = 49
    RIDE = 51
    TOM_HIGH = 50
    TOM_LOW = 45

    start_beat = (start_measure - 1) * 4
    note_events = []

    for measure in range(num_measures):
        current_measure = start_measure + measure
        measure_start = start_beat + (measure * 4)

        # Switch pattern at measure 9
        use_new_pattern = pattern_change_measure and current_measure >= pattern_change_measure

        for beat in range(4):
            beat_time = measure_start + beat
            tick = beats_to_ticks(beat_time, TICKS)

            if not use_new_pattern:
                # Original pattern: basic rock
                # Kick on 1 and 3
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 100))
                    note_events.append((tick + TICKS // 4, 'off', KICK))

                # Snare on 2 and 4
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS // 4, 'off', SNARE))

                # Hi-hat on every eighth note
                for eighth in range(2):
                    eighth_tick = tick + (eighth * TICKS // 2)
                    note_events.append((eighth_tick, 'on', HI_HAT, 80))
                    note_events.append((eighth_tick + TICKS // 4, 'off', HI_HAT))
            else:
                # New pattern at measure 9: driving fill/build
                # Crash on beat 1 of measure 9
                if current_measure == pattern_change_measure and beat == 0:
                    note_events.append((tick, 'on', CRASH, 110))
                    note_events.append((tick + TICKS, 'off', CRASH))

                # Kick on all beats (driving)
                note_events.append((tick, 'on', KICK, 105))
                note_events.append((tick + TICKS // 4, 'off', KICK))

                # Snare on 2 and 4, plus ghost notes
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS // 4, 'off', SNARE))
                else:
                    # Ghost note on the "and" of 1 and 3
                    ghost_tick = tick + TICKS // 2
                    note_events.append((ghost_tick, 'on', SNARE, 50))
                    note_events.append((ghost_tick + TICKS // 4, 'off', SNARE))

                # Ride instead of hi-hat, 8th notes
                for eighth in range(2):
                    eighth_tick = tick + (eighth * TICKS // 2)
                    note_events.append((eighth_tick, 'on', RIDE, 85))
                    note_events.append((eighth_tick + TICKS // 4, 'off', RIDE))

    # Sort by time
    note_events.sort(key=lambda x: (x[0], 0 if x[1] == 'off' else 1))

    # Convert to delta times
    last_tick = 0
    for event in note_events:
        tick = event[0]
        delta = tick - last_tick
        last_tick = tick

        if event[1] == 'on':
            events.append((delta, 'note_on', (event[2], event[3])))
        else:
            events.append((delta, 'note_off', event[2]))

    events.append((TICKS, 'end', None))
    return build_track(events, 9)  # Channel 10 (9 in 0-indexed) for drums

# Create the tracks with layered entry:
# Guitar 1: Measures 1-10 (full intro)
# Guitar 2: Measures 3-10 (enters measure 3, octave lower)
# Guitar 3: Measures 5-10 (enters measure 5, harmony notes)
# Drums: Measures 5-10 (enters with guitar 3)

guitar1_track = create_guitar_track(
    'Guitar 1 (Lead)', GUITAR_PROGRAM, 0,
    start_measure=1, pattern=pattern_notes, repetitions=5,
    octave_offset=0, velocity=100
)

guitar2_track = create_guitar_track(
    'Guitar 2 (Rhythm)', GUITAR2_PROGRAM, 1,
    start_measure=3, pattern=pattern_notes, repetitions=4,
    octave_offset=-1, velocity=90  # Octave lower, slightly quieter
)

guitar3_track = create_guitar_track(
    'Guitar 3 (Power)', GUITAR3_PROGRAM, 2,
    start_measure=5, pattern=pattern_notes, repetitions=3,
    octave_offset=1, velocity=85  # Octave higher for brightness
)

drum_track = create_drum_track(start_measure=5, num_measures=6, pattern_change_measure=9)

# Write the MIDI file
output_path = '/Users/robert/Desktop/daytripper_layered.mid'
write_midi_file(output_path, [
    tempo_track,
    guitar1_track,
    guitar2_track,
    guitar3_track,
    drum_track
])

print(f"\nCreated: {output_path}")
print("\nTrack layout:")
print("  Measures 1-2:  Guitar 1 alone")
print("  Measures 3-4:  Guitar 1 + Guitar 2 (octave lower)")
print("  Measures 5-8:  All 3 guitars + Drums (basic rock pattern)")
print("  Measures 9-10: All 3 guitars + Drums (driving pattern with crash/ride)")
