"""Every ordering of k-chords-from-6, poured into one chord rhythm.

Layout: ~/Desktop/chord_perms/<k>/<rhythm>_<shape>[_<types>][_<song>]/ — k = how
many distinct chords. The folder name IS the spec, in three readable fields:

    rhythm   one group per CHORD, in SIXTEENTHS (Hookpad's smallest unit, so
             every rhythm is expressible). Groups are separated by "-"; within a
             group, "+" marks re-strikes of that same chord.
                 14-18-14-18                 four chords, one strike each
                 24-8-24-8                   long-short long-short
                 3+1+2+1+1+1+1-2+2+2-…       a strum: chord one struck 7 times
    shape    one role letter per GROUP — ABCD plain, ABABC when a chord recurs
             non-adjacently. Omitted = A B C D… in order.
    types    one per group: 5 = triad, 7 = seventh, p = power chord (no 3rd).
             A single character applies to every group; omitted = all triads.

A bar is 16 sixteenths and the rhythm must sum to a whole number of bars. k comes
from the distinct role letters. Each phrase is stated twice by default (--reps).

Pool = C Dm Em F G Am (roots 1 2 3 4 5 6 in C major). Subsets are named by the
user's chord words (`chord_words.json`): 15 words x 24 orderings = 360 for k=4,
20 x 6 = 120 for k=3, 15 x 2 = 30 for k=2. Per rhythm folder: one .txt paste per
word, plus all-<n>.txt with the whole tour. Section = "<WORD> <A>-<B>-<C>".

    themap_venv/python build_perm_pastes.py 14-18-14-18_ABCD --name malibu,mrjones
    themap_venv/python build_perm_pastes.py 16-16-16-6-10_ABABC --name birthday
    themap_venv/python build_perm_pastes.py 10-6-10-6_ABCD_p --reps 1
"""
import json, os, re, sys, itertools, argparse
from fractions import Fraction as F
import perm_melody

ROOTS   = {'C':1, 'Dm':2, 'Em':3, 'F':4, 'G':5, 'Am':6}
POOL    = ['C','Dm','Em','F','G','Am']
ROOT    = os.path.expanduser('~/Desktop/chord_perms')
WORDS   = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chord_words.json')
PER_BAR = 16                                   # sixteenths in a 4/4 bar
SPEC    = re.compile(r'^(\d+(?:\+\d+)*(?:-\d+(?:\+\d+)*)*)(?:_([A-Z]+))?(?:_([57p]+))?$')

def num(x):
    """0.75 stays a float; 4.0 becomes int 4 (Hookpad wants ints on whole beats)."""
    return int(x) if float(x).is_integer() else float(x)

def parse_rhythm(spec):
    """'3+1+2-4-4_ABC_p' -> (slots, phrase_beats, roles).
    slot = (onset_beats, dur_beats, role, type, power)."""
    m = SPEC.match(spec)
    if not m:
        sys.exit(f"{spec}: want <rhythm>_<shape>[_<types>], e.g. 14-18-14-18_ABCD")
    groups = [[int(x) for x in g.split('+')] for g in m.group(1).split('-')]
    shape = m.group(2) or ''.join(chr(ord('A')+i) for i in range(len(groups)))
    types = m.group(3) or '5'
    if len(types) == 1:
        types = types * len(groups)
    if len(shape) != len(groups) or len(types) != len(groups):
        sys.exit(f"{spec}: {len(groups)} chord groups but shape has {len(shape)} "
                 f"and types {len(types)} — one entry per group")
    total = sum(sum(g) for g in groups)
    if total % PER_BAR:
        sys.exit(f"{spec}: sums to {total} sixteenths, not a whole number of bars")
    roles = sorted(set(shape))
    if roles != [chr(ord('A')+i) for i in range(len(roles))]:
        sys.exit(f"{spec}: roles must start at A and be contiguous, got {''.join(roles)}")
    beat = F(4, PER_BAR)                        # beats per sixteenth
    slots, at = [], 0
    for g, role, t in zip(groups, shape, types):
        for strike in g:
            slots.append((float(at*beat), float(strike*beat), role,
                          5 if t == 'p' else int(t), t == 'p'))
            at += strike
    return slots, float(at*beat), roles

def chord(root, beat, duration, ctype, power):
    return {"root":root, "beat":num(beat), "duration":num(duration), "type":ctype, "inversion":0,
            "applied":0, "adds":[], "omits":[3] if power else [], "alterations":[],
            "suspensions":[], "substitutions":[], "pedal":None, "alternate":"", "borrowed":"",
            "isRest":False, "recordingEndBeat":None}

