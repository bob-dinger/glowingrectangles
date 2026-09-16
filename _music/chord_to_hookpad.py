"""Convert Guitar Pro chord names (e.g., "Em7", "G/B", "F#m7b5", "C7sus4") to
Hookpad chord-data dicts (root: 1-7 scale degree, type, borrowed, applied, etc).

Hookpad chord schema fields:
    root          1-7 (scale degree in song's key)
    type          '' (triad) | '5' (power) | '7' (dom7) | 'm' (minor, rare)
    borrowed      'minor' | 'dorian' | 'mixolydian' | 'major' | ...
    applied       integer (secondary dominant target degree)
    adds          list e.g. [6], [9]
    suspensions   list e.g. [2], [4]
    alterations   list of (degree, '#' or 'b')
    pedal         bass-note pitch class (for slash chords)
"""
import re

# Pitch-class indices: C=0, C#=1, ..., B=11
_PITCH_CLASS = {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11}

# Major scale: degree (1-indexed) -> pitch class offset from tonic
_MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]  # I ii iii IV V vi vii
# Natural minor scale
_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]   # i ii bIII iv v bVI bVII


def parse_root_pitch(s):
    """Parse 'C', 'C#', 'Db', 'F#', 'Bb' → pitch class 0-11. Returns (pc, rest_of_string)."""
    if not s: return None, s
    pc = _PITCH_CLASS.get(s[0].upper())
    if pc is None: return None, s
    rest = s[1:]
    if rest.startswith('#'):
        pc = (pc + 1) % 12; rest = rest[1:]
    elif rest.startswith('b') and not rest.startswith('bb'):
        # Be careful with 'bb' which could mean double-flat... rare in chord names
        pc = (pc - 1) % 12; rest = rest[1:]
    return pc, rest


def parse_chord_name(name):
    """Parse a chord-name string into structured pieces.
    Returns: {'root_pc': int, 'quality': str, 'extensions': list, 'sus': int|None,
              'bass_pc': int|None, 'alterations': list}.

    Examples:
      "C"     -> root=0, quality='major'
      "Em7"   -> root=4, quality='minor', extensions=[7]
      "G7"    -> root=7, quality='dom', extensions=[7]
      "Gmaj7" -> root=7, quality='major', extensions=[7maj]
      "C5"    -> root=0, quality='power'
      "Dsus4" -> root=2, quality='major', sus=4
      "G/B"   -> root=7, quality='major', bass_pc=11
      "F#m7b5"-> root=6, quality='minor', extensions=[7], alterations=[(5,'b')]
      "Ab7M"  -> root=8, quality='major', extensions=[7maj]  (Hookpad uses 7M for maj7)
      "Cm6"   -> root=0, quality='minor', extensions=[6]
    """
    name = name.strip()
    # Split off bass note (slash chord)
    bass_pc = None
    if '/' in name:
        # Skip /5- and /3+ style alterations
        slash_idx = name.find('/')
        after_slash = name[slash_idx+1:]
        # If after_slash looks like a pitch letter, it's a bass note
        if after_slash and after_slash[0] in 'CDEFGAB':
            bass_pc, _ = parse_root_pitch(after_slash)
            name = name[:slash_idx]

    root_pc, rest = parse_root_pitch(name)
    if root_pc is None: return None

    quality = 'major'
    extensions = []
    sus = None
    alterations = []

    # Check for minor (m, but not maj). Walk through patterns.
    # Use regex-ish parsing to handle order-sensitive bits.
    # Common patterns:
    #   m, min, -          -> minor
    #   maj, M, Maj        -> major (often used for maj7)
    #   dim, °             -> diminished
    #   aug, +             -> augmented
    #   sus2, sus4         -> suspended
    #   5                  -> power chord
    #   6, 7, 9, 11, 13    -> extensions
    #   7M, maj7, M7       -> major 7
    #   add9, add11, add13 -> extensions without 7 stacked
    #   b5, #5, b9, #9, b13-> alterations

    # Detect quality
    if rest.startswith('maj') or rest.startswith('Maj'):
        # "maj7" or "maj" alone
        rest = rest[3:]
        if rest.startswith('7'):
            extensions.append(('7M',))   # major 7th
            rest = rest[1:]
    elif rest.startswith('m') and not rest.lower().startswith('maj'):
        quality = 'minor'; rest = rest[1:]
        if rest.lower().startswith('aj7'):
            # 'mAj7' weird; not handling
            pass
    elif rest.startswith('-'):
        quality = 'minor'; rest = rest[1:]
    elif rest.startswith('dim') or rest.startswith('°'):
        quality = 'dim'; rest = rest[3:] if rest.startswith('dim') else rest[1:]
    elif rest.startswith('aug') or rest.startswith('+'):
        quality = 'aug'; rest = rest[3:] if rest.startswith('aug') else rest[1:]
    elif rest.startswith('5') and (len(rest) == 1 or not rest[1].isdigit()):
        quality = 'power'; rest = rest[1:]

    # Walk remaining chars for sus, extensions, alterations
    while rest:
        if rest.startswith('sus'):
            m = re.match(r'sus(2|4)', rest)
            if m: sus = int(m.group(1)); rest = rest[len(m.group(0)):]
            else: sus = 4; rest = rest[3:]
        elif rest.startswith('add'):
            m = re.match(r'add(\d+)', rest)
            if m: extensions.append(int(m.group(1))); rest = rest[len(m.group(0)):]
            else: rest = rest[3:]
        elif rest.startswith('7M') or rest.startswith('M7'):
            extensions.append(('7M',)); rest = rest[2:]
        elif rest.startswith('b') and len(rest) > 1 and rest[1].isdigit():
            m = re.match(r'b(\d+)', rest)
            if m: alterations.append((int(m.group(1)), 'b')); rest = rest[len(m.group(0)):]
        elif rest.startswith('#') and len(rest) > 1 and rest[1].isdigit():
            m = re.match(r'#(\d+)', rest)
            if m: alterations.append((int(m.group(1)), '#')); rest = rest[len(m.group(0)):]
        elif rest[0].isdigit():
            m = re.match(r'(\d+)', rest)
            if m:
                n = int(m.group(1))
                # If quality is 'major' and we see 7, treat as dom 7 (default)
                if n == 7 and quality == 'major':
                    quality = 'dom'
                extensions.append(n)
                rest = rest[len(m.group(0)):]
        else:
            # Unknown suffix character; skip to avoid infinite loop
            rest = rest[1:]

    return {
        'root_pc': root_pc, 'quality': quality, 'extensions': extensions,
        'sus': sus, 'bass_pc': bass_pc, 'alterations': alterations,
    }


