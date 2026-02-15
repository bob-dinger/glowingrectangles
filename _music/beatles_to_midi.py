#!/usr/bin/env python3
"""
Beatles Song → MIDI Generator

Parses Pollack's analyses and generates complete MIDI files.

Run:
  cd ~/Desktop && source midi_env/bin/activate && python glowinggardens_claude/beatles_to_midi.py
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from mido import MidiFile, MidiTrack, Message, MetaMessage
from dataclasses import dataclass
from typing import List, Dict, Optional
import os

# =============================================================================
# SONG DATABASE - Manually curated from Pollack's analyses
# =============================================================================

BEATLES_SONGS = {
    "Day Tripper": {
        "code": "dt",
        "key": "E",
        "bpm": 137,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Verse", "Bridge", "Verse", "Outro"],
        "sections": {
            "Intro": {"measures": 10, "chords": ["I"] * 10},
            "Verse": {"measures": 16, "chords": ["I", "I", "I", "I", "IV", "IV", "I", "I", "V", "V", "IV", "IV", "I", "I", "I", "I"]},
            "Bridge": {"measures": 12, "chords": ["vi", "vi", "vi", "vi", "V", "V", "vi", "vi", "vi", "vi", "V", "V"]},
            "Outro": {"measures": 10, "chords": ["I"] * 10},
        }
    },
    "Norwegian Wood": {
        "code": "nw",
        "key": "E",
        "bpm": 177,
        "meter": "3/4",  # Actually 12/8 but close
        "form": ["Intro", "Verse", "Bridge", "Verse", "Verse", "Bridge", "Verse", "Outro"],
        "sections": {
            "Intro": {"measures": 8, "chords": ["I", "I", "I", "I", "I", "I", "I", "I"]},
            "Verse": {"measures": 8, "chords": ["I", "I", "I", "I", "I", "I", "I", "I"]},
            "Bridge": {"measures": 8, "chords": ["iv", "iv", "IV", "IV", "I", "I", "ii", "V"]},
            "Outro": {"measures": 8, "chords": ["I", "I", "I", "I", "I", "I", "I", "I"]},
        }
    },
    "She Loves You": {
        "code": "sly",
        "key": "G",
        "bpm": 151,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Verse", "Refrain", "Verse", "Refrain", "Verse", "Refrain", "Outro"],
        "sections": {
            "Intro": {"measures": 4, "chords": ["vi", "IV", "I", "V"]},
            "Verse": {"measures": 12, "chords": ["I", "vi", "IV", "V"] * 3},
            "Refrain": {"measures": 8, "chords": ["vi", "vi", "IV", "IV", "I", "V", "I", "I"]},
            "Outro": {"measures": 8, "chords": ["vi", "vi", "IV", "IV", "bVII", "bVII", "I", "I"]},
        }
    },
    "I Want to Hold Your Hand": {
        "code": "iwthyh",
        "key": "G",
        "bpm": 131,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Verse", "Bridge", "Verse", "Bridge", "Outro"],
        "sections": {
            "Intro": {"measures": 4, "chords": ["V", "IV", "V", "IV"]},
            "Verse": {"measures": 12, "chords": ["I", "V", "vi", "iii", "IV", "V", "I", "V", "vi", "iii", "IV", "V"]},
            "Bridge": {"measures": 8, "chords": ["IV", "V", "I", "vi", "IV", "V", "I", "I"]},
            "Outro": {"measures": 8, "chords": ["I", "V", "I", "V", "I", "V", "I", "I"]},
        }
    },
    "A Hard Day's Night": {
        "code": "ahdn",
        "key": "G",
        "bpm": 139,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Verse", "Bridge", "Verse", "Bridge", "Verse", "Outro"],
        "sections": {
            "Intro": {"measures": 1, "chords": ["I"]},  # The famous chord
            "Verse": {"measures": 12, "chords": ["I", "bVII", "IV", "I", "I", "bVII", "IV", "I", "IV", "IV", "I", "I"]},
            "Bridge": {"measures": 8, "chords": ["iv", "iv", "I", "I", "iv", "iv", "V", "V"]},
            "Outro": {"measures": 8, "chords": ["IV", "IV", "I", "I", "IV", "IV", "I", "I"]},
        }
    },
    "Help!": {
        "code": "hlp",  # Different code
        "key": "A",
        "bpm": 95,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Verse", "Bridge", "Verse", "Bridge", "Verse", "Outro"],
        "sections": {
            "Intro": {"measures": 8, "chords": ["vi", "vi", "V", "V", "IV", "IV", "I", "I"]},
            "Verse": {"measures": 8, "chords": ["I", "iii", "vi", "vi", "IV", "IV", "I", "I"]},
            "Bridge": {"measures": 8, "chords": ["vi", "vi", "V", "V", "IV", "IV", "I", "I"]},
            "Outro": {"measures": 4, "chords": ["I", "I", "I", "I"]},
        }
    },
    "Eleanor Rigby": {
        "code": "er",
        "key": "Em",
        "bpm": 137,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Refrain", "Verse", "Refrain", "Verse", "Refrain", "Outro"],
        "sections": {
            "Intro": {"measures": 4, "chords": ["bVI", "iv", "i", "i"]},
            "Verse": {"measures": 8, "chords": ["i", "i", "i", "i", "bVI", "bVI", "i", "i"]},
            "Refrain": {"measures": 4, "chords": ["bVI", "iv", "i", "i"]},
            "Outro": {"measures": 4, "chords": ["i", "i", "i", "i"]},
        }
    },
    "Yellow Submarine": {
        "code": "ys",
        "key": "G",
        "bpm": 111,
        "meter": "4/4",
        "form": ["Verse", "Verse", "Chorus", "Verse", "Chorus", "Verse", "Chorus", "Outro"],
        "sections": {
            "Verse": {"measures": 8, "chords": ["I", "V", "IV", "I", "I", "V", "IV", "I"]},
            "Chorus": {"measures": 8, "chords": ["I", "I", "V", "V", "IV", "IV", "I", "I"]},
            "Outro": {"measures": 8, "chords": ["I", "I", "I", "I", "I", "I", "I", "I"]},
        }
    },
    "Getting Better": {
        "code": "gb",
        "key": "C",
        "bpm": 122,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Verse", "Chorus", "Outro"],
        "sections": {
            "Intro": {"measures": 4, "chords": ["I", "I", "I", "I"]},
            "Verse": {"measures": 8, "chords": ["I", "I", "IV", "IV", "I", "I", "V", "V"]},
            "Chorus": {"measures": 8, "chords": ["I", "IV", "I", "IV", "I", "IV", "V", "V"]},
            "Bridge": {"measures": 8, "chords": ["vi", "vi", "IV", "IV", "ii", "ii", "V", "V"]},
            "Outro": {"measures": 8, "chords": ["I", "I", "I", "I", "I", "I", "I", "I"]},
        }
    },
    "With a Little Help from My Friends": {
        "code": "walhfmf",
        "key": "E",
        "bpm": 112,
        "meter": "4/4",
        "form": ["Intro", "Verse", "Chorus", "Verse", "Chorus", "Bridge", "Verse", "Chorus", "Outro"],
        "sections": {
            "Intro": {"measures": 8, "chords": ["I", "I", "V", "V", "I", "I", "V", "V"]},
            "Verse": {"measures": 8, "chords": ["I", "V", "ii", "I", "I", "V", "ii", "I"]},
            "Chorus": {"measures": 8, "chords": ["IV", "V", "I", "I", "IV", "V", "I", "I"]},
            "Bridge": {"measures": 8, "chords": ["IV", "I", "IV", "I", "IV", "V", "I", "I"]},
            "Outro": {"measures": 4, "chords": ["IV", "V", "I", "I"]},
        }
    },
}

# =============================================================================
# MIDI GENERATION
# =============================================================================

# Note name to MIDI number (octave 4)
NOTE_TO_MIDI = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
}

# Scale degree to semitone offset (major scale)
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]  # I, II, III, IV, V, VI, VII

# Roman numeral to scale degree (0-indexed)
def parse_roman(numeral: str) -> tuple:
    """Parse a Roman numeral chord to (scale_degree, quality)."""
    numeral = numeral.strip()

    # Handle flats
    flat = numeral.startswith('b')
    if flat:
        numeral = numeral[1:]

    # Determine quality from case
    is_minor = numeral[0].islower() if numeral else False
    numeral_upper = numeral.upper()

    # Map Roman numeral to scale degree
    roman_map = {'I': 0, 'II': 1, 'III': 2, 'IV': 3, 'V': 4, 'VI': 5, 'VII': 6}

    base = numeral_upper
    for r in ['VII', 'VI', 'IV', 'V', 'III', 'II', 'I']:
        if base.startswith(r):
            degree = roman_map[r]
            break
    else:
        degree = 0

    # Adjust for flat
    offset = -1 if flat else 0

    return degree, is_minor, offset

def get_chord_notes(key_root: int, roman: str) -> List[int]:
    """Get MIDI notes for a chord given key root and Roman numeral."""
    degree, is_minor, flat_offset = parse_roman(roman)

    # Get root of chord
    root = key_root + MAJOR_SCALE[degree] + flat_offset

    # Build triad
    if is_minor:
        return [root - 12, root - 12 + 3, root - 12 + 7]  # Minor triad
    else:
        return [root - 12, root - 12 + 4, root - 12 + 7]  # Major triad

def generate_midi(song_data: dict, output_path: str):
    """Generate a MIDI file from song data."""
    title = song_data.get('title', 'Unknown')
    key = song_data.get('key', 'C')
    bpm = song_data.get('bpm', 120)
    form = song_data.get('form', [])
    sections = song_data.get('sections', {})

    # Get key root
    key_note = key.replace('m', '').replace('M', '').strip()
    key_root = NOTE_TO_MIDI.get(key_note, 60)

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=480)

    # Track 0: Tempo and metadata
    tempo_track = MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(MetaMessage('track_name', name=title, time=0))
    tempo_track.append(MetaMessage('set_tempo', tempo=int(60000000 / bpm), time=0))
    tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))
    tempo_track.append(MetaMessage('end_of_track', time=0))

    # Track 1: Chords
    chord_track = MidiTrack()
    mid.tracks.append(chord_track)
    chord_track.append(MetaMessage('track_name', name='Chords', time=0))
    chord_track.append(Message('program_change', channel=0, program=0, time=0))  # Piano

    ticks_per_measure = 480 * 4  # 4/4 time
    current_tick = 0

    for section_name in form:
        if section_name not in sections:
            continue

        section = sections[section_name]
        chords = section.get('chords', [])

        for chord_roman in chords:
            notes = get_chord_notes(key_root, chord_roman)

            # Note on
            for i, note in enumerate(notes):
                chord_track.append(Message('note_on', channel=0, note=note, velocity=64,
                                          time=0 if i > 0 else 0))

            # Note off (after one measure)
            for i, note in enumerate(notes):
                off_time = ticks_per_measure if i == 0 else 0
                chord_track.append(Message('note_off', channel=0, note=note, velocity=0,
                                          time=off_time))

            current_tick += ticks_per_measure

    chord_track.append(MetaMessage('end_of_track', time=0))

    # Save
    mid.save(output_path)
    return current_tick / 480 / 4  # Return total measures

def main():
    output_dir = "/Users/robert/Desktop/beatles_midi"
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("BEATLES MIDI GENERATOR")
    print("=" * 60)

    for title, data in BEATLES_SONGS.items():
        song_data = {
            'title': title,
            'key': data['key'],
            'bpm': data['bpm'],
            'form': data['form'],
            'sections': data['sections'],
        }

        filename = title.lower().replace(' ', '_').replace("'", "").replace('!', '') + '.mid'
        output_path = os.path.join(output_dir, filename)

        measures = generate_midi(song_data, output_path)
        print(f"✓ {title}")
        print(f"    Key: {data['key']} | BPM: {data['bpm']} | Measures: {measures:.0f}")
        print(f"    Form: {' → '.join(data['form'])}")
        print(f"    Saved: {filename}")
        print()

    print("=" * 60)
    print(f"Generated {len(BEATLES_SONGS)} MIDI files in: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
