"""Terminal visualizer for chord progressions — piano-roll style.

Usage:
    python chord_viz.py "I-Imaj7-vi7-I"             # default C major
    python chord_viz.py "I-V-vi-IV" --key G
    python chord_viz.py "I-bVII-IV-I" --key D

Shows a piano-roll-style chromatic-pitch grid:
  - Rows = pitches (low at bottom, high at top, like a keyboard)
  - Columns = chords in the progression
  - Each cell colored by the note's scale-degree in the key
"""
import re, sys, argparse

# Scale-degree colors (24-bit RGB) — match the spreadsheet/CSS palette
DEG_COLORS = {
    1: (232, 69, 69),    # red
    2: (240, 160, 64),   # orange
    3: (232, 200, 40),   # yellow
    4: (80, 200, 120),   # green
    5: (80, 144, 240),   # blue
    6: (184, 112, 240),  # purple
    7: (224, 112, 176),  # pink
}

def blend(a, b, t=0.5):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

# 12-semitone color map (keyed by key-relative semitone). Chromatics blend adjacent diatonic colors.
SEMI_TO_COLOR_DEG = {
    0:  (DEG_COLORS[1], '1'),
    1:  (blend(DEG_COLORS[1], DEG_COLORS[2]), 'b2'),
    2:  (DEG_COLORS[2], '2'),
    3:  (blend(DEG_COLORS[2], DEG_COLORS[3]), 'b3'),
    4:  (DEG_COLORS[3], '3'),
    5:  (DEG_COLORS[4], '4'),
    6:  (blend(DEG_COLORS[4], DEG_COLORS[5]), 'b5'),
    7:  (DEG_COLORS[5], '5'),
    8:  (blend(DEG_COLORS[5], DEG_COLORS[6]), 'b6'),
    9:  (DEG_COLORS[6], '6'),
    10: (blend(DEG_COLORS[6], DEG_COLORS[7]), 'b7'),
    11: (DEG_COLORS[7], '7'),
}

PC_NAMES = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
KEY_PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
          'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

ROMAN_RE = re.compile(r'^([b#])?(III|II|IV|VII|VI|V|I|iii|ii|iv|vii|vi|v|i)(.*)$')
ROMAN_VAL = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7}
MAJOR_INTERVALS = {1:0, 2:2, 3:4, 4:5, 5:7, 6:9, 7:11}


def parse_chord(token):
    m = ROMAN_RE.match(token.strip())
    if not m: return None
    flat_sharp, roman, rest = m.groups()
    root_deg = ROMAN_VAL[roman.upper()]
    root_semi = MAJOR_INTERVALS[root_deg]
    if flat_sharp == 'b': root_semi -= 1
    elif flat_sharp == '#': root_semi += 1
    root_semi %= 12
    is_minor_quality = roman.islower()

    has_maj7 = 'maj7' in rest; rest = rest.replace('maj7', '')
    has_13 = bool(re.search(r'(?<!\d)13(?!\d)', rest))
    has_11 = bool(re.search(r'(?<!\d)11(?!\d)', rest))
    has_9  = bool(re.search(r'(?<!\d)9(?!\d)',  rest))
    has_7  = bool(re.search(r'(?<!\d)7(?!\d)',  rest))
    rest = re.sub(r'(?<!\d)(13|11|9|7)(?!\d)', '', rest)

    sus_m = re.search(r'sus([24])', rest)
    sus_n = int(sus_m.group(1)) if sus_m else None
    rest = re.sub(r'sus[24]', '', rest)
    adds = [int(x) for x in re.findall(r'add(\d+)', rest)]
    rest = re.sub(r'add\d+', '', rest)
    alts = re.findall(r'[#b]\d+', rest)

    tones = {0}
    if sus_n == 2: tones.add(2)
    elif sus_n == 4: tones.add(5)
    else: tones.add(3 if is_minor_quality else 4)
    fifth = 7
    if '#5' in alts: fifth = 8
    elif 'b5' in alts: fifth = 6
    tones.add(fifth)
    if has_maj7: tones.add(11)
    elif has_7 or has_13 or has_11 or has_9: tones.add(10)
    if has_9 or has_13 or has_11: tones.add(2)
    if has_11 or has_13: tones.add(5)
    if has_13: tones.add(9)
    for a in adds:
        if a == 9: tones.add(2)
        elif a == 11: tones.add(5)
        elif a == 13: tones.add(9)
        elif a == 6: tones.add(9)
        elif a == 4: tones.add(5)
        elif a == 2: tones.add(2)
    if '#9' in alts: tones.add(3)
    if 'b9' in alts: tones.add(1)

    pcs = sorted(((root_semi + iv) % 12) for iv in tones)
    return {'token': token, 'root_pc': root_semi, 'pcs': pcs}


