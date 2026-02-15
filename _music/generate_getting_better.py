#!/usr/bin/env python3
"""
Generate Getting Better MIDI - Based on Alan W. Pollack's analysis

Key: C Major
Form: Intro | Verse | Refrain | Verse | Refrain | Bridge | Verse (+1) | Refrain | Bridge | Outro

Intro: 4 bars (F-F-C-F with G octave chiming)
Verse: 8 bars (G pedal)
Refrain: 8 bars (C-Dm-Em-F x2)
Bridge: 10 bars (F-G vamp 2 bars, then C-Dm-Em-F x2)
Final Verse: 9 bars (extra measure = the "stop")
"""

import struct

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

TICKS = 480
TEMPO_BPM = 118
MICROSECONDS_PER_BEAT = int(60_000_000 / TEMPO_BPM)

def beats_to_ticks(beats):
    return int(beats * TICKS)

# Chord voicings (MIDI notes)
CHORDS = {
    'C': [48, 52, 55, 60],      # C3, E3, G3, C4
    'Dm': [50, 53, 57],         # D3, F3, A3
    'Em': [52, 55, 59],         # E3, G3, B3
    'F': [53, 57, 60],          # F3, A3, C4
    'G': [55, 59, 62],          # G3, B3, D4
}

# G octave chime (piano/guitar)
G_CHIME = [55, 67]  # G3, G4

# === SONG STRUCTURE ===
# Build measure-by-measure chord map

def build_song_structure():
    """Returns list of (measure_number, chord, section_name)"""
    structure = []
    m = 1

    # INTRO: 4 bars (F-F-C-F)
    for chord in ['F', 'F', 'C', 'F']:
        structure.append((m, chord, 'intro'))
        m += 1

    # VERSE 1: 8 bars (G pedal)
    for _ in range(8):
        structure.append((m, 'G', 'verse1'))
        m += 1

    # REFRAIN 1: 8 bars (C-Dm-Em-F x2)
    for _ in range(2):
        for chord in ['C', 'Dm', 'Em', 'F']:
            structure.append((m, chord, 'refrain1'))
            m += 1

    # VERSE 2: 8 bars (G pedal)
    for _ in range(8):
        structure.append((m, 'G', 'verse2'))
        m += 1

    # REFRAIN 2: 8 bars
    for _ in range(2):
        for chord in ['C', 'Dm', 'Em', 'F']:
            structure.append((m, chord, 'refrain2'))
            m += 1

    # BRIDGE 1: 10 bars (F-G vamp x2, then C-Dm-Em-F x2)
    for chord in ['F', 'G', 'F', 'G']:  # 2 bars of F-G vamp (half bar each? or 1 bar each?)
        structure.append((m, chord, 'bridge1'))
        m += 1
    # Wait, Pollack says 2 bars of F-G-F-G vamp, then 8 bars of refrain chords
    # Let me reparse: 2 bars total for the vamp, then 8 bars = 10 total
    # Actually let me do: F-G (1 bar), F-G (1 bar), then C-Dm-Em-F x2
    # I'll simplify to 1 chord per bar for the vamp

    # Let me redo bridge:
    # Actually, let's just do 10 bars: F, G, C, Dm, Em, F, C, Dm, Em, F

    # VERSE 3: 9 bars (G pedal + 1 extra "stop" bar)
    for _ in range(9):
        structure.append((m, 'G', 'verse3'))
        m += 1

    # REFRAIN 3: 8 bars
    for _ in range(2):
        for chord in ['C', 'Dm', 'Em', 'F']:
            structure.append((m, chord, 'refrain3'))
            m += 1

    # BRIDGE 2: 10 bars
    for chord in ['F', 'G', 'F', 'G', 'C', 'Dm', 'Em', 'F', 'C', 'Dm']:
        structure.append((m, chord, 'bridge2'))
        m += 1

    # OUTRO: 6 bars (F-G vamp then C fade)
    for chord in ['F', 'G', 'F', 'G', 'C', 'C']:
        structure.append((m, chord, 'outro'))
        m += 1

    return structure

