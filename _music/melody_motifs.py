"""Find recurring melodic motifs.

Two layers:
 1. Within-section n-gram recurrence — find sub-sequences of 3-8 notes
    that repeat 2+ times inside one section.
 2. Within-song & cross-song matching — same engine, different scopes.

Three match abstractions (pick whichever lens fits the question):
 - sd:        scale-degree only (octave-invariant) — most permissive, catches the "shape"
 - sd_oct:    (sd, octave) tuples — preserves register
 - interval:  semitone deltas — transposition-invariant (useful if a motif moves
              within the song to a different scale-degree starting point)

Sub-sequence rule: longer motifs subsume shorter ones if every occurrence of the
shorter is contained in an occurrence of the longer. We keep only "maximal" motifs
so a 6-note hook doesn't get reported as itself + every 3/4/5-note prefix.

Usage:
    from extract_melodies import extract_song_melodies
    from melody_motifs import find_motifs
    for sec in extract_song_melodies(hookpad_json):
        motifs = find_motifs(sec['sd_seq'], min_len=3, max_len=8, min_count=2)
        for m in motifs:
            print(m)
"""
from collections import defaultdict


def _ngram_positions(seq, n):
    """Return {tuple(ngram): [start_indices...]} for all length-n windows."""
    out = defaultdict(list)
    for i in range(len(seq) - n + 1):
        out[tuple(seq[i:i + n])].append(i)
    return out


def find_motifs(seq, min_len=3, max_len=64, min_count=2):
    """Find maximal recurring n-grams in `seq`.

    A motif `m` is reported iff:
      - len(min_len) <= len(m) <= max_len
      - m occurs at >=min_count distinct (non-overlapping) positions
      - no longer motif `m'` exists such that every occurrence of m is the
        prefix (at the same offset) of an occurrence of m'

    Returns a list of dicts: {'motif': tuple, 'count': int, 'positions': [int]}
    sorted by length desc, then count desc.
    """
    seq = list(seq)
    if len(seq) < min_len:
        return []

    # 1. Collect all ngrams length min_len..max_len with their positions.
    # Distinct starting positions all count — adjacent repeats may share boundary notes
    # (a common pop pattern: closing tonic of one phrase = opening tonic of the next).
    all_ngrams = {}  # (length, tuple) -> [positions]
    for n in range(min_len, min(max_len, len(seq)) + 1):
        for ngram, positions in _ngram_positions(seq, n).items():
            if len(positions) >= min_count:
                all_ngrams[(n, ngram)] = positions

    # 2. Drop motifs subsumed by a longer motif
    #    A length-n motif m at positions P is subsumed if there's a length-(n+k)
    #    motif m' (k>=1) at positions P' such that for every p in P there's
    #    some p' in P' with p in [p'-n', p']... For simplicity: subsumed if there
    #    exists a longer motif whose positions are a superset (offset-shifted).
    #    Practical heuristic: drop if a longer motif starts at the same positions
    #    OR at positions exactly k earlier (so this motif is a suffix), with
    #    same count.
    keep = []
    by_pos_set = {(n, ngram): frozenset(pos) for (n, ngram), pos in all_ngrams.items()}
    for (n, ngram), pos in all_ngrams.items():
        pos_set = frozenset(pos)
        subsumed = False
        for (n2, ngram2), pos2 in all_ngrams.items():
            if n2 <= n: continue
            pos2_set = frozenset(pos2)
            # offsets at which `ngram` would appear inside `ngram2`
            inside_offsets = [k for k in range(n2 - n + 1) if ngram2[k:k + n] == ngram]
            for k in inside_offsets:
                shifted = frozenset(p + k for p in pos2)
                if pos_set.issubset(shifted):
                    subsumed = True
                    break
            if subsumed: break
        if not subsumed:
            keep.append({'motif': ngram, 'count': len(pos), 'positions': pos})

    keep.sort(key=lambda m: (-len(m['motif']), -m['count']))
    return keep


def fmt_motif(m, sep=' '):
    """Pretty-print a motif tuple. Handles both `sd` strings and (sd, octave) tuples."""
    pieces = []
    for x in m['motif']:
        if isinstance(x, tuple):
            sd, oct_ = x
            mark = '^' * max(0, oct_) + 'v' * max(0, -oct_)
            pieces.append(f"{mark}{sd}")
        elif isinstance(x, int):
            pieces.append(f"{x:+d}")  # interval
        else:
            pieces.append(str(x))
    return sep.join(pieces)


def main():
    """CLI: python melody_motifs.py <title-substring> [--artist X] [--mode sd|sd_oct|interval]"""
    import argparse, sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_melodies import extract_song_melodies
    from dotenv import load_dotenv
    load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
    from supabase import create_client

    ap = argparse.ArgumentParser()
    ap.add_argument('title')
    ap.add_argument('--artist', default=None)
    ap.add_argument('--mode', default='sd', choices=['sd', 'sd_oct', 'interval'])
    ap.add_argument('--min-len', type=int, default=3)
    ap.add_argument('--max-len', type=int, default=64)
    ap.add_argument('--skip-trivial', action='store_true',
                    help='hide motifs that are a single repeated note (e.g. 4 4 4 4)')
    ap.add_argument('--min-count', type=int, default=2)
    args = ap.parse_args()

    SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    q = SB.schema('parcels').table('songs').select(
        'artist,title,key_tonic,key_scale,hookpad_json'
    ).ilike('title', f'%{args.title}%')
    if args.artist:
        q = q.ilike('artist', f'%{args.artist}%')
    rows = q.limit(5).execute().data
    if not rows:
        sys.exit(f"no song matches {args.title!r}")
    s = rows[0]
    print(f"=== {s['artist']} - {s['title']}  ({s['key_tonic']} {s['key_scale']}) — motif mode: {args.mode} ===\n")

    seen_sections = set()
    for sec in extract_song_melodies(s['hookpad_json']):
        if sec['n_notes'] < args.min_len + 1: continue
        key = (sec['name'].lower(), tuple(sec['sd_seq']))
        if key in seen_sections: continue  # dedupe identical repeats
        seen_sections.add(key)

        if args.mode == 'sd':
            seq = sec['sd_seq']
        elif args.mode == 'sd_oct':
            seq = sec['sd_oct_seq']
        else:  # interval
            seq = sec['interval_seq']

        motifs = find_motifs(seq, args.min_len, args.max_len, args.min_count)
        if args.skip_trivial:
            motifs = [m for m in motifs if len(set(m['motif'])) > 1]
        if not motifs: continue
        print(f"[{sec['name']}]  {sec['n_notes']} notes")
        for m in motifs[:8]:
            print(f"  ×{m['count']:>2}  ({len(m['motif'])} notes)  {fmt_motif(m)}   at beats {m['positions']}")
        print()


if __name__ == '__main__':
    main()
