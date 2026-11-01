#!/usr/bin/env python3
"""
Chords from a recording, for audio_to_hookpad.py.

The candidates come from the song's UG chart when there is one (the chords it
names, at sounding pitch after its capo, with their real extensions: Am7,
Cadd9, D/F#), else the six diatonic triads of the key. Each beat of the band
(demucs no_vocals) is scored against every candidate:

    treble chroma . chord template   (root and third count most, the fifth a
                                      little less, sevenths/adds a little less)
  + bass chroma at the chord's bass  (the slash bass, else the root) -- this is
                                      what tells Am from C and Em from G

then a Viterbi pass picks the path with a penalty for each change, so a chord
holds unless the band really moves, and changes can land on any beat.

    best_path(no_vocals_wav, beats, candidates) -> [(name, first_beat, n_beats)]
    to_hookpad(name, tonic, mode, proto, beat, dur) -> a Hookpad chord dict
"""
import glob, os, re
from collections import Counter
import numpy as np, librosa

NAMES = 'C C# D Eb E F F# G Ab A Bb B'.split()
PCS = {n: i for i, n in enumerate(NAMES)} | {'Db': 1, 'D#': 3, 'Gb': 6, 'G#': 8, 'A#': 10, 'Cb': 11, 'Fb': 4,
                                             'E#': 5, 'B#': 0}
TOKEN = re.compile(r'^([A-G][#b]?)((?:maj|min|m|dim|aug|sus|add|\+|°|M|\d|b|#|\(|\))*)(?:/([A-G][#b]?))?$')
UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')


# ---- UG ---------------------------------------------------------------------
def _toks(s):
    s = re.sub(r'\.txt$', '', s, flags=re.I)
    s = re.sub(r"[^a-z0-9 ]", '', re.sub(r'[_\-\s]+', ' ', s.lower()))
    return [t for t in s.split() if t and t not in {'the', 'a', 'of'} and not t.isdigit()]


def find_ug(artist, title):
    """the saved UG page for a song (same matching as ug_chart.find_ug)"""
    asq, tsq, at = ''.join(_toks(artist or '')), ''.join(_toks(title or '')), set(_toks(artist or ''))
    if len(tsq) < 4:
        return None
    c = []
    for p in glob.glob(os.path.join(UG_DIR, '*.txt')):
        b = os.path.basename(p)
        sq, tk = ''.join(_toks(b)), set(_toks(b))
        if tsq in sq and (asq[:5] in sq or at & tk) and not re.search(r'verse|chorus|solo|intro', b, re.I):
            c.append(p)
    return min(c, key=lambda p: len(os.path.basename(p))) if c else None


def ug_chart(path):
    """-> (capo, Counter of chord names in the chart, chord names in order)"""
    txt = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'Capo:\s*(\d+)', txt)
    capo = int(m.group(1)) if m else 0
    order = []
    for line in txt.split('\n'):
        s = line.strip()
        if not s or len(s) > 90 or s.startswith(('#', 'Tuning', 'Key:', 'Capo')):
            continue
        s = re.sub(r'\[[^\]]*\]', ' ', s)          # [Verse] on the same line
        toks = [t.strip('|()') for t in s.split() if t.strip('|()-x0123456789')]
        good = [t for t in toks if TOKEN.match(t)]
        if toks and len(good) == len(toks) and len(good) >= 1:
            order += good
    # the diagram block near the top lists each chord once; it is not the chart
    return capo, Counter(order), order


# ---- chord names -> pitch classes ---------------------------------------------
def parse(name, capo=0):
    """'Cadd9' -> dict(root, pcs {pc: weight}, bass, quality, seventh, add9, sus)"""
    m = TOKEN.match(name)
    if not m:
        return None
    root = (PCS[m.group(1)] + capo) % 12
    q = m.group(2) or ''
    bass = (PCS[m.group(3)] + capo) % 12 if m.group(3) else root
    minor = bool(re.match(r'^(m(?!aj)|min)', q))
    dim, aug = 'dim' in q or '°' in q, 'aug' in q or '+' in q
    sus = 2 if 'sus2' in q else 4 if 'sus' in q else 0
    third = None if sus or q.startswith('5') else 3 if (minor or dim) else 4
    fifth = 6 if dim else 8 if aug else 7
    w = {0: 1.0, fifth: 0.8}
    if third is not None: w[third] = 1.0
    if sus: w[2 if sus == 2 else 5] = 0.9
    seventh = None
    if 'maj7' in q or 'M7' in q: seventh = 11
    elif re.search(r'(?<!add)(7|9|11|13)', q): seventh = 9 if dim and '7' in q and 'm7b5' not in q else 10
    if seventh is not None: w[seventh] = 0.7
    add9 = bool(re.search(r'add(9|2)', q)) or (re.search(r'(?<!add)9', q) is not None)
    if add9: w[2] = 0.7
    if re.search(r'(?<![1-9])6', q): w[9] = 0.7
    return dict(root=root, bass=bass, minor=minor or dim, dim=dim, sus=sus, seventh=seventh, add9=add9,
                pcs={(root + k) % 12: v for k, v in w.items()}, name=name)


