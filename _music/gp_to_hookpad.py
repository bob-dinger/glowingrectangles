"""GP → Hookpad paste exporter.

End-to-end: takes a Guitar Pro file, extracts sections+chords+melody,
converts to Hookpad paste-JSON format with `version: 1` to bypass fp check.

Usage:
    python gp_to_hookpad.py <file.gp[3-5]> [output.json]
"""
import os, sys, json

from gp_extract import extract
from chord_to_hookpad import chord_to_hookpad

# Major scale interval offsets (semitones) for degrees 1-7
_MAJOR_INT = [0, 2, 4, 5, 7, 9, 11]
# Note names per pitch class (sharp preference for sd '#1' style; we pick conventional names)
_NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def pitch_to_sd_octave(midi_pitch, key_root):
    """Convert a MIDI pitch to Hookpad's (scale-degree-string, octave) relative to song key.

    Octave is measured from middle C (60). Scale degree is 1-7, prefixed with # or b for chromatics.
    """
    rel = midi_pitch - 60 - key_root  # semitones from tonic in middle-C octave
    octave = rel // 12
    semi_in_oct = rel - octave * 12
    for d, iv in enumerate(_MAJOR_INT, 1):
        if iv == semi_in_oct: return str(d), octave
    for d, iv in enumerate(_MAJOR_INT, 1):
        if (iv + 1) % 12 == semi_in_oct: return f'#{d}', octave
    for d, iv in enumerate(_MAJOR_INT, 1):
        if (iv - 1) % 12 == semi_in_oct: return f'b{d}', octave
    return None, octave


def _measure_start_beats(measure_ts):
    """Given per-measure time signatures [(num,den), ...], return list of measure-start beats
    (1-indexed, quarter-note units). starts[i] = beat where measure i+1 begins."""
    starts = [1.0]
    cur = 1.0
    for num, den in measure_ts:
        cur += num * (4.0 / den)
        starts.append(cur)
    return starts


def gp_to_hookpad_paste(path):
    """Build a Hookpad-paste-compatible song dict from a GP file."""
    data = extract(path)
    key_root, key_mode = data['key']['root'], data['key']['mode']
    bpm = data['time_sig'][0] * (4.0 / data['time_sig'][1])   # beats/measure in quarter units

    starts = _measure_start_beats(data['measure_ts'])

    # Chords — type/duration must be int, matching verified working format from chord-chart-visualizer.html
    def to_int_type(t):
        if t == '7': return 7
        if t == '5': return 5
        if isinstance(t, int): return t
        return 5   # default triad

    hp_chords = []
    for c in data['chord_progression']:
        enc = chord_to_hookpad(c['name'], key_root, key_mode)
        if not enc or 'root' not in enc: continue
        mstart = starts[c['measure'] - 1]
        dur = c['duration_beats']
        dur_val = int(dur) if dur == int(dur) else round(dur, 3)
        chord_dict = {
            'root': enc['root'],
            'beat': round(mstart + c['beat'], 3),
            'duration': dur_val,
            'type': to_int_type(enc.get('type', '')),
            'inversion': 0,
            'applied': enc.get('applied', 0),
            'adds': enc.get('adds', []),
            'omits': [],
            'alterations': enc.get('alterations', []),
            'suspensions': enc.get('suspensions', []),
            'substitutions': [],
            'pedal': enc.get('pedal'),
            'alternate': '',
            'borrowed': enc.get('borrowed', ''),
            'isRest': False,
            'recordingEndBeat': None,
        }
        hp_chords.append(chord_dict)

    # Pad chord durations to fill gaps to next chord (GP only marks chord onsets)
    hp_chords.sort(key=lambda c: c['beat'])
    for i in range(len(hp_chords) - 1):
        gap = hp_chords[i+1]['beat'] - hp_chords[i]['beat']
        if hp_chords[i]['duration'] < gap:
            g = round(gap, 3)
            hp_chords[i]['duration'] = int(g) if g == int(g) else g

    # Melody notes
    hp_notes = []
    for n in data['melody']:
        sd, octave = pitch_to_sd_octave(n['pitch'], key_root)
        if sd is None: continue
        mstart = starts[n['measure'] - 1]
        hp_notes.append({
            'sd': sd, 'octave': int(octave),
            'beat': round(mstart + n['beat'], 3),
            'duration': round(n['duration_beats'], 3),
            'isRest': False, 'recordingEndBeat': None,
        })

    # Sections
    hp_sections = [{'beat': int(starts[s['measure'] - 1]), 'name': s['name']} for s in data['sections']]

    end_beat = int(starts[-1])
    tonic_name = _NOTE_NAMES[key_root]

    return {
        'version': 1,
        'chords': hp_chords,
        'notes': hp_notes,
        'keys': [{'beat': 1, 'scale': key_mode, 'tonic': tonic_name}],
        'tempos': [{'beat': 1, 'bpm': data['tempo'], 'swingFactor': 0, 'swingBeat': 0.5}],
        'meters': [{'beat': 1, 'numBeats': int(bpm), 'beatUnit': 1}],
        'breaks': [],
        'sections': hp_sections,
        'endBeat': end_beat,
        'audioTracks': [],
    }


def main():
    if len(sys.argv) < 2:
        print('usage: gp_to_hookpad.py <file.gp[3-5]> [output.json]'); sys.exit(1)
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(path)[0] + '_paste.txt'
    paste = gp_to_hookpad_paste(path)
    open(out, 'w').write(json.dumps(paste, separators=(',', ':')))
    # Summary
    print(f'  title: {os.path.basename(path)}')
    print(f'  endBeat: {paste["endBeat"]}, key: {paste["keys"][0]["tonic"]} {paste["keys"][0]["scale"]}')
    print(f'  meter: {paste["meters"][0]["numBeats"]}/4, tempo: {paste["tempos"][0]["bpm"]}')
    print(f'  chords: {len(paste["chords"])}, notes: {len(paste["notes"])}, sections: {len(paste["sections"])}')
    print(f'  sections:')
    for s in paste['sections']: print(f'    beat {s["beat"]:>4}: {s["name"]}')
    print(f'  first 10 chords:')
    for c in paste['chords'][:10]:
        extras = []
        if c['borrowed']: extras.append(f"borrowed={c['borrowed']}")
        if c['type']: extras.append(f"type={c['type']}")
        if c['adds']: extras.append(f"adds={c['adds']}")
        if c['suspensions']: extras.append(f"sus={c['suspensions']}")
        if c['alterations']: extras.append(f"alt={c['alterations']}")
        if c['pedal']: extras.append(f"pedal={c['pedal']}")
        extra_str = ' '.join(extras)
        print(f'    beat {c["beat"]:>5}: root={c["root"]} dur={c["duration"]:>4} {extra_str}')
    print(f'\nwrote → {out}')


if __name__ == '__main__':
    main()
