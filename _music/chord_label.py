"""Canonical Hookpad chord → Roman-numeral label converter.

This is the single source of truth used by:
  - show_song.py (look up & display)
  - The 4-chord progression analysis (CSV/XLSX export scripts)
  - 10 HTML viz pages (via mirror in chord-label.js)

Hookpad chord field schema:
    root: int 1-7 — scale degree of the chord root
    type: int — 5 (triad), 7 (7th chord), 9/11/13 (extended)
    applied: int 0-7 — if >0, secondary dominant of degree N
    borrowed: str — 'minor', 'mixolydian', 'dorian', etc.
    suspensions: list — [2] = sus2, [4] = sus4
    adds: list — interval numbers (9 = add9, 4 = add11, 6 = add13)
    omits: list — [3] = no3 (power chord shorthand), [5] = no5
    alterations: list — string codes like '#5', 'b5', '#9'

Standardizations applied (in order):
    1. Minor → relative-major reference: A-minor's VII = C-major's V, etc.
    2. bVII (root=7 + minor/mixolydian borrow, no applied) → IV/IV unified
    3. For applied chords, compute actual pitch class and prefer simpler labels:
       - If chord pc matches a diatonic major position (I/IV/V), output simple Roman
       - Otherwise try V/Y form (V of some degree)
       - bVII case (pc=10) always labels as IV/IV
"""

NUM = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

# Relative-major mapping for minor-mode degrees: A-minor's i (degree 1) = C-major's vi (degree 6)
MIN_TO_MAJ = {1: 6, 2: 7, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5}

# Scale-degree → semitones-from-tonic (0-11)
MAJ_INT = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
MIN_INT = {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10}

# Borrowed-mode → semitones per scale degree. A borrowed chord's accidental is the
# difference between its mode interval and the major interval on that degree.
MODE_INT = {
    'major':            {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11},
    'ionian':           {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11},
    'dorian':           {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 9, 7: 10},
    'phrygian':         {1: 0, 2: 1, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10},
    'lydian':           {1: 0, 2: 2, 3: 4, 4: 6, 5: 7, 6: 9, 7: 11},
    'mixolydian':       {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 10},
    'aeolian':          {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10},
    'minor':            {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10},
    'locrian':          {1: 0, 2: 1, 3: 3, 4: 5, 5: 6, 6: 8, 7: 10},
    'harmonicMinor':    {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 11},
    'melodicMinor':     {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 9, 7: 11},
    'phrygianDominant': {1: 0, 2: 1, 3: 4, 4: 5, 5: 7, 6: 8, 7: 10},
}


def _add_ext(base, c, t):
    """Append type/sus/add/omit/alteration extensions to a base Roman label."""
    if t == 7:
        base += '7'
    elif t in (9, 11, 13):
        base += str(t)
    for s in c.get('suspensions') or []:
        base += 'sus' + str(s)
    for a in c.get('adds') or []:
        base += f'add{a}'
    om = c.get('omits') or []
    if 3 in om and not (c.get('suspensions') or []) and not (c.get('adds') or []):
        base += '5'  # power chord shorthand
    elif 3 in om:
        base += '(no3)'
    if 5 in om:
        base += '(no5)'
    for a in c.get('alterations') or []:
        base += str(a)
    return base


