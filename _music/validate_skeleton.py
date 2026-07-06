"""Dev loop for the SIMPLIFIER. 'mine_perfect melodies' stores songs as versions:
v0 = real, v1 = hand-simplified (v2+ = alternate simplifications). This runs
skeleton.simplify() on v0 and scores it against v1 (ground truth), so we can see
whether the subtractive selector reproduces the user's bones. Re-run after any
edit to simplify(). Same idea as validate_corpus.py for melisma.
"""
import json, os, difflib
import skeleton

CORPUS = os.path.join(os.path.dirname(__file__), 'perfect_melodies.json')

def tok(n): return f"{n['sd']}{'^' if n['octave']>0 else (',' if n['octave']<0 else '')}"
def pitches(ns): return [tok(n) for n in ns]
def rhythms(ns): return [round(n['duration'], 2) for n in ns]
def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio()

def show(ns): return ' '.join(tok(n) + '(' + format(n['duration'], 'g') + ')' for n in ns)

def main():
    corpus = json.load(open(CORPUS))
    rows = []
    for name, vers in corpus.items():
        if len(vers) < 2:
            continue
        real, target = vers[0], vers[1]
        pr, pt = set(pitches(real)), set(pitches(target))
        genuine = len(pr & pt) / len(pr | pt)           # palette overlap = same phrase?
        mel = skeleton.simplify(real)                    # melody axis only (keep rhythm)
        both = skeleton.simplify_rhythm(mel)             # + rhythm axis (regularize)
        def sc(o): return sim(pitches(o), pitches(target)), sim(rhythms(o), rhythms(target))
        pm, rm = sc(mel); pb, rb = sc(both)
        axis = 'melody-only' if (pm + rm) >= (pb + rb) else 'melody+rhythm'
        best = (pm, rm) if axis == 'melody-only' else (pb, rb)
        rows.append((name, genuine, best[0], best[1], axis))
        flag = '' if genuine > 0.55 else '   (NOT same phrase - skip)'
        print(f"\n### {name}  genuine={genuine:.0%}{flag}")
        print(f"    melody-only   pitch {pm:.0%}  rhythm {rm:.0%}")
        print(f"    melody+rhythm pitch {pb:.0%}  rhythm {rb:.0%}   <- target used: {axis}")
        print(f"    target : {show(target)}")
        print(f"    {axis:13}: {show(both if axis=='melody+rhythm' else mel)}")
    genu = [x for x in rows if x[1] > 0.55]
    print(f"\n{'='*64}\nGENUINE PAIRS: {len(genu)}/{len(rows)}  (best-axis per song)")
    if genu:
        print(f"  mean pitch {sum(x[2] for x in genu)/len(genu):.0%}   mean rhythm {sum(x[3] for x in genu)/len(genu):.0%}")
        for name, g, p, r, axis in sorted(genu, key=lambda x: x[2] + x[3]):
            print(f"  {name:16} pitch {p:>4.0%}  rhythm {r:>4.0%}   [{axis}]")

if __name__ == '__main__':
    main()
