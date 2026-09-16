"""Run pattern detectors over 8-bar sections (loaded from the JSON we already exported).

Reduces each section to a per-beat chord stamp (32 elements for 8-bar 4/4) AND a collapsed
chord-change sequence. Detectors pick whichever fits — root-only progression detectors
(axis, doo-wop, ii-V-I, I-bVII-IV) use the change sequence with sliding windows so they
match whether the song moves a chord/beat (Ace of Base) or a chord/measure (typical pop).

Output: ~/Desktop/glowinggardens_claude/_music/eight_bar_patterns.json
Each section gets a 'patterns' array listing every matched pattern name.
"""
import os, json
from collections import defaultdict

SRC = '/Users/robert/Desktop/glowinggardens_claude/_music/eight_bar_sections.json'
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/eight_bar_patterns.json'


def chord_key(c):
    """Compact identity for a chord: root + type/borrowed/sus marker. Ignores adds/inversion.
    Examples: '1' (I), '57' (V7), '7b' (bVII borrowed), '5s4' (V sus4)."""
    k = str(c.get('r', '?'))
    if c.get('t') == 7: k += '7'
    if c.get('bor'): k += 'b'
    if c.get('sus'): k += 's' + str(c['sus'][0])
    return k


def root_of(k):
    """Extract integer root from a chord_key string."""
    if not k: return None
    try: return int(k[0])
    except: return None


def per_beat_chords(section):
    """Return list of length = section beat-span (typically 32 for 8-bar 4/4).
    Each element = chord_key of the chord sounding on that beat, or None."""
    span = section['end'] - section['start']
    beats = int(round(span))
    out = [None] * beats
    for c in section['chords']:
        cs = c['b']; ce = c['b'] + c['d']
        k = chord_key(c)
        for b in range(max(0, int(cs)), min(beats, int(round(ce)))):
            out[b] = k
    return out


