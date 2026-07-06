"""Survey the library for melodic STRUCTURES. For every vocal section: auto-detect
the reducer knobs (grid, pick), reduce to the harmonic main-note line
(skeleton.simplify_harmonic), then tag it on two independent axes:
  CONTOUR  = shape of the line (arch / descent / ascent / oscillation / pedal / valley / wander)
  MOTIF    = repetition of the line (periodic cell / parallel halves / through-composed)
A section's structural fingerprint = CONTOUR x MOTIF. See REDUCER.md, music_skeleton_varier.
"""
import os, json, collections, statistics
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2
import skeleton as sk

VOCAL = ('verse', 'chorus', 'bridge', 'pre', 'refrain', 'hook')
SKIP = ('solo', 'instrumental', 'intro', 'outro', 'interlude', 'break', 'section')

def pitch(n):
    d = ''.join(c for c in str(n['sd']) if c.isdigit())
    return (int(d) if d else 0) + 7 * n['octave']

# ---- knob auto-detection ----
def detect_grid(sn, sc, nb, span):
    nbars = max(1, round(span / nb))
    return nb if len(sc) > nbars * 1.4 else None      # sub-bar chords -> reduce per measure

def detect_pick(sn, sc, nb):
    cbs = sorted(c['beat'] for c in sc)
    bars = dom = 0
    for i, cb in enumerate(cbs):
        hi = cbs[i+1] if i+1 < len(cbs) else cb + nb
        reg = [n for n in sn if cb - 0.5 <= n['beat'] < hi - 0.5]
        if len(reg) >= 2:
            bars += 1
            durs = sorted(n['duration'] for n in reg)
            if durs[-1] >= 2 * durs[len(durs)//2] and durs[-1] >= nb * 0.5:
                dom += 1                               # one long note dwarfs short pickups
    return 'longest' if bars and dom / bars >= 0.5 else 'downbeat'

# ---- structure tags ----
def contour(seq):
    if len(seq) < 3: return None
    lo, hi = min(seq), max(seq); rng = hi - lo; net = seq[-1] - seq[0]; n = len(seq)
    diffs = [b - a for a, b in zip(seq, seq[1:])]
    rev = sum(1 for i in range(1, len(diffs)) if diffs[i]*diffs[i-1] < 0)
    imax, imin = seq.index(hi), seq.index(lo)
    mid = lambda i: n*0.2 <= i <= n*0.8
    osc = sum(1 for i in range(2, n) if seq[i] == seq[i-2]) / (n-2)
    if rng <= 1: return 'pedal'
    if osc >= 0.5 and rng <= 5: return 'oscillation'
    if net <= -2 and rev <= n/3: return 'descent'
    if net >= 2 and rev <= n/3: return 'ascent'
    if mid(imax) and seq[0] < hi-1 and seq[-1] < hi-1: return 'arch'
    if mid(imin) and seq[0] > lo+1 and seq[-1] > lo+1: return 'valley'
    return 'wander'

def motif(degs):
    n = len(degs)
    for k in range(1, n//2 + 1):
        if n % k == 0 and all(degs[i] == degs[i % k] for i in range(n)):
            return f'cell{k}x{n//k}'                   # perfectly periodic cell
    if n >= 4 and n % 2 == 0 and degs[:n//2] == degs[n//2:]:
        return 'AAparallel'
    if n >= 4 and degs[0] == degs[2] and degs[1] != degs[0]:
        return 'oscel'                                 # ABAB-ish
    return 'through'

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select slug, hookpad_json from parcels.songs where has_chords and has_melody and hookpad_json is not null")
    rows = cur.fetchall()
    con = collections.Counter(); mot = collections.Counter(); cross = collections.Counter()
    ex = collections.defaultdict(list); seen = set(); nsec = 0
    for slug, hj in rows:
        notes = [n for n in (hj.get('notes') or []) if not n.get('isRest')]
        chords = hj.get('chords') or []; secs = hj.get('sections') or []
        nb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        if not (notes and chords and secs): continue
        endb = hj.get('endBeat') or max(n['beat'] for n in notes) + nb
        for i, s in enumerate(secs):
            name = (s.get('name') or '').lower()
            if not any(v in name for v in VOCAL) or any(k in name for k in SKIP): continue
            b0 = s['beat']; b1 = secs[i+1]['beat'] if i+1 < len(secs) else endb
            sn = [n for n in notes if b0 <= n['beat'] < b1]
            sc = [ch for ch in chords if b0 <= ch['beat'] < b1]
            if len(sn) < 4 or len(sc) < 3: continue
            key = (slug, name.split()[0])
            if key in seen: continue
            seen.add(key); nsec += 1
            grid = detect_grid(sn, sc, nb, b1 - b0); pk = detect_pick(sn, sc, nb)
            m = sk.simplify_harmonic(sn, sc, merge=True, measure=grid, pick=pk)
            seq = [pitch(n) for n in m]; degs = [str(n['sd']) for n in m]
            ct = contour(seq)
            if not ct: continue
            mt = motif(degs)
            con[ct] += 1; mot[mt] += 1; cross[(ct, mt)] += 1
            if len(ex[ct]) < 4: ex[ct].append((slug, name.split()[0], '-'.join(degs)))
    print(f"scanned {nsec} vocal sections (knobs auto-detected)\n")
    print("== CONTOUR ==")
    for k, v in con.most_common():
        print(f"  {k:12} {v:4} {v*100//nsec:>3}%   e.g. {ex[k][0][0][:30]}/{ex[k][0][1]}: {ex[k][0][2][:34]}")
    print("\n== MOTIF (repetition) ==")
    for k, v in mot.most_common():
        print(f"  {k:12} {v:4} {v*100//nsec:>3}%")
    print("\n== top CONTOUR x MOTIF fingerprints ==")
    for (ct, mt), v in cross.most_common(12):
        print(f"  {ct+' x '+mt:26} {v:4}")
    c.close()

if __name__ == '__main__':
    main()
