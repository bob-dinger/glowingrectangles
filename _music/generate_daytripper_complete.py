#!/usr/bin/env python3
"""
Generate Day Tripper MIDI - COMPLETE SONG

Structure from Hookpad file:
- Intro: measures 1-10
- Verse 1: measures 11-18
- Chorus 1: measures 19-26
- Half-intro: measures 27-30
- Verse 2: measures 31-38
- Chorus 2: measures 39-46
- Bridge: measures 47-58
- Half-intro: measures 59-62
- Verse 3: measures 63-70
- Chorus 3: measures 71-78
- Half-intro: measures 79-82
- Outro: measures 83-84
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

SCALE_DEGREES = {
    '1': 0, '#1': 1, 'b2': 1, '2': 2, '#2': 3, 'b3': 3, '3': 4,
    '4': 5, '#4': 6, 'b5': 6, '5': 7, '#5': 8, 'b6': 8, '6': 9,
    '#6': 10, 'b7': 10, '7': 11
}

CHORD_ROOTS = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}

CHORD_TYPES = {
    5: [0, 4, 7],
    6: [0, 3, 7],
    7: [0, 4, 7, 10],
    8: [0, 4, 7, 11],
    9: [0, 3, 7, 10],
}

TICKS = 480
END_MEASURE = 84

def sd_to_midi(sd, octave, tonic=64):
    semitones = SCALE_DEGREES.get(sd, 0)
    return tonic + semitones + (octave * 12)

def beats_to_ticks(beats, ticks_per_beat=480):
    return int(beats * ticks_per_beat)

def chord_to_midi_notes(root, chord_type, tonic=52, inversion=0):
    root_semitone = CHORD_ROOTS.get(root, 0)
    intervals = CHORD_TYPES.get(chord_type, [0, 4, 7])
    notes = [tonic + root_semitone + interval for interval in intervals]
    for i in range(inversion):
        if notes:
            notes[i % len(notes)] += 12
    return notes

with zipfile.ZipFile('/Users/robert/Desktop/daytripper.zip', 'r') as z:
    with z.open('project.json') as f:
        project = json.load(f)

tempo_bpm = project['tempos'][0]['bpm']
microseconds_per_beat = int(60_000_000 / tempo_bpm)

riff_notes = [n for n in project['notes'] if not n.get('isRest', False)]
vocal_notes = [n for n in project['inactiveNotes'][0] if not n.get('isRest', False)]
chords = [c for c in project['chords'] if not c.get('isRest', False)]

pattern_notes = [n for n in riff_notes if n['beat'] <= 8]

print(f"Tempo: {tempo_bpm} BPM")
print(f"Riff notes: {len(riff_notes)}, Vocal notes: {len(vocal_notes)}, Chords: {len(chords)}")

def create_melody_track(name, program, channel, notes, velocity=100, octave_offset=0, tonic=64):
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for note in notes:
        if note.get('isRest', False):
            continue
        beat = note['beat'] - 1
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

def create_guitar_track_full(name, program, channel, pattern, start_measure, end_measure, octave_offset=0, velocity=100):
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for measure in range(start_measure, end_measure + 1):
        measure_beat = (measure - 1) * 4
        pattern_offset = ((measure - 1) % 2) * 4

        for note in pattern:
            if note['beat'] > pattern_offset and note['beat'] <= pattern_offset + 4:
                note_beat = measure_beat + (note['beat'] - 1 - pattern_offset)
                tick = beats_to_ticks(note_beat, TICKS)
                duration_ticks = beats_to_ticks(note['duration'], TICKS)
                midi_note = sd_to_midi(note['sd'], note['octave'] + octave_offset, tonic=64)
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

def create_chord_track(name, program, channel, chords, velocity=70, tonic=52):
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

def create_bass_track_riff(name, program, channel, pattern, start_measure, end_measure, velocity=95, tonic=40):
    """Bass plays the riff pattern starting at measure 3"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for measure in range(start_measure, end_measure + 1):
        measure_beat = (measure - 1) * 4
        pattern_offset = ((measure - 1) % 2) * 4

        for note in pattern:
            if note['beat'] > pattern_offset and note['beat'] <= pattern_offset + 4:
                note_beat = measure_beat + (note['beat'] - 1 - pattern_offset)
                tick = beats_to_ticks(note_beat, TICKS)
                duration_ticks = beats_to_ticks(note['duration'], TICKS)
                # Bass plays 2 octaves lower than lead
                midi_note = sd_to_midi(note['sd'], note['octave'] - 2, tonic=64)
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

def get_section_for_measure(measure):
    if measure <= 10: return 'intro'
    if measure <= 18: return 'verse'
    if measure <= 26: return 'chorus'
    if measure <= 30: return 'half_intro'
    if measure <= 38: return 'verse'
    if measure <= 46: return 'chorus'
    if measure <= 58: return 'bridge'
    if measure <= 62: return 'half_intro'
    if measure <= 70: return 'verse'
    if measure <= 78: return 'chorus'
    if measure <= 82: return 'half_intro'
    return 'outro'

