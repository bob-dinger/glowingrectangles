"""A CLIMB: a melodic figure defined relative to the chord, not as fixed pitches.

The user: "there are note climbs all over music. it's like its own category of riff."

The source example runs root, fifth, octave, twelfth over every chord — four eighths,
identical shape on IV, V, I and vi:

    IV   F4 C5 F5 C6      [0, 4, 7, 11] scale steps above the chord root
    V    G4 D5 G5 D6      [0, 4, 7, 11]
    I    C4 G4 C5 G5      [0, 4, 7, 11]
    vi   A3 E4 A4 E5      [0, 4, 7, 11]

Because it is stated in steps above the root it permutes for free — unlike a melody,
there is nothing to invent. And because [0,4,7,11] SKIPS THE THIRD it is
mode-agnostic: the same shape sits on a major or a minor chord without adjustment,
which is why the figure can run through IV V I vi unchanged.

Voicing: the figure starts on the chord root placed low — the root's own scale index,
dropped an octave when it would otherwise start above G, which is what the source
does (A starts at A3, not A4).
"""
import sys

# Two ways to write a figure:
#   comma form   "0,4,7,11"  raw scale steps above the chord root
#   digit form   "1232"      CHORD-TONE POSITIONS — 1 root, 2 third, 3 fifth,
#                            4 octave, 5 tenth, 6 twelfth, 7 two octaves
# The digit form is the useful one: "1232" is root-third-fifth-third, "1243" and
# "1342" are re-orderings of the same four tones, and there are 24 of those.
# Working in SCALE STEPS means the third is automatically the right quality — +2
# steps over Am is C (minor third), over C is E (major third). No mode handling.
POSITION = {1: 0, 2: 2, 3: 4, 4: 7, 5: 9, 6: 11, 7: 14}

# A figure has a SHAPE and a CAST, exactly as a chord spec does one level up:
#   shape   which slots share a tone, by role letter    ABCB
#   cast    which chord tone fills each role            1,3,2
#   =>      the compact form                            p1232
# Shape is derivable from the compact form, so folder names carry the compact one;
# `shape_of` and `casts_of` recover the grouping. 4 slots over 3 tones gives 6
# shapes (which two of the four slots share a tone, C(4,2)) x 6 casts = 36.

def shape_of(spec):
    """'1232' -> 'ABCB' — relabel by first appearance."""
    t = str(spec).lstrip('p')
    seen, out = {}, ''
    for c in t:
        if c not in seen: seen[c] = chr(ord('A') + len(seen))
        out += seen[c]
    return out

def from_shape(shape, cast):
    """('ABCB', '132') -> '1232'. cast gives the tone for A, B, C… in order."""
    roles = []
    for c in shape:
        if c not in roles: roles.append(c)
    if len(cast) != len(roles):
        sys.exit(f"{shape}:{cast} — shape has {len(roles)} roles, cast gives {len(cast)}")
    m = dict(zip(roles, cast))
    return ''.join(m[c] for c in shape)

def parse(spec):
    """'0,4,7,11' or '1232' -> [steps above the chord root]."""
    t = str(spec).strip()
    if ',' in t or t.startswith('-'):
        try:
            steps = [int(x) for x in t.split(',')]
        except ValueError:
            sys.exit(f"{spec}: a climb is whole scale steps above the root, e.g. 0,4,7,11")
    elif ':' in t:                      # shape:cast, e.g. ABCB:132
        sh, _, ca = t.partition(':')
        steps = [POSITION[int(c)] for c in from_shape(sh.upper(), ca)]
    elif t.startswith('p') and t[1:].isdigit():
        t = t[1:]
        steps = [POSITION[int(c)] for c in t]
    elif t.isdigit():
        bad = [c for c in t if int(c) not in POSITION]
        if bad:
            sys.exit(f"{spec}: chord-tone positions are 1-7 (1 root, 2 third, 3 fifth, "
                     f"4 octave, 5 tenth, 6 twelfth, 7 two octaves); got {''.join(bad)}")
        steps = [POSITION[int(c)] for c in t]
    else:
        sys.exit(f"{spec}: want digits like 1232, or steps like 0,4,7,11")
    if not steps:
        sys.exit(f"{spec}: empty climb")
    return steps

def label(spec):
    """Folder tag. A digit figure gets the user's 'p' prefix — p1243 — because a bare
    135 reads as a chord progression (C-Em-G), not a figure."""
    t = str(spec).strip()
    if ':' in t:
        sh, _, ca = t.partition(':')
        t = from_shape(sh.upper(), ca)
    t = t.lstrip('p')
    return ('p' + t) if t.isdigit() else ('clm' + t.replace(',', '-'))

def start_index(root):
    """The chord root voiced low: its scale index, dropped an octave above G."""
    i = root - 1
    return i - 7 if i > 4 else i

def notes_for(root, onset, dur, spec):
    """Hookpad notes for one chord's slot, the figure spread evenly across it."""
    steps = parse(spec)
    base = start_index(root)
    each = dur / len(steps)
    out = []
    for j, st in enumerate(steps):
        p = base + st
        out.append({"sd": str((p % 7) + 1), "octave": p // 7,
                    "beat": onset + j*each, "duration": each,
                    "isRest": False, "recordingEndBeat": None})
    return out
