#!/usr/bin/env python3
"""
incubus_dig -> incubus_dig-E: the whole song at the record's pitch, written in E major.

The source file (key C) holds the song two ways. Bars 5-12 and 37-44 treat the
verse chord as I (C = E on the record). Everything else treats it as IV (C = B).
Each section is moved to real pitch by its own reading, then every note and chord
is re-spelled in E major: verse E F# C#m = I II vi (II = V/V), chorus E B F# C#m =
I V II vi. The A# in the pre-chorus melody becomes #4.

    themap_venv/python dig_to_e.py            # writes ~/Desktop/hookpad_fill_backups/incubus_dig-E.json
    themap_venv/python dig_to_e.py --upload   # + creates it in the main Hookpad account
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthv_song as SV

SRC = os.path.expanduser('~/Desktop/music/hookpad_songs_full/incubus_dig.json')
OUT = os.path.expanduser('~/Desktop/hookpad_fill_backups/incubus_dig-E.json')
TONIC_ON = lambda b: 4 if (17 <= b < 49 or 145 <= b < 177) else -1   # C = E (bars 5-12, 37-44), else C = B
SD = {0: '1', 1: '#1', 2: '2', 3: 'b3', 4: '3', 5: '4', 6: '#4', 7: '5', 8: '#5', 9: '6', 10: 'b7', 11: '7'}
# chord (pc above E, minor?) -> Hookpad (root, applied)
CH = {(0, False): (1, 0), (2, True): (2, 0), (4, True): (3, 0), (5, False): (4, 0), (7, False): (5, 0),
      (9, True): (6, 0), (2, False): (5, 5), (4, False): (5, 6), (9, False): (5, 2), (11, False): (5, 3)}
CPC = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}


def chord_pc(c):
    """(pc in the C file, minor?) for the chord forms this song uses"""
    if c['applied']:   # V/x: a major chord a fifth above degree x
        return (CPC[c['applied']] + 7) % 12, False
    return CPC[c['root']], c['root'] in (2, 3, 6)


def main():
    d = json.load(open(SRC)); d.pop('fp', None)
    keys = d['keys']
    for n in d['notes']:
        if n.get('isRest'): continue
        p = SV.midi_pitch(n, keys) + TONIC_ON(n['beat']) - 4      # real pitch, relative to E4 = 64
        rel = p - 60
        n['octave'], n['sd'] = rel // 12, SD[rel % 12]
    for c in d['chords']:
        if c.get('isRest'): continue
        pc, minor = chord_pc(c)
        real = (pc + TONIC_ON(c['beat']) - 4) % 12
        c['root'], c['applied'] = CH[(real, minor)]
    d['keys'] = [{'beat': 1, 'scale': 'major', 'tonic': 'E'}]
    # check: every note lands where the source put it on the record
    src = json.load(open(SRC))
    for a, b in zip(src['notes'], d['notes']):
        if a.get('isRest'): continue
        assert SV.midi_pitch(b, d['keys']) == SV.midi_pitch(a, src['keys']) + TONIC_ON(a['beat']), a
    json.dump(d, open(OUT, 'w'))
    print(OUT)
    if '--upload' in sys.argv:
        import hookpad_upload_variants as U
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        rec, err = U.upload(tok, 'incubus_dig-E', d)
        print(rec or err)


if __name__ == '__main__':
    main()
