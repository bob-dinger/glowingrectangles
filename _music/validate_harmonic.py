"""Dev loop for the HARMONIC axis. harmonic_examples.json holds human-made
note-per-chord bones. Runs skeleton.simplify_harmonic (dedupe=False = one note
per chord entry) and scores vs the user's bones, trying merge on/off. Re-run
after tuning simplify_harmonic; feed more examples into harmonic_examples.json.
"""
import json, os, difflib, skeleton
C = json.load(open(os.path.join(os.path.dirname(__file__), 'harmonic_examples.json')))
def tok(n): return f"{n['sd']}{'^' if n['octave']>0 else (',' if n['octave']<0 else '')}"
def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio()
rows = []
for name, ex in C.items():
    if name.startswith('_'): continue
    tgt = ex['bones']
    best = None
    for pk in ('downbeat', 'longest'):
        for mg in (False, True):
            got = skeleton.simplify_harmonic(ex['real'], ex['chords'], fill=True, merge=mg, measure=ex.get('measure'), pick=pk)
            p = sim([tok(n) for n in got], [tok(n) for n in tgt])
            r = sim([round(n['duration'],2) for n in got], [round(n['duration'],2) for n in tgt])
            if best is None or p+r > best[0]+best[1]: best = (p, r, mg, pk, got)
    p, r, mg, pk, got = best
    rows.append((name, p, r))
    print(f"\n### {name}   pitch {p:.0%}  rhythm {r:.0%}  (merge={mg}, pick={pk})")
    print(f"   bones: {'-'.join(tok(n) for n in tgt)}")
    print(f"   tool : {'-'.join(tok(n) for n in got)}")
if rows:
    n=len(rows); print(f"\n{'='*50}\n{n} examples  mean pitch {sum(x[1] for x in rows)/n:.0%}  rhythm {sum(x[2] for x in rows)/n:.0%}")
