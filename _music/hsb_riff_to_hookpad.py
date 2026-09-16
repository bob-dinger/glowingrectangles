"""Extract Heart-Shaped Box opening riff (Guitar 1, intro m1-4) from the GP4
and emit a Hookpad paste-JSON. Monophonic reduction: top note of each beat.
Key: E major (relative major of the riff's C#-minor center)."""
import json, guitarpro

GP = '/Users/robert/Desktop/6-23-26/midi_files_gp5/nirvana_heart-shaped-box.gp4'
OUT = '/Users/robert/Desktop/hsb_opening_riff_hookpad.txt'
TONIC_MIDI = 64            # E4 = degree 1, octave 0
BARS = 4                   # intro before vocals (m1-4)
BEATS_PER_BAR = 4

# semitones-above-tonic -> (scale-degree string) in a major key
DEG = {0:'1', 2:'2', 4:'3', 5:'4', 7:'5', 9:'6', 11:'7',
       1:'b2', 3:'b3', 6:'b5', 8:'b6', 10:'b7'}

def to_sd_octave(pitch):
    rel = pitch - TONIC_MIDI
    octave = rel // 12
    semi = rel - octave * 12
    return DEG[semi], octave

def dur_beats(b):
    d = 4.0 / b.duration.value
    if b.duration.isDotted: d *= 1.5
    return d

g = guitarpro.parse(GP)
gtr = g.tracks[1]                      # Guitar 1 (Kurt Cobain)
strings = [s.value for s in gtr.strings]

notes = []
for mi in range(BARS):
    bar_start = 1 + mi * BEATS_PER_BAR
    pos = 0.0
    for v in gtr.measures[mi].voices:
        for b in v.beats:
            dur = dur_beats(b)
            beat = round(bar_start + pos, 4)
            if b.notes:
                top = max(strings[n.string-1] + n.value for n in b.notes)  # melodic top voice
                sd, octv = to_sd_octave(top)
                notes.append({'sd': sd, 'octave': octv, 'beat': beat,
                              'duration': dur, 'isRest': False, 'recordingEndBeat': None})
            else:
                notes.append({'sd': '1', 'octave': 0, 'beat': beat,
                              'duration': dur, 'isRest': True, 'recordingEndBeat': None})
            pos += dur
        break                          # first voice only

song = {
    'notes': notes,
    'chords': [],
    'keys':   [{'beat': 1, 'scale': 'major', 'tonic': 'E'}],
    'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
    'tempos': [{'beat': 1, 'bpm': g.tempo, 'swingFactor': 0, 'swingBeat': 0.5}],
    'sections': [{'name': 'intro riff', 'beat': 1}],
    'endBeat': 1 + BARS * BEATS_PER_BAR,
    'audioTracks': [],
    'version': 1,                      # bypass fp validation
}

with open(OUT, 'w') as f:
    json.dump(song, f, separators=(',', ':'))

# human-readable summary
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
print(f"tempo={g.tempo}  key=E major  notes={len(notes)}  bars={BARS}")
for mi in range(BARS):
    row=[n for n in notes if 1+mi*4 <= n['beat'] < 1+(mi+1)*4]
    disp=[f"{n['sd']}^{n['octave']}({n['duration']})" for n in row]
    print(f"  bar{mi+1}: "+"  ".join(disp))
print("wrote", OUT)
