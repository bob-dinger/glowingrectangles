#!/usr/bin/env python3
"""
Find real words and phrases that encode a chord progression, using the
chord peg system.

Works from PRONUNCIATION (cmudict), not spelling — so "cough" is k-f and
"cash" is k-sh, which is the whole point of the system.

    python3 peg_words.py "Dm G C Am"
    python3 peg_words.py "F C G" --max 30
    python3 peg_words.py --test

Consecutive repeats collapse: F-F-G-Am is treated as F-G-Am, because the
rhythm is a separate thing to remember.
"""
import argparse, collections, re, sys

import cmudict

# ARPAbet phoneme -> chord.  Anything absent is FREE (vowels, L, N, NG, W, Y, HH)
PHON = {
    'K':'C',  'G':'C',
    'F':'F',  'V':'F',
    'JH':'G', 'SH':'G', 'CH':'G', 'ZH':'G',
    'S':'Am', 'Z':'Am',
    'T':'Dm', 'D':'Dm',
    'TH':'D', 'DH':'D',
    'M':'Em',
    'R':'E',  'ER':'E',        # ER is the r-coloured vowel — still an r
    'P':'A#', 'B':'A#',
}
CHORDS = ['C','Dm','Em','F','G','Am','A#','D','E']


def skeleton(phones):
    out = []
    for p in phones:
        c = PHON.get(re.sub(r'\d', '', p))
        if c and (not out or out[-1] != c):   # collapse doubles: butter = one t
            out.append(c)
    return tuple(out)


WORDLIST = '/usr/share/dict/words'


def real_words():
    """cmudict is built for speech recognition and is full of surnames and
    acronyms ('fejes', 'svec', 'dj'). A mnemonic has to be a word you already
    know, so intersect with the system dictionary — plus a morphology fallback,
    since web2 has no plurals or inflected forms."""
    try:
        base = {l.strip().lower() for l in open(WORDLIST) if l.strip().islower()}
    except OSError:
        return None                      # no filter available; fall back to raw
    def known(w):
        if w in base: return True
        for suf, repl in (('s',''), ('es',''), ('ed',''), ('ed','e'),
                          ('ing',''), ('ing','e'), ('ies','y'), ('er',''), ('est','')):
            if w.endswith(suf) and (w[:-len(suf)] + repl) in base:
                return True
        return False
    return known


def build_index():
    d = cmudict.dict()
    known = real_words()
    idx = collections.defaultdict(list)
    for word, prons in d.items():
        if not re.fullmatch(r"[a-z]{3,}", word):      # 3+ letters kills 'dj', 'cv'
            continue
        if known and not known(word):
            continue
        for ph in prons:
            s = skeleton(ph)
            if s and word not in idx[s]:
                idx[s].append(word)
    for s in idx:
        idx[s].sort(key=lambda w: (len(w), w))
    return idx


def parse(prog):
    raw = [x for x in re.split(r'[\s,\-–>|]+', prog.strip()) if x]
    seq = []
    for x in raw:
        c = x[0].upper() + x[1:].lower().replace('min', 'm')
        c = {'Am':'Am','Dm':'Dm','Em':'Em','A#':'A#','Bb':'A#',
             'C':'C','D':'D','E':'E','F':'F','G':'G'}.get(c, c)
        if c not in CHORDS:
            sys.exit(f'unknown chord {x!r} — use one of {" ".join(CHORDS)}')
        if not seq or seq[-1] != c:          # collapse consecutive repeats
            seq.append(c)
    return tuple(seq)


def solve(target, idx, limit=14):
    singles = idx.get(target, [])[:limit]
    pairs = []
    for i in range(1, len(target)):
        a, b = target[:i], target[i:]
        for wa in idx.get(a, [])[:9]:
            for wb in idx.get(b, [])[:9]:
                pairs.append(f'{wa} {wb}')
    pairs.sort(key=lambda p: (len(p), p))
    return singles, pairs[:limit]


def show(prog, idx, limit):
    t = parse(prog)
    print(f'\n{"-".join(t)}   ->   {" · ".join(t)}')
    s, p = solve(t, idx, limit)
    if s: print('   one word :', ', '.join(s))
    if p: print('   two words:', ', '.join(p))
    if not s and not p: print('   nothing found')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('progression', nargs='*')
    ap.add_argument('--max', type=int, default=14)
    ap.add_argument('--test', action='store_true')
    a = ap.parse_args()

    print('building index from cmudict ...', file=sys.stderr)
    idx = build_index()

    if a.test:
        for w, want in [('cash safe','C-G-Am-F'), ('cough shack','C-F-G-C'),
                        ('dutch cake','Dm-G-C'), ('the fab show','D-F-A#-G')]:
            got = []
            for part in w.split():
                got += list(skeleton(cmudict.dict()[part][0]))
            merged = [c for i,c in enumerate(got) if i==0 or got[i-1]!=c]
            ok = '-'.join(merged) == want
            print(f"  {w:<14} -> {'-'.join(merged):<14} want {want:<14} {'OK' if ok else 'MISMATCH'}")
        return

    for prog in (a.progression or []):
        show(prog, idx, a.max)


if __name__ == '__main__':
    main()
