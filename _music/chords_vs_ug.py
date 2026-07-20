"""Compare the chord SET your Hookpad file claims against the chord set the UG tab claims.

Both get reduced to absolute pitch classes (UG transposed by its capo, Hookpad resolved
through its key) so they're comparable. Sequence alignment is hopeless across two formats
that don't share a time axis — but set difference already tells you where they argue.
"""
import os, re, glob, argparse
from collections import Counter, defaultdict
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label

UGDIR = os.path.expanduser('~/Desktop/music/ug_tabs')
PC = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
IDX = {n: i for i, n in enumerate(PC)}
for a, b in [('C#', 1), ('D#', 3), ('F#', 6), ('G#', 8), ('A#', 10), ('Cb', 11), ('B#', 0), ('E#', 5), ('Fb', 4)]:
    IDX[a] = b
NUM = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7}
MAJ = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def roman_pc(tok):
    """roman numeral -> (semitones above tonic, quality). Handles applied chords (V/V)."""
    if '/' in tok and '°' not in tok:
        l, r = tok.split('/', 1)
        lp, rp = roman_pc(l), roman_pc(r)
        if lp and rp: return ((lp[0] + rp[0]) % 12, lp[1])
        return None
    m = re.match(r'^([b#]*)([ivxIVX]+)(°?)', tok)
    if not m: return None
    acc = sum(-1 if x == 'b' else 1 for x in m.group(1))
    deg = NUM.get(m.group(2).lower())
    if not deg: return None
    q = 'dim' if m.group(3) else ('maj' if m.group(2).isupper() else 'min')
    return ((MAJ[deg] + acc) % 12, q)

def hookpad_set(hj):
    """absolute pitch-class + quality for every chord, following key changes"""
    keys = sorted(hj.get('keys') or [{'beat': 1, 'tonic': 0, 'scale': 'major'}], key=lambda k: k.get('beat', 0))
    out = Counter()
    for ch in hj.get('chords') or []:
        if not ch.get('root') or not 1 <= ch['root'] <= 7: continue
        b = ch.get('beat', 0)
        k = keys[0]
        for kk in keys:
            if kk.get('beat', 0) <= b: k = kk
        sc = k.get('scale', 'major'); sc = sc if sc in ('major', 'minor') else 'major'
        t = k.get('tonic', 0)
        tpc = IDX.get(str(t), t if isinstance(t, int) else 0)
        rp = roman_pc(chord_label(ch, sc))
        if rp: out[((tpc + rp[0]) % 12, rp[1])] += 1
    return out

CH_RE = re.compile(r'^[A-G][#b]?(m|min|maj|dim|aug|sus|add|°)?\d*')
def ug_set(path):
    """chord tokens from a UG tab, transposed by the capo to sounding pitch"""
    txt = open(path, errors='ignore').read()
    mc = re.search(r'Capo:\s*(\d+)', txt)
    capo = int(mc.group(1)) if mc else 0
    out = Counter()
    for line in txt.split('\n'):
        s = line.strip()
        if not s or s.startswith(('#', '[', 'Tuning', 'Key:', 'Capo')): continue
        toks = s.split()
        # a chord line is mostly chord tokens and short
        good = [t for t in toks if CH_RE.match(t)]
        if not toks or len(good) / len(toks) < 0.8 or len(s) > 78: continue
        for t in good:
            m = re.match(r'^([A-G][#b]?)(.*)$', t)
            if not m: continue
            pc = (IDX.get(m.group(1), 0) + capo) % 12
            rest = m.group(2)
            q = 'dim' if 'dim' in rest or '°' in rest else ('min' if re.match(r'^(m|min)(?!aj)', rest) else 'maj')
            out[(pc, q)] += 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title'); ap.add_argument('--min', type=int, default=2)
    a = ap.parse_args()
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select title,hookpad_json from parcels.songs where has_chords and hookpad_json is not null "
                "and lower(artist) like %s", ('%beatle%',))
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -len((r[1] or {}).get('chords') or []))
    ug = {}
    for f in glob.glob(os.path.join(UGDIR, 'beatles_*.txt')):
        ug.setdefault(norm(os.path.basename(f)[len('beatles_'):-4]), f)
    seen = set(); results = []
    for t, hj in rows:
        t = (t or '').strip()
        if not t: continue
        k = norm(t)
        if k in seen or k not in ug: continue
        seen.add(k)
        if a.title and a.title.lower() not in t.lower(): continue
        H, U = hookpad_set(hj), ug_set(ug[k])
        if not H or not U: continue
        hs = {p for p, n in H.items() if n >= a.min}
        us = {p for p, n in U.items() if n >= a.min}
        if not hs or not us: continue
        results.append((t, hs, us))
    def name(p): return PC[p[0]] + ('m' if p[1] == 'min' else '°' if p[1] == 'dim' else '')
    agree = tot = 0
    diffs = []
    for t, hs, us in results:
        both = hs & us
        agree += len(both); tot += len(hs | us)
        diffs.append((len(both) / len(hs | us), t, sorted(hs - us, key=lambda p: p[0]),
                      sorted(us - hs, key=lambda p: p[0]), sorted(both, key=lambda p: p[0])))
    print(f'{len(results)} songs with both a Hookpad file and a UG tab')
    print(f'chord-set agreement overall: {agree}/{tot} = {agree/tot*100:.0f}%\n')
    print('most disagreement first:\n')
    for r, t, honly, uonly, both in sorted(diffs)[:26]:
        print(f'  {t[:30]:32} {r*100:>3.0f}% agree   shared: {" ".join(name(p) for p in both)}')
        if honly: print(f'       only Hookpad: {" ".join(name(p) for p in honly)}')
        if uonly: print(f'       only UG:      {" ".join(name(p) for p in uonly)}')

if __name__ == '__main__':
    main()
