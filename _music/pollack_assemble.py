"""Assemble parsed Pollack figures into a linear per-measure chord sequence,
expanding repeat groups, then align to a Hookpad song's section bar-counts.

Prototype target: 'do you want to know a secret' (dywtkas / Hookpad slug).
"""
import itertools
from pollack_parse import parse_song

def expand_figure(fig, structural_only=True):
    """Return a flat list of measures (each = list of chord names), with
    label-groups repeated per their 'repeat' count.
    structural_only drops passing chords (tokens with no roman numeral)."""
    out = []
    for label, group in itertools.groupby(fig['measures'], key=lambda m: m['label']):
        grp = list(group)
        rep = max(m['repeat'] for m in grp)
        expanded = []
        for m in grp:
            if structural_only:
                keep = [c for c, s in zip(m['chords'], m['structural']) if s and c]
                # if a bar has no labeled chord, fall back to its first token (held-over)
                if not keep:
                    keep = [next((c for c in m['chords'] if c), None)]
                expanded.append(keep)
            else:
                expanded.append([c for c in m['chords'] if c])
        for _ in range(rep):
            out.extend([list(x) for x in expanded])
    return out

def measure_str(chords):
    return ' '.join(c or '·' for c in chords) if chords else '·'

if __name__ == '__main__':
    figs = parse_song('dywtkas')
    roles = ['INTRO (fig 32.1)', 'VERSE+CHORUS (fig 32.2)', 'BRIDGE (fig 32.3)']
    for role, fig in zip(roles, figs):
        lin = expand_figure(fig)
        print(f"=== {role}  = {len(lin)} measures ===")
        for i, m in enumerate(lin, 1):
            print(f"   m{i:2d}: {measure_str(m)}")
        print()
