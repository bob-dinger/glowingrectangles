"""Pattern detectors for 24-bar sections. The natural phrase grains are:
  - 8-bar (AAB form / 24-bar blues — 3 phrases of 8 bars)
  - 6-bar (AABA-style with 6-bar phrases — 4 phrases of 6 bars)
  - 12-bar (half-repeat shape)

Imports shared helpers + progression detectors from detect_patterns.py.
Output: ~/Desktop/glowinggardens_claude/_music/twenty_four_bar_patterns.json
"""
import os, json
from collections import defaultdict
from detect_patterns import (
    chord_key, root_of, per_beat_chords, chord_changes,
    detect_axis, detect_doowop, detect_pachelbel, detect_ii_V_I,
    detect_mixolydian, detect_andalusian, detect_descent,
)

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/twenty_four_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/twenty_four_bar_patterns.json'

BEATS = 96         # 24 bars × 4
HALF = 48          # 12 bars
THIRD = 32         # 8 bars
QUARTER = 24       # 6 bars
BAR = 4

# === Form shapes ===

def detect_full_half_repeat(pb):
    """First 12 bars = second 12 bars."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:HALF] == pb[HALF:BEATS]


def detect_thirds_repeat(pb):
    """All three 8-bar thirds identical — 8-bar idea × 3 (8+8+8)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    t1 = pb[:THIRD]
    return pb[THIRD:2*THIRD] == t1 and pb[2*THIRD:3*THIRD] == t1


def detect_aab_8bar(pb):
    """AAB at 8-bar grain — 24-bar blues form: first 8 bars = middle 8 bars, last 8 differ.
    Loose match (first bar of each A matches) for 1st/2nd ending tolerance."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bar1_a1 = pb[0:BAR]
    return (pb[THIRD:THIRD+BAR] == bar1_a1 and pb[2*THIRD:2*THIRD+BAR] != bar1_a1)


def detect_quarters_repeat(pb):
    """All four 6-bar quarters identical — 6-bar idea × 4."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    q1 = pb[:QUARTER]
    return all(pb[i*QUARTER:(i+1)*QUARTER] == q1 for i in range(1, 4))


def detect_aaba_6bar(pb):
    """AABA at 6-bar phrase grain. Loose: first bar of each phrase matches."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bar1_a1 = pb[0:BAR]
    return (pb[QUARTER:QUARTER+BAR] == bar1_a1 and
            pb[3*QUARTER:3*QUARTER+BAR] == bar1_a1 and
            pb[2*QUARTER:2*QUARTER+BAR] != bar1_a1)


def detect_aaab_6bar(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a = pb[0:QUARTER]
    return (pb[QUARTER:2*QUARTER] == a and
            pb[2*QUARTER:3*QUARTER] == a and
            pb[3*QUARTER:4*QUARTER] != a)


def detect_abab_6bar(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b = pb[0:QUARTER], pb[QUARTER:2*QUARTER]
    return (pb[2*QUARTER:3*QUARTER] == a and pb[3*QUARTER:4*QUARTER] == b and a != b)


def detect_abad_6bar(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b, d = pb[0:QUARTER], pb[QUARTER:2*QUARTER], pb[3*QUARTER:4*QUARTER]
    return (pb[2*QUARTER:3*QUARTER] == a and a != b and a != d and b != d)


def detect_abcd_6bar(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    blocks = [pb[i*QUARTER:(i+1)*QUARTER] for i in range(4)]
    for i in range(4):
        for j in range(i+1, 4):
            if blocks[i] == blocks[j]: return False
    return True


# === Density / shape ===

def detect_drone(pb):
    nn = [b for b in pb if b is not None]
    if not nn: return False
    counts = defaultdict(int)
    for b in nn: counts[b] += 1
    return max(counts.values()) / len(nn) >= 0.75


def detect_two_chord(pb):
    distinct = set(b for b in pb if b is not None)
    return len(distinct) == 2


def detect_walking_long(changes):
    """18+ distinct chords across a 24-bar section."""
    return len(set(changes)) >= 18


def detect_one_per_bar_no_repeat(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bars = []
    for m in range(24):
        b = pb[m*BAR:(m+1)*BAR]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 24):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(pb):
    """Last 2 bars are tonic, bar 22 (3rd-to-last) has no tonic."""
    if len(pb) < BEATS: return False
    last_two = pb[BEATS-8:BEATS]
    bar_before = pb[BEATS-12:BEATS-8]
    if any(b is None for b in last_two + bar_before): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in last_two) and not any(is_tonic(b) for b in bar_before)


DETECTORS = [
    # Progressions (same as 8/16-bar)
    ('axis (I-V-vi-IV)',         'roots',    lambda r: detect_axis(r)),
    ('doo-wop (I-vi-IV-V)',      'roots',    lambda r: detect_doowop(r)),
    ('pachelbel/8-chord',        'roots',    lambda r: detect_pachelbel(r)),
    ('ii-V-I',                   'roots',    lambda r: detect_ii_V_I(r)),
    ('andalusian (i-bVII-bVI-V)','roots',    lambda r: detect_andalusian(r)),
    ('mixolydian (bVII-IV)',     'changes',  lambda c: detect_mixolydian(c)),
    ('stepwise descent (4+)',    'roots',    lambda r: detect_descent(r)),
    # Form shapes
    ('full 12+12 repeat',        'per_beat', detect_full_half_repeat),
    ('8+8+8 repeat',             'per_beat', detect_thirds_repeat),
    ('AAB (8-bar phrases)',      'per_beat', detect_aab_8bar),
    ('6+6+6+6 repeat',           'per_beat', detect_quarters_repeat),
    ('AABA (6-bar phrases)',     'per_beat', detect_aaba_6bar),
    ('AAAB (6-bar phrases)',     'per_beat', detect_aaab_6bar),
    ('ABAB (6-bar phrases)',     'per_beat', detect_abab_6bar),
    ('ABAD (6-bar phrases)',     'per_beat', detect_abad_6bar),
    ('ABCD (6-bar phrases)',     'per_beat', detect_abcd_6bar),
    ('ends on I (arrival)',      'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats',  'per_beat', detect_one_per_bar_no_repeat),
    # Density
    ('one-chord drone',          'per_beat', detect_drone),
    ('two-chord vamp',           'per_beat', detect_two_chord),
    ('walking (18+ changes)',    'changes',  detect_walking_long),
]


def main():
    sections = json.load(open(SRC))
    sections = [s for s in sections if (s['end'] - s['start']) == BEATS]
    print(f'{len(sections)} 24-bar sections (96-beat 4/4)\n')

    out = []
    pattern_counts = defaultdict(int)
    sections_with_any = 0

    for sec in sections:
        per_beat = per_beat_chords(sec)
        changes = chord_changes(per_beat)
        roots = [root_of(k) for k in changes if root_of(k) is not None]

        patterns = []
        args = {'per_beat': per_beat, 'changes': changes, 'roots': roots}
        for name, kind, fn in DETECTORS:
            try:
                if fn(args[kind]):
                    patterns.append(name)
                    pattern_counts[name] += 1
            except Exception:
                pass

        out.append({**sec, 'changes': changes, 'patterns': patterns})
        if patterns: sections_with_any += 1

    print(f'{sections_with_any}/{len(sections)} sections matched ≥1 pattern\n')
    print(f'  {"pattern":30s} {"count":>6}  {"%":>6}')
    for name, _, _ in DETECTORS:
        c = pattern_counts[name]
        print(f'  {name:30s} {c:>6}  {100*c/len(sections):>5.1f}%')

    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'))
    print(f'\nout → {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)')


if __name__ == '__main__': main()
