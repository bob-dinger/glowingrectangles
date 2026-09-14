#!/usr/bin/env python3
"""
Turn the card's normalised chord names into the chords you actually play.

pao_pools normalises every song to C major so one picture works in any key —
which is right for the mnemonic and wrong for the caption. A card reading
"| G F Em | Dm |" for Fire Escape, a song in G, would have you playing the
wrong four chords: the real progression is V-IV-iii-ii, or D-C-Bm-Am.

    from chord_key import actual
    actual('G', 'major', 'G')   -> 'D'
    actual('G', 'major', 'Dm')  -> 'Am'
"""
# normalised nine -> (scale degree, quality)
DEG = {'C': (1, ''), 'Dm': (2, 'm'), 'Em': (3, 'm'), 'F': (4, ''),
       'G': (5, ''), 'Am': (6, 'm'), 'A#': (7, 'b'), 'D': (2, ''),
       'E': (3, '')}
STEPS = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
# keys conventionally written with flats
FLATKEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'd', 'g', 'c', 'f'}


def _pc(name):
    n = name.replace('b', 'b').strip()
    for i, s in enumerate(SHARP):
        if s == n: return i
    for i, s in enumerate(FLAT):
        if s == n: return i
    return 0


def actual(tonic, scale, norm):
    """normalised card name -> the chord as played in this song's key."""
    if norm in ('·', '?', ''): return norm
    if norm not in DEG: return norm
    deg, qual = DEG[norm]
    root = _pc(tonic)
    # minor-key songs are normalised through their relative major, so the
    # tonic stored is the relative major's tonic already
    semis = (STEPS[deg] - (1 if qual == 'b' else 0)) % 12
    names = FLAT if (tonic in FLATKEYS or 'b' in tonic) else SHARP
    out = names[(root + semis) % 12]
    return out + ('m' if qual == 'm' else '')


def bar(tonic, scale, bar_tuple):
    return ' '.join(actual(tonic, scale, c) for c in bar_tuple)


def line(tonic, scale, bars):
    return '| ' + ' | '.join(bar(tonic, scale, b) for b in bars) + ' |'


if __name__ == '__main__':
    for t, n in [('G', 'G'), ('G', 'F'), ('G', 'Em'), ('G', 'Dm'), ('G', 'C'),
                 ('C', 'G'), ('E', 'F'), ('Bb', 'G'), ('D', 'Am')]:
        print(f'  key {t:<3} card {n:<3} -> {actual(t, "major", n)}')
