"""A melody over a permuted chord section — the second pillar for chord_perms.

The chord folders sweep every ordering of a palette through one rhythm. This puts
a PHRASE over them, so a paste is a part (progression + melody) rather than a
chord chart. The phrase is fixed in SHAPE and re-pitched per perm: each note
snaps to a chord tone of whatever chord is sounding under it, so one phrase gets
360 harmonisations and you hear the ordering, not a clash.

Four dials, same vocabulary as build_blocks.py (memory music_block_system):
    focus     the reciting tone — scale degree 1-7 the phrase orbits
    register  octave band: 0 = home (middle C octave), -1 low, +1 high
    motion    how it moves around the focus: orbit | arch | descend | rise
    cells     one rhythm cell per bar, cycled to fill the phrase

Cells are onsets in SIXTEENTHS within the bar — the same grid melody_rhythm.py
measured (85% of real notes on a beat or its "and", 15% on a sixteenth).

    spec: <focus>:<register>:<motion>:<cell>-<cell>...     e.g. 3:0:orbit:walk-hold
"""
import math, re, sys

CELLS = {
    'long':    [0],                             # one note, the whole bar
    'hold':    [0, 8],                          # two halves
    'walk':    [0, 4, 8, 12],                   # four quarters
    'dot':     [0, 6, 8, 12],                   # dotted-quarter lean
    'skip':    [0, 4, 10],                      # quarter, quarter, pushed
    'eighths': [0, 2, 4, 6, 8, 10, 12, 14],
    'anac':    [6, 8, 12],                      # enters late — an answer bar
    'rest':    [],                              # silence
}
MOTIONS = ('orbit', 'arch', 'descend', 'rise')
# Successive notes inside a bar step through the sounding chord's tones by these
# offsets, so repeated onsets move instead of hammering one pitch. Orbit turns
# around the focus; the contour motions lean the way they are already going.
TURN = {'orbit': (0, 1, 0, -1), 'arch': (0, 1), 'descend': (0, -1), 'rise': (0, 1)}
SPEC = re.compile(r'^([1-7]):(-?[012]):([a-z]+):([a-z]+(?:-[a-z]+)*)$')

def parse(spec):
    """'3:0:orbit:walk-hold' -> (focus, register, motion, [cell names])."""
    m = SPEC.match(spec)
    if not m:
        sys.exit(f"{spec}: want <focus 1-7>:<register -1..1>:<motion>:<cells>, "
                 f"e.g. 3:0:orbit:walk-hold")
    focus, register, motion, cells = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4).split('-')
    if motion not in MOTIONS:
        sys.exit(f"{spec}: motion must be one of {', '.join(MOTIONS)}")
    bad = [c for c in cells if c not in CELLS]
    if bad:
        sys.exit(f"{spec}: unknown cell(s) {', '.join(bad)}; have {', '.join(CELLS)}")
    return focus, register, motion, cells

def _ctones(root):
    """Pitch indices (octave*7 + degree-1) of the triad on this scale degree."""
    sds = [root, ((root - 1 + 2) % 7) + 1, ((root - 1 + 4) % 7) + 1]
    return sorted({t - 1 + 7*k for t in sds for k in range(-2, 3)})

# Measured move distribution — melody_moves.py over 409,282 corpus transitions.
# A melody almost never goes anywhere new: 88.9% of its moves circulate inside the
# pitches the section has already claimed. So the walker picks a MOVE CLASS against
# what it has used, rather than a step size in the abstract.
MOVES = {
    'corpus':     {'repeat':.337, 'step-known':.303, 'step-new':.058,
                   'vault':.026, 'reach':.027, 'return':.249},
    'prechorus':  {'repeat':.364, 'step-known':.282, 'step-new':.080,
                   'vault':.037, 'reach':.034, 'return':.202},
}
FALLBACK = ('step-known', 'return', 'step-new', 'reach', 'repeat')
# Melodies are NOT chord-tone machines: 40.3% of corpus melody notes sit off the
# chord under them, 37.8% even among notes a beat or longer (the source melody for
# melody_mix is 56% / 79%). Requiring chord tones makes a single step impossible —
# chord tones are a third apart — which distorts the move distribution into leaps.
# So only the FIRST note is anchored to the chord; after that the move model rules.
RUN_CAP    = 3        # real melodies repeat in short bursts, not long stretches
SPAN       = 10       # keep the line inside a reasonable compass, in scale steps
# A section's melody lives in a SMALL pitch vocabulary: median 6 distinct pitches,
# p90 = 9, across 8,238 corpus sections. Without a cap the walker keeps discovering
# new pitches, which starves step-known (a step is only "known" if the neighbour is
# already in use) and inflates vault. The cap is what makes the vocabulary close.
VOCAB_CAP  = 7        # once this many pitches are used, stop finding new ones


