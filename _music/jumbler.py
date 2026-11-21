"""The jumbler: ~20 eight-bar candidates in one Hookpad paste, to be sifted by ear.

The user writes by recombination -- "just jumble everything until something comes
out" -- so this is a BATCH, never one right answer. Every draw is random, but random in
the places the corpus is random and fixed where the corpus is fixed (music_melody_model):

    the bar word     a real four-bar word (H hold / M move / . air), then the
                     restatement: AA 32.6%, AA' 29.0% (the changed bar is bar 8 53.8%
                     of the time, M<->H 56%), otherwise a real second half
    the bars         each bar is a REAL bar from a real major-key section with that
                     letter -- its rhythm and its own intervals, transplanted. 97% of
                     notes are flair, so this is where the jumble lives
    the landings     ONE landing degree per section. Each half is transposed (by scale
                     steps, contour kept) so its phrase-end note lands on it; bar 8
                     keeps bar 4's degree 60% of the time
    the chords       a four-chord word, entry chord weighted by role (I 48 / vi 17 /
                     IV 15 / V 8; tonic verse 62 > chorus 42 > bridge 33 > pre 28,
                     pre-chorus IV 30), struck in a real 16-slot rhythm. About a
                     quarter of draws use F Am C G / G C F Am, the two GOOSEFISH
                     orderings no section in the library opens on

Chord tones are NOT forced (40% of real melody notes sit off the chord); the chord
under the landing does the answering. Layout is the settled one: marker == bar 1 ==
first chord, 8 bars per section, no gap, everything clipped at the section end.

    themap_venv/python jumbler.py                 # 20 draws, random seed
    themap_venv/python jumbler.py --n 30 --seed 7 --bpm 92
"""
import os, re, sys, json, random, argparse, collections
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of
from melody_bar_words import letter

OUT = os.path.expanduser('~/Desktop/jumble')
WORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chord_words.json')
DEG = {str(i): i - 1 for i in range(1, 8)}

# chord name in C major -> Hookpad fields. Applied chords are always major.
CHORD = {'C': dict(root=1), 'Dm': dict(root=2), 'Em': dict(root=3), 'F': dict(root=4),
         'G': dict(root=5), 'Am': dict(root=6), 'D': dict(root=5, applied=5),
         'E': dict(root=5, applied=6), 'A': dict(root=5, applied=2),
         'A#': dict(root=7, borrowed='mixolydian')}
FUNC = {'C': 'I', 'Am': 'vi', 'F': 'IV', 'G': 'V'}
# opening-chord shares over 1,991 sections; "other" covers every remaining chord
OPEN = {'I': .48, 'vi': .17, 'IV': .15, 'V': .08, 'other': .12}
TONIC = {'verse': .62, 'chorus': .42, 'bridge': .33, 'pre-chorus': .28}
ROLES = ['verse', 'verse', 'chorus', 'chorus', 'pre-chorus', 'bridge']
# the 16-slot chord-change vocabulary, eighths over two bars (music_rhythm_slots)
SLOTS = [((0, 8), 653), ((0,), 467), ((0, 4, 8, 12), 285), ((0, 4, 8), 204),
         ((0, 8, 12), 202), ((0, 3, 8, 11), 56), ((0, 12), 49), ((0, 7), 37)]
UNUSED = [['F', 'Am', 'C', 'G'], ['G', 'C', 'F', 'Am']]
LO, HI = -3, 10          # melody range in scale steps from C4: A3 .. E5

def num(x): return int(x) if float(x).is_integer() else round(float(x), 4)

def idx(n):
    s = str(n.get('sd', ''))
    return n.get('octave', 0) * 7 + DEG[s] if s in DEG else None

