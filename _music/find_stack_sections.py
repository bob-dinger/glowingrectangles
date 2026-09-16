"""Scan parcels.songs for sections shaped like the "stack" form (see memory
music_stack_form): statement/answer units S A S A S S A -- two call-response
pairs, a DOUBLED statement, then the answer -- with held-note landings and an
early cadence. Heuristic DRAFT; machine proposes, human curates.

Per section, at grain g in {1,2} bars/unit:
  - unit = S (busy, statement) / A (contains a held note >=3 beats, a landing) /
    . (empty, ring-out).
  - score the S/A string against the stack target S A S A S S A, reward the
    signature SS-doubling, reward held-note landings and an early final cadence.
"""
import os, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2

TARGET = "SASASSA"

def unit_label(notes, u0, span, nb):
    ns = [n for n in notes if u0 - 0.05 <= n['beat'] < u0 + span - 0.05 and not n.get('isRest')]
    if not ns:
        return '.', None
    longest = max(ns, key=lambda n: n['duration'])
    if longest['duration'] >= 3:                       # a held landing note
        return 'A', longest
    return 'S', None

def score_seq(seq):
    """seq like 'SASASSA.' -> (score, has_SS, matched_len)."""
    core = seq.rstrip('.')
    if len(core) < 6:
        return 0, False, core
    m = sum(1 for a, b in zip(core, TARGET) if a == b)          # positional match to SASASSA
    has_ss = 'SS' in core[:7] and core[:2] == 'SA'              # the doubled-statement signature
    alt = sum(1 for i in range(min(4, len(core)-1)) if core[i] != core[i+1])  # early SASA alternation
    s = m + (3 if has_ss else 0) + alt
    return s, has_ss, core

def analyze(notes, chords, sec_beat, sec_end, nb):
    notes = [n for n in notes if sec_beat <= n['beat'] < sec_end]
    if not notes:
        return None
    bars = (sec_end - sec_beat) / nb
    best = None
    for g in (1, 2):
        span = g * nb
        nunits = int(round((sec_end - sec_beat) / span))
        if not (6 <= nunits <= 9):
            continue
        seq = ''
        landings = []
        for u in range(nunits):
            u0 = sec_beat + u * span
            lab, held = unit_label(notes, u0, span, nb)
            seq += lab
            if lab == 'A' and held:
                landings.append((u, held))
        sc, has_ss, core = score_seq(seq)
        # early cadence bonus: last landing onsets before its unit's last downbeat
        early = False
        if landings:
            u, held = landings[-1]
            u0 = sec_beat + u * span
            early = held['beat'] > u0 + 0.5 and held['beat'] < sec_end - nb + 0.5
        sc += 2 if early else 0
        skel = [h['sd'] for _, h in landings]
        # classify: hovering (all landings same pitch) = "double" sibling, not a true stack
        hovering = len(set(skel)) <= 1 and len(skel) >= 2
        if best is None or sc > best['score']:
            best = {'grain': g, 'seq': seq, 'score': sc, 'has_ss': has_ss,
                    'skel': skel, 'nland': len(landings), 'hovering': hovering,
                    'early': early, 'bars': round(bars)}
    return best

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select slug, section from parcels.melodies where phrases->>'form' ilike '%stack%' or phrases->>'form' ilike '%ender%'")
    logged = {(s, (sec or '').lower()) for s, sec in cur.fetchall()}
    cur.execute("select slug, title, artist, hookpad_json from parcels.songs where hookpad_json is not null")
    rows = cur.fetchall()
    out = []
    seen = set()
    for slug, title, artist, hj in rows:
        notes = hj.get('notes') or []
        chords = hj.get('chords') or []
        secs = hj.get('sections') or []
        meters = hj.get('meters') or [{}]
        nb = meters[0].get('numBeats', 4)
        endb = hj.get('endBeat') or (max((n['beat'] for n in notes), default=0) + nb)
        if not secs:
            secs = [{'beat': 1, 'name': 'song'}]
        for i, s in enumerate(secs):
            b0 = s['beat']
            b1 = secs[i+1]['beat'] if i+1 < len(secs) else endb
            name = s.get('name', '?')
            if name.lower() in ('section', 'intro', 'outro', 'solo') or b1 - b0 < nb * 6:
                continue
            key = (artist or '', title or '', name.lower())
            if key in seen:
                continue
            if (slug, name.lower()) in logged:
                continue
            r = analyze(notes, chords, b0, b1, nb)
            # tightened: SS-doubling, >=3 landings (kills chants), not hovering (kills doubles)
            if r and r['score'] >= 9 and r['has_ss'] and r['nland'] >= 3 and not r['hovering']:
                seen.add(key)
                out.append((r['score'], slug, name, r))
    out.sort(reverse=True, key=lambda x: x[0])
    print(f"scanned {len(rows)} songs -> {len(out)} NEW stack candidates (SS + >=3 landings + non-hovering)\n")
    print(f"{'score':>5}  {'slug':42} {'section':10} {'grain':5} {'seq':10} {'early':5} skeleton")
    for sc, slug, name, r in out[:35]:
        print(f"{sc:>5}  {slug[:42]:42} {name[:10]:10} {r['grain']}bar  {r['seq']:10} {'yes' if r['early'] else '  -':5} {'-'.join(r['skel'])}")
    c.close()

if __name__ == '__main__':
    main()
