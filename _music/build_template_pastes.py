"""Generate 3 multi-section Hookpad paste-JSON .txt files:
  - choruses.txt — 10 chorus archetypes as 10 sections
  - verses.txt   — 10 verse archetypes
  - bridges.txt  — 10 bridge archetypes

Each section is labeled with its template (e.g. "8-44-AA").
Format follows chord-chart-visualizer.html (verified working).
"""
import os, json, hashlib

OUT_DIR = os.path.expanduser('~/Desktop/template_pastes')
LETTERS = {'A': 1, 'B': 5, 'C': 6, 'D': 4, 'E': 2, 'F': 3, 'G': 7}


def make_chord(root, beat, duration):
    return {
        'root': root, 'beat': beat, 'duration': duration, 'type': 5,
        'inversion': 0, 'applied': 0, 'adds': [], 'omits': [],
        'alterations': [], 'suspensions': [], 'substitutions': [],
        'pedal': None, 'alternate': '', 'borrowed': '',
        'isRest': False, 'recordingEndBeat': None,
    }


def make_note(sd, beat, duration):
    return {
        'sd': str(sd), 'beat': beat, 'isRest': False, 'octave': 0,
        'duration': duration, 'recordingEndBeat': None,
    }


def build_multi_section(sections_spec):
    """sections_spec entries: (label, letters)  OR  (label, letters, beats_per_chord)
    Default beats_per_chord = 4 (one chord per measure)."""
    bpb = 4
    chords, notes, section_events = [], [], []
    beat = 1
    for spec in sections_spec:
        if len(spec) == 2:
            label, letters = spec; bpc = bpb
        else:
            label, letters, bpc = spec
        seq = letters.replace(' ', '')
        section_events.append({'beat': beat, 'name': label})
        for L in seq:
            root = LETTERS[L]
            chords.append(make_chord(root, beat, bpc))
            notes.append(make_note(root, beat, bpc))
            beat += bpc
    end_beat = beat
    obj = {
        'version': 1,
        'chords': chords,
        'notes': notes,
        'keys': [{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
        'tempos': [{'beat': 1, 'bpm': 100, 'swingFactor': 0, 'swingBeat': 0.5}],
        'meters': [{'beat': 1, 'numBeats': bpb, 'beatUnit': 1}],
        'breaks': [],
        'sections': section_events,
        'endBeat': end_beat,
        'audioTracks': [],
    }
    compact = json.dumps(obj, separators=(',', ':'))
    obj['fp'] = hashlib.sha1(compact.encode('utf-8')).hexdigest()
    return obj


# 10 archetypes per section type. Each line: (label, per-measure letter pattern)
CHORUSES = [
    ('8-44-AA',         'ADBA ADBA'),
    ('8-44-AB',         'ADBA CDEA'),
    ('8-2222-ABAB',     'AB CD AB CD'),
    ('8-2222-AAAB',     'AB AB AB DA'),
    ('8-2222-AAAA',     'AB AB AB AB'),
    ('8-2222-AABA',     'AB AB DC AB'),
    ('8-2222-ABAC',     'AB CD AB EF'),
    ('12-444-AAB',      'ACDB ACDB DBAA'),
    ('16-4444-AABA',    'ACDB ACDB DBAA ACDB'),
    ('16-4444-AAAA',    'ACDB ACDB ACDB ACDB'),
    # 4 chords per 2-bar phrase (half-measure each), phrase repeats 4x
    ('8-2222-AAAA fast', 'ADCB ADCB ADCB ADCB', 2),
]

VERSES = [
    ('8-44-AA',         'ADBA ADBA'),
    ('8-44-AB',         'ADBA CDEA'),
    ('8-2222-ABAB',     'AB CD AB CD'),
    ('8-2222-AABA',     'AB AB DC AB'),
    ('8-2222-ABBC',     'AB CD CD EF'),
    ('10-55-AA',        'ADBCA ADBCA'),
    ('12-444-AAB',      'ACDB ACDB DBAA'),
    ('16-4444-AABC',    'ACDB ACDB BDAA EDBA'),
    ('16-4444-ABAC',    'ACDB CDAB ACDB EBAA'),
    ('16-4444-AABA',    'ACDB ACDB DBAA ACDB'),
]

BRIDGES = [
    ('8-2222-AAAB',     'AB AB AB DA'),
    ('8-2222-ABCB',     'DB AC EB AC'),
    ('8-44-AB',         'ADBA CDEA'),
    ('8-2222-ABCD',     'AB CD EF AC'),
    ('4-22-AB',         'AB CD'),
    ('4-22-AA',         'AB AB'),
    ('8-2222-ABAB',     'AB CD AB CD'),
    ('8-2222-AABA',     'AB AB DC AB'),
    ('12-444-ABC',      'ACDB CDEA EBAD'),
    ('16-4444-ABAB',    'ACDB DBAA ACDB DBAA'),
    # m1=m2, m3=m4, m5=m6, m7+m8 each unique
    ('8-AABBCCDE',      'AABBCCDE'),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    bundles = [
        ('choruses.txt', CHORUSES),
        ('verses.txt',   VERSES),
        ('bridges.txt',  BRIDGES),
    ]
    for fname, spec in bundles:
        obj = build_multi_section(spec)
        path = os.path.join(OUT_DIR, fname)
        with open(path, 'w') as f:
            json.dump(obj, f, separators=(',', ':'))
        total_chord_events = sum(len(s[1].replace(' ','')) for s in spec)
        print(f"  wrote {path}  ({len(spec)} sections, {total_chord_events} chord events, fp={obj['fp'][:8]}...)")
    summary = os.path.join(OUT_DIR, 'SUMMARY.txt')
    with open(summary, 'w') as f:
        f.write("3 Hookpad multi-section pastes — open .txt in TextEdit, Cmd+A, Cmd+C,\n")
        f.write("paste into an empty Hookpad project. Each archetype appears as its own labeled section.\n\n")
        for fname, spec in bundles:
            f.write(f"\n=== {fname} ({len(spec)} sections) ===\n")
            for s in spec:
                label, pattern = s[0], s[1]
                f.write(f"  {label:<20}  {pattern}\n")
    print(f"  wrote {summary}")


if __name__ == '__main__':
    main()