def chord_label(c, scale='major'):
    """Convert a Hookpad chord dict to a Roman-numeral label.

    Args:
        c: dict with Hookpad fields (root, type, applied, borrowed, suspensions, adds, omits, alterations)
        scale: 'major' or 'minor' — song's scale; minor gets shifted to relative-major reference

    Returns:
        Roman-numeral string like 'I', 'vi7', 'V/V', 'IV/IV', 'Imaj7', 'bVI7#5', 'I5', etc.
        '?' if root is missing or out of range.
    """
    r = c.get('root')
    if not r or r < 1 or r > 7:
        return '?'

    applied = c.get('applied') or 0

    t_raw = c.get('type', 5)
    try:
        t = int(t_raw)
    except (ValueError, TypeError):
        t = 5

    bor = c.get('borrowed')
    orig_scale = scale  # remember for pitch-class calculations

    # Secondary leading-tone diminished: Hookpad stores vii°7-of-X as applied=7, where
    # `root` is the TARGET degree and the chord is a fully-diminished chord on the leading
    # tone just below it (Lovefool root=3 = D#°7→iii; Bennie root=2 = G#°7→ii). Catch this
    # BEFORE the minor shift so applied=7 isn't remapped.
    if applied == 7:
        deg = '°7' if t == 7 else '°'   # °7 (dim7) or ° (dim triad)
        if r == 1:
            return 'vii' + deg                    # vii°7 of the tonic — no slash needed
        y = NUM[r - 1]
        if r in (2, 3, 6):
            y = y.lower()                          # minor target degree
        return 'vii' + deg + '/' + y

    # Minor-mode shift: convert diatonic degree (or applied target) to relative-major reference
    if scale == 'minor':
        if applied > 0:
            applied = MIN_TO_MAJ[applied]
            # root stays — it's relative to the secondary key, not the song key
        else:
            r = MIN_TO_MAJ[r]
        scale = 'major'

    # bVII → IV/IV unified label. Triggers on any flat-7 borrowed mode, OR a bare
    # degree-7 triad with no borrow: the diatonic vii° (B dim) essentially never
    # appears as a plain triad, so a major/power chord on 7 is the subtonic bVII.
    if r == 7 and applied == 0 and (
            (isinstance(bor, str) and MODE_INT.get(bor, {}).get(7) == 10) or not bor):
        r = 4
        applied = 4
        bor = None

    # ===== Applied (secondary dominant) path =====
    if applied > 0:
        # Compute the chord's actual pitch class in major-mode reference
        y_pc = MAJ_INT[applied]
        # Root in secondary key uses minor-scale intervals if origin was minor-mode (preserves
        # natural-minor VII interpretation across the shift); otherwise major-scale intervals.
        root_intervals = MIN_INT if orig_scale == 'minor' else MAJ_INT
        chord_pc = (y_pc + root_intervals[r]) % 12

        # If chord pc matches a naturally-major diatonic position (I/IV/V), use simple Roman
        for d in (1, 4, 5):
            if MAJ_INT[d] == chord_pc:
                return _add_ext(NUM[d - 1], c, t)

        # bVII case (chord pc = 10) → unified IV/IV label
        if chord_pc == 10:
            return f"{_add_ext('IV', c, t)}/IV"

        # Try V/Z form — find diatonic Z such that V of Z = our chord
        v_target_pc = (chord_pc - 7) % 12
        v_z_deg = None
        for d in (1, 2, 3, 4, 5, 6, 7):
            if MAJ_INT[d] == v_target_pc:
                v_z_deg = d
                break
        if v_z_deg is not None:
            x = _add_ext('V', c, t)
            y = NUM[v_z_deg - 1]
            if v_z_deg in (2, 3, 6):
                y = y.lower()
            return f"{x}/{y}"

        # Fallback: original X/Y notation (rare — non-diatonic V target)
        x = NUM[r - 1]
        if r in (2, 3, 6) and t != 7:
            x = x.lower()
        x = _add_ext(x, c, t)
        y = NUM[applied - 1]
        if applied in (2, 3, 6):
            y = y.lower()
        return f"{x}/{y}"

    # ===== Diatonic / borrowed path =====
    base = NUM[r - 1]
    if not bor:
        if r in (2, 3, 6):
            base = base.lower()
    if isinstance(bor, str) and bor in MODE_INT:
        # Roman-numeral case = triad quality. A borrowed mode changes the chord's
        # THIRD (not its root), so quality must be read from the third within that
        # mode — e.g. root=5 in mixolydian is a MINOR v (Gm), not V. Skip when the
        # chord has no third (sus / omit-3 power chord).
        has_third = not (c.get('suspensions') or []) and 3 not in (c.get('omits') or [])
        if has_third:
            deg3 = ((r - 1 + 2) % 7) + 1              # the chord's third, as a scale degree
            third_iv = (MODE_INT[bor][deg3] - MODE_INT[bor][r]) % 12
            if third_iv == 3:                         # minor third → lowercase
                base = base.lower()
            elif third_iv == 4:                       # major third → uppercase
                base = base.upper()
        diff = MODE_INT[bor][r] - MAJ_INT[r]          # flat/sharp vs the major scale
        if diff < 0:
            base = 'b' * (-diff) + base
        elif diff > 0:
            base = '#' * diff + base

    # type-7: maj7 on I/IV diatonic-major (no borrow), else dom7/min7 (Roman case carries quality)
    if t == 7:
        if r in (1, 4) and not bor:
            base += 'maj7'
        else:
            base += '7'
    elif t in (9, 11, 13):
        base += str(t)

    # Other extensions (sus/add/omit/alterations)
    for s in c.get('suspensions') or []:
        base += 'sus' + str(s)
    for a in c.get('adds') or []:
        base += f'add{a}'
    om = c.get('omits') or []
    if 3 in om and not (c.get('suspensions') or []) and not (c.get('adds') or []):
        base += '5'
    elif 3 in om:
        base += '(no3)'
    if 5 in om:
        base += '(no5)'
    for a in c.get('alterations') or []:
        base += str(a)
    return base


