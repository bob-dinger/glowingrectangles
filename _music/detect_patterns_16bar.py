"""Pattern detectors for 16-bar sections. Mirrors detect_patterns.py but with
phrase grain doubled (4-bar phrases instead of 2-bar) and form-shapes scaled to
the 64-beat section length.

Output: ~/Desktop/glowinggardens_claude/_music/sixteen_bar_patterns.json
"""
import os, json
from collections import defaultdict
from detect_patterns import (
    chord_key, root_of, per_beat_chords, chord_changes,
    detect_axis, detect_doowop, detect_pachelbel, detect_ii_V_I,
    detect_mixolydian, detect_andalusian, detect_descent,
    is_rotation,
)

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/sixteen_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/sixteen_bar_patterns.json'

BEATS = 64        # 16 bars × 4 beats
PHRASE = 16       # 4-bar phrase (so AABA = each A is 4 bars)
HALF = 32         # 8-bar half (so "full 8+8 repeat" = first half equals second)
BAR = 4

# 16-bar form-shape detectors. Phrase grain = 4 bars (= 16 beats), so a 4-phrase
# shape (AABA, AAAB, ABAB, ABCD) carves the section into four equal quarters.

def detect_full_half_repeat(pb):
    """First 8 bars repeat as second 8 bars."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:HALF] == pb[HALF:BEATS]


def detect_quarters_repeat(pb):
    """All four 4-bar quarters identical — 4-bar idea × 4."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    q1 = pb[:PHRASE]
    return all(pb[i*PHRASE:(i+1)*PHRASE] == q1 for i in range(1, 4))


def detect_aaba_4bar(pb):
    """AABA at 4-bar grain — the classic 16-bar AABA form. Loose match on first
    bar of each A (tolerates 1st/2nd ending variation in the closing bar of each A)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a1 = pb[0:BAR]
    return (pb[PHRASE:PHRASE+BAR] == a1 and
            pb[3*PHRASE:3*PHRASE+BAR] == a1 and
            pb[2*PHRASE:2*PHRASE+BAR] != a1)


def detect_aaab_4bar(pb):
    """AAAB at 4-bar grain — first three 4-bar phrases identical, last differs."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a = pb[0:PHRASE]
    return (pb[PHRASE:2*PHRASE] == a and
            pb[2*PHRASE:3*PHRASE] == a and
            pb[3*PHRASE:4*PHRASE] != a)


def detect_abab_4bar(pb):
    """ABAB at 4-bar grain — bars 1-4 = bars 9-12 (A), bars 5-8 = bars 13-16 (B)."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b = pb[0:PHRASE], pb[PHRASE:2*PHRASE]
    return (pb[2*PHRASE:3*PHRASE] == a and
            pb[3*PHRASE:4*PHRASE] == b and a != b)


def detect_abcd_4bar(pb):
    """All four 4-bar phrases pairwise distinct — section keeps developing."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    blocks = [pb[i*PHRASE:(i+1)*PHRASE] for i in range(4)]
    for i in range(4):
        for j in range(i+1, 4):
            if blocks[i] == blocks[j]: return False
    return True


def detect_abad_4bar(pb):
    """ABAD at 4-bar grain: bars 1-4 = bars 9-12 (A), bars 5-8 (B) and bars 13-16 (D)
    each differ from A and from each other."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b, d = pb[0:PHRASE], pb[PHRASE:2*PHRASE], pb[3*PHRASE:4*PHRASE]
    return (pb[2*PHRASE:3*PHRASE] == a and a != b and a != d and b != d)


def detect_4_4_8_phrase(pb):
    """First 4 bars repeat in bars 5-8, then bars 9-16 differ (4+4+8 phrase)."""
    if len(pb) < BEATS or any(b is None for b in pb[:32]): return False
    return pb[0:PHRASE] == pb[PHRASE:2*PHRASE] and pb[0:PHRASE] != pb[2*PHRASE:3*PHRASE]


def detect_8_8_qa(pb):
    """8+8 question/answer: halves differ but start on the same chord."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    return pb[:HALF] != pb[HALF:] and pb[0] == pb[HALF]


def detect_drone(pb):
    """≥75% of beats hold the same chord."""
    nn = [b for b in pb if b is not None]
    if not nn: return False
    counts = defaultdict(int)
    for b in nn: counts[b] += 1
    return max(counts.values()) / len(nn) >= 0.75


