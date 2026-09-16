"""Pattern detectors for 12-bar sections (48 beats in 4/4).

12-bar is the home of the blues. Natural shapes:
  - 12-bar blues (classic I-I-I-I / IV-IV-I-I / V-IV-I-I)
  - 6+6 halves
  - 4+4+4 thirds (AAA / AAB / ABC at 4-bar grain)
  - AAB blues form
  - 8+4 (8-bar phrase + 4-bar tag)

Imports shared helpers + progression detectors from detect_patterns.py.
Output: ~/Desktop/glowinggardens_claude/_music/twelve_bar_patterns.json
"""
import os, json
from collections import defaultdict
from detect_patterns import (
    chord_key, root_of, per_beat_chords, chord_changes,
    detect_axis, detect_doowop, detect_pachelbel, detect_ii_V_I,
    detect_mixolydian, detect_andalusian, detect_descent,
)

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/twelve_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/twelve_bar_patterns.json'

BEATS = 48       # 12 bars × 4 beats
HALF = 24        # 6 bars
THIRD = 16       # 4 bars (= one phrase in AAB)
BAR = 4


def detect_full_half_repeat(pb):
    """First 6 bars = last 6 bars."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:HALF] == pb[HALF:BEATS]


def detect_thirds_repeat(pb):
    """All three 4-bar phrases identical — AAA at 4-bar grain."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    p1 = pb[:THIRD]
    return pb[THIRD:2*THIRD] == p1 and pb[2*THIRD:3*THIRD] == p1


def detect_aab_4bar(pb):
    """AAB at 4-bar grain — bars 1-4 = bars 5-8 (A), bars 9-12 differ (B).
    Classic 12-bar blues macro-form."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a = pb[:THIRD]
    return pb[THIRD:2*THIRD] == a and pb[2*THIRD:3*THIRD] != a


def detect_aab_4bar_loose(pb):
    """AAB at 4-bar grain — loose: first bar of A1 = first bar of A2, B differs.
    Catches AAB with melodic variation across the two A's."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a1 = pb[0:BAR]
    return pb[THIRD:THIRD+BAR] == a1 and pb[2*THIRD:2*THIRD+BAR] != a1


def detect_aba_4bar(pb):
    """ABA at 4-bar grain — sandwich (bars 1-4 = bars 9-12, middle 4 differ)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a = pb[:THIRD]
    return pb[2*THIRD:3*THIRD] == a and pb[THIRD:2*THIRD] != a


def detect_abc_4bar(pb):
    """All three 4-bar phrases pairwise distinct — through-composed."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    p1, p2, p3 = pb[:THIRD], pb[THIRD:2*THIRD], pb[2*THIRD:3*THIRD]
    return p1 != p2 and p2 != p3 and p1 != p3


def detect_8_4_phrase(pb):
    """First 8 bars = a coherent shape (bars 1-4 = bars 5-8), last 4 bars differ."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[0:16] == pb[16:32] and pb[0:16] != pb[32:48]


def detect_12bar_blues(pb):
    """Classic 12-bar blues structure (per-beat granularity loose):
    bars 1-4: I, bars 5-6: IV, bars 7-8: I, bars 9: V, bar 10: IV, bars 11-12: I (or V turnaround).
    Match on chord roots being [1,1,1,1, 4,4,1,1, 5,4,1,1] or close variants."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    # Reduce to one chord per bar
    bars = []
    for m in range(12):
        b = pb[m*BAR:(m+1)*BAR]
        # take the modal (most common) chord in this bar
        from collections import Counter
        c = Counter(b)
        bars.append(c.most_common(1)[0][0])
    # Convert chord_keys to root integers
    roots = [root_of(k) for k in bars]
    if None in roots: return False
    # Classic 12-bar blues (allow either I or V in bar 12)
    target_a = [1,1,1,1, 4,4,1,1, 5,4,1,1]
    target_b = [1,1,1,1, 4,4,1,1, 5,4,1,5]   # V turnaround
    return roots == target_a or roots == target_b


def detect_drone(pb):
    nn = [b for b in pb if b is not None]
    if not nn: return False
    counts = defaultdict(int)
    for b in nn: counts[b] += 1
    return max(counts.values()) / len(nn) >= 0.75


def detect_two_chord(pb):
    return len(set(b for b in pb if b is not None)) == 2


def detect_walking(changes):
    return len(set(changes)) >= 9


def detect_one_per_bar_no_repeat(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bars = []
    for m in range(12):
        b = pb[m*BAR:(m+1)*BAR]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 12):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(pb):
    """Bars 11-12 are tonic, bar 10 has no tonic."""
    if len(pb) < BEATS: return False
    last_two = pb[BEATS-8:BEATS]
    bar_before = pb[BEATS-12:BEATS-8]
    if any(b is None for b in last_two + bar_before): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in last_two) and not any(is_tonic(b) for b in bar_before)


DETECTORS = [
    # Progressions
    ('axis (I-V-vi-IV)',         'roots',    lambda r: detect_axis(r)),
    ('doo-wop (I-vi-IV-V)',      'roots',    lambda r: detect_doowop(r)),
    ('pachelbel/8-chord',        'roots',    lambda r: detect_pachelbel(r)),
    ('ii-V-I',                   'roots',    lambda r: detect_ii_V_I(r)),
    ('andalusian (i-bVII-bVI-V)','roots',    lambda r: detect_andalusian(r)),
    ('mixolydian (bVII-IV)',     'changes',  lambda c: detect_mixolydian(c)),
    ('stepwise descent (4+)',    'roots',    lambda r: detect_descent(r)),
    # 12-bar-specific form shapes
    ('12-bar blues',             'per_beat', detect_12bar_blues),
    ('full 6+6 repeat',          'per_beat', detect_full_half_repeat),
    ('AAA (4-bar phrases)',      'per_beat', detect_thirds_repeat),
    ('AAB (4-bar phrases)',      'per_beat', detect_aab_4bar),
    ('AAB loose (4-bar)',        'per_beat', detect_aab_4bar_loose),
    ('ABA (4-bar phrases)',      'per_beat', detect_aba_4bar),
    ('ABC (4-bar phrases)',      'per_beat', detect_abc_4bar),
    ('8+4 phrase',               'per_beat', detect_8_4_phrase),
    ('ends on I (arrival)',      'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats',  'per_beat', detect_one_per_bar_no_repeat),
    # Density
    ('one-chord drone',          'per_beat', detect_drone),
    ('two-chord vamp',           'per_beat', detect_two_chord),
    ('walking (9+ changes)',     'changes',  detect_walking),
]


def main():
    sections = json.load(open(SRC))
    sections = [s for s in sections if (s['end'] - s['start']) == BEATS]
    print(f'{len(sections)} 12-bar sections (48-beat 4/4)\n')

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
            except Exception: pass
        out.append({**sec, 'changes': changes, 'patterns': patterns})
        if patterns: sections_with_any += 1

    print(f'{sections_with_any}/{len(sections)} sections matched ≥1 pattern\n')
    print(f'  {"pattern":30s} {"count":>6}  {"%":>6}')
    for name, _, _ in DETECTORS:
        c = pattern_counts[name]
        print(f'  {name:30s} {c:>6}  {100*c/max(1,len(sections)):>5.1f}%')

    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'))
    print(f'\nout → {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)')


if __name__ == '__main__': main()