def per_measure_chords(per_beat):
    """Reduce per-beat → per-measure (most beats wins). Used for display + back-compat."""
    bpm = 4
    out = []
    for m in range(len(per_beat) // bpm):
        slice_ = per_beat[m*bpm:(m+1)*bpm]
        tally = defaultdict(int)
        for k in slice_:
            if k: tally[k] += 1
        out.append(max(tally.items(), key=lambda x: x[1])[0] if tally else None)
    return out


def chord_changes(per_beat):
    """Collapse consecutive identical keys → ordered list of distinct chord_keys."""
    out = []
    for k in per_beat:
        if k is None: continue
        if not out or out[-1] != k: out.append(k)
    return out


# === Detectors ===
# Each returns bool. Take per_beat + changes (chord_key list) + roots (int list).

def is_rotation(window, pattern):
    return any(window == pattern[i:] + pattern[:i] for i in range(len(pattern)))


def detect_axis(roots):
    """Any 4-chord window in the changes sequence is a rotation of I-V-vi-IV."""
    pat = [1, 5, 6, 4]
    for i in range(len(roots) - 3):
        if is_rotation(roots[i:i+4], pat): return True
    return False


def detect_doowop(roots):
    """Any 4-chord window = rotation of I-vi-IV-V (50s changes)."""
    pat = [1, 6, 4, 5]
    for i in range(len(roots) - 3):
        if is_rotation(roots[i:i+4], pat): return True
    return False


def detect_pachelbel(roots):
    """I-V-vi-iii-IV-I-IV-V (Canon / Don't Stop Believin') — 8-chord window."""
    pat = [1, 5, 6, 3, 4, 1, 4, 5]
    for i in range(len(roots) - 7):
        if roots[i:i+8] == pat: return True
    return False


def detect_ii_V_I(roots):
    """ii-V-I anywhere in the changes."""
    for i in range(len(roots) - 2):
        if roots[i:i+3] == [2, 5, 1]: return True
    return False


def detect_mixolydian(changes):
    """bVII→IV cadence — the audible mixolydian signature. Catches Sweet Home Alabama,
    Centerfield, We Can Work It Out, etc. We look for any bVII (root=7 with borrowed flag)
    immediately followed by IV; plain V→IV is rare so this pair is unambiguous."""
    for i in range(len(changes) - 1):
        a, b = changes[i], changes[i+1]
        if root_of(a) == 7 and 'b' in a[1:] and root_of(b) == 4:
            return True
    return False


def detect_andalusian(roots):
    """i-bVII-bVI-V descent (minor-key Hit the Road Jack). In our data root-only catches the shape."""
    for i in range(len(roots) - 3):
        if roots[i:i+4] == [1, 7, 6, 5]: return True
    return False


def detect_full_repeat(per_beat):
    """First half = second half (4+4 same)."""
    if any(b is None for b in per_beat): return False
    half = len(per_beat) // 2
    return per_beat[:half] == per_beat[half:]


def detect_2_2_4(per_beat):
    """First 2 bars repeat in bars 3-4, then bars 5-8 are different (2+2+4 phrase).
    At per-beat resolution: 8-beat block repeats, then 16-beat tail differs."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:16]): return False
    return per_beat[0:8] == per_beat[8:16] and per_beat[0:8] != per_beat[16:24]


def detect_2222_repeat(per_beat):
    """All four 2-bar blocks identical — 2-bar idea repeated 4 times to fill 8 bars."""
    if len(per_beat) < 32 or any(b is None for b in per_beat): return False
    b1 = per_beat[0:8]
    return per_beat[8:16] == b1 and per_beat[16:24] == b1 and per_beat[24:32] == b1


def detect_abc_224_bars(per_beat):
    """Three single-chord blocks: A held 2 bars (8 beats), B held 2 bars, C held 4 bars (16 beats).
    Same chord throughout each block. Three distinct chords."""
    if len(per_beat) < 32 or any(b is None for b in per_beat): return False
    a, b, c = per_beat[0], per_beat[8], per_beat[16]
    if len({a, b, c}) < 3: return False
    return (all(x == a for x in per_beat[0:8]) and
            all(x == b for x in per_beat[8:16]) and
            all(x == c for x in per_beat[16:32]))


def detect_abab_2bar(per_beat):
    """ABAB at 2-bar grain: bars 1-2 = bars 5-6 (A), bars 3-4 = bars 7-8 (B), A ≠ B.
    Subset of full 4+4 repeat where the two halves of the 4-bar phrase differ."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    a, b = per_beat[0:8], per_beat[8:16]
    return (per_beat[16:24] == a and per_beat[24:32] == b and a != b)


def detect_aaab_2bar(per_beat):
    """AAAB at 2-bar grain: first three 2-bar phrases identical, last 2 bars differ.
    Nowhere Man bridge: III-IV / III-IV / III-IV / IV-V."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    a = per_beat[0:8]
    return (per_beat[8:16] == a and per_beat[16:24] == a and per_beat[24:32] != a)


def detect_abcd_2bar(per_beat):
    """All four 2-bar phrases pairwise distinct — section keeps developing, no repeats."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    blocks = [per_beat[0:8], per_beat[8:16], per_beat[16:24], per_beat[24:32]]
    for i in range(4):
        for j in range(i+1, 4):
            if blocks[i] == blocks[j]: return False
    return True


def detect_abad_2bar(per_beat):
    """ABAD at 2-bar grain: bars 1-2 = bars 5-6 (A), bars 3-4 (B) ≠ A, bars 7-8 (D)
    ≠ A and ≠ B. Subset of full 4+4 repeat would need B=D — this is the variation
    where the second and fourth phrases diverge."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    a, b, d = per_beat[0:8], per_beat[8:16], per_beat[24:32]
    return (per_beat[16:24] == a and a != b and a != d and b != d)


def detect_one_per_bar_no_repeat(per_beat):
    """Each measure holds a single chord (no sub-bar changes) and no two adjacent
    measures share the same chord. Constant motion — every downbeat is a fresh chord."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    bars = []
    for m in range(8):
        b = per_beat[m*4:(m+1)*4]
        if any(x != b[0] for x in b): return False
        bars.append(b[0])
    for i in range(1, 8):
        if bars[i] == bars[i-1]: return False
    return True


def detect_i_arrival_ending(per_beat):
    """Section closes with 2 full measures of I (bars 7-8), and bar 6 has NO I in it
    — so the tonic arrival feels fresh, not a continuation. Matches root=1 family
    (I, I7, Isus4 all count as tonic)."""
    if len(per_beat) < 32: return False
    bars_7_8 = per_beat[24:32]
    bar_6    = per_beat[20:24]
    if any(b is None for b in bars_7_8 + bar_6): return False
    is_tonic = lambda k: root_of(k) == 1
    return all(is_tonic(b) for b in bars_7_8) and not any(is_tonic(b) for b in bar_6)


def detect_aaba_2bar(per_beat):
    """AABA at 2-bar grain. Matches each A by its FIRST measure (beats 0-3 of the
    2-bar block) — so 1st-ending / 2nd-ending variation in the closing bar of each A
    is tolerated. Fire Escape verse: A=[V,IV,V] all start with same melodic descent
    but close differently. Strict byte-match would miss it."""
    if len(per_beat) < 32 or any(b is None for b in per_beat): return False
    a1_open = per_beat[0:4]
    a2_open = per_beat[8:12]
    b_open  = per_beat[16:20]
    a3_open = per_beat[24:28]
    return (a1_open == a2_open and a1_open == a3_open and b_open != a1_open)


def detect_qa(per_beat):
    """4+4 question/answer: halves differ but anchor on same chord."""
    if any(b is None for b in per_beat): return False
    half = len(per_beat) // 2
    return per_beat[:half] != per_beat[half:] and per_beat[0] == per_beat[half]


def detect_drone(per_beat):
    """≥75% of beats hold the same chord."""
    notnone = [b for b in per_beat if b is not None]
    if not notnone: return False
    counts = defaultdict(int)
    for b in notnone: counts[b] += 1
    top = max(counts.values())
    return top / len(notnone) >= 0.75


def detect_two_chord(per_beat):
    """Exactly 2 distinct chords across the whole section."""
    distinct = set(b for b in per_beat if b is not None)
    return len(distinct) == 2


def detect_walking(changes):
    """6+ distinct chords across the changes — section moves a lot."""
    return len(set(changes)) >= 6


def detect_224_groove(per_beat):
    """2-bar pattern of (chord A for 2 beats, chord B for 2 beats, chord C for 4 beats),
    repeated to fill the section. The shape user specifically flagged."""
    if len(per_beat) < 16 or any(b is None for b in per_beat[:8]): return False
    block = per_beat[:8]
    a, b, c = block[0], block[2], block[4]
    if len({a, b, c}) < 3: return False
    if block != [a, a, b, b, c, c, c, c]: return False
    # Require at least one repeat
    return per_beat[8:16] == block


def detect_422_groove(per_beat):
    """2-bar pattern: chord A held 1 full measure (4 beats), chord B for 2 beats,
    chord C for 2 beats. Repeated to fill the section."""
    if len(per_beat) < 16 or any(b is None for b in per_beat[:8]): return False
    block = per_beat[:8]
    a, b, c = block[0], block[4], block[6]
    if len({a, b, c}) < 3: return False
    if block != [a, a, a, a, b, b, c, c]: return False
    return per_beat[8:16] == block


def detect_3_1_4_groove(per_beat):
    """4-bar pattern: chord A held 1.5 measures (6 beats), chord B held 0.5 measures
    (2 beats), chord C held 2 measures (8 beats). Repeated once to fill 8 bars."""
    if len(per_beat) < 32 or any(b is None for b in per_beat[:32]): return False
    block = per_beat[:16]
    a, b, c = block[0], block[6], block[8]
    if len({a, b, c}) < 3: return False
    target = [a]*6 + [b]*2 + [c]*8
    if block != target: return False
    return per_beat[16:32] == block


def detect_descent(roots):
    """4+ consecutive stepwise descending roots (1→7→6→5 or any 4-step run)."""
    if len(roots) < 4: return False
    longest, cur = 1, 1
    for i in range(1, len(roots)):
        diff = (roots[i-1] - roots[i]) % 7
        if diff == 1:
            cur += 1; longest = max(longest, cur)
        else:
            cur = 1
    return longest >= 4


DETECTORS = [
    # Progression shapes (root-only, sliding window)
    ('axis (I-V-vi-IV)',     'roots',   detect_axis),
    ('doo-wop (I-vi-IV-V)',  'roots',   detect_doowop),
    ('pachelbel/8-chord',    'roots',   detect_pachelbel),
    ('ii-V-I',               'roots',   detect_ii_V_I),
    ('andalusian (i-bVII-bVI-V)', 'roots', detect_andalusian),
    ('mixolydian (bVII-IV)', 'changes', detect_mixolydian),
    ('stepwise descent (4+)','roots',   detect_descent),
    # Form shapes (timing-sensitive)
    ('full 4+4 repeat',      'per_beat', detect_full_repeat),
    ('2+2+2+2 repeat',       'per_beat', detect_2222_repeat),
    ('AABA (2-bar phrases)', 'per_beat', detect_aaba_2bar),
    ('AAAB (2-bar phrases)', 'per_beat', detect_aaab_2bar),
    ('ABAB (2-bar phrases)', 'per_beat', detect_abab_2bar),
    ('ABAD (2-bar phrases)', 'per_beat', detect_abad_2bar),
    ('ends on I (arrival)',  'per_beat', detect_i_arrival_ending),
    ('1 chord/bar, no repeats','per_beat', detect_one_per_bar_no_repeat),
    ('ABCD (2-bar phrases)',  'per_beat', detect_abcd_2bar),
    ('2+2+4 phrase',         'per_beat', detect_2_2_4),
    ('ABC blocks (2+2+4 bars)', 'per_beat', detect_abc_224_bars),
    ('4+4 question/answer',  'per_beat', detect_qa),
    ('224 groove (2+2+4 bts)','per_beat', detect_224_groove),
    ('422 groove (4+2+2 bts)','per_beat', detect_422_groove),
    ('1.5+.5+2 groove (4-bar)','per_beat', detect_3_1_4_groove),
    # Density shapes
    ('one-chord drone',      'per_beat', detect_drone),
    ('two-chord vamp',       'per_beat', detect_two_chord),
    ('walking (6+ changes)', 'changes', detect_walking),
]


def main():
    sections = json.load(open(SRC))
    print(f'{len(sections)} sections\n')
    out = []
    pattern_counts = defaultdict(int)
    sections_with_any = 0

    for sec in sections:
        per_beat = per_beat_chords(sec)
        changes = chord_changes(per_beat)
        roots = [root_of(k) for k in changes if root_of(k) is not None]
        pmc = per_measure_chords(per_beat)

        patterns = []
        args_by_kind = {'per_beat': per_beat, 'changes': changes, 'roots': roots}
        for name, kind, fn in DETECTORS:
            try:
                if fn(args_by_kind[kind]):
                    patterns.append(name)
                    pattern_counts[name] += 1
            except Exception:
                pass

        out.append({**sec, 'pmc': pmc, 'changes': changes, 'patterns': patterns})
        if patterns: sections_with_any += 1

    print(f'{sections_with_any}/{len(sections)} sections matched ≥1 pattern\n')
    print(f'  {"pattern":30s} {"count":>6}  {"%":>6}')
    for name, _, _ in DETECTORS:
        c = pattern_counts[name]
        print(f'  {name:30s} {c:>6}  {100*c/len(sections):>5.1f}%')

    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'))
    print(f'\nout → {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)')


if __name__ == '__main__': main()
