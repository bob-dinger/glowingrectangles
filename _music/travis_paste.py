"""Travis-picking generator -> Hookpad paste (and MIDI).

A Travis pattern is a fixed sequence of STRINGS the right hand plucks; the left-hand chord
decides what note sits on each string. So you enter a progression + a string-pattern, and
this voices the pattern through every chord — you see the same shape produce different
pitches as the chord changes. The basic pattern here is the user's:
    thumb->A string, index->G, thumb->D, ring->B   (no pinch, so it stays monophonic)

  python travis_paste.py --key C --prog C G Am F
  python travis_paste.py --key C --prog C G Am F --pattern A G D B --midi
"""
import os, re, json, argparse
import mido

# open-position chord voicings: MIDI note per guitar string, low->high [E A D G B e], None=muted.
# standard tuning open strings: E2=40 A2=45 D3=50 G3=55 B3=59 e4=64
VOICING = {
    'C':  [None, 48, 52, 55, 60, 64],   # x32010
    'G':  [43, 47, 50, 55, 59, 67],     # 320003
    'D':  [None, None, 50, 57, 62, 66], # xx0232
    'A':  [None, 45, 52, 57, 61, 64],   # x02220
    'E':  [40, 47, 52, 56, 59, 64],     # 022100
    'Am': [None, 45, 52, 57, 60, 64],   # x02210
    'Em': [40, 47, 52, 55, 59, 64],     # 022000
    'Dm': [None, None, 50, 57, 62, 65], # xx0231
    'F':  [41, 48, 53, 57, 60, 65],     # 133211 barre
    'Fmaj7': [None, 48, 53, 57, 60, 64],# xx3210
}
STRING = {'E': 0, 'A': 1, 'D': 2, 'G': 3, 'B': 4, 'e': 5}   # name -> index low..high
PC = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
DEG_SEMI = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
SEMI_DEG = {0: ('1', ''), 2: ('2', ''), 4: ('3', ''), 5: ('4', ''), 7: ('5', ''), 9: ('6', ''), 11: ('7', ''),
            1: ('1', '#'), 3: ('3', 'b'), 6: ('4', '#'), 8: ('6', 'b'), 10: ('7', 'b')}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TPB = 480

def chord_root_deg(name, tonic_pc):
    """scale degree (1-7) of the chord root in the key, for the Hookpad chord object"""
    root = re.match(r'^([A-G][#b]?)', name).group(1)
    semi = (PC[root] - tonic_pc) % 12
    return {0: 1, 2: 2, 4: 3, 5: 4, 7: 5, 9: 6, 11: 7}.get(semi, 1)

def midi_to_sd(midi, tonic_pc):
    rel = midi - (60 + tonic_pc)
    octv = rel // 12
    sd, acc = SEMI_DEG[rel % 12]
    return acc + sd, octv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', default='C')
    ap.add_argument('--prog', nargs='+', default=['C', 'G', 'Am', 'F'])
    ap.add_argument('--pattern', nargs='+', default=['A', 'G', 'D', 'B'],
                    help='string pluck order, repeated to fill each bar')
    ap.add_argument('--bpm', type=float, default=110)
    ap.add_argument('--beats-per-chord', type=int, default=4)
    ap.add_argument('--midi', action='store_true')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    tonic = PC[a.key]
    step = a.beats_per_chord / len(a.pattern)          # eighths if pattern=4 over 4 beats -> 1 beat? see below
    # play the pattern as continuous eighth notes, repeating the cell across the bar
    per_bar = a.beats_per_chord * 2                     # eighth-note slots per chord
    cell = a.pattern
    notes, chords = [], []
    beat = 1.0
    print(f"key {a.key} · pattern {'-'.join(cell)} · {' '.join(a.prog)}\n")
    for ci, ch in enumerate(a.prog):
        voic = VOICING.get(ch)
        if not voic: print(f'  no voicing for {ch}, skipping'); continue
        chords.append({'root': chord_root_deg(ch, tonic), 'beat': beat, 'duration': a.beats_per_chord,
                       'type': 5, 'inversion': 0, 'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
                       'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': 0,
                       'borrowed': '', 'isRest': False, 'recordingEndBeat': None})
        row = []
        for k in range(per_bar):
            s = cell[k % len(cell)]
            midi = voic[STRING[s]]
            if midi is None:                            # muted string — hop to nearest sounding one
                for d in (1, -1, 2, -2, 3):
                    if voic[min(5, max(0, STRING[s] + d))] is not None:
                        midi = voic[min(5, max(0, STRING[s] + d))]; break
            sd, octv = midi_to_sd(midi, tonic)
            b = beat + k * 0.5
            notes.append({'sd': sd, 'octave': int(octv), 'beat': b, 'duration': 0.5,
                          'isRest': False, 'recordingEndBeat': None})
            row.append(f'{s}:{NAMES[midi % 12]}')
        print(f'  {ch:5} -> ' + '  '.join(row[:len(cell)]))
        beat += a.beats_per_chord
    end = beat
    paste = {'version': 1, 'chords': chords, 'notes': notes,
             'keys': [{'beat': 1, 'scale': 'major', 'tonic': tonic}],
             'tempos': [{'beat': 1, 'bpm': round(a.bpm), 'swingFactor': 0, 'swingBeat': 0.5}],
             'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}], 'breaks': [],
             'sections': [{'beat': 1, 'name': 'travis'}], 'endBeat': end - 1, 'audioTracks': []}
    base = a.out or os.path.expanduser(f'~/Desktop/travis_{a.key}_{"".join(a.prog)}')
    txt = base + '.txt'                                 # .txt so it opens as plain text to copy
    open(txt, 'w').write(json.dumps(paste, separators=(',', ':')))
    print(f'\nwrote {txt}  (paste into an empty Hookpad song)')

    if a.midi:
        mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(round(a.bpm))))
        ev = []
        for n in notes:
            m = 60 + tonic + (DEG_SEMI[int(re.sub(r'[b#]', '', n['sd']))] + n['sd'].count('#') - n['sd'].count('b')) + 12 * n['octave']
            s = round((n['beat'] - 1) * TPB); ev.append((s, 'on', m)); ev.append((s + round(n['duration'] * TPB), 'off', m))
        ev.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1)); last = 0
        for t, typ, m in ev:
            tr.append(mido.Message('note_on' if typ == 'on' else 'note_off', note=m, velocity=72 if typ == 'on' else 0, time=t - last)); last = t
        mid.save(base + '.mid'); print(f'wrote {base}.mid')

if __name__ == '__main__':
    main()
