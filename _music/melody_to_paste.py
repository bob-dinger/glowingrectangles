"""Convert a perfect_melodies.json entry into a Hookpad paste-JSON .txt file on
the Desktop. Chords are pulled from the perfect_chords.json sidecar when present.

    python _music/melody_to_paste.py "seashores" "anger" ...

Beat layout:
  - If the song HAS chords, melody + chords are emitted on their ORIGINAL beats so
    they stay locked together (the corpus stores absolute beats per phrase).
  - If the song has NO chords, phrases are repacked back-to-back onto barlines so
    entries whose phrases each restart at beat 1 (e.g. anger) don't collide.

version:1 bypasses Hookpad's fp check.
"""
import json, os, sys, math

HERE = os.path.dirname(__file__)
CORPUS = os.path.join(HERE, 'perfect_melodies.json')
CHORDS = os.path.join(HERE, 'perfect_chords.json')
DESKTOP = os.path.expanduser('~/Desktop')

CHORD_ORDER = ['root', 'beat', 'duration', 'type', 'inversion', 'applied', 'adds',
               'omits', 'alterations', 'suspensions', 'substitutions', 'pedal',
               'alternate', 'borrowed', 'isRest', 'recordingEndBeat']


def next_barline(beat, bar=4):
    return 1 + math.ceil((beat - 1) / bar) * bar


def note(n, shift=0.0):
    return {'sd': str(n['sd']), 'octave': int(n['octave']),
            'beat': round(n['beat'] + shift, 3), 'duration': n['duration'],
            'isRest': False, 'recordingEndBeat': None}


def flatten(phrases, realign):
    """realign=False keeps original beats; True repacks phrases onto barlines."""
    if not realign:
        return [note(n) for ph in phrases for n in ph]
    notes, cursor = [], 1.0
    for ph in phrases:
        shift = cursor - ph[0]['beat']
        end = 0
        for n in ph:
            m = note(n, shift)
            notes.append(m)
            end = max(end, m['beat'] + m['duration'])
        cursor = next_barline(end)
    return notes


def chord(c):
    d = {'root': c['root'], 'beat': c['beat'], 'duration': c['duration'],
         'type': c['type'], 'inversion': 0, 'applied': c.get('applied', 0),
         'adds': [], 'omits': [], 'alterations': [], 'suspensions': [],
         'substitutions': [], 'pedal': None, 'alternate': '',
         'borrowed': c.get('borrowed', '') or '', 'isRest': False,
         'recordingEndBeat': None}
    return {k: d[k] for k in CHORD_ORDER}


def paste_json(phrases, chords):
    realign = not chords          # only repack when there are no chords to keep aligned
    obj = {'notes': flatten(phrases, realign),
           'chords': [chord(c) for c in (chords or [])],
           'audioTracks': [], 'version': 1}
    return json.dumps(obj, separators=(',', ':'))


def main(names):
    corpus = json.load(open(CORPUS))
    chordbook = json.load(open(CHORDS)) if os.path.exists(CHORDS) else {}
    for name in names:
        if name not in corpus:
            print(f'  ! "{name}" not in corpus'); continue
        chords = chordbook.get(name)
        txt = paste_json(corpus[name], chords)
        safe = name.replace('/', '-').replace(' ', '_')
        out = os.path.join(DESKTOP, f'{safe}_hookpad.txt')
        with open(out, 'w') as f:
            f.write(txt)
        tag = f'{txt.count(chr(34)+"sd"+chr(34))} notes'
        tag += f', {len(chords)} chords' if chords else ', no chords'
        print(f'  {name:20} -> {out}  ({tag})')


if __name__ == '__main__':
    main(sys.argv[1:] or ['anger', 'seashores'])