def transpose(name, semis):
    """'Cadd9/E' up 2 -> 'Dadd9/F#' (sharps, Eb/Ab/Bb as flats)"""
    m = TOKEN.match(name)
    up = lambda n: NAMES[(PCS[n] + semis) % 12]
    return up(m.group(1)) + (m.group(2) or '') + ('/' + up(m.group(3)) if m.group(3) else '')


def sounding(cands, capo):
    """chart chord names -> the names at sounding pitch (after the capo)"""
    return {transpose(c, capo): n for c, n in cands.items()}


def chart_key(wav, beats, cands, treble='full'):
    """The chart may be in another key than the record (an easier key, a
    record tuned down a half step). Try the chart's chords in all 12 keys and
    keep the one the band fits best. -> (semitones, {fit by semitones})"""
    T, B = _feat(wav, beats, treble)
    Tn = T / (np.linalg.norm(T, axis=0, keepdims=True) + 1e-9)
    Bn = B / (B.max(axis=0, keepdims=True) + 1e-9)
    fit = {}
    for s in range(12):
        ch = [parse(transpose(c, s)) for c in cands]
        ch = [c for c in ch if c]
        M = np.zeros((len(ch), 12))
        for i, c in enumerate(ch):
            for pc, w in c['pcs'].items(): M[i, pc] = w
        M /= np.linalg.norm(M, axis=1, keepdims=True)
        S = M @ Tn + 0.3 * np.array([np.maximum(Bn[c['bass']], Bn[c['root']]) for c in ch])
        fit[s] = float(S.max(0).mean())
    best = max(fit, key=fit.get)
    return best, fit


def diatonic(tonic, mode):
    """the six triads of the key (no diminished), named"""
    from audio_to_hookpad import scale
    sc, t0 = scale(mode), PCS[tonic]
    out = []
    for d in range(7):
        r, third = sc[d], (sc[(d + 2) % 7] - sc[d]) % 12
        fifth = (sc[(d + 4) % 7] - sc[d]) % 12
        if fifth != 7:
            continue
        out.append(NAMES[(t0 + r) % 12] + ('m' if third == 3 else ''))
    return out


# ---- the band -> a chord per beat ----------------------------------------------
def features(wav, beats, treble='full'):
    """per-beat chroma: treble ('full' = C1 up 7 octaves, 'mid' = C3 up 4) and bass (E1 up 2)"""
    y, sr = librosa.load(wav, sr=22050)
    yh = librosa.effects.hpss(y)[0]
    hop = 512
    if treble == 'mid':
        treble = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=hop, fmin=librosa.note_to_hz('C3'), n_octaves=4)
    else:
        treble = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=hop)
    bass = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=hop, fmin=librosa.note_to_hz('E1'), n_octaves=2,
                                      bins_per_octave=36)
    frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
    T = librosa.util.sync(treble, frames, aggregate=np.mean)[:, 1:]   # column i = beat i .. i+1
    B = librosa.util.sync(bass, frames, aggregate=np.mean)[:, 1:]
    return T, B


def candidates(counts, min_share=0.02):
    """chart chords worth considering: drop one-offs (a stray 'A' in the text)"""
    tot = sum(counts.values())
    keep = {c: n for c, n in counts.items() if n >= 2 and n / tot >= min_share and parse(c)}
    return keep or dict(counts)


_FEAT = {}


def _feat(wav, beats, treble):
    key = (wav, len(beats), float(beats[0]), treble)
    if key not in _FEAT:
        _FEAT[key] = features(wav, beats, treble)
    return _FEAT[key]


