"""Pattern detectors for 10-bar sections (40 beats in 4/4).

10-bar is an odd form — common shapes:
  - 5+5 halves (folk/country style verse)
  - 4+4+2 (8-bar phrase + 2-bar tag)
  - 2+2+2+2+2 (five 2-bar blocks)

Imports shared helpers + progression detectors from detect_patterns.py.
Output: ~/Desktop/glowinggardens_claude/_music/ten_bar_patterns.json
"""
import os, json
from collections import defaultdict
from detect_patterns import (
    chord_key, root_of, per_beat_chords, chord_changes,
    detect_axis, detect_doowop, detect_pachelbel, detect_ii_V_I,
    detect_mixolydian, detect_andalusian, detect_descent,
)

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/ten_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/ten_bar_patterns.json'

BEATS = 40       # 10 bars × 4 beats
HALF = 20        # 5 bars
BAR = 4


def detect_5_5_repeat(pb):
    """First 5 bars = last 5 bars (10-bar palindrome of halves)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:HALF] == pb[HALF:BEATS]


def detect_4_4_2_phrase(pb):
    """8-bar phrase + 2-bar tag: bars 1-8 form a coherent shape, bars 9-10 differ."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    # The 4+4 in the first 8 bars: bars 1-4 = bars 5-8
    return pb[0:16] == pb[16:32] and pb[0:16] != pb[32:40]


def detect_5x_2bar_repeat(pb):
    """All five 2-bar blocks identical — drone-y 2-bar idea ×5."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    b1 = pb[0:8]
    return all(pb[i*8:(i+1)*8] == b1 for i in range(1, 5))


def detect_ABABA_2bar(pb):
    """ABABA shape at 2-bar grain — five 2-bar phrases alternating A, B, A, B, A."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b = pb[0:8], pb[8:16]
    if a == b: return False
    return pb[16:24] == a and pb[24:32] == b and pb[32:40] == a


def detect_drone(pb):
    nn = [b for b in pb if b is not None]
    if not nn: return False
    counts = defaultdict(int)
    for b in nn: counts[b] += 1
    return max(counts.values()) / len(nn) >= 0.75


def detect_two_chord(pb):
    return len(set(b for b in pb if b is not None)) == 2


def detect_walking(changes):
    return len(set(changes)) >= 8


def detect_one_per_bar_no_repeat(pb):
    """Each bar holds a single chord, no adjacent bars share it."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bars = []
    for m in range(10):
        b = pb[m*BAR:(m+1)*BAR]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 10):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(pb):
    """Bars 9-10 are tonic (root=1), bar 8 has no tonic."""
    if len(pb) < BEATS: return False
    last_two = pb[BEATS-8:BEATS]
    bar_before = pb[BEATS-12:BEATS-8]
    if any(b is None for b in last_two + bar_before): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in last_two) and not any(is_tonic(b) for b in bar_before)


DETECTORS = [
    # Progression shapes (sliding window, length-agnostic)
    ('axis (I-V-vi-IV)',         'roots',    lambda r: detect_axis(r)),
    ('doo-wop (I-vi-IV-V)',      'roots',    lambda r: detect_doowop(r)),
    ('pachelbel/8-chord',        'roots',    lambda r: detect_pachelbel(r)),
    ('ii-V-I',                   'roots',    lambda r: detect_ii_V_I(r)),
    ('andalusian (i-bVII-bVI-V)','roots',    lambda r: detect_andalusian(r)),
    ('mixolydian (bVII-IV)',     'changes',  lambda c: detect_mixolydian(c)),
    ('stepwise descent (4+)',    'roots',    lambda r: detect_descent(r)),
    # Form shapes specific to 10-bar
    ('5+5 repeat',               'per_beat', detect_5_5_repeat),
    ('4+4+2 phrase',             'per_beat', detect_4_4_2_phrase),
    ('2-bar x5 repeat',          'per_beat', detect_5x_2bar_repeat),
    ('ABABA (2-bar phrases)',    'per_beat', detect_ABABA_2bar),
    ('ends on I (arrival)',      'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats',  'per_beat', detect_one_per_bar_no_repeat),
    # Density
    ('one-chord drone',          'per_beat', detect_drone),
    ('two-chord vamp',           'per_beat', detect_two_chord),
    ('walking (8+ changes)',     'changes',  detect_walking),
]


def main():
    sections = json.load(open(SRC))
    sections = [s for s in sections if (s['end'] - s['start']) == BEATS]
    print(f'{len(sections)} 10-bar sections (40-beat 4/4)\n')

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
