"""Pattern detectors for 14-bar sections (56 beats in 4/4).

14-bar is "almost 16" — usually feels like a 16-bar phrase truncated by 2, or an
8-bar phrase with a 6-bar tail. Natural shapes:
  - 8+6 (8-bar phrase + 6-bar tail)
  - 6+8 (less common)
  - 12+2 (12-bar phrase + 2-bar tag)
  - 4+4+6 (two 4-bar phrases + 6-bar tail)
  - 7+7 halves (rare)

Imports shared helpers + progression detectors from detect_patterns.py.
Output: ~/Desktop/glowinggardens_claude/_music/fourteen_bar_patterns.json
"""
import os, json
from collections import defaultdict
from detect_patterns import (
    chord_key, root_of, per_beat_chords, chord_changes,
    detect_axis, detect_doowop, detect_pachelbel, detect_ii_V_I,
    detect_mixolydian, detect_andalusian, detect_descent,
)

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/fourteen_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/fourteen_bar_patterns.json'

BEATS = 56       # 14 bars × 4
BAR = 4


def detect_7_7_repeat(pb):
    """First 7 bars = last 7 bars (palindromic halves)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:28] == pb[28:56]


def detect_8_6_phrase(pb):
    """First 8 bars form a coherent 4+4 phrase, bars 9-14 are a different tail."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    # 4+4 within first 8 bars
    return pb[0:16] == pb[16:32] and pb[0:16] != pb[32:48]


def detect_6_8_phrase(pb):
    """First 6 bars are a phrase, last 8 a different one (less common asymmetric shape)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    # bars 1-6 distinct from bars 7-14, and 7-14 has internal 4+4 structure
    p1 = pb[0:24]
    p2 = pb[24:56]
    if p1 == p2[:24]: return False
    return p2[0:16] == p2[16:32]


def detect_12_2_phrase(pb):
    """First 12 bars form a phrase, last 2 bars are a tag/turnaround."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    # Phrase shape in first 12: AAB or AAA at 4-bar grain
    p1, p2, p3 = pb[0:16], pb[16:32], pb[32:48]
    tag = pb[48:56]
    return p1 == p2 and tag != p3


def detect_4_4_6_phrase(pb):
    """4+4+6: two 4-bar phrases + 6-bar tail."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[0:16] == pb[16:32] and pb[32:56] != pb[0:24]


def detect_drone(pb):
    nn = [b for b in pb if b is not None]
    if not nn: return False
    counts = defaultdict(int)
    for b in nn: counts[b] += 1
    return max(counts.values()) / len(nn) >= 0.75


def detect_two_chord(pb):
    return len(set(b for b in pb if b is not None)) == 2


def detect_walking(changes):
    return len(set(changes)) >= 10


def detect_one_per_bar_no_repeat(pb):
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bars = []
    for m in range(14):
        b = pb[m*BAR:(m+1)*BAR]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 14):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(pb):
    """Bars 13-14 are tonic (root=1), bar 12 has no tonic."""
    if len(pb) < BEATS: return False
    last_two = pb[BEATS-8:BEATS]
    bar_before = pb[BEATS-12:BEATS-8]
    if any(b is None for b in last_two + bar_before): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in last_two) and not any(is_tonic(b) for b in bar_before)


DETECTORS = [
    # Progressions (length-agnostic)
    ('axis (I-V-vi-IV)',         'roots',    lambda r: detect_axis(r)),
    ('doo-wop (I-vi-IV-V)',      'roots',    lambda r: detect_doowop(r)),
    ('pachelbel/8-chord',        'roots',    lambda r: detect_pachelbel(r)),
    ('ii-V-I',                   'roots',    lambda r: detect_ii_V_I(r)),
    ('andalusian (i-bVII-bVI-V)','roots',    lambda r: detect_andalusian(r)),
    ('mixolydian (bVII-IV)',     'changes',  lambda c: detect_mixolydian(c)),
    ('stepwise descent (4+)',    'roots',    lambda r: detect_descent(r)),
    # 14-bar form shapes
    ('7+7 repeat',               'per_beat', detect_7_7_repeat),
    ('8+6 phrase',               'per_beat', detect_8_6_phrase),
    ('6+8 phrase',               'per_beat', detect_6_8_phrase),
    ('12+2 phrase',              'per_beat', detect_12_2_phrase),
    ('4+4+6 phrase',             'per_beat', detect_4_4_6_phrase),
    ('ends on I (arrival)',      'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats',  'per_beat', detect_one_per_bar_no_repeat),
    # Density
    ('one-chord drone',          'per_beat', detect_drone),
    ('two-chord vamp',           'per_beat', detect_two_chord),
    ('walking (10+ changes)',    'changes',  detect_walking),
]


def main():
    sections = json.load(open(SRC))
    sections = [s for s in sections if (s['end'] - s['start']) == BEATS]
    print(f'{len(sections)} 14-bar sections (56-beat 4/4)\n')

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