# Rebuild with cleaner structure
def build_song_structure_v2():
    structure = []
    m = 1

    # INTRO: 4 bars
    intro_chords = ['F', 'F', 'C', 'F']
    for chord in intro_chords:
        structure.append((m, chord, 'intro'))
        m += 1

    # VERSE 1: 8 bars
    for _ in range(8):
        structure.append((m, 'G', 'verse'))
        m += 1

    # REFRAIN 1: 8 bars
    refrain_chords = ['C', 'Dm', 'Em', 'F', 'C', 'Dm', 'Em', 'F']
    for chord in refrain_chords:
        structure.append((m, chord, 'refrain'))
        m += 1

    # VERSE 2: 8 bars
    for _ in range(8):
        structure.append((m, 'G', 'verse'))
        m += 1

    # REFRAIN 2: 8 bars
    for chord in refrain_chords:
        structure.append((m, chord, 'refrain'))
        m += 1

    # BRIDGE 1: 10 bars (F-G-F-G then C-Dm-Em-F-C-Dm-Em-F... but that's 12)
    # Let's do: F-G-F-G (4) + C-Dm-Em-F (4) + Em-F (2) = 10?
    # Or: F-G (2) + C-Dm-Em-F-C-Dm-Em-F (8) = 10
    bridge_chords = ['F', 'G', 'C', 'Dm', 'Em', 'F', 'C', 'Dm', 'Em', 'F']
    for chord in bridge_chords:
        structure.append((m, chord, 'bridge'))
        m += 1

    # VERSE 3: 9 bars (the extra bar!)
    for i in range(9):
        section = 'verse_stop' if i == 8 else 'verse'
        structure.append((m, 'G', section))
        m += 1

    # REFRAIN 3: 8 bars
    for chord in refrain_chords:
        structure.append((m, chord, 'refrain'))
        m += 1

    # BRIDGE 2: 10 bars
    for chord in bridge_chords:
        structure.append((m, chord, 'bridge'))
        m += 1

    # OUTRO: 6 bars
    outro_chords = ['F', 'G', 'F', 'G', 'C', 'C']
    for chord in outro_chords:
        structure.append((m, chord, 'outro'))
        m += 1

    return structure

SONG = build_song_structure_v2()
TOTAL_MEASURES = len(SONG)

