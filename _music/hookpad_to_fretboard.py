"""Convert a Hookpad melody paste (notes JSON with sd/octave/beat/duration) into a
guitar.html riff array: [stringIdx, fret, midi, durationMs] per note.

Hookpad `sd` is major-scale-relative (b3 = minor third), so only a tonic is needed
(the guitar page has a live transpose control anyway). Picks fretboard positions
that stay in one hand position.

Usage: hookpad_to_fretboard.py <json_file> [tonic_midi_of_sd1_oct0] [beat_ms]
Default tonic0=52 (E3), beat_ms=430.
"""
import json, sys, re

MAJOR = [0, 2, 4, 5, 7, 9, 11]
OPEN = {0: 64, 1: 59, 2: 55, 3: 50, 4: 45, 5: 40}   # e B G D A E (low)

def sd_semitone(sd):
    m = re.match(r'([b#]?)(\d)', str(sd))
    acc, deg = m.group(1), int(m.group(2))
    st = MAJOR[deg - 1]
    return st + (-1 if acc == 'b' else 1 if acc == '#' else 0)

def positions(midi):
    return [(s, midi - o) for s, o in OPEN.items() if 0 <= midi - o <= 16]

def in_range(midi):
    while not positions(midi) and midi < 40: midi += 12
    while not positions(midi) and midi > 80: midi -= 12
    return midi

def convert(notes, tonic0=52, beat_ms=430):
    """Lay the melody out VERTICALLY (in a fret box across strings) rather than
    running horizontally up one string. Pick the anchor fret that keeps every note
    closest to a single hand position, then place each note on whichever string
    lands nearest that anchor."""
    seq = []
    for n in notes:
        if n.get('isRest'):
            continue
        midi = in_range(tonic0 + sd_semitone(n['sd']) + 12 * n.get('octave', 0))
        seq.append((midi, int(round(n.get('duration', 1) * beat_ms))))
    midis = [m for m, _ in seq]

    def box_cost(anchor):
        # sum of each note's nearest-fret distance to the anchor (tight box = low)
        return sum(min(abs(f - anchor) for _, f in positions(m)) for m in midis)
    anchor = min(range(0, 13), key=box_cost)

    out, prev_s = [], 3
    for m, dur in seq:
        # nearest fret to the anchor; tiebreak toward the previous string
        s, f = min(positions(m), key=lambda c: (abs(c[1] - anchor), abs(c[0] - prev_s)))
        prev_s = s
        out.append([s, f, m, dur])
    return out

def as_js(name, arr, comment=''):
    body = ',\n                '.join(
        ', '.join(f'[{a[0]}, {a[1]}, {a[2]}, {a[3]}]' for a in arr[i:i+4])
        for i in range(0, len(arr), 4))
    c = f'\n                // {comment}' if comment else ''
    return f'            {name}: [{c}\n                {body}\n            ]'

if __name__ == '__main__':
    data = json.load(open(sys.argv[1]))
    tonic0 = int(sys.argv[2]) if len(sys.argv) > 2 else 52
    beat_ms = int(sys.argv[3]) if len(sys.argv) > 3 else 430
    arr = convert(data['notes'], tonic0, beat_ms)
    print(as_js('SONGID', arr))