def _ctone_set(root):
    return set(_ctones(root))

def _chordtone(p, root):
    """Nearest chord tone, preferring the smallest move."""
    return min(_ctones(root), key=lambda i: (abs(i - p), i))

def _candidates(kind, cur, used, run):
    """Pitches reachable by this move class from `cur`, given what is used."""
    if kind in ('step-new', 'vault', 'reach') and len(used) >= VOCAB_CAP:
        return []                     # the vocabulary is closed
    if kind == 'repeat':
        return [] if run >= RUN_CAP else [cur]
    if kind == 'step-known':
        return [p for p in (cur-1, cur+1) if p in used]
    if kind == 'step-new':
        return [p for p in (cur-1, cur+1) if p not in used]
    far = [p for p in range(cur-SPAN, cur+SPAN+1) if abs(p - cur) >= 2]
    if kind == 'return':
        return [p for p in far if p in used]
    out = []
    for p in far:
        if p in used:
            continue
        hurdled = any(q in used for q in range(min(p, cur)+1, max(p, cur)))
        if (kind == 'vault') == bool(hurdled):
            out.append(p)
    return out

def walk(rhythm, root_at, phrase_beats, focus, register, motion, rng, mix='corpus'):
    """The fixed rhythm, re-pitched by sampling measured move classes.
    rhythm: [(onset, duration)]. root_at(beat) -> scale degree of the chord."""
    weights = MOVES[mix]
    kinds = list(weights); probs = [weights[k] for k in kinds]
    home = register*7 + (focus - 1)
    cur = min(_ctones(root_at(0.0)), key=lambda i: abs(i - home))
    used, run, out = {cur}, 1, []

    for onset, dur in rhythm:
        root = root_at(onset % phrase_beats)
        target = home + _shape(motion, onset / max(1e-9, rhythm[-1][0]))
        structural = not out          # anchor the entry note, then let go

        pick = rng.choices(kinds, probs)[0]
        # try the sampled class first, then the others by weight, then the fixed
        # chain — re-sampling rather than always falling to step-known keeps the
        # generated distribution near the measured one
        order = [pick] + [k for k in rng.sample(kinds, len(kinds)) if k != pick] \
                + [k for k in FALLBACK]
        tones = _ctone_set(root) if structural else None
        cands = []
        for kind in order:
            c = _candidates(kind, cur, used, run)
            if structural:
                c = [p for p in c if p in tones]     # hard rule, never relaxed
            if c:
                cands = c
                break
        if not cands:
            cands = [_chordtone(target, root) if structural else cur]
        # among what this class allows, follow the contour
        best = min(abs(p - target) for p in cands)
        cur_next = rng.choice([p for p in cands if abs(p - target) <= best + 1])

        run = run + 1 if cur_next == cur else 1
        cur = max(-14, min(14, cur_next))
        used.add(cur)
        out.append({"sd": str((cur % 7) + 1), "octave": cur // 7, "beat": onset,
                    "duration": dur, "isRest": False, "recordingEndBeat": None})
    return out

def _pitch(desired, root, step, motion):
    """Nearest chord tone to `desired`, then moved `step` places along the chord."""
    ct = _ctones(root)
    base = min(range(len(ct)), key=lambda i: (abs(ct[i] - desired), ct[i]))
    turn = TURN[motion]
    return ct[max(0, min(len(ct) - 1, base + turn[step % len(turn)]))]

def _shape(motion, x):
    """Contour offset in scale steps, x running 0..1 across the phrase."""
    return {'orbit': 0.0, 'arch': 4*math.sin(math.pi*x),
            'descend': 4*(1 - x), 'rise': 4*x}[motion]

