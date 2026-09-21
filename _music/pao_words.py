#!/usr/bin/env python3
"""Find English words that spell a chord group in the nine-sound system.

    k g / t d / m / f v / j sh ch / s z / p b / th w / r
    C     Dm    Em   F     G         Am     A#     D      E
    n l are free -- no chord claims them, so they pass through as filler.

A word qualifies when its consonant sounds, read in order and with the free
sounds dropped, are exactly the target chords with no repeats. CATFISH is
k-t-f-sh = C-Dm-F-G. Vowels, h and y are free like n and l.

Phonemes come from cmudict, not spelling: the g in "gadfly" is hard (C) and the
g in "gift" is soft (G), and only the dictionary knows which. Words whose first
pronunciation disagrees with a later one are reported so they can be rejected
by ear.

    python3 pao_words.py C F G A#
    python3 pao_words.py --all-out-of-key
"""
import sys, collections
import cmudict

SOUND = {
    'K':'C','G':'C', 'T':'Dm','D':'Dm', 'M':'Em', 'F':'F','V':'F',
    'JH':'G','SH':'G','CH':'G','ZH':'G', 'S':'Am','Z':'Am',
    'P':'A#','B':'A#', 'TH':'D','DH':'D','W':'D', 'R':'E','ER':'E',
}
FREE = {'N','L','NG','HH','Y'}          # claimed by nothing

CMU = cmudict.dict()


def chords_of(pron):
    """phoneme list -> the chords it spells, in order, or None if unusable"""
    out = []
    for ph in pron:
        p = ph.rstrip('012')
        if p in FREE:
            continue
        if p in SOUND:
            out.append(SOUND[p])
        elif p[0] in 'AEIOU':            # a plain vowel is free
            continue
        else:
            return None
    return out


def find(target):
    want = sorted(target)
    hits = []
    for w, prons in CMU.items():
        if not w.isalpha() or len(w) < 3:
            continue
        got = chords_of(prons[0])
        if got is None or sorted(got) != want:
            continue
        # flag words whose other pronunciations disagree
        amb = any(chords_of(p) != got for p in prons[1:])
        hits.append((w, got, amb))
    hits.sort(key=lambda h: (h[2], -len(h[0])))
    return hits


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--all-out-of-key' in sys.argv:
        sets = [['C','F','G','A#'], ['C','D','F','G'], ['C','Dm','F','A#'],
                ['C','F','Am','A#'], ['C','Em','G','E'], ['C','F','G','D'],
                ['C','G','Am','A#'], ['C','Dm','G','D'], ['C','Em','Am','E']]
    else:
        sets = [args]
    for t in sets:
        hits = find(t)
        print(f"\n  {' '.join(t)}  —  {len(hits)} words")
        for w, got, amb in hits[:12]:
            print(f"    {w.upper():<16}{'-'.join(got):<22}{'  (other pronunciation differs)' if amb else ''}")
