#!/usr/bin/env python3
"""
One chord tone per chord: every melody that picks the root, 3rd or 5th of each
chord and sings it in a fixed rhythm, drawn as a batch to sift by ear.

    python3 chord_tone_perms.py                          # Friday's verse, 20 draws
    python3 chord_tone_perms.py --chords "C F C G Am F C G" --rhythm 4,4,4,16,4,4,4,16
    python3 chord_tone_perms.py --n 30 --seed 7 --bpm 136

The user's idea from Friday I'm in Love (2026-10-14): its verse skeleton is one note
per bar -- G F G G | A F C D -- and each note is just a tone of the chord under it.
So any of the three tones per chord is a candidate: 3^8 = 6,561 melodies for eight
chords. This is the bones layer only (see skeleton.py); flair goes on top later.

RHYTHM is one number per chord, a note length in sixteenths repeated to fill the
bar: 4 = four quarters, 8 = two halves, 16 = one whole note, 2 = eighths.

Octaves are voice-led: each note takes the octave nearest the one before, inside
G below middle C to the G above (Friday's range), so a pick never leaps further
than it has to. Section 1 is always the recorded skeleton, for reference.
"""
import argparse, hashlib, itertools, json, os, random

TONES = {'C': ['C', 'E', 'G'], 'Dm': ['D', 'F', 'A'], 'Em': ['E', 'G', 'B'],
         'F': ['F', 'A', 'C'], 'G': ['G', 'B', 'D'], 'Am': ['A', 'C', 'E']}
ROOTS = {'C': 1, 'Dm': 2, 'Em': 3, 'F': 4, 'G': 5, 'Am': 6}
SD = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}   # scale step in C
ROLE = 'R35'
LO, HI = -3, 11              # G3 .. G5 in scale steps from middle C
FRIDAY = 'G F G G A F C D'


def chord(root, beat):
    return {"root": root, "beat": beat, "duration": 4, "type": 5, "inversion": 0,
            "applied": 0, "adds": [], "omits": [], "alterations": [], "suspensions": [],
            "substitutions": [], "pedal": None, "alternate": "", "borrowed": "",
            "isRest": False, "recordingEndBeat": None}


def voice(letters):
    """note letters -> scale steps from middle C, each nearest the last"""
    out = []
    for i, l in enumerate(letters):
        s = SD[l]
        if i:
            s = min((s + 7 * k for k in range(-2, 3) if LO <= s + 7 * k <= HI),
                    key=lambda x: abs(x - out[-1]))
        out.append(s)
    return out


def paths(chords, rule):
    """every tone choice that can be SUNG under the rule, with one pitch path
    for it (the first found, preferring the smallest moves) -> {picks: steps}"""
    out = {}
    def tones(c):
        return sorted(SD[l] + 7 * k for l in TONES[c] for k in range(-2, 3)
                      if LO <= SD[l] + 7 * k <= HI)
    def ok(a, b, c):
        if rule == 'step': return abs(a - b) <= 1
        lo, hi = sorted((a, b))
        return not any(lo < t < hi for t in tones(c))
    def go(i, path):
        if i == len(chords):
            key = tuple(TONES[c].index('CDEFGAB'[x % 7]) for c, x in zip(chords, path))
            out.setdefault(key, path)
            return
        for t in sorted(tones(chords[i]), key=lambda t: abs(t - path[-1]) if path else 0):
            if (path and ok(path[-1], t, chords[i])) or (not path and 0 <= t < 7):
                go(i + 1, path + [t])
    go(0, [])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chords', default='C F C G Am F C G')
    ap.add_argument('--rhythm', default='4,4,4,16,4,4,4,16')
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--bpm', type=int, default=136)
    ap.add_argument('--rule', choices=['any', 'noskip', 'step'], default='any',
                    help='noskip: never jump over a tone of the new chord; step: repeat or one scale step')
    a = ap.parse_args()
    chords = a.chords.split()
    rhythm = [int(x) for x in a.rhythm.split(',')]
    assert len(rhythm) == len(chords), 'one rhythm value per chord'
    nb = len(chords)
    seed = a.seed if a.seed is not None else random.randrange(10**4)
    rnd = random.Random(seed)

    if a.rule == 'any':
        every = [(p, voice([TONES[c][i] for c, i in zip(chords, p)]))
                 for p in itertools.product(range(3), repeat=nb)]
    else:
        every = list(paths(chords, a.rule).items())
    picks = rnd.sample(every, min(a.n or len(every), len(every)))
    ref = FRIDAY.split()
    if chords == 'C F C G Am F C G'.split() and a.rule == 'any':
        fr = tuple(TONES[c].index(l) for c, l in zip(chords, ref))
        picks = [(fr, voice(ref))] + [x for x in picks if x[0] != fr][:a.n - 1]

    notes, chs, secs = [], [], []
    for s, (p, steps) in enumerate(picks):
        at = 1 + s * nb * 4
        letters = [TONES[c][i] for c, i in zip(chords, p)]
        for m, (c, st, r) in enumerate(zip(chords, steps, rhythm)):
            b0 = at + m * 4
            chs.append(chord(ROOTS[c], b0))
            for k in range(16 // r):
                notes.append({"sd": str(st % 7 + 1), "octave": st // 7, "beat": b0 + k * r / 4,
                              "duration": r // 4 if r % 4 == 0 else r / 4,
                              "isRest": False, "recordingEndBeat": None})
        roles = ''.join(ROLE[i] for i in p)
        tag = ' (recorded)' if s == 0 and letters == ref else ''
        secs.append({"beat": at, "name": f"{s+1:02} {' '.join(letters)}  {roles}{tag}"})

    end = 1 + len(picks) * nb * 4
    obj = {"version": 1, "chords": chs, "notes": notes,
           "keys": [{"beat": 1, "scale": "major", "tonic": "C"}],
           "tempos": [{"beat": 1, "bpm": a.bpm, "swingBeat": 0.5, "swingFactor": 0}],
           "meters": [{"beat": 1, "numBeats": 4, "beatUnit": 1}], "breaks": [],
           "sections": secs, "endBeat": end, "audioTracks": []}
    obj["fp"] = hashlib.sha1(json.dumps({k: v for k, v in obj.items()},
                                        separators=(',', ':')).encode()).hexdigest()
    path = os.path.expanduser(f'~/Desktop/friday im in love/chord_tone_perms_{a.rule}_seed{seed}.txt')
    open(path, 'w').write(json.dumps(obj, separators=(',', ':')))

    # read it back: every note a tone of the chord under it, nothing past the end
    d = json.load(open(path))
    under = {c['beat']: c['root'] for c in d['chords']}
    bad = 0
    for n in d['notes']:
        root = under[int((n['beat'] - 1) // 4) * 4 + 1]
        name = next(k for k, v in ROOTS.items() if v == root)
        letter = 'CDEFGAB'[int(n['sd']) - 1]
        bad += letter not in TONES[name] or n['beat'] + n['duration'] > end
    print(f'{path}\n  {len(picks)} of {len(every):,} melodies ({a.rule}), seed {seed}, {a.bpm} bpm, '
          f'{len(d["notes"])} notes, off-chord or spilling: {bad}')
    for sc in secs: print('  ' + sc['name'])


if __name__ == '__main__':
    main()
