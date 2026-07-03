"""Strumming as data: DECODE a Hookpad chord-onset paste into a strum pattern,
ENCODE a named/written strum + a progression back into a paste, and a growing
LIBRARY.  See memory music_chord_riff_fingerprint (Layer 2 = strike rhythm) and
music_skeleton_varier (same skeleton<->varier structure).

Encoding: strumming lives in Hookpad as re-struck CHORDS with empty `notes`.
Each strum onset = one chord event at that beat.

Notation: a bar = 4 space-separated BEAT CELLS (beats 1 2 3 4).  A cell's LENGTH
is its subdivision: 1=quarter, 2=eighths, 3=triplet, 4=sixteenths.  Char per slot:
  D=downstroke   U=upstroke   x=muted chuck   .=no strike
Slot 0 of a cell is the downbeat.  This holds triplets (UG's "3" bracket) and
16ths, not just eighths -- e.g. I'm Only Sleeping = "D D D.U D.U" (triplet swing
on beats 3-4: down on the beat, up on the "let").

Layers (auto-separable from a paste):
  - re-strike of the SAME chord root  = Layer 2 texture (the strum)
  - a NEW chord root                  = a Layer 1 change
  - a new chord landing off the beat  = a PUSH (anticipation)
"""
import os, json
from fractions import Fraction

LIB_PATH = os.path.join(os.path.dirname(__file__), 'strum_library.json')
TOL = 0.04

# ---------------- Library ----------------
def load_lib():
    return json.load(open(LIB_PATH))['patterns']
def save_pattern(name, pattern):
    d = json.load(open(LIB_PATH)); d['patterns'][name] = pattern
    json.dump(d, open(LIB_PATH, 'w'), indent=2); return name

# ---------------- Pattern <-> onsets ----------------
def cell_hits(cell):
    """[(offset_fraction_within_beat, stroke)] for struck slots of one cell."""
    n = len(cell)
    return [(Fraction(i, n), cell[i]) for i in range(n) if cell[i] in 'DUx']

def pattern_onsets(pattern):
    """[(beat_offset_from_bar_start, stroke)] over a whole bar."""
    out = []
    for bi, cell in enumerate(pattern.split()):
        for frac, stroke in cell_hits(cell):
            out.append((bi + float(frac), stroke))
    return out

def _fit_subdiv(offsets):
    """smallest n in 1..4 whose slots land all offsets (fractions of a beat)."""
    for n in (1, 2, 3, 4):
        if all(any(abs(o - k / n) < TOL for k in range(n)) for o in offsets):
            return n
    return 4

def onsets_to_cell(offsets):
    """offsets: fractions-of-a-beat within one beat. -> a cell string."""
    n = _fit_subdiv(offsets)
    cell = ['.'] * n
    for o in offsets:
        i = min(range(n), key=lambda k: abs(o - k / n))
        cell[i] = 'D' if i == 0 else 'U'
    return ''.join(cell)

# ---------------- Decode: paste chords -> pattern(s) ----------------
def decode(chords, nb=4):
    """chords: Hookpad chord dicts. -> per-bar {bar, root, pattern, name, changes, pushes}."""
    chords = sorted(chords, key=lambda c: c['beat'])
    if not chords:
        return []
    first = chords[0]['beat']
    out, prev_root = [], None
    nbars = int((chords[-1]['beat'] - first) // nb) + 1
    for bi in range(nbars):
        bs = first + bi * nb
        evs = [c for c in chords if bs - TOL <= c['beat'] < bs + nb - TOL]
        if not evs:
            continue
        cells, changes, pushes = [], [], []
        for beat in range(nb):
            offs = [c['beat'] - (bs + beat) for c in evs if abs((c['beat'] - bs) - beat) < 1 - TOL and (c['beat'] - bs) - beat >= -TOL]
            cells.append(onsets_to_cell(offs) if offs else '.')
        for c in evs:
            if c['root'] != prev_root:
                off = c['beat'] - bs
                (pushes if abs(off - round(off)) > TOL else changes).append((c['root'], round(off, 3)))
            prev_root = c['root']
        pat = ' '.join(cells)
        out.append({'bar': bi, 'root': evs[0]['root'], 'pattern': pat,
                    'name': match(pat), 'changes': changes, 'pushes': pushes})
    return out

def match(pattern):
    norm = ' '.join(pattern.split())
    for name, p in load_lib().items():
        if ' '.join(p.split()) == norm:
            return name
    return None

# ---------------- Encode: pattern + progression -> paste ----------------
def _chord(root, beat, dur, type=5):
    return {"root": root, "beat": round(beat, 4), "duration": round(dur, 4), "type": type,
            "inversion": 0, "applied": 0, "adds": [], "omits": [], "alterations": [],
            "suspensions": [], "substitutions": [], "pedal": None, "alternate": "",
            "borrowed": "", "isRest": False, "recordingEndBeat": None}

def encode(pattern, progression, start=1, nb=4, type=5):
    """pattern: a written pattern OR a library name. progression: chord roots (one
    per bar) or (root,type) tuples. -> list of Hookpad chord dicts (strum onsets)."""
    pat = load_lib().get(pattern, pattern)
    prog = [p if isinstance(p, tuple) else (p, type) for p in progression]
    ons = pattern_onsets(pat)
    chords = []
    for bi, (root, ty) in enumerate(prog):
        bs = start + bi * nb
        times = [bs + off for off, _ in ons]
        for j, (off, stroke) in enumerate(ons):
            beat = bs + off
            nxt = times[j + 1] if j + 1 < len(times) else bs + nb
            chords.append(_chord(root, beat, nxt - beat, ty))
    return chords

def paste(chords, path=None):
    s = json.dumps({"notes": [], "chords": chords, "audioTracks": [], "version": 1},
                   separators=(',', ':'))
    if path:
        open(os.path.expanduser(path), 'w').write(s)
    return s

# ---------------- Pretty view ----------------
ARROW = {'D': '↓', 'U': '↑', 'x': '×', '.': '·'}
def render(pattern):
    cells = pattern.split()
    top, bot = [], []
    for bi, cell in enumerate(cells):
        top.append(str(bi + 1) + ' ' * (len(cell) * 2 - 1))
        bot.append(' '.join(ARROW[c] for c in cell))
    return "beat:  " + '  '.join(top) + "\nstrum: " + '  '.join(bot)

if __name__ == '__main__':
    lib = load_lib()
    print("== Library ==")
    for n, g in lib.items():
        print(f"  {n:22} {g}")
    print("\n== Decode: I'm Only Sleeping (16th-encoded paste, vi->ii) ==")
    ios = [{"root":6,"beat":289},{"root":6,"beat":290},{"root":6,"beat":291},{"root":6,"beat":291.75},
           {"root":6,"beat":292},{"root":6,"beat":292.75},{"root":2,"beat":293},{"root":2,"beat":294},
           {"root":2,"beat":295},{"root":2,"beat":295.75},{"root":2,"beat":296},{"root":2,"beat":296.75}]
    for bar in decode(ios):
        print(f"  bar {bar['bar']} root {bar['root']}: {bar['pattern']:16} ({bar['name']})")
    print("\n" + render(lib['im-only-sleeping']))
