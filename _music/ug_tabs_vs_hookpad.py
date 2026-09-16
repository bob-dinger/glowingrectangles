"""Cross-reference UG text-tab folder against Hookpad library; report what's missing.

Input:
    ~/Desktop/music/ug_tabs/*.txt    (filenames are 'artist_title.txt', kebab-case)
    ~/Desktop/hookpad_song_names.csv (from dump_hookpad_names.py)
Output:
    ~/Desktop/ug_tabs_vs_hookpad.csv

Excludes Beatles by default.
"""
import csv, os, re, glob, sys
from collections import defaultdict

# Reuse the matcher from guitar550_vs_hookpad
sys.path.insert(0, os.path.dirname(__file__))
from guitar550_vs_hookpad import norm, norm_artist, artist_token_overlap

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
HP_CSV = os.path.expanduser('~/Desktop/hookpad_song_names.csv')
OUT = os.path.expanduser('~/Desktop/ug_tabs_vs_hookpad.csv')


def main():
    # Load Hookpad index
    hp_rows = list(csv.DictReader(open(HP_CSV)))
    hp_index = []
    hp_by_title = defaultdict(list)
    for r in hp_rows:
        name = r['name'] or ''
        nid = r['id']
        parts = name.split('_', 1)
        if len(parts) == 2: art, tit = parts
        else: art, tit = '', name
        na = norm_artist(art); nt = norm(tit)
        hp_index.append((na, nt, name, nid))
        hp_by_title[nt].append((na, name, nid))

    # Load UG tab filenames
    rows = []
    for f in sorted(glob.glob(os.path.join(UG_DIR, '*.txt'))):
        bn = os.path.splitext(os.path.basename(f))[0]
        if '_' not in bn: continue   # weird filename, skip
        artist_kb, title_kb = bn.split('_', 1)
        if artist_kb.lower() == 'beatles': continue
        artist = artist_kb.replace('-', ' ')
        title = title_kb.replace('-', ' ')
        rows.append({'filename': bn + '.txt', 'artist': artist, 'title': title})

    print(f'{len(rows)} UG tab files (excluding Beatles)')

    n_exact = n_fuzzy = n_diff = n_miss = 0
    out_rows = []
    for r in rows:
        nart = norm_artist(r['artist']); ntit = norm(r['title'])
        status = 'missing'; match_name = ''

        # 1. Title exact + artist match
        for hp_art, name, nid in hp_by_title.get(ntit, []):
            if nart == hp_art or nart in hp_art or hp_art in nart or artist_token_overlap(nart, hp_art):
                status = 'exact'; match_name = name; break

        # 2. Title-word overlap + artist overlap (fuzzy)
        if status == 'missing':
            tw = set(w for w in ntit.split() if len(w) >= 3)
            if tw:
                for hp_art, hp_tit, name, nid in hp_index:
                    hw = set(w for w in hp_tit.split() if len(w) >= 3)
                    if not hw: continue
                    overlap = tw & hw
                    if len(overlap) >= max(1, int(0.7 * len(tw))):
                        if artist_token_overlap(nart, hp_art) or nart == hp_art:
                            status = 'fuzzy'; match_name = name; break

        # 3. Compressed title match (handles "12:51" vs "1251" + 1-char typos)
        if status == 'missing':
            tit_compressed = ntit.replace(' ', '')
            for hp_art, hp_tit, name, nid in hp_index:
                hp_compressed = hp_tit.replace(' ', '')
                match = (tit_compressed == hp_compressed or
                         (len(tit_compressed) >= 5 and abs(len(tit_compressed) - len(hp_compressed)) <= 1 and
                          (tit_compressed in hp_compressed or hp_compressed in tit_compressed)))
                if match and (artist_token_overlap(nart, hp_art) or nart == hp_art):
                    status = 'fuzzy'; match_name = name; break

        # 4. Title-only match → diff artist attribution
        if status == 'missing':
            for hp_art, name, nid in hp_by_title.get(ntit, []):
                status = 'diff_artist'; match_name = name; break

        out_rows.append({**r, 'status': status, 'hp_match': match_name})
        if status == 'exact': n_exact += 1
        elif status == 'fuzzy': n_fuzzy += 1
        elif status == 'diff_artist': n_diff += 1
        else: n_miss += 1

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['filename','artist','title','status','hp_match'])
        w.writeheader()
        for r in out_rows: w.writerow(r)

    print(f'\n=== overall ===')
    print(f'  exact match:        {n_exact}')
    print(f'  fuzzy match:        {n_fuzzy}')
    print(f'  diff-artist match:  {n_diff}')
    print(f'  truly missing:      {n_miss}')

    print(f'\nfirst 25 truly-missing UG tabs (not in Hookpad in any form):')
    for r in [r for r in out_rows if r['status'] == 'missing'][:25]:
        print(f'  {r["artist"]:30s} — {r["title"]}')
    print(f'\nspreadsheet → {OUT}')


if __name__ == '__main__': main()
