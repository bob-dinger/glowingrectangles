"""Categorize every Beatles section by its MELODIC phrase form (AABA, AABC, AAB, AA...).

Form letters track the melody, not the chords (verified 2026-07-18). Each section is cut
into equal phrases and the phrases are labelled by melodic likeness — identical -> same
letter, shared opening -> prime (A'), else a new letter.

Bar-scale -> phrase division (the natural one for each, per the user's taxonomy):
    16 bars -> 4 phrases x 4 bars   (AABA / AABC)
    12 bars -> 3 phrases x 4 bars   (AAB)   and also 2 x 6  (AA / 6+6)
     8 bars -> 4 phrases x 2 bars   (AABA)

Sections come from single Hookpad sections AND from stitched runs of consecutive sections
that sum to the target (Things We Said Today carries its 16 as verse8 + prechorus4 + chorus4).
Bar math is meter-aware. Repeated identical sections collapse to one.
"""
import os, re, argparse
from collections import defaultdict, Counter
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

VARIANT = re.compile(r'[-_](simple|hooktab|right|wrong|double|half|\d+|[A-G]b?|mixolydian|ly_o_COMPLETED)$', re.I)
SKIP = re.compile(r'^(intro|outro|section|pickup|)$', re.I)
PRIME = 0.55        # shared opening this fraction -> a prime, not a new letter
SAME = 0.80         # this alike -> the same letter
SEMI = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def numbeats_at(hj, beat):
    ms = sorted(hj.get('meters') or [{'beat': 1, 'numBeats': 4}], key=lambda m: m.get('beat', 1))
    cur = ms[0]
    for m in ms:
        if m.get('beat', 1) <= beat: cur = m
    return cur.get('numBeats') or 4

def bars_between(hj, b0, b1):
    ms = sorted(hj.get('meters') or [{'beat': 1, 'numBeats': 4}], key=lambda m: m.get('beat', 1))
    total, pos = 0.0, b0
    while pos < b1:
        cur = ms[0]
        for m in ms:
            if m.get('beat', 1) <= pos: cur = m
        nxt = min([m['beat'] for m in ms if m.get('beat', 1) > pos] + [b1])
        total += (min(nxt, b1) - pos) / (cur.get('numBeats') or 4)
        pos = min(nxt, b1)
    return round(total, 3)

def bar_at(hj, b0, nbars):
    """beat that sits nbars measures after b0"""
    ms = sorted(hj.get('meters') or [{'beat': 1, 'numBeats': 4}], key=lambda m: m.get('beat', 1))
    pos, left = b0, nbars
    while left > 1e-6:
        cur = ms[0]
        for m in ms:
            if m.get('beat', 1) <= pos: cur = m
        npb = cur.get('numBeats') or 4
        nxt = min([m['beat'] for m in ms if m.get('beat', 1) > pos] + [b0 + 10**9])
        take = min(left, (nxt - pos) / npb)
        pos += take * npb; left -= take
    return pos

def sd_semis(sd):
    m = re.match(r'^([b#]*)(\d)$', str(sd))
    if not m: return None
    acc = sum(-1 if c == 'b' else 1 for c in m.group(1))
    d = int(m.group(2))
    return SEMI.get(d, 0) + acc if d in SEMI else None

def phrase_notes(hj, a, b):
    out = []
    for n in hj.get('notes') or []:
        nb = n.get('beat', 0)
        if not (a <= nb < b) or n.get('isRest'): continue
        sem = sd_semis(n.get('sd'))
        if sem is None: continue
        out.append((sem, int(n.get('octave', 0)), round(nb - a, 2), round(n.get('duration', 1), 2)))
    return tuple(sorted(out, key=lambda x: x[2]))

