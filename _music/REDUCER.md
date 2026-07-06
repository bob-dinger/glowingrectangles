# The Harmonic Reducer — how it works

Turns a real melody into its **essence**: one "main note" per chord (or per measure),
i.e. the note-against-each-chord line. Tempo + chords + these main notes = the
reduced score / "napkin score" of a section. Code: `skeleton.simplify_harmonic()`.
Dev loop: hand-bones in `harmonic_examples.json`, scored by `validate_harmonic.py`
(currently ~97% mean pitch vs the user's own reductions).

## Input
- `notes` — the melody: each `{sd (scale degree), octave, beat, duration}` (rests dropped).
- `chords` — each `{root, beat, ...}`. Beats are the harmonic grid.

## The one rule
Walk the **grid** (one slot per chord, or per measure). For each slot, choose the
**main note** by one of two picks. Then optionally clean up (merge / fill).

### Step 1 — build the grid (`grid` knob)
The slots we place a note on:
- **chord grid (default):** one slot per chord entry (`cbs = every chord's beat`).
  Repeated roots still each get a slot (ii7 ii7 = two slots) — do NOT dedupe
  (deduping collapsed Choosin' Texas's `2 3` statement rise; wrong).
- **measure grid (`measure=N`):** one slot per N-beat bar. Use when chords change
  more than once a bar (half-measure chords) but the melody reduces per full bar —
  e.g. song16 (I 2.5 / ♭VII 1.5 per bar, reduced per bar).
- `dedupe=True` (rarely) = collapse consecutive same-identity chords to real
  root-changes only.

### Step 2 — pick the main note per slot (`pick` knob)
For slot at beat `cb` (next slot at `hi`):

- **`downbeat` (default):** the note **sounding at the downbeat** `cb` —
  its onset is at/just-before `cb` and it sustains ACROSS it
  (`onset <= cb < onset+duration`). This makes a PUSHED/anticipated note count
  (it's tied over the downbeat) but a note that merely ENDS on the downbeat (a
  phrase tail) does NOT. If nothing sounds at `cb`, take the first note onsetting
  after it. Rule of thumb the user gave: *"one note per measure = the first note
  of the measure, wherever it sits."*

- **`longest` = ARRIVAL:** the **dominant long note** of the bar
  (`max duration` among notes onsetting in `[cb-0.5, hi-0.5)`). Use for the
  "anacrusis → long held note" structure, where each bar is short pickups launching
  into one sustained note the chord lands under — e.g. Country Roads chorus.

### Step 3 — clean up (optional)
- **`merge=True`** — collapse consecutive same-pitch main notes into one held note
  (Broken `5 5 → 5`). Song-dependent (a-little-help keeps repeated notes as a
  rhythmic figure), so it's a knob, not default.
- **`fill=True`** — stretch each main note to the next one's onset (note-per-chord
  held its full length). Makes the reduction look like the user's "held bones";
  off by default (keeps the picked note's real duration).

## Auto-detecting the knobs (in `find_structures.py`)
So the reducer can run unattended:
- **grid:** if `#chords > #bars * 1.4` → sub-bar chords → use **measure** grid; else chord grid.
- **pick:** for each bar, is there one note ≥2× the median duration and ≥ half a bar?
  If ≥50% of bars have such a dominant long note → **`longest`**; else `downbeat`.

## What comes after (structure classification)
The reduced main-note line gets tagged on two independent axes:
- **CONTOUR** — shape: arch / descent / ascent / oscillation / pedal / valley / wander.
- **MOTIF** — repetition: periodic cell (`cellKxN`) / parallel halves / oscillating / through-composed.
A section's fingerprint = `CONTOUR × MOTIF` (e.g. Country Roads verse = oscillation × cell4x2).
The "stack" etc. are a third, phrase-structure axis (statement/answer repetition) — see music_stack_form.

## How to tweak
1. Edit the rule in `skeleton.simplify_harmonic()` (Step 2 is where the judgment lives).
2. Add the disagreeing example (real + your hand-bones) to `harmonic_examples.json`
   (fields: `real`, `chords`, `bones`, optional `measure`, `pick`).
3. Re-run `validate_harmonic.py` — it tries both picks/merge and reports the best per song.
   Watch the mean pitch move. Ship the rule that lifts the corpus without regressing others.

## Known open edges
- **Cadence tails** — Broken (88%) / Choosin (97%): the tool trims the last note or
  two differently than the user. Endings need work.
- **Held-over nuance** — if the note sounding at a downbeat is just a long hold carried
  over from before, the user grabs the measure's first FRESH note instead. Not yet
  implemented (no example has forced it).
- **wander bucket (22%)** — through-composed lines a simple contour can't name; likely
  where genuinely melodic sections and reducer noise both hide.