def _scale_degree(root_pc, key_root, key_mode):
    """Map a chord root pitch class to scale degree in the given key.
    Returns (degree 1-7, is_diatonic, semitone_offset_from_diatonic).
    For chromatic roots, picks the nearest diatonic degree and reports offset."""
    interval = (root_pc - key_root) % 12
    scale = _MAJOR_SCALE if key_mode == 'major' else _MINOR_SCALE
    if interval in scale:
        return scale.index(interval) + 1, True, 0
    # Pop/rock convention: prefer flat-side (bVII over #VI). Check "interval+1 in scale" first.
    for i, d in enumerate(scale):
        if d == (interval + 1) % 12:   # interval is a semitone BELOW a diatonic degree → b<degree>
            return i + 1, False, -1
    for i, d in enumerate(scale):
        if d == (interval - 1) % 12:   # interval is a semitone ABOVE a diatonic degree → #<degree>
            return i + 1, False, 1
    closest = min(range(7), key=lambda i: min((scale[i] - interval) % 12, (interval - scale[i]) % 12))
    return closest + 1, False, 0


def chord_to_hookpad(chord_name, key_root, key_mode):
    """Convert a GP chord name to a Hookpad chord-data dict.
    Returns dict with at least {root, type} plus any non-default fields, or None if unparseable.
    Adds '_raw' field with original chord name and '_warnings' for issues."""
    parsed = parse_chord_name(chord_name)
    if not parsed: return {'_raw': chord_name, '_warnings': ['parse_failed']}

    warnings = []
    degree, diatonic, offset = _scale_degree(parsed['root_pc'], key_root, key_mode)

    out = {'root': degree, '_raw': chord_name}

    if not diatonic:
        # Flat-side roots: pick the borrowed mode that actually LOWERS that degree.
        # bIII/bVI/bVII come from natural minor; bII must come from phrygian (minor's
        # 2nd is a whole step, so borrowed='minor' would render the wrong pitch); bV
        # from locrian. Sharp-side roots are usually secondary dominants -> punt lydian.
        _FLAT_MODE = {2: 'phrygian', 3: 'minor', 5: 'locrian', 6: 'minor', 7: 'minor'}
        if offset <= 0:
            out['borrowed'] = _FLAT_MODE.get(degree, 'minor')
        else:
            out['borrowed'] = 'lydian'
        warnings.append(f'non-diatonic root pc={parsed["root_pc"]}')

    # Quality → type/borrowed
    q = parsed['quality']
    if q == 'power':
        out['type'] = '5'
    elif q == 'dom':
        out['type'] = '7'
        # In major mode, dom 7 is diatonic only on V. Otherwise need borrowed=mixolydian or applied.
        if key_mode == 'major' and degree != 5:
            out.setdefault('borrowed', 'mixolydian')
    elif q == 'minor':
        # For diatonic minor chords (ii, iii, vi in major; i, iv, v in minor): no extra type needed
        # (Hookpad treats lowercase from the key context).
        # For non-diatonic minor: mark borrowed minor
        if key_mode == 'major' and degree not in (2, 3, 6):
            out.setdefault('borrowed', 'minor')
        # If has extension 7: it's a minor 7
        if 7 in parsed['extensions']:
            out['type'] = '7'
    elif q == 'major':
        # Major triad. For diatonic non-major-quality positions (ii, iii, vi in major mode are minor),
        # need borrowed=major or applied to make them major.
        if key_mode == 'major' and degree in (2, 3, 6):
            out.setdefault('borrowed', 'major')
        if 7 in parsed['extensions']:
            out['type'] = '7'
            if degree == 1 or degree == 4:
                # In major key, I and IV have diatonic maj7. The 7th adds the diatonic note.
                pass
            else:
                out.setdefault('borrowed', 'mixolydian')
    elif q == 'dim':
        # Diminished: viio in major. Treat as type=7 with borrowed if not on vii
        out.setdefault('alterations', []).append([5, 'b'])
        if 7 in parsed['extensions']:
            out['type'] = '7'
    elif q == 'aug':
        out.setdefault('alterations', []).append([5, '#'])

    # Handle maj7 extensions ('7M')
    for ext in parsed['extensions']:
        if isinstance(ext, tuple) and ext[0] == '7M':
            out['type'] = '7'  # Hookpad handles maj7 via type=7 + key context
        elif isinstance(ext, int):
            if ext == 5: continue   # power chord already handled
            if ext == 7: continue   # already handled above
            if ext == 6: out.setdefault('adds', []).append(6)
            elif ext in (9, 11, 13): out.setdefault('adds', []).append(ext)

    # Suspensions
    if parsed['sus']:
        out['suspensions'] = [parsed['sus']]

    # Alterations
    for alt_deg, alt_sym in parsed['alterations']:
        out.setdefault('alterations', []).append([alt_deg, alt_sym])

    # Slash chord (bass note)
    if parsed['bass_pc'] is not None:
        bass_degree, bass_diatonic, _ = _scale_degree(parsed['bass_pc'], key_root, key_mode)
        out['pedal'] = bass_degree

    if warnings: out['_warnings'] = warnings
    if 'type' not in out: out['type'] = ''
    return out


if __name__ == '__main__':
    # Test cases
    tests = [
        # (chord, key_root, key_mode, expected_root)
        ('C', 0, 'major', 1),
        ('Am', 0, 'major', 6),
        ('G7', 0, 'major', 5),
        ('Em7', 0, 'major', 3),
        ('Fmaj7', 0, 'major', 4),
        ('Dm7b5', 0, 'major', 2),
        ('D5', 2, 'major', 1),    # D power chord in D major
        ('Csus4', 0, 'major', 1),
        ('G/B', 0, 'major', 5),
        ('Bb', 0, 'major', 7),    # bVII
        ('Cm6', 0, 'major', 1),   # i6 borrowed from minor
        ('Ab7M', 10, 'major', 7), # Ab in Bb major = bVII... wait
        ('E7/B', 10, 'major', 4), # E in Bb = #IV ?
    ]
    for name, kr, km, expected in tests:
        r = chord_to_hookpad(name, kr, km)
        ok = '✓' if r and r.get('root') == expected else '✗'
        print(f'  {ok} {name:8s} in {kr}/{km}: {r}')