def melsim(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    ra, rb = {n[2] for n in a}, {n[2] for n in b}
    rhythm = len(ra & rb) / len(ra | rb)
    pa, pb = {n[2]: (n[0], n[1]) for n in a}, {n[2]: (n[0], n[1]) for n in b}
    shared = ra & rb
    pitch = sum(pa[o] == pb[o] for o in shared) / len(shared) if shared else 0.0
    return 0.6 * rhythm + 0.4 * pitch

def label(phrases):
    reps, out = [], []
    for p in phrases:
        hit = None
        for L, rep in reps:
            if melsim(p, rep) >= SAME: hit = L; break
        if hit is None:
            for L, rep in reps:
                if melsim(p, rep) >= PRIME: hit = L + "'"; break
        if hit is None:
            hit = chr(ord('A') + len(reps)); reps.append((hit, p))
        out.append(hit)
    return ''.join(out)

def spans(hj, target):
    """(name, b0, b1) for every single section of `target` bars, plus stitched runs summing
    to it when no single section already covers that span."""
    secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
    if not secs: return
    end = hj.get('endBeat', 0) + 1
    bounds = [((s.get('name') or '').strip(), s.get('beat', 0),
               secs[i + 1]['beat'] if i + 1 < len(secs) else end) for i, s in enumerate(secs)]
    singles = set()
    for nm, b0, b1 in bounds:
        if SKIP.match(nm): continue
        if abs(bars_between(hj, b0, b1) - target) < .05:
            singles.add(b0); yield nm, b0, b1, False
    # composite only for a coherent verse-group: verse -> (pre-chorus)* -> (chorus/refrain).
    # No second verse, no bridge, no solo — those cross a real phrase boundary.
    def role(nm):
        n = nm.lower()
        if 'verse' in n: return 'v'
        if 'pre' in n: return 'p'
        if 'chorus' in n or 'refrain' in n: return 'c'
        return 'x'
    for i in range(len(bounds)):
        if bounds[i][1] in singles or role(bounds[i][0]) != 'v': continue
        for j in range(i + 1, min(i + 4, len(bounds))):
            run = bounds[i:j + 1]
            roles = [role(b[0]) for b in run]
            if roles[j - i] not in ('p', 'c') or 'x' in roles or roles[1:].count('v'): break
            b0, b1 = run[0][1], run[-1][2]
            bb = bars_between(hj, b0, b1)
            if bb > target + .05: break
            if abs(bb - target) < .05 and 'c' in roles:
                segs = '·'.join(f'{b[0][:8]}{bars_between(hj, b[1], b[2]):g}' for b in run)
                yield segs, b0, b1, True
                break

def form_of(hj, b0, b1, nphrases, pbars):
    phs = [phrase_notes(hj, bar_at(hj, b0, k * pbars), bar_at(hj, b0, (k + 1) * pbars))
           for k in range(nphrases)]
    if not any(phs): return None
    return label(phs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bars', type=int, default=16)
    ap.add_argument('--div', choices=['4x4', '3x4', '2x6', '4x2', '2x4'], help='override phrase division')
    a = ap.parse_args()
    div = a.div or {16: '4x4', 12: '3x4', 8: '4x2'}.get(a.bars, '4x4')
    nph, pb = (int(x) for x in div.split('x'))

    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select title,hookpad_json from parcels.songs where hookpad_json is not null "
                "and lower(artist) like %s", ('%beatle%',))
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -len((r[1] or {}).get('notes') or []))

    seen, by = set(), defaultdict(list)
    for t, hj in rows:
        t = (t or '').strip()
        if not t or VARIANT.search(t): continue
        k = norm(t)
        if k in seen: continue
        seen.add(k)
        perslug = set()
        for nm, b0, b1, stitched in spans(hj, a.bars):
            f = form_of(hj, b0, b1, nph, pb) or ('\u2014' if stitched else None)
            if not f: continue
            sig = (re.sub(r'[^a-z]', '', nm.lower()), f)   # one row per section-name + form
            if sig in perslug: continue
            perslug.add(sig)
            by[f].append((t, nm, stitched))

    # singles carry the pure phrase form; composites are the verse-group 8-4-4 shapes
    singtally = Counter(f for f, items in by.items() for _, _, st in items if not st)
    nsing = sum(singtally.values())
    ncomp = sum(1 for items in by.values() for _, _, st in items if st)
    print(f"{a.bars}-bar as {div}  ·  {nsing} single sections + {ncomp} verse-group composites, {len(seen)} songs\n")
    print("SINGLE-SECTION phrase forms:")
    for f, n in singtally.most_common():
        print(f'  {f:<8} {n}')
    print()
    for f, items in sorted(by.items(), key=lambda kv: -sum(1 for x in kv[1] if not x[2])):
        sing = [(t, nm) for t, nm, st in items if not st]
        if len(sing) < 2 and a.bars != 8: continue
        if not sing: continue
        print(f'=== {f} ({len(sing)}) ===')
        for t, nm in sorted(sing, key=lambda x: x[0].lower()):
            print(f'   {t[:30]:32} {nm[:20]}')
        print()
    comps = [(t, nm, f) for f, items in by.items() for t, nm, st in items if st]
    if comps:
        print(f'=== VERSE-GROUP COMPOSITES ({len(comps)}) — melodic form across the whole 16 ===')
        for t, nm, f in sorted(comps, key=lambda x: x[0].lower()):
            print(f'   {f:<7} {t[:28]:30} {nm}')

if __name__ == '__main__':
    main()
