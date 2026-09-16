"""Validate parse_ug.py output against existing Hookpad data in Supabase.

For each tab in ~/Desktop/music/ug_tabs/{basename}.txt:
  1. Parse it
  2. Look up matching slug in Supabase (basename → make_slug)
  3. If found, compare parser output to DB ground truth
  4. Score: # sections match, chord-progression overlap, bar-count diff
  5. Dump per-song + aggregate report

Usage:
    python validate_ug.py
    python validate_ug.py <basename>     # single song
"""
import os, sys, json, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

from parse_ug import parse_file, UG_DIR
from update_song_json import make_slug

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])


def chord_token(c):
    """Compact roman-ish token for comparison: deg + acc + quality + 7?"""
    deg = c.get('root', '?')
    bw = c.get('borrowed') or ''
    typ = c.get('type', 5)
    return f'{deg}{bw[0] if bw else ""}{"7" if typ == 7 else ""}'


def chord_progression(d, sec_start, sec_end):
    return [chord_token(c) for c in d.get('chords', []) if sec_start <= c.get('beat',0) < sec_end and not c.get('isRest')]


def score_song(basename):
    """Compare parser output to DB ground truth. Returns dict of metrics."""
    parsed = parse_file(basename, paste=False)
    if not parsed: return None
    slug_candidates = [make_slug(basename + '.json')]   # also try a few suffix variants
    base = slug_candidates[0]
    for suf in ['', '_o', '_ly', '_c', '_o_ly', '_o_c_ly']:
        slug_candidates.append(base + suf)

    # Find slug that exists
    db_row = None
    for s in slug_candidates:
        r = sb.schema('parcels').table('songs').select('slug,hookpad_json').eq('slug', s).execute()
        if r.data: db_row = r.data[0]; break
    if not db_row: return {'basename': basename, 'status': 'no_db_match', 'parsed_sections': len(parsed['sections'])}

    db = db_row['hookpad_json'] or {}
    db_secs = db.get('sections') or []
    db_end = db.get('endBeat', 0)
    db_bpb = (db.get('meters') or [{'numBeats':4}])[0].get('numBeats',4)
    p_secs = parsed['sections']
    p_end  = parsed['endBeat']
    p_bpb  = (parsed.get('meters') or [{'numBeats':4}])[0].get('numBeats',4)

    # Section-name match (order-independent set)
    db_names  = [s.get('name','').strip().lower() for s in db_secs]
    p_names   = [s.get('name','').strip().lower() for s in p_secs]
    name_overlap = len(set(db_names) & set(p_names))
    name_union   = len(set(db_names) | set(p_names))

    # Bar count diff
    bar_diff = abs((db_end // db_bpb) - (p_end // p_bpb))

    # First-verse chord progression overlap
    def first_section(secs, end_b, bpb, name_filter):
        for i, s in enumerate(secs):
            if name_filter(s.get('name','').lower()):
                nxt = secs[i+1]['beat'] if i+1 < len(secs) else end_b
                return s['beat'], nxt
        return None

    overlap_score = None
    db_v = first_section(db_secs, db_end, db_bpb, lambda n: 'verse' in n)
    p_v  = first_section(p_secs,  p_end,  p_bpb,  lambda n: 'verse' in n)
    if db_v and p_v:
        db_prog = chord_progression(db, *db_v)
        p_prog  = chord_progression(parsed, *p_v)
        # Compute longest common subsequence ratio
        common = sum(1 for a, b in zip(db_prog, p_prog) if a == b)
        overlap_score = round(common / max(len(db_prog), len(p_prog)), 2) if db_prog and p_prog else None

    return {
        'basename': basename, 'slug': db_row['slug'],
        'p_sections': len(p_secs), 'db_sections': len(db_secs),
        'name_match': f'{name_overlap}/{name_union}',
        'bar_diff':   bar_diff,
        'p_bars':     p_end // p_bpb,
        'db_bars':    db_end // db_bpb,
        'p_chords':   len(parsed.get('chords') or []),
        'db_chords':  len(db.get('chords') or []),
        'verse_chord_overlap': overlap_score,
    }


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        r = score_song(sys.argv[1])
        print(json.dumps(r, indent=2))
        return
    results = []
    for f in sorted(os.listdir(UG_DIR)):
        if not f.endswith('.txt'): continue
        r = score_song(f[:-4])
        if r: results.append(r)
    # Aggregate
    matched = [r for r in results if 'verse_chord_overlap' in r and r.get('verse_chord_overlap') is not None]
    print(f'\n=== AGGREGATE  ({len(matched)} songs with DB match + verse) ===')
    if matched:
        avg_overlap = sum(r['verse_chord_overlap'] for r in matched) / len(matched)
        print(f'avg verse chord overlap: {avg_overlap:.2f}')
    print(f'\n=== PER-SONG ===')
    for r in results:
        print(json.dumps(r))


if __name__ == '__main__':
    main()