def phrase(slots, cast, phrase_beats, spec):
    """Notes for one statement. slots are (onset, dur, role, type, power) in beats.
    Returns Hookpad note dicts with beats relative to the statement start."""
    focus, register, motion, cells = parse(spec)
    bars = max(1, int(round(phrase_beats / 4)))
    home = register*7 + (focus - 1)

    def root_at(beat):
        """The chord sounding at this beat — the melody follows the perm."""
        live = [s for s in slots if s[0] <= beat + 1e-9 < s[0] + s[1]]
        s = live[-1] if live else min(slots, key=lambda s: abs(s[0] - beat))
        return cast[s[2]]

    notes = []
    for m in range(bars):
        onsets = CELLS[cells[m % len(cells)]]
        for j, slot in enumerate(onsets):
            beat = m*4 + slot/4.0
            nxt = onsets[j+1]/4.0 + m*4 if j+1 < len(onsets) else (m+1)*4
            dur = nxt - beat
            x = (m + slot/16.0) / max(1, bars)          # position across the phrase
            pitch = _pitch(home + _shape(motion, x), root_at(beat), j, motion)
            notes.append({"sd": str((pitch % 7) + 1), "octave": pitch // 7,
                          "beat": beat, "duration": dur,
                          "isRest": False, "recordingEndBeat": None})
    return notes

def label(spec):
    """Folder/section tag for a melody spec: 3:0:orbit:walk-hold -> mel3-0-orbit-walk-hold."""
    return 'mel' + spec.replace(':', '-')

# ---------------- landing-first ----------------
# The measured model (memory music_melody_model): an 8-bar melody is movement-
# movement-movement-BREAK, twice. Bar 4 is non-running 55% of the time and bar 8
# 60%, against ~36% elsewhere. The two break notes are the SAME scale degree 57%
# of the time (1->1 21%, 5->5 11%, 3->3 9%), and bar 8 resolves harder: degree 1
# in 33.7% vs bar 4's 26.8%. Everything between is transit — 51.8% of measures
# run, and only 1.9% of those are literal quarters.
LANDING_DEGREES = ((1, 0.34), (5, 0.20), (3, 0.14), (2, 0.13),
                   (6, 0.09), (4, 0.07), (7, 0.05))

def pick_landing(rng):
    """One degree, serving both breaks — the corpus's dominant choice."""
    ds, ws = zip(*LANDING_DEGREES)
    return rng.choices(ds, ws)[0]

def land_first(rhythm, root_at, phrase_beats, landing, register, rng,
               mix='corpus', break_bars=(4, 8)):
    """The fixed rhythm, pitched so the notes at the break bars ARE the landing.

    Bars are 1-indexed: break_bars=(4,8) means the last note starting inside bar 4
    and inside bar 8 is forced to `landing`; everything else walks toward whichever
    break comes next, so the movement arrives instead of wandering.
    """
    weights = MOVES[mix]
    kinds = list(weights); probs = [weights[k] for k in kinds]
    home = register*7 + (landing - 1)

    # Which note index is the landing in each break bar: the last onset inside it.
    # Bars are measured on the RHYTHM's own timeline — the melodic phrase is often
    # longer than the chord phrase, so onset % phrase_beats would wrap and lose bar 8.
    targets = {}
    for b in break_bars:
        lo, hi = (b-1)*4, b*4
        inside = [i for i, (o, _) in enumerate(rhythm) if lo <= o < hi]
        if not inside: continue
        # the LAST onset that is actually held — skip a short pickup at the bar end
        held = []
        for i in inside:
            o, du = rhythm[i]
            nxt = rhythm[i+1][0] if i+1 < len(rhythm) else o + du
            if du >= 1 or (nxt - o) >= 1: held.append(i)
        targets[(held or inside)[-1]] = home

    cur = home
    used, run, out = {cur}, 1, []
    for j, (onset, dur) in enumerate(rhythm):
        root = root_at(onset % phrase_beats)
        if j in targets:                       # a break note: the landing, no argument
            cand = targets[j]
        else:
            nxt = min((i for i in targets if i > j), default=None)
            aim = targets[nxt] if nxt is not None else home
            pull_steps = max(1, (nxt - j)) if nxt is not None else 8
            target = cur + (aim - cur) / pull_steps      # close the gap gradually
            pick = rng.choices(kinds, probs)[0]
            order = [pick] + [k for k in rng.sample(kinds, len(kinds)) if k != pick] + list(FALLBACK)
            cands = []
            for kind in order:
                c = _candidates(kind, cur, used, run)
                if c: cands = c; break
            if not cands: cands = [cur]
            best = min(abs(p - target) for p in cands)
            cand = rng.choice([p for p in cands if abs(p - target) <= best + 1])
        run = run + 1 if cand == cur else 1
        cur = max(-14, min(14, cand))
        used.add(cur)
        out.append({"sd": str((cur % 7) + 1), "octave": cur // 7, "beat": onset,
                    "duration": dur, "isRest": False, "recordingEndBeat": None})
    return out