def song(entries, slots, roles, phrase, reps, bpm, key='C', melody=None):
    """entries: [(word, perm), ...] — perm assigns one chord to each role, in order."""
    span = phrase * reps
    tag = ''
    if melody:
        f, r, mo, _ = perm_melody.parse(melody)
        tag = f" {f}@{r}{mo}"
    chords, sections, notes = [], [], []
    for i, (word, perm) in enumerate(entries):
        base = 1 + i*span
        cast = dict(zip(roles, perm))
        sections.append({"beat":num(base), "name":f"{word} {'-'.join(perm)}{tag}"})
        mel = perm_melody.phrase(slots, {k: ROOTS[v] for k, v in cast.items()},
                                 phrase, melody) if melody else []
        for rep in range(reps):
            off = base + rep*phrase
            for onset, dur, role, ctype, power in slots:
                chords.append(chord(ROOTS[cast[role]], off + onset, dur, ctype, power))
            for n in mel:
                notes.append(dict(n, beat=num(off + n['beat']), duration=num(n['duration'])))
    return {"version":1, "chords":chords, "notes":notes,
            "keys":[{"beat":1, "scale":"major", "tonic":key}],
            "tempos":[{"beat":1, "bpm":bpm, "swingBeat":0.5, "swingFactor":0}],
            "meters":[{"beat":1, "numBeats":4, "beatUnit":1}],
            "breaks":[], "sections":sections,
            "endBeat":num(1 + len(entries)*span), "audioTracks":[]}

def word_map(pick):
    """Chord word per subset. chord_words.json only covers 2-, 3- and 4-chord sets,
    so larger picks fall back to the chord set itself as the name (C-DM-EM-F-G).
    Coin real words for those and they will be picked up automatically."""
    words = json.load(open(WORDS))
    m = {frozenset(c): w for w, c in words.items() if len(c) == pick and set(c) <= set(POOL)}
    for sub in itertools.combinations(POOL, pick):
        m.setdefault(frozenset(sub), '-'.join(sub).upper())
    return m

def build(spec, bpm, reps, name=None, quiet=False, melody=None):
    slots, phrase, roles = parse_rhythm(spec)
    pick, bars = len(roles), int(phrase // 4)
    by_set = word_map(pick)
    folder = spec + (f"_{perm_melody.label(melody)}" if melody else "") + (f"_{name}" if name else "")
    out = os.path.join(ROOT, str(pick), folder); os.makedirs(out, exist_ok=True)

    if not quiet:
        print(f"{pick}/{folder}  ({len(slots)} strikes over {int(phrase*4)} sixteenths = "
              f"{bars} bars, x{reps} = {bars*reps} measures per perm, {bpm} bpm)")
    everything = []
    for subset in itertools.combinations(POOL, pick):
        word = by_set[frozenset(subset)]
        entries = [(word, p) for p in itertools.permutations(subset)]
        everything += entries
        obj = song(entries, slots, roles, phrase, reps, bpm, melody=melody)
        path = os.path.join(out, f"{word.lower()}.txt")
        open(path, 'w').write(json.dumps(obj, separators=(',',':'), ensure_ascii=False))
        if not quiet:
            print(f"  {word.lower()+'.txt':18} {' '.join(subset):16} {len(entries):3} perms  "
                  f"{len(entries)*bars*reps:5} bars  {os.path.getsize(path)//1024}K")
    obj = song(everything, slots, roles, phrase, reps, bpm, melody=melody)
    fname = f"all-{len(everything)}.txt"
    path = os.path.join(out, fname)
    open(path, 'w').write(json.dumps(obj, separators=(',',':'), ensure_ascii=False))
    if not quiet:
        print(f"  {fname:18} {'every word':16} {len(everything):3} perms  "
              f"{len(everything)*bars*reps:5} bars  {os.path.getsize(path)//1024}K")
    print(f"-> {out}/")
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('rhythms', nargs='+', help="<rhythm>_<shape>[_<types>], e.g. 14-18-14-18_ABCD")
    ap.add_argument('--bpm', type=int, default=110)
    ap.add_argument('--reps', type=int, default=2,
                    help="statements of the phrase per section (2 = one repeat)")
    ap.add_argument('--name', help="song the riff came from; appended to the folder name")
    ap.add_argument('--melody', help="add a phrase over every perm: "
                    "<focus>:<register>:<motion>:<cells>, e.g. 3:0:orbit:walk-hold")
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    for spec in a.rhythms:
        build(spec, a.bpm, a.reps, a.name, a.quiet, a.melody)
