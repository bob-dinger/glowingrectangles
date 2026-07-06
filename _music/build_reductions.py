"""Build the SIMPLIFIED LIBRARY: reduce every vocal section in parcels.songs to its
harmonic main-note line (auto-detected knobs), tag contour x motif, and store into
parcels.melodies.reduction (jsonb). Then the library is queryable by essence:
which songs share the 5-6-2-6 wobble, the 3-2-1 descent, etc. See REDUCER.md.
"""
import os, json, collections
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2
import skeleton as sk
from find_structures import detect_grid, detect_pick, contour, motif, pitch, VOCAL, SKIP

ROM = {1: 'I', 2: 'ii', 3: 'iii', 4: 'IV', 5: 'V', 6: 'vi', 7: 'vii'}
def roman(c):
    r = c['root']; s = ROM.get(r, str(r)); b = str(c.get('borrowed') or '')
    if b == 'minor' and r in (3, 6, 7): s = 'b' + s.upper()
    if c.get('type') in (7, '7'): s += '7'
    if c.get('applied'): s += '/' + ROM.get(c['applied'], str(c['applied']))
    return s

def prog(sc):
    out, prev = [], None
    for c in sorted(sc, key=lambda c: c['beat']):
        t = roman(c)
        if t != prev: out.append(t)
        prev = t
    return ' '.join(out)

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("alter table parcels.melodies add column if not exists reduction jsonb")
    c.commit()
    cur.execute("select slug, hookpad_json from parcels.songs where has_chords and has_melody and hookpad_json is not null")
    rows = cur.fetchall()
    n = 0; con = collections.Counter()
    for slug, hj in rows:
        notes = [x for x in (hj.get('notes') or []) if not x.get('isRest')]
        chords = hj.get('chords') or []; secs = hj.get('sections') or []
        nb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        if not (notes and chords and secs): continue
        endb = hj.get('endBeat') or max(x['beat'] for x in notes) + nb
        done = set()
        for i, s in enumerate(secs):
            name = (s.get('name') or '').lower()
            if not any(v in name for v in VOCAL) or any(k in name for k in SKIP): continue
            sec = name.split()[0]
            if sec in done: continue
            b0 = s['beat']; b1 = secs[i+1]['beat'] if i+1 < len(secs) else endb
            sn = [x for x in notes if b0 <= x['beat'] < b1]
            scc = [x for x in chords if b0 <= x['beat'] < b1]
            if len(sn) < 4 or len(scc) < 3: continue
            done.add(sec)
            grid = detect_grid(sn, scc, nb, b1 - b0); pk = detect_pick(sn, scc, nb)
            m = sk.simplify_harmonic(sn, scc, merge=True, measure=grid, pick=pk)
            if len(m) < 3: continue
            seq = [pitch(x) for x in m]; degs = [str(x['sd']) for x in m]
            ct = contour(seq)
            if not ct: continue
            red = {"main": '-'.join(degs), "prog": prog(scc), "contour": ct, "motif": motif(degs),
                   "grid": "measure" if grid else "chord", "pick": pk, "bars": round((b1 - b0) / nb),
                   "palette": sorted(set(degs), key=lambda d: int(''.join(ch for ch in d if ch.isdigit()) or 0))}
            cur.execute("""insert into parcels.melodies (slug, section, reduction, updated_at)
                values (%s,%s,%s::jsonb, now())
                on conflict (slug, section) do update set reduction = excluded.reduction, updated_at = now()""",
                (slug, sec, json.dumps(red)))
            n += 1; con[ct] += 1
        if n % 300 == 0 and n:
            c.commit()
    c.commit()
    print(f"stored {n} section reductions into parcels.melodies.reduction")
    print("contour spread:", dict(con.most_common()))
    c.close()

if __name__ == '__main__':
    main()
