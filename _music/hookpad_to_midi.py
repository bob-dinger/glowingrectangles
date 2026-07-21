"""Hookpad note JSON -> a MIDI file you can drag into a DAW.

Hookpad stores melody as scale-degree + octave; this resolves each to an absolute pitch
in the given key and writes a standard MIDI file. Fingerpicking transcriptions come out as
one interleaved line (Hookpad melody is monophonic) — with --split, the low notes (thumb)
and the rest (fingers) are written to two separate MIDI tracks so the boom-chick is visible.

  python hookpad_to_midi.py notes.txt --tonic D --bpm 140 -o out.mid
  python hookpad_to_midi.py notes.txt --tonic D --split        # thumb / fingers on 2 tracks
"""
import os, re, json, argparse
import mido

PC = {'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5, 'F#': 6, 'GB': 6,
      'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11}
DEG = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}          # major-scale semitones
TPB = 480

def deg_semis(sd):
    m = re.match(r'^([b#]*)(\d)$', str(sd))
    if not m: return None
    acc = sum(-1 if c == 'b' else 1 for c in m.group(1))
    d = int(m.group(2))
    return DEG.get(d, 0) + acc if d in DEG else None

def midi_of(n, tonic_pc, minor=False):
    """octave 0 = the middle-C octave (MIDI 60-71), matching Hookpad's convention"""
    sem = deg_semis(n.get('sd'))
    if sem is None: return None
    if minor: sem = (sem + 3)  # relative-major convention: degrees are vs the relative major
    return 60 + tonic_pc + sem + 12 * int(n.get('octave', 0))

def build_track(events, name):
    tr = mido.MidiTrack(); tr.append(mido.MetaMessage('track_name', name=name))
    events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))
    last = 0
    for tick, typ, pitch in events:
        tr.append(mido.Message('note_on' if typ == 'on' else 'note_off',
                               note=pitch, velocity=72 if typ == 'on' else 0, time=tick - last))
        last = tick
    return tr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--tonic', default='C')
    ap.add_argument('--minor', action='store_true')
    ap.add_argument('--bpm', type=float, default=120)
    ap.add_argument('--split', action='store_true', help='thumb (low) / fingers on separate tracks')
    ap.add_argument('--bass-below', type=int, default=52, help='MIDI note; at/below = thumb voice')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()

    data = json.load(open(a.file))
    notes = data.get('notes') if isinstance(data, dict) else data
    tonic_pc = PC[a.tonic.upper()]
    resolved = []
    for n in notes:
        if n.get('isRest'): continue
        p = midi_of(n, tonic_pc, a.minor)
        if p is None: continue
        resolved.append((float(n.get('beat', 1)), float(n.get('duration', 1)), p))
    if not resolved: print('no notes'); return
    base = min(b for b, _, _ in resolved)          # shift so it starts at time 0

    def evs(rows):
        e = []
        for b, d, p in rows:
            s = round((b - base) * TPB); e.append((s, 'on', p)); e.append((s + round(d * TPB), 'off', p))
        return e

    mid = mido.MidiFile(ticks_per_beat=TPB)
    tempo = mido.MidiTrack(); tempo.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(round(a.bpm))))
    mid.tracks.append(tempo)
    if a.split:
        thumb = [r for r in resolved if r[2] <= a.bass_below]
        fingers = [r for r in resolved if r[2] > a.bass_below]
        mid.tracks.append(build_track(evs(thumb), 'thumb'))
        mid.tracks.append(build_track(evs(fingers), 'fingers'))
        print(f'thumb {len(thumb)} notes / fingers {len(fingers)} notes')
    else:
        mid.tracks.append(build_track(evs(resolved), 'melody'))

    out = a.out or os.path.splitext(a.file)[0] + ('.split.mid' if a.split else '.mid')
    mid.save(out)
    lo, hi = min(p for _, _, p in resolved), max(p for _, _, p in resolved)
    print(f'wrote {out}  |  {len(resolved)} notes, {a.bpm:g}bpm, range MIDI {lo}-{hi}')

if __name__ == '__main__':
    main()
