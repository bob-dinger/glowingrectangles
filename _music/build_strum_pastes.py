"""Curated 'strums to try' -> one Hookpad paste on the Desktop.

Each strum is one 4/4 bar written as 4 beat-cells over the alphabet:
    .  = rest (skip beat)     D  = downstroke      DU = down-up      .U = push (skip down, catch up)
A strike becomes a re-struck I chord at that 8th-slot (rhythm only, no melody).
Each pattern gets its own named section + 1 empty bar of space so it's audible
on its own. 2-bar patterns are A + an answer-op on bar B (AA'/AB).

    python _music/build_strum_pastes.py
"""
import json, os

# ---- cell -> onset offsets within a beat (in beats) --------------------------
def cell_onsets(cell, i):
    on = []
    if cell in ('D', 'DU'):  on.append(i)          # downstroke on the beat
    if cell in ('DU', '.U'): on.append(i + 0.5)    # up on the '&'
    return on

def bar_onsets(cells):
    return [b for i, c in enumerate(cells) for b in cell_onsets(c, i)]

def byte(cells):
    m = {'.': '00', 'D': '10', 'DU': '11', '.U': '01'}
    return int(''.join(m[c] for c in cells), 2)

def density(cells): return sum(c in ('D', '.U') for c in cells) + 2*sum(c == 'DU' for c in cells)
def pushes(cells):  return sum(c == '.U' for c in cells)

# ---- curated 1-bar core ------------------------------------------------------
ONES = [
    ('pulse',          ['D', '.', 'D', '.']),     # halves, beats 1&3
    ('quarters',       ['D', 'D', 'D', 'D']),     # steady down
    ('three-then-rest',['D', 'D', 'D', '.']),
    ('front-load',     ['DU', 'DU', 'D', 'D']),
    ('back-load',      ['D', 'D', 'DU', 'DU']),
    ('wonderwall',     ['D', 'D', 'DU', 'D']),
    ('boom-ba',        ['D', 'DU', 'D', 'DU']),
    ('eighths',        ['DU', 'DU', 'DU', 'DU']),  # full drive
    ('folk',           ['D', 'DU', '.U', 'DU']),   # the campfire strum
    ('driving',        ['DU', '.U', 'DU', '.U']),  # Oasis lean
    ('push-3',         ['D', 'D', '.U', 'D']),     # anticipate beat 3
    ('push-4',         ['D', 'D', 'D', '.U']),     # anticipate next bar
    ('reggae-lite',    ['D', '.U', 'D', '.U']),
    ('half-push',      ['D', 'DU', '.U', 'D']),
    ('gallop',         ['D', 'DU', 'DU', 'D']),
    ('ska',            ['.U', '.U', '.U', '.U']),  # all upstrokes (offbeat)
]

# ---- 2-bar answer-ops (bar B from bar A) ------------------------------------
def op_repeat(a):   return list(a)
def op_endpush(a):  return a[:3] + ['.U']   # turnaround: anticipate the loop
def op_endfill(a):  return a[:3] + ['DU']   # turnaround: extra up
def op_openend(a):  return a[:3] + ['.']    # leave space
def op_answer(a):   return ['D', '.', 'DU', '.U']  # sparser call-and-response B

TWOS = [
    ('folk x2',        ['D', 'DU', '.U', 'DU'], op_repeat),
    ('folk turnaround',['D', 'DU', '.U', 'DU'], op_endpush),
    ('quarters+pickup',['D', 'D', 'D', 'D'],    op_endfill),
    ('eighths+open',   ['DU', 'DU', 'DU', 'DU'], op_openend),
    ('island-lean',    ['D', '.U', 'D', '.U'],  op_endpush),
    ('driving 2-bar',  ['DU', '.U', 'DU', '.U'], op_repeat),
    ('wonderwall 2-bar',['D', 'D', 'DU', 'D'],  op_endpush),
    ('boston-answer',  ['D', 'DU', '.', 'D'],   op_answer),      # A states, B answers
    ('backload+turn',  ['D', 'D', 'DU', 'DU'],  op_endpush),
    ('push-4 loop',    ['D', 'D', 'D', '.U'],   op_repeat),
    ('gallop+fill',    ['D', 'DU', 'DU', 'D'],  op_endfill),
    ('half-push x2',   ['D', 'DU', '.U', 'D'],  op_repeat),
    ('open-then-drive',['D', '.', 'D', '.'],    lambda a: ['DU', 'DU', 'DU', 'DU']),
    ('reggae 2-bar',   ['D', '.U', 'D', '.U'],  op_openend),
    ('call-response',  ['D', 'D', 'D', 'D'],    op_answer),
]

# ---- render to chords --------------------------------------------------------
def chord(beat, dur, root=1):
    return {'root': root, 'beat': round(beat, 3), 'duration': round(dur, 3), 'type': 5,
            'inversion': 0, 'applied': 0, 'adds': [], 'omits': [], 'alterations': [],
            'suspensions': [], 'substitutions': [], 'pedal': None, 'alternate': '',
            'borrowed': '', 'isRest': False, 'recordingEndBeat': None}

def emit(onsets, base_beat, span):
    """onsets: absolute beat offsets (0-based within pattern); span = total beats."""
    out = []
    for j, o in enumerate(onsets):
        nxt = onsets[j+1] if j+1 < len(onsets) else span
        out.append(chord(base_beat + o, nxt - o))
    return out

def main():
    chords, sections = [], []
    cursor = 1.0            # Hookpad beats are 1-indexed
    GAP = 4                 # one empty bar between patterns

    def add(name, onsets, span):
        nonlocal cursor
        sections.append({'beat': cursor, 'name': name})
        chords.extend(emit(onsets, cursor, span))
        cursor += span + GAP

    for k, (name, cells) in enumerate(ONES):
        label = ('1BAR · ' if k == 0 else '') + f'{name} [{byte(cells)}]'
        add(label, bar_onsets(cells), 4)

    for k, (name, a, op) in enumerate(TWOS):
        name = ('2BAR · ' if k == 0 else '') + name
        b = op(a)
        onsets = bar_onsets(a) + [4 + x for x in bar_onsets(b)]
        add(f'{name}', onsets, 8)

    obj = {'notes': [], 'chords': chords, 'audioTracks': [],
           'keys': [{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
           'tempos': [{'beat': 1, 'bpm': 100, 'swingFactor': 0, 'swingBeat': 0.5}],
           'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
           'sections': sections, 'endBeat': int(cursor), 'version': 1}
    out = os.path.expanduser('~/Desktop/strums_to_try_hookpad.txt')
    with open(out, 'w') as f:
        f.write(json.dumps(obj, separators=(',', ':')))
    print(f'{len(ONES)} one-bar + {len(TWOS)} two-bar -> {out}')
    print(f'{len(chords)} chords, {len(sections)} sections, endBeat {int(cursor)}')
    print('\n1-BAR CORE:')
    for name, cells in ONES:
        print(f'  {name:16} {" ".join(cells):16} byte={byte(cells):>3} dens={density(cells)} push={pushes(cells)}')
    print('\n2-BAR (A + answer-op):')
    for name, a, op in TWOS:
        print(f'  {name:18} A={" ".join(a):14} B={" ".join(op(a))}')

if __name__ == '__main__':
    main()