# ---------------------------------------------------------------- harvest
def harvest():
    """One pass over the corpus: real words, real bars by letter, real steps."""
    words, bars, steps, lands = [], collections.defaultdict(list), [], collections.Counter()
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if not notes: continue
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, d.get('endBeat') or 10**9)
            if int((end - b0) // 4) != 8: continue
            inn = [n for n in notes if b0 <= n['beat'] < b0 + 32]
            if len(inn) < 6: continue
            used.add(role)
            per = []
            for m in range(8):
                lo = b0 + m * 4
                # confined to the bar, so the letter survives the transplant
                bar = [dict(n, beat=n['beat'] - lo, duration=min(n['duration'], 4 - (n['beat'] - lo)))
                       for n in inn if lo <= n['beat'] < lo + 4]
                per.append(bar)
            words.append(''.join(letter(b) for b in per))
            if corpus.mode_at(d, b0) != 'major': continue      # pitch material: major only
            prev = None
            for m, bar in enumerate(per):
                p = [idx(n) for n in bar]
                if not bar or any(x is None for x in p):
                    prev = None; continue
                # one voice only, no octave-plus jumps: harmony voices share an onset
                # and are not a melody (corpus.py rule 4)
                if (len({n['beat'] for n in bar}) < len(bar)
                        or any(abs(y - x) > 7 for x, y in zip(p, p[1:]))):
                    prev = None; continue
                bars[letter(bar)].append(tuple((n['beat'], n['duration'], x)
                                               for n, x in zip(bar, p)))
                if prev is not None: steps.append(p[0] - prev)
                prev = p[-1]
                if m in (3, 7) and letter(bar) == 'H':
                    lands[max(zip([n['duration'] for n in bar], p))[1] % 7] += 1
    steps = [s for s in steps if abs(s) <= 7]
    return words, bars, steps, lands

# ---------------------------------------------------------------- melody
def restate(first, rnd, words):
    """Second-half word: AA, AA' (bar 8 most often), or a real second half."""
    r = rnd.random()
    if r < .326: return first, "AA"
    if r < .616:
        i = 3 if rnd.random() < .538 else rnd.randrange(3)
        a = first[i]
        swap = {'M': 'H', 'H': 'M'}.get(a)
        b = swap if swap and rnd.random() < .56 else rnd.choice([x for x in 'HM.' if x != a])
        return first[:i] + b + first[i+1:], "AA'"
    return rnd.choice(words)[4:], "AB"

def walk(letters, bars, steps, rnd, start, span=(-4, 6)):
    """Chain real bars: each bar starts a real inter-bar step from the last note.
    Redraw until the half stays within about an octave and a third of where it
    began -- unbounded steps drift, which is the perm_melody bug again."""
    out, cur = [], start
    for L in letters:
        if L == '.' and rnd.random() < .25:
            out.append(()); continue                   # a fully empty bar of air
        for _ in range(60):
            bar = rnd.choice(bars[L])
            shift = (cur + rnd.choice(steps) if any(out) else start) - bar[0][2]
            new = tuple((b, d, x + shift) for b, d, x in bar)
            if all(start + span[0] <= x <= start + span[1] for _, _, x in new): break
        out.append(new); cur = new[-1][2]
    return out

def land_note(half):
    """(bar, i) of the phrase-end landing: the longest note of bar 4, else bar 3."""
    for m in (3, 2):
        if half[m]:
            i = max(range(len(half[m])), key=lambda k: (half[m][k][1], k))
            return m, i
    return None

def last(half):
    return next((bar[-1][2] for bar in reversed(half) if bar), None)

def transpose(half, k):
    return [tuple((b, d, x + k) for b, d, x in bar) for bar in half]

def fit(half, target, prev=None):
    """Transpose the half by scale steps so its landing hits `target` (mod 7), choosing
    the octave that keeps the line most inside the range and, for a second half, the
    one that joins the first half without a leap past a fifth."""
    ln = land_note(half)
    if ln is None: return half
    m, i = ln
    base = target - half[m][i][2] % 7 - (half[m][i][2] // 7) * 7
    pitches = [x for bar in half for _, _, x in bar]
    best = min((base + 7 * o for o in range(-3, 4)),
               key=lambda k: sum(max(0, LO - (x + k)) + max(0, x + k - HI) for x in pitches)
                             + abs(sum(pitches) / len(pitches) + k - 3) * .01
                             + (max(0, abs(pitches[0] + k - prev) - 4) if prev is not None else 0))
    return transpose(half, best)

def melody(rnd, H):
    words, bars, steps, lands = H
    first = rnd.choice(words)[:4]
    second, form = restate(first, rnd, words)
    land = rnd.choices(list(lands), weights=list(lands.values()))[0]
    a = fit(walk(first, bars, steps, rnd, 2), land)
    if form == "AA":
        b = [bar for bar in a]
    else:
        land8 = land if rnd.random() < .602 else rnd.choices(list(lands), weights=list(lands.values()))[0]
        if form == "AA'":
            b = list(a)
            i = next(k for k in range(4) if first[k] != second[k])
            nb = walk([second[i]], bars, steps, rnd, 0)[0]
            if nb:   # join the new bar to whatever precedes it
                prev = next((bar[-1][2] for bar in reversed(b[:i] if i else a) if bar), 2)
                nb = tuple((t, d, x - nb[0][2] + prev + rnd.choice(steps)) for t, d, x in nb)
                # the restated bars keep their pitches; only a new bar 8 is moved,
                # so it lands (bars 1-3 changed -> bar 8 still restates bar 4)
                if i == 3: nb = fit([(), (), (), nb], land8, prev)[3]
                else:
                    land8 = land
                    while max(x for *_, x in nb) > HI: nb = transpose([nb], -7)[0]
                    while min(x for *_, x in nb) < LO: nb = transpose([nb], 7)[0]
            elif i != 3: land8 = land
            b[i] = nb
        else:
            b = fit(walk(second, bars, steps, rnd, 2), land8, last(a))
        land = (land, land8)
    return first + second, form, land, a + b

# ---------------------------------------------------------------- chords
def chords_for(rnd, role, words):
    if rnd.random() < .25:
        return 'GOOSEFISH*', list(rnd.choice(UNUSED))
    name = rnd.choice(sorted(words))
    chs = list(words[name])
    w = {}
    for c in chs:
        f = FUNC.get(c, 'other')
        if f == 'I': w[c] = TONIC[role]
        elif role == 'pre-chorus' and f == 'IV': w[c] = .30
        else: w[c] = OPEN[f] / (1 - OPEN['I']) * (1 - TONIC[role])
    first = rnd.choices(chs, weights=[w[c] for c in chs])[0]
    rest = [c for c in chs if c != first]; rnd.shuffle(rest)
    return name, [first] + rest

def chord(name, beat, dur):
    c = CHORD[name]
    return {"root": c['root'], "beat": num(beat), "duration": num(dur), "type": 5,
            "inversion": 0, "applied": c.get('applied', 0), "adds": [], "omits": [],
            "alterations": [], "suspensions": [], "substitutions": [], "pedal": None,
            "alternate": "", "borrowed": c.get('borrowed', ''), "isRest": False,
            "recordingEndBeat": None}

# ---------------------------------------------------------------- build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--bpm', type=int, default=100)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randrange(10**4)
    rnd = random.Random(seed)
    H = harvest()
    print(f"  harvested {len(H[0])} words, "
          + ', '.join(f"{len(v)} {k!r}-bars" for k, v in sorted(H[1].items()))
          + f", {len(H[2])} bar-to-bar steps")
    cw = {k: v for k, v in json.load(open(WORDS)).items()
          if len(v) == 4 and all(c in CHORD for c in v)}

    notes, chords, secs, rows = [], [], [], []
    for s in range(a.n):
        at = 1 + s * 32
        role = rnd.choice(ROLES)
        word, form, land, mel = melody(rnd, H)
        cname, order = chords_for(rnd, role, cw)
        slots = rnd.choices([p for p, _ in SLOTS], weights=[w for _, w in SLOTS])[0]
        # chords: cycle the order through the strike rhythm, two bars at a time
        k = 0
        for w in range(4):
            for j, sl in enumerate(slots):
                nxt = slots[j + 1] if j + 1 < len(slots) else 16
                chords.append(chord(order[k % 4], at + w * 8 + sl / 2, (nxt - sl) / 2)); k += 1
        # melody, clipped against the next onset and the section end
        flat = [(at + m * 4 + b, d, x) for m, bar in enumerate(mel) for b, d, x in bar]
        for i, (b, d, x) in enumerate(flat):
            stop = min(flat[i + 1][0] if i + 1 < len(flat) else at + 32, at + 32)
            notes.append({"sd": str(x % 7 + 1), "octave": x // 7, "beat": num(b),
                          "duration": num(min(d, stop - b)), "isRest": False,
                          "recordingEndBeat": None})
        ln = '-'.join(str(l + 1) for l in land) if isinstance(land, tuple) else str(land + 1)
        sl = ','.join(map(str, slots))
        label = f"{s+1:02} {role[:5]} {word} {form} L{ln} {'-'.join(order)} [{sl}]"
        secs.append({"beat": at, "name": label[:62]})
        rows.append((s + 1, role, word, form, ln, cname, order, sl))

    obj = {"version": 1, "chords": chords, "notes": notes,
           "keys": [{"beat": 1, "scale": "major", "tonic": "C"}],
           "tempos": [{"beat": 1, "bpm": a.bpm, "swingBeat": 0.5, "swingFactor": 0}],
           "meters": [{"beat": 1, "numBeats": 4, "beatUnit": 1}], "breaks": [],
           "sections": secs, "endBeat": 1 + a.n * 32, "audioTracks": []}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"jumble_seed{seed}.txt")
    open(path, 'w').write(hp3.clipboard(obj))

    print(f"\n  {'#':>2} {'role':10} {'bar word':9} {'form':4} {'land':5} {'chords':22} rhythm")
    for n, role, word, form, ln, cname, order, sl in rows:
        print(f"  {n:2} {role:10} {word:9} {form:4} {ln:5} {' '.join(order):13} "
              f"{cname[:8]:8} [{sl}]")
    readback(path, H[0])
    print(f"\n  -> {path}")

# ---------------------------------------------------------------- read-back
def readback(path, words):
    """Measure the paste as written, not as intended."""
    d = json.load(open(path))
    secs = [s['beat'] for s in d['sections']] + [d['endBeat']]
    spill = sum(1 for x in d['notes'] + d['chords']
                for a, b in zip(secs, secs[1:])
                if a <= x['beat'] < b and x['beat'] + x['duration'] > b + 1e-9)
    down = sum(1 for c in d['chords'] if (c['beat'] - 1) % 4 == 0) / len(d['chords'])
    first = sum(1 for a in secs[:-1] if any(c['beat'] == a for c in d['chords']))
    got, aa = [], 0
    for a in secs[:-1]:
        w = ''.join(letter([n for n in d['notes'] if a + m*4 <= n['beat'] < a + m*4 + 4])
                    for m in range(8))
        got.append(w); aa += sum(x != y for x, y in zip(w[:4], w[4:])) <= 1
    air = collections.Counter(i for w in got for i, c in enumerate(w) if c == '.')
    real = collections.Counter(i for w in words for i, c in enumerate(w) if c == '.')
    print(f"\n  read-back: {len(d['notes'])} notes, {len(d['chords'])} chords, "
          f"{len(secs)-1} sections")
    print(f"    spills across a marker        {spill}")
    print(f"    first chord on the marker     {first}/{len(secs)-1}")
    print(f"    chords on a bar downbeat      {100*down:.0f}%   (corpus 65%)")
    print(f"    AA or AA' (by re-read word)   {100*aa/len(got):.0f}%   (corpus 61.6%)")
    print(f"    air by bar, batch vs corpus   " + '  '.join(
        f"{m+1}:{100*air[m]/len(got):.0f}/{100*real[m]/len(words):.0f}" for m in range(8)))

if __name__ == '__main__':
    main()
