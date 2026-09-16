"""Two-way translator between strike onsets (Hookpad beats) and D/U strum
notation (Ultimate Guitar style). D/U is not stored data — it falls out of the
"strumming machine": the hand alternates down-up continuously, so a strike's
direction is fixed by its slot position AT THE BEAT'S RESOLUTION.

  - 8th-note beat:  down on the beat, UP on the '&'         (D U)
  - 16th-note beat: down on beat & '&', UP on the 'e'/'a'   (D U D U)

So the '&' flips direction depending on whether that beat is strummed in 8ths
or 16ths. Resolution is detected per beat (any onset on a .25/.75 => 16th).
"""

def _res(onsets_in_beat):
    return 16 if any(round(o % 1, 2) in (0.25, 0.75) for o in onsets_in_beat) else 8

def to_du(onsets, bars=None):
    """onsets: strike times in beats, 0-based from bar 1 downbeat.
    Returns a string, one space-separated cell per beat: chars D/U for strikes,
    '.' for empty slots (at that beat's resolution)."""
    onsets = sorted(set(round(o, 3) for o in onsets))
    nbeats = bars * 4 if bars else int(max(onsets)) + 1
    cells = []
    for b in range(nbeats):
        here = [o for o in onsets if b <= o < b + 1]
        res = _res([o - b for o in here])
        step = 1.0 / (res / 4)          # 8->0.5, 16->0.25
        n = int(round(1 / step))        # slots this beat: 2 or 4
        cell = ''
        for s in range(n):
            pos = b + s * step
            if any(abs(pos - o) < 1e-6 for o in here):
                cell += 'D' if s % 2 == 0 else 'U'   # even slot = down, odd = up
            else:
                cell += '.'
        cells.append(cell)
    return ' '.join(cells)

def from_du(du):
    """D/U string (space per beat) -> onset beats. Inverse of to_du."""
    onsets = []
    for b, cell in enumerate(du.split()):
        n = len(cell)                    # 2 = eighths, 4 = sixteenths
        step = 1.0 / n
        for s, ch in enumerate(cell):
            if ch in 'DUx':
                onsets.append(round(b + s * step, 3))
    return onsets

def to_flat(onsets, bars=None, miss='.', barsep='|'):
    """Canonical display: full DUDUDUDU with skipped slots shown IN PLACE as
    `miss` ('.' unambiguous, ' ' = UG style). One char per 8th-slot; bars split
    by `barsep`. Byte = read D/U as 1, miss as 0."""
    onsets = set(round(o, 3) for o in onsets)
    nbeats = bars * 4 if bars else int(max(onsets)) + 1
    out = []
    for bar in range((nbeats + 3) // 4):
        here = [o for o in onsets if bar * 4 <= o < bar * 4 + 4]
        res16 = any(round(o % 0.5, 3) in (0.25,) or round(o % 1, 3) in (0.25, 0.75)
                    for o in here)                # bar has a 16th onset?
        nslot, step = (16, 0.25) if res16 else (8, 0.5)
        chars = ''
        for s in range(nslot):
            pos = bar * 4 + s * step
            if any(abs(pos - o) < 1e-6 for o in here):
                chars += 'D' if s % 2 == 0 else 'U'
            else:
                chars += miss
        out.append(chars)
    return f' {barsep} '.join(out)


def from_flat(s):
    """Parse a flat D/U string (any non-D/U char = a skipped slot) -> onsets.
    Bars split on '|'; a bar of >8 chars is read at 16th resolution, else 8th."""
    onsets = []
    for bar, part in enumerate(s.split('|')):
        part = part.strip()
        step = 0.25 if len(part) > 8 else 0.5
        for slot, ch in enumerate(part):
            if ch.upper() in 'DU':
                onsets.append(round(bar * 4 + slot * step, 3))
    return onsets


def check_machine(s):
    """Verify every written stroke matches the down-up alternation for its slot
    (even slot=Down, odd=Up). Returns list of violating (bar, slot, wrote, want)."""
    bad = []
    for bar, part in enumerate(s.split('|')):
        part = part.strip()
        for slot, ch in enumerate(part):
            if ch.upper() in 'DU':
                want = 'D' if slot % 2 == 0 else 'U'
                if ch.upper() != want:
                    bad.append((bar, slot, ch.upper(), want))
    return bad


def from_ug(s, res=8):
    """Parse a struck-only UG strum string ('DUDU UDU', 'D DU UDU', spaces
    optional) into onset beats. The hand alternates D,U,D,U... over the grid;
    each written letter is placed at the next slot whose implied direction
    matches it, inserting a rest for any skipped slot. That's how UG's spacing
    (a same-direction jump) encodes a missed stroke."""
    step = 4 / res                       # 8->0.5 beats/slot
    onsets, slot = [], 0
    for ch in s:
        if ch.upper() not in 'DU':
            continue
        want = 'D' if slot % 2 == 0 else 'U'
        # advance (skipping = rest) until the grid direction matches this letter
        while ('D' if slot % 2 == 0 else 'U') != ch.upper():
            slot += 1
        onsets.append(round(slot * step, 3))
        slot += 1
    return onsets


def byte8(onsets):
    """8-bit onset byte for a single bar (8th grid). 16ths not representable."""
    slots = ['0'] * 8
    for o in onsets:
        if 0 <= o < 4 and round(o / 0.5, 3).is_integer():
            slots[int(round(o / 0.5))] = '1'
    return int(''.join(slots), 2)


if __name__ == '__main__':
    # pasted rhythm (beats 72-79) normalized to 0-based
    raw = [72, 73, 73.5, 74.5, 75.5, 76, 76.5, 77, 78, 79]
    ons = [b - raw[0] for b in raw]
    du = to_du(ons, bars=2)
    print('pasted rhythm onsets:', ons)
    print('D/U                 :', du)
    print('round-trip ok       :', from_du(du) == [round(o, 3) for o in ons])
