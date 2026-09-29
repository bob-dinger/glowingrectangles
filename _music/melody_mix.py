"""Fix a real melodic rhythm, then vary everything else — N mixed takes in one paste.

The chord_perms library fixes a chord rhythm and sweeps progressions. This fixes
a MELODIC rhythm — every onset and duration lifted from a real song — and varies
the progression underneath it and the pitch dials over it. The rhythm never
changes, so you hear what the same phrase becomes in different harmony.

Pitches snap to a chord tone of whatever chord is sounding (perm_melody's rule),
so no take clashes; the dials (focus / register / motion) decide which chord tone.

Source rhythm here: JoJo "Too Little Too Late" chorus, beats 65-81, read at the
DOUBLED metric level (162bpm) so its sixteenths become eighths — see memory
music_doubling_variants.

    themap_venv/python melody_mix.py --takes 25
"""
import json, os, random, re, sys, argparse, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perm_melody as pm
from build_perm_pastes import parse_rhythm, chord, num, ROOTS, POOL, WORDS

OUT   = os.path.expanduser('~/Desktop/chord_perms/_melody_mix')
RHYTHMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'melody_rhythms')
FOCI  = (1, 3, 5, 6)
REGS  = (0, 0, -1)

def source_rhythm(path, factor=1.0):
    """(onset, duration) per note, relative to the first beat, at `factor` scale."""
    d = json.load(open(path))
    ns = sorted([n for n in d['notes'] if not n.get('isRest')], key=lambda n: n['beat'])
    lo = min(n['beat'] for n in d['notes'])
    return [((n['beat'] - lo) * factor, n['duration'] * factor) for n in ns]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rhythm', help="a melody source in melody_rhythms/, e.g. f-am-g_112")
    ap.add_argument('--chords', required=True, help="chord spec, e.g. 16-16-32_ABC")
    ap.add_argument('--takes', type=int, default=25)
    ap.add_argument('--reps', type=int, default=2, help="statements of the chord phrase")
    ap.add_argument('--bpm', type=int, default=110)
    ap.add_argument('--factor', type=float, default=1.0, help="2.0 to read at the doubled level")
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--mix', default='corpus', choices=('corpus','prechorus'),
                    help="which measured move distribution to walk by")
    ap.add_argument('--landing', action='store_true',
                    help="landing-first: force the break bars onto one degree and "
                         "fill the movement to arrive there")
    ap.add_argument('--breaks', default='4,8', help="break bars, 1-indexed")
    a = ap.parse_args()

    rhythm = source_rhythm(os.path.join(RHYTHMS, a.rhythm + '.json'), a.factor)
    slots, phrase, roles = parse_rhythm(a.chords)
    pick = len(roles)
    span = max(phrase * a.reps, (rhythm[-1][0] + rhythm[-1][1] + 4) // 4 * 4)
    words = {frozenset(c): w for w, c in json.load(open(WORDS)).items()
             if len(c) == pick and set(c) <= set(POOL)}

    rng = random.Random(a.seed)
    combos = [(sub, p) for sub in itertools.combinations(POOL, pick)
              for p in itertools.permutations(sub)]
    rng.shuffle(combos)

    chords, notes, sections = [], [], []
    print(f"{len(rhythm)} notes of fixed rhythm, {span/4:g} bars per take, {a.bpm}bpm\n")
    for i in range(a.takes):
        sub, perm = combos[i]
        word = words[frozenset(sub)]
        focus, reg, motion = FOCI[i % 4], REGS[i % 3], pm.MOTIONS[(i // 2) % 4]
        if a.landing:
            focus = pm.pick_landing(random.Random(a.seed*7919 + i))
        base = 1 + i*span
        cast = dict(zip(roles, perm))
        roots = {k: ROOTS[v] for k, v in cast.items()}
        sections.append({"beat": num(base), "name":
                         f"{word} {'-'.join(perm)} {focus}@{reg}{motion}"})
        for rep in range(a.reps):
            off = base + rep*phrase
            for onset, dur, role, ctype, power in slots:
                chords.append(chord(roots[role], off + onset, dur, ctype, power))
        def root_at(b, _slots=slots, _roots=roots):
            live = [s for s in _slots if s[0] <= b + 1e-9 < s[0] + s[1]]
            return _roots[(live[-1] if live else _slots[0])[2]]
        rng = random.Random(a.seed*1000 + i)
        if a.landing:
            brk = tuple(int(x) for x in a.breaks.split(','))
            gen = pm.land_first(rhythm, root_at, phrase, focus, reg, rng, a.mix, brk)
        else:
            gen = pm.walk(rhythm, root_at, phrase, focus, reg, motion, rng, a.mix)
        for n in gen:
            notes.append(dict(n, beat=num(base + n['beat']), duration=num(n['duration'])))
        print(f"  {i+1:3}  bar {int((base-1)/4)+1:4}  {word:12} {'-'.join(perm):16} "
              f"focus {focus} reg {reg:+d} {motion}")

    obj = {"version":1, "chords":chords, "notes":notes,
           "keys":[{"beat":1, "scale":"major", "tonic":"C"}],
           "tempos":[{"beat":1, "bpm":a.bpm, "swingBeat":0.5, "swingFactor":0}],
           "meters":[{"beat":1, "numBeats":4, "beatUnit":1}],
           "breaks":[], "sections":sections,
           "endBeat":num(1 + a.takes*span), "audioTracks":[]}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{a.rhythm}_{a.takes}takes.txt")
    open(path, 'w').write(json.dumps(obj, separators=(',',':'), ensure_ascii=False))
    print(f"\n{a.takes} takes, {int(a.takes*span/4)} bars, {len(notes)} notes, "
          f"{os.path.getsize(path)//1024}K\n-> {path}")

if __name__ == '__main__':
    main()