def best_path(wav, beats, cands, change=0.25, bass_w=0.5, off_mult=3.0, prior=None, prior_w=0.1, unit=1, treble='full', triads=False):
    """cands: chord names; prior: {name: count} from the chart. A change on an
    even beat (1, 3, 5 ... = bar and half-bar starts) costs `change`, on any
    other beat `change * off_mult`."""
    T, B = _feat(wav, beats, treble)
    n = min(T.shape[1], len(beats) - 1)
    chords = [parse(c) for c in cands]
    chords = [c for c in chords if c]
    M = np.zeros((len(chords), 12))
    for i, c in enumerate(chords):
        pcs = c['pcs']
        if triads:              # match on the triad only; the name keeps its extensions
            pcs = {p: w for p, w in pcs.items() if (p - c['root']) % 12 in (0, 3, 4, 6, 7, 8, 2, 5)
                   and not ((p - c['root']) % 12 in (2, 5) and not c['sus'])}
        for pc, w in pcs.items(): M[i, pc] = w
    M /= np.linalg.norm(M, axis=1, keepdims=True)
    Tn = T[:, :n] / (np.linalg.norm(T[:, :n], axis=0, keepdims=True) + 1e-9)
    Bn = B[:, :n] / (B[:, :n].max(axis=0, keepdims=True) + 1e-9)
    # a slash chord's bass may be either note (charts write G/B where the record often plays G)
    S = M @ Tn + bass_w * np.array([np.maximum(Bn[c['bass']], Bn[c['root']]) for c in chords])
    if prior:
        tot = sum(prior.get(c['name'], 0) for c in chords) or 1
        S += prior_w * np.log(np.array([max(prior.get(c['name'], 0), 0.5) / tot for c in chords]))[:, None]
    if unit > 1:                                   # score whole half bars: chords rarely change faster
        m = S.shape[1] // unit * unit
        S = S[:, :m].reshape(len(chords), -1, unit).mean(2)
        n = S.shape[1]
    # Viterbi: stay free, change costs `change` (more off the half bar)
    K = len(chords)
    score, back = S[:, 0].copy(), np.zeros((K, n), int)
    for t in range(1, n):
        best = int(np.argmax(score))
        stay, move = score, score[best] - change * (1 if unit > 1 or t % 2 == 0 else off_mult)
        back[:, t] = np.where(stay >= move, np.arange(K), best)
        score = np.maximum(stay, move) + S[:, t]
    path = [int(np.argmax(score))]
    for t in range(n - 1, 0, -1):
        path.append(back[path[-1], t])
    path = path[::-1]
    out = []
    for t, k in enumerate(path):
        if out and out[-1][0] == chords[k]['name']:
            out[-1][2] += unit
        else:
            out.append([chords[k]['name'], t * unit + 1, unit])
    return out


# ---- a chord name -> Hookpad -------------------------------------------------------
BORROW = ['minor', 'mixolydian', 'dorian', 'lydian', 'phrygian', 'harmonicMinor']


def _scale(mode):
    from audio_to_hookpad import scale
    if mode == 'harmonicMinor':
        s = scale('minor'); s[6] = 11; return s
    return scale(mode)


def _triad_q(sc, d):
    third, fifth = (sc[(d + 2) % 7] - sc[d]) % 12, (sc[(d + 4) % 7] - sc[d]) % 12
    return 'dim' if fifth == 6 else 'min' if third == 3 else 'maj'


def to_hookpad(name, tonic, mode, proto, beat, dur, capo=0):
    c = parse(name, capo)
    rel = (c['root'] - PCS[tonic]) % 12
    q = 'dim' if c['dim'] else 'min' if c['minor'] else 'maj'
    root, applied, borrowed = None, 0, ''
    sc = _scale(mode)
    if rel in sc and (c['sus'] or _triad_q(sc, sc.index(rel)) == q):
        root = sc.index(rel) + 1
    elif q == 'maj' and (rel - 7) % 12 in sc and (rel - 7) % 12 != 0:
        root, applied = 5, sc.index((rel - 7) % 12) + 1           # V/x
    else:
        for b in BORROW:
            s2 = _scale(b)
            if rel in s2 and _triad_q(s2, s2.index(rel)) == q:
                root, borrowed = s2.index(rel) + 1, b
                break
    if root is None:                                              # nearest degree, by ear later
        root = min(range(7), key=lambda d: min((sc[d] - rel) % 12, (rel - sc[d]) % 12)) + 1
    ch = dict(proto)
    ch.update(root=root, beat=beat, duration=dur, type=7 if c['seventh'] is not None else 5, inversion=0,
              applied=applied, adds=[9] if c['add9'] and c['seventh'] is None else [], omits=[], alterations=[],
              suspensions=[c['sus']] if c['sus'] else [], substitutions=[], pedal=None, alternate='',
              borrowed=borrowed, isRest=False, recordingEndBeat=None)
    if c['bass'] != c['root']:
        iv = (c['bass'] - c['root']) % 12
        ch['inversion'] = 1 if iv in (3, 4) else 2 if iv == 7 else 3 if iv in (10, 11) and c['seventh'] else 0
    return ch
