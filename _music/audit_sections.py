"""Audit section boundaries. Three distinct defects, three different fixes:

  TRAIL   the last section runs to endBeat, swallowing the outro/silence
          (revolution's chorus reading 31 bars) -> move endBeat or add a marker
  CONFLICT  same section name, different bar counts within one song
          (You're Going to Lose That Girl: bridges 9, 7, 7) -> a marker sits late/early
  FRACTION  a section that isn't a whole number of measures
          -> marker off the barline, or a genuine half-bar (check before touching)

Only CONFLICT and FRACTION are reliably errors; TRAIL is often just how the file ends.
"""
import os, re, argparse
from collections import defaultdict
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

SKIP = re.compile(r'^\s*$|^section$|^pickup$', re.I)
VARIANT = re.compile(r'[-_](simple|hooktab|right|wrong|double|half|\d+|[A-G]b?|mixolydian|ly_o_COMPLETED)$', re.I)
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def sections(hj):
    npb = ((hj.get('meters') or [{}])[0].get('numBeats')) or 4
    secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
    end = hj.get('endBeat', 0) + 1
    out = []
    for i, s in enumerate(secs):
        b0 = s.get('beat', 0)
        b1 = secs[i+1]['beat'] if i+1 < len(secs) else end
        if b1 > b0: out.append((s.get('name', '').strip(), b0, b1, (b1-b0)/npb, i == len(secs)-1))
    return out, npb

def audit(rows):
    found = defaultdict(list)
    seen = set()
    for artist, title, hj in rows:
        t = (title or '').strip()
        if not t or VARIANT.search(t): continue
        k = norm(t)
        if k in seen: continue
        seen.add(k)
        secs, npb = sections(hj)
        body = [s for s in secs if not SKIP.match(s[0])]
        if not body: continue
        # TRAIL — final section wildly longer than the song's typical section
        med = sorted(m for _, _, _, m, _ in body)[len(body)//2]
        for nm, b0, b1, m, last in body:
            if last and m > max(med * 2.5, med + 8):
                found['TRAIL'].append((t, nm, m, f'median section {med:g} bars'))
        # FRACTION — not a whole number of measures
        for nm, b0, b1, m, last in body:
            if abs(m - round(m)) > .01 and not last:
                found['FRACTION'].append((t, nm, m, f'beat {b0}, {(b1-b0):g} beats @ {npb}/bar'))
        # CONFLICT — same name, different lengths
        g = defaultdict(list)
        for nm, b0, b1, m, last in body:
            if not last: g[norm(nm)].append((m, b0))
        for nm, lens in g.items():
            lastbeat = max(b for _, b in lens)   # last occurrence OF THIS SECTION NAME
            vals = sorted({m for m, _ in lens})
            if len(lens) > 1 and len(vals) > 1:
                counts = defaultdict(int)
                for m, _ in lens: counts[m] += 1
                majority = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
                for m, b in lens:
                    if m == majority: continue
                    ratio = m / majority if majority else 0
                    # an exact multiple = a marker that was never placed between repeats
                    if majority > 0 and abs(ratio - round(ratio)) < .04 and round(ratio) >= 2:
                        found['MERGED'].append((t, nm, m, f'{round(ratio)}x the usual {majority:g} — missing marker @beat{b}'))
                    elif m < majority and b >= lastbeat:
                        found['TRUNCATED'].append((t, nm, m, f'final one, usual is {majority:g} — probably a real short ending'))
                    else:
                        found['DRIFT'].append((t, nm, m, f'usual {majority:g}, off by {m-majority:+g} @beat{b}'))
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artist', default='beatle')
    ap.add_argument('--kind')
    a = ap.parse_args()
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select artist,title,hookpad_json from parcels.songs where has_chords "
                "and hookpad_json is not null and lower(artist) like %s", ('%' + a.artist.lower() + '%',))
    rows = cur.fetchall(); c.close()
    rows.sort(key=lambda r: -(len((r[2] or {}).get('notes') or []) + len((r[2] or {}).get('chords') or [])))
    found = audit(rows)
    order = [a.kind] if a.kind else ['MERGED', 'DRIFT', 'FRACTION', 'TRUNCATED', 'TRAIL']
    for kind in order:
        items = found[kind]
        print(f'\n=== {kind} — {len(items)} ===')
        for t, nm, val, note in sorted(items, key=lambda x: x[0].lower()):
            if kind in ('MERGED','DRIFT','TRUNCATED'):
                print(f'  {t[:30]:32} {nm[:12]:14} {val:g} bars — {note}')
            else:
                print(f'  {t[:30]:32} {nm[:12]:14} {val:g} bars   ({note})')
    print(f'\ntotal {sum(len(v) for v in found.values())} findings')

if __name__ == '__main__':
    main()
