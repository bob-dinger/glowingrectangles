"""Generate 10 random Hookpad paste-JSON 'songs' for study.

Each song:
  - random tempo from {75,90,105,120,135,150,165,180}
  - random key (major or minor)
  - random structure (intro -> verse -> ... -> outro), parts are 4/8/10/12/16 bars
  - named after an animal so you can remember it
  - chords: per-measure root progressions chosen from canonical archetypes per section type
  - melody: one whole-note placeholder per measure on the chord root

Writes .txt pastes to ~/Desktop/random_songs/ plus a SUMMARY.txt.
"""
import os, json, random, hashlib

OUT_DIR = os.path.expanduser('~/Desktop/random_songs')

TEMPOS = [75, 90, 105, 120, 135, 150, 165, 180]
SECTION_BARS = [4, 8, 10, 12, 16]
KEYS = ['C', 'G', 'D', 'A', 'E', 'F', 'Bb']

ANIMALS = [
    'aardvark', 'badger', 'cheetah', 'dingo', 'eel', 'falcon', 'gecko', 'heron',
    'ibis', 'jaguar', 'koala', 'lynx', 'manatee', 'narwhal', 'otter', 'panther',
    'quokka', 'raven', 'salamander', 'tapir', 'urchin', 'vulture', 'walrus',
    'yak', 'zebra', 'okapi', 'capybara', 'pangolin', 'meerkat', 'osprey',
]

# Section archetypes — list of (chord_root_pattern, options)
# Patterns are Roman-numeral degrees (1-7). We'll tile to fit the bar count.
PROGRESSIONS = {
    'intro': [
        [1, 4, 5, 1],
        [1, 5, 1, 5],
        [6, 4, 1, 5],
        [1, 1, 4, 5],
    ],
    'verse': [
        [1, 5, 6, 4],   # axis
        [1, 6, 4, 5],   # 50s
        [6, 4, 1, 5],   # axis variant
        [1, 4, 5, 1],
        [1, 5, 6, 3, 4, 1, 4, 5],   # pachelbel-ish 8-bar
    ],
    'pre-chorus': [
        [4, 5, 4, 5],
        [2, 5, 2, 5],
        [4, 5, 6, 5],
        [6, 4, 2, 5],
    ],
    'chorus': [
        [1, 5, 6, 4],
        [4, 1, 5, 6],
        [1, 4, 6, 5],
        [1, 5, 4, 5],
        [6, 4, 1, 5],
    ],
    'half-intro': [
        [1, 5, 1, 5],
        [1, 4, 1, 5],
    ],
    'bridge': [
        [6, 3, 4, 1],
        [4, 5, 6, 1],
        [2, 5, 1, 6],
        [6, 4, 5, 1],
    ],
    'outro': [
        [1, 5, 1, 1],
        [4, 5, 1, 1],
        [1, 4, 1, 1],
    ],
    'solo': [
        [1, 5, 6, 4],   # often verse progression
        [1, 4, 5, 1],
    ],
}

# Section sequences — full song structures
STRUCTURES = [
    # (label, section_type_list)
    ('Simple ABAB',
     ['intro', 'verse', 'chorus', 'verse', 'chorus', 'outro']),
    ('Standard pop',
     ['intro', 'verse', 'pre-chorus', 'chorus', 'verse', 'pre-chorus', 'chorus', 'bridge', 'chorus', 'outro']),
    ('Verse-heavy',
     ['intro', 'verse', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'verse', 'chorus', 'outro']),
    ('Ballad',
     ['intro', 'verse', 'chorus', 'verse', 'chorus', 'bridge', 'chorus', 'chorus', 'outro']),
    ('Half-intro mid',
     ['intro', 'verse', 'chorus', 'half-intro', 'verse', 'chorus', 'bridge', 'chorus', 'outro']),
    ('AABA',
     ['intro', 'verse', 'verse', 'bridge', 'verse', 'outro']),
    ('With solo',
     ['intro', 'verse', 'chorus', 'verse', 'chorus', 'solo', 'chorus', 'outro']),
    ('Pre-chorus light',
     ['intro', 'verse', 'pre-chorus', 'chorus', 'verse', 'chorus', 'outro']),
]


def section_bars_for(section_type):
    """Pick a sensible bar count for a section type."""
    if section_type in ('intro', 'half-intro', 'outro'):
        return random.choice([4, 8])
    if section_type == 'pre-chorus':
        return random.choice([4, 8])
    if section_type == 'bridge':
        return random.choice([8, 12, 16])
    # verse, chorus, solo
    return random.choice([8, 10, 12, 16])


