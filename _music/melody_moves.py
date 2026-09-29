"""Where does a melody go when it changes note?

The user: "how many shift to a new place, jumping other used notes, like D-D-C-E
(E jumps the D that has already been used)."

Every transition is classified against what the section has ALREADY established,
because that is what makes a leap feel like a leap — not its size, but whether it
vaults over ground the melody already owns. `used` resets each section.

    repeat       same pitch again
    step-known   one scale step, onto a pitch already used
    step-new     one scale step, onto a pitch heard for the first time
    vault        >= 2 steps onto a NEW pitch, over at least one USED pitch   <- the case
    reach        >= 2 steps onto a NEW pitch, over nothing already used
    return       >= 2 steps back onto a pitch already used

Pitch space is diatonic (octave*7 + degree), so "one step" is one scale degree and
accidentals fold onto their natural — this is about melodic distance, not semitones.

    themap_venv/python melody_moves.py
    themap_venv/python melody_moves.py --song "norwegian wood"
    themap_venv/python melody_moves.py --demo D-D-C-E
"""
import os, re, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

DEG = {'1':0, '2':1, '3':2, '4':3, '5':4, '6':5, '7':6}
ORDER = ['repeat', 'step-known', 'step-new', 'vault', 'reach', 'return']

def idx(n):
    m = re.match(r'^[b#]*([1-7])$', str(n.get('sd', '')))
    return None if not m else n.get('octave', 0)*7 + DEG[m.group(1)]

def classify(pitches):
    """Yield (move, delta) for each transition, tracking what is already used."""
    used = {pitches[0]}
    for a, b in zip(pitches, pitches[1:]):
        d = b - a
        if d == 0:
            yield 'repeat', d
        else:
            new = b not in used
            between = range(min(a, b)+1, max(a, b))
            hurdled = sum(1 for p in between if p in used)
            if abs(d) == 1:
                yield ('step-new' if new else 'step-known'), d
            elif not new:
                yield 'return', d
            else:
                yield ('vault' if hurdled else 'reach'), d
        used.add(b)

def section_pitches(d):
    """Yield (section name, [pitch indices]) — melody only, rests dropped."""
    notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                   key=lambda n: n['beat'])
    for name, s0, s1 in corpus.sections(d):
        ps = [idx(n) for n in notes if s0 <= n['beat'] < s1]
        ps = [p for p in ps if p is not None]
        if len(ps) >= 4:
            yield name, ps

def table(counts, sizes, label, total):
    print(f"\n{label}  ({total} transitions)")
    for m in ORDER:
        n = counts[m]
        sz = sizes[m]
        extra = f"  mean jump {sum(abs(x) for x in sz)/len(sz):.2f} steps" if sz and m not in ('repeat',) else ""
        print(f"  {m:11} {n:7} {100*n/total:5.1f}%  {'#'*int(46*n/total)}{extra}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--song'); ap.add_argument('--demo')
    a = ap.parse_args()

    if a.demo:
        names = a.demo.upper().split('-')
        scale = 'CDEFGAB'
        ps, oct_ = [], 0
        for i, nm in enumerate(names):
            p = scale.index(nm[0])
            if ps and p < ps[-1] % 7 and p + 7 - ps[-1] % 7 <= 3: p += 7   # nearest upward
            ps.append(p)
        print(f"{a.demo}  ->  pitches {ps}")
        for (m, d), b in zip(classify(ps), names[1:]):
            print(f"   -> {b:2} {m:11} {d:+d}")
        return

    counts = collections.Counter(); sizes = collections.defaultdict(list)
    per_role = collections.defaultdict(collections.Counter)
    total = 0
    for name, d, nb in corpus.songs(need_chords=False):
        if a.song and a.song.lower() not in name.lower(): continue
        for sec, ps in section_pitches(d):
            role = re.sub(r'[^a-z]', '', sec.lower()) or 'unnamed'
            for m, delta in classify(ps):
                counts[m] += 1; sizes[m].append(delta); total += 1
                per_role[role][m] += 1
    if not total:
        print('no melodies matched'); return
    table(counts, sizes, a.song or 'whole corpus', total)

    if not a.song:
        print("\nby section role (share of that role's transitions)")
        hdr = ''.join(f"{m[:6]:>8}" for m in ORDER)
        print(f"  {'role':12}{hdr}    n")
        for role, c in sorted(per_role.items(), key=lambda kv: -sum(kv[1].values()))[:8]:
            t = sum(c.values())
            row = ''.join(f"{100*c[m]/t:7.1f}%" for m in ORDER)
            print(f"  {role[:12]:12}{row} {t:7}")

if __name__ == '__main__':
    main()