# Compatibility alias for older code that may have expected this name
roman_label = chord_label


if __name__ == '__main__':
    # Smoke tests
    tests = [
        ({'root': 1, 'type': 5}, 'major', 'I'),
        ({'root': 5, 'type': 5}, 'major', 'V'),
        ({'root': 6, 'type': 5}, 'major', 'vi'),
        ({'root': 5, 'applied': 5, 'type': 5}, 'major', 'V/V'),
        ({'root': 5, 'applied': 5, 'type': 5}, 'minor', 'V/iii'),     # minor V/V shifts to V/iii
        ({'root': 7, 'borrowed': 'mixolydian', 'type': 5}, 'major', 'IV/IV'),
        ({'root': 7, 'borrowed': 'minor', 'type': 5}, 'major', 'IV/IV'),
        ({'root': 4, 'applied': 4, 'type': 5}, 'major', 'IV/IV'),
        ({'root': 1, 'type': 7}, 'major', 'Imaj7'),
        ({'root': 5, 'type': 7}, 'major', 'V7'),
        ({'root': 6, 'type': 7}, 'major', 'vi7'),
        ({'root': 7, 'applied': 5, 'type': 5}, 'minor', 'V/V'),       # VII/V in minor → V/V in major
        ({'root': 5, 'type': 5, 'omits': [3]}, 'major', 'V5'),         # power chord on V
        ({'root': 5, 'borrowed': 'mixolydian', 'type': 5}, 'major', 'v'),   # minor v (Gm) — quality from the third
        ({'root': 5, 'borrowed': 'minor', 'type': 5}, 'major', 'v'),        # minor v via aeolian borrow
        ({'root': 5, 'borrowed': 'mixolydian', 'type': 7}, 'major', 'v7'),  # minor v7 (Gm7)
        ({'root': 6, 'borrowed': 'minor', 'type': 5}, 'major', 'bVI'),      # bVI stays MAJOR (Ab)
        ({'root': 3, 'borrowed': 'minor', 'type': 5}, 'major', 'bIII'),     # bIII stays MAJOR (Eb)
        ({'root': 5, 'borrowed': 'mixolydian', 'type': 5, 'suspensions': [4]}, 'major', 'Vsus4'),  # sus → no third, keep V
        ({'root': 3, 'applied': 7, 'type': 5}, 'major', 'vii°/iii'),   # secondary leading-tone dim → iii (Lovefool D#dim)
        ({'root': 2, 'applied': 7, 'type': 5}, 'major', 'vii°/ii'),    # → ii (Bennie G#dim)
        ({'root': 5, 'applied': 7, 'type': 7}, 'major', 'vii°7/V'),    # dim7 → V (Blackbird C#dim7)
        ({'root': 1, 'applied': 7, 'type': 7}, 'major', 'vii°7'),      # dim7 of the tonic
    ]
    fail = 0
    for c, sc, expected in tests:
        got = chord_label(c, sc)
        mark = '✓' if got == expected else '✗'
        if got != expected:
            fail += 1
        print(f"  {mark} chord_label({c}, {sc!r}) = {got!r} (expected {expected!r})")
    print(f"\n{len(tests) - fail}/{len(tests)} passed")