def create_chord_track(name, program, channel):
    """Main chord/piano track"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for measure, chord, section in SONG:
        measure_start = (measure - 1) * 4
        tick = beats_to_ticks(measure_start)

        # Staccato stabs for intro and verse, sustained for refrain/bridge
        if section in ['intro', 'verse', 'verse_stop']:
            # Staccato pattern: hits on 1, 2&, 3, 4&
            for beat_offset in [0, 1.5, 2, 3.5]:
                t = beats_to_ticks(measure_start + beat_offset)
                for note in CHORDS[chord]:
                    note_events.append((t, 'on', note, 90))
                    note_events.append((t + TICKS // 4, 'off', note))
        else:
            # Sustained chord for refrain/bridge
            duration = TICKS * 4 - 10  # Almost full bar
            for note in CHORDS[chord]:
                note_events.append((tick, 'on', note, 80))
                note_events.append((tick + duration, 'off', note))

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

def create_g_chime_track(name, program, channel):
    """G octave chime - plays in intro, refrain, bridge, outro (not verses)"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    for measure, chord, section in SONG:
        if section in ['verse', 'verse_stop']:
            continue  # No chime in verses

        measure_start = (measure - 1) * 4
        # Chime on each beat
        for beat in range(4):
            tick = beats_to_ticks(measure_start + beat)
            for note in G_CHIME:
                note_events.append((tick, 'on', note, 70))
                note_events.append((tick + TICKS // 2, 'off', note))

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

def create_bass_track(name, program, channel):
    """Bass following chord roots"""
    events = [(0, 'track_name', name), (0, 'program', program)]
    note_events = []

    bass_notes = {'C': 36, 'Dm': 38, 'Em': 40, 'F': 41, 'G': 43}

    for measure, chord, section in SONG:
        measure_start = (measure - 1) * 4
        root = bass_notes[chord]

        if section in ['verse', 'verse_stop']:
            # G pedal - sustained
            tick = beats_to_ticks(measure_start)
            note_events.append((tick, 'on', root, 95))
            note_events.append((tick + TICKS * 4 - 10, 'off', root))
        else:
            # Walking bass pattern
            tick = beats_to_ticks(measure_start)
            note_events.append((tick, 'on', root, 95))
            note_events.append((tick + TICKS * 2, 'off', root))
            # Octave on beat 3
            tick2 = beats_to_ticks(measure_start + 2)
            note_events.append((tick2, 'on', root + 12, 85))
            note_events.append((tick2 + TICKS * 2 - 10, 'off', root + 12))

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

def create_drum_track(start_measure):
    """Drums - enter after intro"""
    events = [(0, 'track_name', 'Drums')]

    KICK = 36
    SNARE = 38
    HI_HAT = 42

    note_events = []

    for measure, chord, section in SONG:
        if measure < start_measure:
            continue

        measure_start = (measure - 1) * 4

        # STOP bar - silence!
        if section == 'verse_stop':
            continue

        for beat in range(4):
            tick = beats_to_ticks(measure_start + beat)

            # Kick on 1 and 3
            if beat in [0, 2]:
                note_events.append((tick, 'on', KICK, 100))
                note_events.append((tick + TICKS // 4, 'off', KICK))

            # Snare on 2 and 4
            if beat in [1, 3]:
                note_events.append((tick, 'on', SNARE, 100))
                note_events.append((tick + TICKS // 4, 'off', SNARE))

            # Hi-hat 8ths
            for eighth in range(2):
                t = tick + eighth * TICKS // 2
                note_events.append((t, 'on', HI_HAT, 80))
                note_events.append((t + TICKS // 4, 'off', HI_HAT))

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

# === BUILD TRACKS ===

tempo_events = [
    (0, 'track_name', 'Getting Better'),
    (0, 'tempo', MICROSECONDS_PER_BEAT),
    (0, 'time_sig', (4, 2)),
    (0, 'end', None)
]
tempo_track = build_track(tempo_events)

chord_track = create_chord_track('Piano/Guitar', 0, 0)
chime_track = create_g_chime_track('G Chime', 0, 1)
bass_track = create_bass_track('Bass', 33, 2)
drum_track = create_drum_track(start_measure=3)  # Drums enter M3

# === WRITE FILE ===
output_path = '/Users/robert/Desktop/getting_better.mid'
write_midi_file(output_path, [tempo_track, chord_track, chime_track, bass_track, drum_track])

print(f"Created: {output_path}")
print(f"\nTotal measures: {TOTAL_MEASURES}")
print("\nStructure:")
print("  M1-4:    Intro (F-F-C-F + G chime)")
print("  M5-12:   Verse 1 (G pedal)")
print("  M13-20:  Refrain 1 (C-Dm-Em-F x2)")
print("  M21-28:  Verse 2 (G pedal)")
print("  M29-36:  Refrain 2")
print("  M37-46:  Bridge 1 (F-G vamp + C-Dm-Em-F)")
print("  M47-55:  Verse 3 (G pedal + STOP bar at M55)")
print("  M56-63:  Refrain 3")
print("  M64-73:  Bridge 2")
print("  M74-79:  Outro (F-G vamp + C fade)")
print("\nFeatures:")
print("  - G octave chime in intro/refrain/bridge (not verses)")
print("  - Drums enter M3")
print("  - STOP bar at M55 (verse 3 extra measure)")