def create_tambourine_track(start_measure, end_measure):
    """Tambourine enters at measure 5, plays steady eighth notes"""
    events = [(0, 'track_name', 'Tambourine')]
    TAMBOURINE = 54  # GM tambourine
    note_events = []

    for measure in range(start_measure, end_measure + 1):
        measure_start = (measure - 1) * 4
        for beat in range(4):
            tick = beats_to_ticks(measure_start + beat, TICKS)
            # Eighth notes
            for eighth in range(2):
                t = tick + eighth * TICKS // 2
                vel = 80 if eighth == 0 else 60  # Accent on the beat
                note_events.append((t, 'on', TAMBOURINE, vel))
                note_events.append((t + TICKS // 4, 'off', TAMBOURINE))

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
    return build_track(events, 9)  # Channel 10 for percussion

def create_drum_track(start_measure, end_measure):
    events = [(0, 'track_name', 'Drums')]
    KICK, SNARE, HI_HAT, CRASH, RIDE = 36, 38, 42, 49, 51
    note_events = []

    section_starts = [5, 11, 19, 27, 31, 39, 47, 59, 63, 71, 79, 83]

    for measure in range(start_measure, end_measure + 1):
        measure_start = (measure - 1) * 4
        section = get_section_for_measure(measure)
        is_section_start = measure in section_starts

        for beat in range(4):
            tick = beats_to_ticks(measure_start + beat, TICKS)

            if is_section_start and beat == 0:
                note_events.append((tick, 'on', CRASH, 110))
                note_events.append((tick + TICKS, 'off', CRASH))

            if section == 'intro' and measure < 9:
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 100))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', HI_HAT, 80))
                    note_events.append((t + TICKS//4, 'off', HI_HAT))

            elif section == 'intro' and measure >= 9:
                note_events.append((tick, 'on', KICK, 105))
                note_events.append((tick + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', RIDE, 85))
                    note_events.append((t + TICKS//4, 'off', RIDE))

            elif section == 'verse':
                if beat == 0:
                    note_events.append((tick, 'on', KICK, 100))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                elif beat == 2:
                    note_events.append((tick, 'on', KICK, 90))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                    note_events.append((tick + TICKS//2, 'on', KICK, 80))
                    note_events.append((tick + TICKS//2 + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 100))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', HI_HAT, 75))
                    note_events.append((t + TICKS//4, 'off', HI_HAT))

            elif section == 'chorus':
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 110))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                if beat == 1:
                    note_events.append((tick + TICKS//2, 'on', KICK, 90))
                    note_events.append((tick + TICKS//2 + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 110))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', RIDE, 90))
                    note_events.append((t + TICKS//4, 'off', RIDE))

            elif section == 'bridge':
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 95))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 95))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                note_events.append((tick, 'on', HI_HAT, 70))
                note_events.append((tick + TICKS//4, 'off', HI_HAT))

            elif section == 'half_intro':
                if beat in [0, 2]:
                    note_events.append((tick, 'on', KICK, 90))
                    note_events.append((tick + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 90))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', HI_HAT, 70))
                    note_events.append((t + TICKS//4, 'off', HI_HAT))

            elif section == 'outro':
                note_events.append((tick, 'on', KICK, 105))
                note_events.append((tick + TICKS//4, 'off', KICK))
                if beat in [1, 3]:
                    note_events.append((tick, 'on', SNARE, 105))
                    note_events.append((tick + TICKS//4, 'off', SNARE))
                for e in range(2):
                    t = tick + e * TICKS//2
                    note_events.append((t, 'on', CRASH, 95))
                    note_events.append((t + TICKS//4, 'off', CRASH))

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

# Build all tracks
tempo_events = [
    (0, 'track_name', 'Day Tripper - Complete'),
    (0, 'tempo', microseconds_per_beat),
    (0, 'time_sig', (4, 2)),
    (0, 'end', None)
]
tempo_track = build_track(tempo_events)

# Correct arrangement per Beatles recording:
# M1-2: Lead + Rhythm guitar in unison (double-tracked)
# M3-4: Bass joins
# M5-6: Additional rhythm guitar + tambourine
# M9-10: Drums come in

guitar1_track = create_guitar_track_full('Guitar 1 (Lead)', 25, 0, pattern_notes, 1, END_MEASURE, 0, 100)
guitar2_track = create_guitar_track_full('Guitar 2 (Rhythm)', 26, 1, pattern_notes, 1, END_MEASURE, 0, 95)  # Unison from start
guitar3_track = create_guitar_track_full('Guitar 3 (Fill)', 29, 2, pattern_notes, 5, END_MEASURE, 1, 80)   # Enters m5
vocal_track = create_melody_track('Vocal', 73, 3, vocal_notes, 100, 1, 64)
chord_track = create_chord_track('Chords', 4, 4, chords, 65, 52)
bass_track = create_bass_track_riff('Bass', 33, 5, pattern_notes, 3, END_MEASURE, 95, 40)  # Bass enters m3
tambourine_track = create_tambourine_track(5, END_MEASURE)  # Tambourine at measure 5
drum_track = create_drum_track(9, END_MEASURE)  # Full drums at measure 9

output_path = '/Users/robert/Desktop/daytripper_complete.mid'
write_midi_file(output_path, [tempo_track, guitar1_track, guitar2_track, guitar3_track, vocal_track, chord_track, bass_track, tambourine_track, drum_track])

print(f"\nCreated: {output_path}")
print(f"\n{'='*50}")
print("FULL SONG - 84 measures (CORRECTED ARRANGEMENT)")
print("="*50)
print("INTRO:")
print("  M1-2:  Lead + Rhythm guitar (unison)")
print("  M3-4:  + Bass")
print("  M5-8:  + Fill guitar + TAMBOURINE")
print("  M9-10: + Full DRUMS")
print("-"*50)
print("VERSE 1    (11-18)  Full band + vocals")
print("CHORUS 1   (19-26)  Big energy")
print("HALF-INTRO (27-30)  Riff break")
print("VERSE 2    (31-38)  Full band + vocals")
print("CHORUS 2   (39-46)  Big energy")
print("BRIDGE     (47-58)  Tension build")
print("HALF-INTRO (59-62)  Riff break")
print("VERSE 3    (63-70)  Full band + vocals")
print("CHORUS 3   (71-78)  Final chorus")
print("HALF-INTRO (79-82)  Riff break")
print("OUTRO      (83-84)  Crashing end")
print("="*50)