def detect_two_chord(pb):
    distinct = set(b for b in pb if b is not None)
    return len(distinct) == 2


def detect_walking_long(changes):
    """12+ distinct chords across a 16-bar section."""
    return len(set(changes)) >= 12


def detect_one_per_bar_no_repeat(pb):
    """Each measure is one chord, no adjacent bars the same — 16 changes in a row."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    bars = []
    for m in range(16):
        b = pb[m*BAR:(m+1)*BAR]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 16):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(pb):
    """Bars 15-16 are tonic (root=1), bar 14 has no tonic."""
    if len(pb) < BEATS: return False
    last_two = pb[BEATS-8:BEATS]
    bar_before = pb[BEATS-12:BEATS-8]
    if any(b is None for b in last_two + bar_before): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in last_two) and not any(is_tonic(b) for b in bar_before)


def detect_112_groove(pb):
    """4-bar groove: chord A for 1 measure (4 beats), chord B for 1 measure (4 beats),
    chord C held for 2 measures (8 beats). Three distinct chords. Repeats at least once."""
    if len(pb) < 32 or any(b is None for b in pb[:32]): return False
    block = pb[:16]
    a, b, c = block[0], block[4], block[8]
    if len({a, b, c}) < 3: return False
    if block != [a]*4 + [b]*4 + [c]*8: return False
    return pb[16:32] == block


def detect_abc_blocks_4_4_8(pb):
    """Three single-chord blocks: A held 4 bars, B held 4 bars, C held 8 bars.
    16-bar analog of the 2+2+4 ABC pattern at 8-bar scale."""
    if len(pb) < BEATS or any(b is None for b in pb[:BEATS]): return False
    a, b, c = pb[0], pb[PHRASE], pb[2*PHRASE]
    if len({a, b, c}) < 3: return False
    return (all(x == a for x in pb[0:PHRASE]) and
            all(x == b for x in pb[PHRASE:2*PHRASE]) and
            all(x == c for x in pb[2*PHRASE:4*PHRASE]))


DETECTORS = [
    # Progressions (root-only sliding window — same as 8-bar)
    ('axis (I-V-vi-IV)',        'roots',    lambda r: detect_axis(r)),
    ('doo-wop (I-vi-IV-V)',     'roots',    lambda r: detect_doowop(r)),
    ('pachelbel/8-chord',       'roots',    lambda r: detect_pachelbel(r)),
    ('ii-V-I',                  'roots',    lambda r: detect_ii_V_I(r)),
    ('andalusian (i-bVII-bVI-V)','roots',   lambda r: detect_andalusian(r)),
    ('mixolydian (bVII-IV)',    'changes',  lambda c: detect_mixolydian(c)),
    ('stepwise descent (4+)',   'roots',    lambda r: detect_descent(r)),
    # Form shapes
    ('full 8+8 repeat',         'per_beat', detect_full_half_repeat),
    ('4+4+4+4 repeat',          'per_beat', detect_quarters_repeat),
    ('AABA (4-bar phrases)',    'per_beat', detect_aaba_4bar),
    ('AAAB (4-bar phrases)',    'per_beat', detect_aaab_4bar),
    ('ABAB (4-bar phrases)',    'per_beat', detect_abab_4bar),
    ('ABAD (4-bar phrases)',    'per_beat', detect_abad_4bar),
    ('ends on I (arrival)',     'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats', 'per_beat', detect_one_per_bar_no_repeat),
    ('ABCD (4-bar phrases)',    'per_beat', detect_abcd_4bar),
    ('4+4+8 phrase',            'per_beat', detect_4_4_8_phrase),
    ('ABC blocks (4+4+8 bars)', 'per_beat', detect_abc_blocks_4_4_8),
    ('112 groove (1+1+2 bars)', 'per_beat', detect_112_groove),
    ('8+8 question/answer',     'per_beat', detect_8_8_qa),
    # Density
    ('one-chord drone',         'per_beat', detect_drone),
    ('two-chord vamp',          'per_beat', detect_two_chord),
    ('walking (12+ changes)',   'changes',  detect_walking_long),
]


def main():
    sections = json.load(open(SRC))
    # Filter to standard 64-beat 4/4 sections
    sections = [s for s in sections if (s['end'] - s['start']) == BEATS]
    print(f'{len(sections)} 16-bar sections (64-beat 4/4)\n')

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