def bg_color(text, rgb):
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m\033[38;2;0;0;0m{text}\033[0m"


def fg_color(text, rgb, bold=False):
    r, g, b = rgb
    bold_str = '1;' if bold else ''
    return f"\033[{bold_str}38;2;{r};{g};{b}m{text}\033[0m"


def render_piano_roll(progression, key='C', scale='major'):
    chords = [parse_chord(t.strip()) for t in progression.split('-')]
    chords = [c for c in chords if c]
    if not chords:
        print("(could not parse progression)"); return

    chord_w = max(len(c['token']) for c in chords) + 2
    chord_w = max(chord_w, 5)

    # Pitch rows (high to low: B, Bb, A, ..., C). PC index 11 → top, 0 → bottom.
    # Render each row of the piano roll.
    LABEL_W = 4  # column for "Db 1" style label

    # Track which pitches appeared in any chord — used to dim unused rows
    used_pcs = set()
    for c in chords:
        used_pcs.update(c['pcs'])

    # Determine which PCs to display: always show diatonic (0,2,4,5,7,9,11), plus any chromatic that's used.
    diatonic_pcs = set(MAJOR_INTERVALS.values())
    display_pcs = sorted(diatonic_pcs | used_pcs, reverse=True)   # high → low

    # Header row: chord labels at the top
    print()
    print(' ' * (LABEL_W + 1) + '│ ' + ''.join(f"{c['token']:^{chord_w}}" for c in chords))
    print('─' * (LABEL_W + 1) + '┼─' + '─' * (chord_w * len(chords)))

    # Pitch rows from high to low
    for pc in display_pcs:
        col, lbl = SEMI_TO_COLOR_DEG[pc]
        name = PC_NAMES[pc]
        # Left label: "B  7"
        label = f"{name:<2} {lbl:>2}"
        # Row data: filled blocks where the pitch is present in each chord
        cells = []
        for c in chords:
            if pc in c['pcs']:
                # Filled block — show the scale degree
                fill = lbl.center(chord_w)
                cells.append(bg_color(fill, col))
            else:
                cells.append(' ' * chord_w)
        # Label is colored by the pitch's key-relative degree
        is_diatonic = pc in diatonic_pcs
        labeled = fg_color(label, col, bold=is_diatonic)
        print(f"{labeled} │ {''.join(cells)}")

    # Bottom row: chord labels again for easy reference
    print('─' * (LABEL_W + 1) + '┴─' + '─' * (chord_w * len(chords)))
    print(' ' * (LABEL_W + 1) + '  ' + ''.join(f"{c['token']:^{chord_w}}" for c in chords))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('progression', nargs='?')
    ap.add_argument('--key', default='C')
    ap.add_argument('--scale', default='major')
    args = ap.parse_args()

    if args.progression:
        print(f"Key: {args.key} {args.scale}")
        render_piano_roll(args.progression, args.key, args.scale)
    else:
        print(f"Key: {args.key} {args.scale}  (Ctrl+D to exit; 'key X' to change key)")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print(); break
            if not line: continue
            if line.startswith('key '):
                args.key = line.split()[1]; print(f"key → {args.key}"); continue
            render_piano_roll(line, args.key, args.scale)


if __name__ == '__main__':
    main()
