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
    if isinstance(norm, str) and '~' in norm:
        base, _, suf = norm.partition('~')
        return actual(tonic, scale, base) + suf
    if isinstance(norm, str) and norm.startswith('@'):
        # an applied dominant, carried as semitones above the tonic and always
        # major — V/iii in A major is G#, which no white-note name can hold
        semis = int(norm[1:])
        names = FLAT if (tonic in FLATKEYS or 'b' in tonic) else SHARP
        return names[(_pc(tonic) + semis) % 12]
    if norm not in DEG: return norm
    deg, qual = DEG[norm]
    root = _pc(tonic)
    # minor-key songs are normalised through their relative major, so the
    # tonic stored is the relative major's tonic already
    semis = (STEPS[deg] - (1 if qual == 'b' else 0)) % 12
    names = FLAT if (tonic in FLATKEYS or 'b' in tonic) else SHARP
    out = names[(root + semis) % 12]
    return out + ('m' if qual == 'm' else '')


def key_at(keys, beat):
    """The key in effect at a given beat -> (tonic, scale).

    Reading keys[0] and transposing the whole song with it is wrong for 22
    songs in the pools: Heaven Is a Place on Earth moves to D for exactly the
    pre-chorus, and twenty Beatles songs change at least once (Lucy in the Sky
    five times). The chord roots are degrees of the CURRENT key, so a root-1
    chord means a different letter before and after the change.
    """
    cur = ('C', 'major')
    for k in sorted(keys or [], key=lambda x: x.get('beat', 1)):
        if k.get('beat', 1) <= beat:
            cur = (k.get('tonic', 'C'), k.get('scale', 'major'))
        else:
            break
    return cur


def changes_within(keys, lo, hi):
    """key changes strictly inside [lo, hi) — a section that modulates part-way
    through cannot be transposed with one key, so it needs flagging"""
    out = []
    prev = key_at(keys, lo)
    for k in sorted(keys or [], key=lambda x: x.get('beat', 1)):
        b = k.get('beat', 1)
        if lo < b < hi:
            nxt = (k.get('tonic', 'C'), k.get('scale', 'major'))
            if nxt != prev: out.append((b, nxt)); prev = nxt
    return out


def bar(tonic, scale, bar_tuple):
    return ' '.join(actual(tonic, scale, c) for c in bar_tuple)


def line(tonic, scale, bars):
    return '| ' + ' | '.join(bar(tonic, scale, b) for b in bars) + ' |'


if __name__ == '__main__':
    for t, n in [('G', 'G'), ('G', 'F'), ('G', 'Em'), ('G', 'Dm'), ('G', 'C'),
                 ('C', 'G'), ('E', 'F'), ('Bb', 'G'), ('D', 'Am')]:
        print(f'  key {t:<3} card {n:<3} -> {actual(t, "major", n)}')