def make_chord(root, beat, duration):
    return {
        'root': root, 'beat': beat, 'duration': duration, 'type': 5,
        'inversion': 0, 'applied': 0,
        'adds': [], 'omits': [], 'alterations': [], 'suspensions': [], 'substitutions': [],
        'pedal': None, 'alternate': '', 'borrowed': '',
        'isRest': False, 'recordingEndBeat': None,
    }


def make_note(sd, beat, duration, octave=0):
    return {
        'sd': str(sd), 'beat': beat, 'isRest': False, 'octave': octave,
        'duration': duration, 'recordingEndBeat': None,
    }


def build_section(section_type, bars, palette, beat_offset, bpb=4):
    """Return (chords, notes) for one section starting at beat_offset (1-indexed)."""
    chords, notes = [], []
    for measure_idx in range(bars):
        # Tile the palette across the section's bars
        root = palette[measure_idx % len(palette)]
        beat = beat_offset + measure_idx * bpb
        chords.append(make_chord(root, beat, bpb))
        # Placeholder whole-note melody on the chord root
        notes.append(make_note(root, beat, bpb, octave=0))
    return chords, notes


def build_song(animal, tempo, key_tonic, key_scale, structure_label, structure):
    chords, notes, sections = [], [], []
    beat = 1
    bpb = 4

    # Pre-decide bar count + chord palette per section TYPE so all instances match
    unique_types = list(dict.fromkeys(structure))   # preserves order, unique
    type_bars    = {t: section_bars_for(t) for t in unique_types}
    type_palette = {t: random.choice(PROGRESSIONS[t]) for t in unique_types}

    # Section-name disambiguation: track multiplicities
    sec_counts = {}
    for sec_type in structure:
        bars = type_bars[sec_type]
        sec_counts[sec_type] = sec_counts.get(sec_type, 0) + 1
        if sec_counts[sec_type] == 1:
            sec_name = sec_type
        else:
            sec_name = f"{sec_type} {sec_counts[sec_type]}"
        sections.append({'beat': beat, 'name': sec_name})
        c, n = build_section(sec_type, bars, type_palette[sec_type], beat, bpb)
        chords.extend(c)
        notes.extend(n)
        beat += bars * bpb
    end_beat = beat

    obj = {
        'version': 1,
        'chords': chords,
        'notes': notes,
        'keys':   [{'beat': 1, 'scale': key_scale, 'tonic': key_tonic}],
        'tempos': [{'beat': 1, 'bpm': tempo, 'swingFactor': 0, 'swingBeat': 0.5}],
        'meters': [{'beat': 1, 'numBeats': bpb, 'beatUnit': 1}],
        'breaks': [],
        'sections': sections,
        'endBeat': end_beat,
        'audioTracks': [],
    }
    compact = json.dumps(obj, separators=(',', ':'))
    obj['fp'] = hashlib.sha1(compact.encode('utf-8')).hexdigest()
    return obj


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    picked = random.sample(ANIMALS, 10)
    summary_lines = ['10 random Hookpad paste-JSON songs.', '', 'How to use:', '  1. Open one of the .txt files in TextEdit', '  2. Cmd+A, Cmd+C', '  3. Paste into an empty Hookpad project', '  4. Save in Hookpad to remember it', '']
    for animal in picked:
        tempo = random.choice(TEMPOS)
        key_tonic = random.choice(KEYS)
        key_scale = random.choices(['major', 'minor'], weights=[3, 1])[0]
        struct_label, structure = random.choice(STRUCTURES)
        obj = build_song(animal, tempo, key_tonic, key_scale, struct_label, structure)
        # File
        fname = f"{animal}.txt"
        path = os.path.join(OUT_DIR, fname)
        with open(path, 'w') as f:
            json.dump(obj, f, separators=(',', ':'))
        total_bars = (obj['endBeat'] - 1) // 4
        summary_lines.append(f"  {animal:<12}  {tempo:>3} BPM · {key_tonic} {key_scale} · {struct_label}")
        summary_lines.append(f"               sections: {' → '.join(s['name'] for s in obj['sections'])}")
        summary_lines.append(f"               total: {total_bars} bars")
        summary_lines.append('')
        print(f"  wrote {path}  ({tempo} BPM, {key_tonic} {key_scale}, {total_bars} bars)")
    summary_path = os.path.join(OUT_DIR, 'SUMMARY.txt')
    with open(summary_path, 'w') as f:
        f.write('\n'.join(summary_lines))
    print(f"\nwrote {summary_path}")


if __name__ == '__main__':
    main()
