"""Extract the vocal/melody line from a MIDI and emit a melody-only Hookpad
paste-JSON .txt (notes + key + meter + one section), for import & eyeballing.

Scores tracks by name affinity + monophony + vocal range, reduces to a single
top-voice monophonic line, quantizes to a 1/4-beat grid, and converts pitches to
Hookpad scale-degree/octave in a KNOWN key.

Usage: python3 midi_melody_extract.py <midi> <tonic> [major|minor] [out.txt]
"""
import os, sys, json, hashlib
import mido
from collections import Counter, defaultdict
from midi_to_hookpad_paste import extract_notes, melody_sd_octave

PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
      'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
DRUM_CH = 9

def track_notes(track, tpb):
    return extract_notes(track, tpb)

def monophony_ratio(notes):
    """Fraction of notes NOT overlapped by a simultaneous note (higher = more monophonic)."""
    if len(notes) < 2: return 1.0
    ns = sorted(notes, key=lambda n: n['beat'])
    overlaps = 0
    for i, n in enumerate(ns[:-1]):
        if ns[i+1]['beat'] < n['beat'] + n['duration'] - 1e-6:
            overlaps += 1
    return 1 - overlaps / len(ns)

def score_track(track, tpb):
    name = ' '.join(m.name for m in track if m.type == 'track_name').lower()
    chans = set(m.channel for m in track if hasattr(m, 'channel'))
    if DRUM_CH in chans:
        return -1, None
    notes = track_notes(track, tpb)
    if len(notes) < 12:
        return -1, None
    pitches = [n['pitch'] for n in notes]
    median = sorted(pitches)[len(pitches)//2]
    mono = monophony_ratio(notes)
    s = 0.0
    for kw, w in [('vocal', 6), ('melody', 6), ('lead', 4), ('voice', 5), ('sing', 4)]:
        if kw in name: s += w
    if 'backup' in name or 'backing' in name or 'harmon' in name: s -= 4
    if 'bass' in name or 'guitar' in name or 'piano' in name or 'string' in name: s -= 2
    s += mono * 4                                   # prefer monophonic
    s += 3 if 55 <= median <= 79 else -2            # vocal register (G3..G5)
    return s, notes

def top_voice(notes):
    """Reduce to monophonic: at each onset keep the highest pitch; drop notes that
    start while a higher note is still sounding."""
    ns = sorted(notes, key=lambda n: (round(n['beat']*4), -n['pitch']))
    out = []
    for n in ns:
        if out and abs(out[-1]['beat'] - n['beat']) < 0.125:
            continue                                 # same onset, lower pitch -> skip
        # trim previous note so it doesn't overlap this onset
        if out and out[-1]['beat'] + out[-1]['duration'] > n['beat']:
            out[-1]['duration'] = max(0.25, n['beat'] - out[-1]['beat'])
        out.append(dict(n))
    return out

def q(x, grid=0.25):
    v = round(x / grid) * grid
    return int(v) if v == int(v) else v

def octave_of(pitch, tonic_pc):
    """Hookpad octave = floor distance from the tonic placed nearest middle C.
    Tonic-relative (not C-relative) so notes of one register share an octave."""
    tonic0 = 60 + tonic_pc
    while tonic0 - 60 > 6: tonic0 -= 12
    while 60 - tonic0 > 6: tonic0 += 12
    return (pitch - tonic0) // 12

def build(midi_path, tonic, scale='major', out_path=None, quiet=False):
    mid = mido.MidiFile(midi_path)
    tpb = mid.ticks_per_beat
    scored = [(score_track(tr, tpb)) for tr in mid.tracks]
    best = max(range(len(scored)), key=lambda i: scored[i][0])
    s, notes = scored[best]
    if not notes:
        print('no melody track found'); return None
    name = ' '.join(m.name for m in mid.tracks[best] if m.type == 'track_name')
    mono = top_voice(notes)
    tonic_pc = PC[tonic]

    hp_notes, min_beat = [], min(n['beat'] for n in mono)
    for n in mono:
        beat = q(n['beat'] - min_beat) + 1           # shift so melody starts at beat 1
        dur = max(0.25, q(n['duration']))
        sd, _ = melody_sd_octave(n['pitch'], tonic_pc)
        octv = octave_of(n['pitch'], tonic_pc)
        hp_notes.append({'sd': sd, 'beat': beat, 'isRest': False,
                         'octave': octv, 'duration': dur, 'recordingEndBeat': None})
    end = max(n['beat'] + n['duration'] for n in hp_notes)
    end = int(q(end, 4)) + 4

    obj = {'version': 1, 'chords': [], 'notes': hp_notes,
           'keys': [{'beat': 1, 'scale': scale, 'tonic': tonic}],
           'tempos': [{'beat': 1, 'bpm': 120, 'swingFactor': 0, 'swingBeat': 0.5}],
           'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
           'breaks': [], 'sections': [{'beat': 1, 'name': 'melody'}],
           'endBeat': end, 'audioTracks': []}
    obj['fp'] = hashlib.sha1(json.dumps(obj, separators=(',', ':')).encode()).hexdigest()

    if out_path:
        json.dump(obj, open(out_path, 'w'), separators=(',', ':'))
    hist = Counter(n['sd'] for n in hp_notes)
    named = any(kw in name.lower() for kw in ('vocal', 'melody', 'lead', 'voice', 'sing'))
    meta = {'track': name, 'score': round(s, 1), 'mono': round(monophony_ratio(notes), 2),
            'n_notes': len(hp_notes), 'endBeat': end, 'named_melody': named,
            'octaves': dict(sorted(Counter(n['octave'] for n in hp_notes).items())),
            'hist': dict(sorted(hist.items()))}
    if not quiet:
        print(f"track: {name!r}  score={s:.1f}  mono={meta['mono']:.0%}  named={named}")
        print(f"notes: {len(notes)} raw -> {len(hp_notes)}   endBeat={end}")
        print("scale-degree histogram:", meta['hist'])
    return obj, meta

if __name__ == '__main__':
    midi = sys.argv[1]; tonic = sys.argv[2]
    scale = sys.argv[3] if len(sys.argv) > 3 else 'major'
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.expanduser(
        '~/Desktop/pollack_pastes/_melody_' +
        os.path.basename(midi).rsplit('.', 1)[0] + '.txt')
    build(midi, tonic, scale, out)
    print('wrote', out)
