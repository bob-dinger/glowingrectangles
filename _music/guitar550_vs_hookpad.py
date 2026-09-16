"""Match Guitar 50–550 song list against Hookpad library; report what's missing.

Inputs:
    ~/Desktop/guitar{50,100,...,550}_ug_urls.txt   (TSV: title, artist, kind, url)
    ~/Desktop/hookpad_song_names.csv               (from dump_hookpad_names.py)

Output:
    ~/Desktop/guitar550_vs_hookpad.csv  (per-song: list, artist, title, status, hp_match)
"""
import csv, os, re, glob, sys
from collections import defaultdict


def norm(s):
    """Lowercase, strip apostrophes, replace dashes/punctuation with spaces, collapse whitespace."""
    s = (s or '').lower()
    s = re.sub(r"['']", '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


_ARTIST_ALIASES = {
    'creedence clearwater revival': 'ccr',
    'red hot chili peppers': 'rhcp',
    'lynyrd skynyrd': 'lynryd skynyrd',   # match typo in user's Hookpad
    'the band': 'band',
    'guns n roses': 'gnr',
}

def norm_artist(s):
    """Lowercase, strip 'the', apply known aliases."""
    n = norm(s)
    if n.startswith('the '): n = n[4:]
    return _ARTIST_ALIASES.get(n, n)


def artist_token_overlap(a1, a2):
    """True if the two artist strings share any 3+ character word."""
    w1 = {w for w in a1.split() if len(w) >= 3}
    w2 = {w for w in a2.split() if len(w) >= 3}
    return bool(w1 & w2)


def main():
    # Load Hookpad names. Hookpad format is "artist_title" lowercase.
    hp_path = os.path.expanduser('~/Desktop/hookpad_song_names.csv')
    hp_rows = list(csv.DictReader(open(hp_path)))
    hp_index = []   # list of (norm_artist, norm_title, name, id) tuples
    hp_by_title = defaultdict(list)   # norm_title → [(norm_artist, name, id), ...]
    for r in hp_rows:
        name = r['name'] or ''
        nid = r['id']
        parts = name.split('_', 1)
        if len(parts) == 2:
            art, tit = parts
        else:
            art, tit = '', name
        na = norm_artist(art); nt = norm(tit)
        hp_index.append((na, nt, name, nid))
        hp_by_title[nt].append((na, name, nid))

    # Load guitar lists
    rows = []
    for path in sorted(glob.glob(os.path.expanduser('~/Desktop/guitar*_ug_urls.txt'))):
        list_name = re.search(r'guitar(\d+)', os.path.basename(path)).group(1)
        seen_in_list = set()   # dedupe within each list (multiple URLs per song)
        for r in csv.DictReader(open(path), delimiter='\t'):
            title = r.get('title') or ''
            artist = r.get('artist') or ''
            key = (norm_artist(artist), norm(title))
            if key in seen_in_list: continue
            seen_in_list.add(key)
            rows.append({'list': int(list_name), 'title': title, 'artist': artist})

    print(f'{len(rows)} unique songs across guitar lists')

    # Match each guitar song against Hookpad
    n_exact = n_fuzzy = n_miss = 0
    out_rows = []
    for r in rows:
        nart = norm_artist(r['artist']); ntit = norm(r['title'])
        status = 'missing'
        match_name = ''

        # 1. Exact normalized match on title; then verify artist overlap or contains
        for hp_art, name, nid in hp_by_title.get(ntit, []):
            if nart == hp_art or nart in hp_art or hp_art in nart or artist_token_overlap(nart, hp_art):
                status = 'exact'; match_name = name; break

        # 2. Title-near match: same words (any order) + artist overlap
        if status == 'missing':
            tw = set(w for w in ntit.split() if len(w) >= 3)
            if tw:
                for hp_art, hp_tit, name, nid in hp_index:
                    hw = set(w for w in hp_tit.split() if len(w) >= 3)
                    if not hw: continue
                    # Title-word overlap = at least 70% of our words present in hp title
                    overlap = tw & hw
                    if len(overlap) >= max(1, int(0.7 * len(tw))):
                        if artist_token_overlap(nart, hp_art) or nart == hp_art:
                            status = 'fuzzy'; match_name = name; break

        # 3. Compressed title match (handles "12:51" vs "1251" and minor typos)
        if status == 'missing':
            tit_compressed = ntit.replace(' ', '')
            for hp_art, hp_tit, name, nid in hp_index:
                hp_compressed = hp_tit.replace(' ', '')
                match = (tit_compressed == hp_compressed or
                         (len(tit_compressed) >= 5 and abs(len(tit_compressed) - len(hp_compressed)) <= 1 and
                          (tit_compressed in hp_compressed or hp_compressed in tit_compressed)))
                if match and (artist_token_overlap(nart, hp_art) or nart == hp_art):
                    status = 'fuzzy'; match_name = name; break

        # 4. Title-only match (different artist attribution — surface for user's review)
        if status == 'missing':
            for hp_art, name, nid in hp_by_title.get(ntit, []):
                status = 'diff_artist'; match_name = name; break

        if status == 'exact': n_exact += 1
        elif status == 'fuzzy': n_fuzzy += 1
        elif status == 'diff_artist': pass
        else: n_miss += 1

        out_rows.append({**r, 'status': status, 'hp_match': match_name})

    out_path = os.path.expanduser('~/Desktop/guitar550_vs_hookpad.csv')
    with open(out_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['list','artist','title','status','hp_match'])
        w.writeheader()
        for r in out_rows: w.writerow(r)

    n_diff = sum(1 for r in out_rows if r['status'] == 'diff_artist')
    print(f'\n=== overall ===')
    print(f'  exact match:        {n_exact}')
    print(f'  fuzzy match:        {n_fuzzy}')
    print(f'  diff-artist match:  {n_diff}')
    print(f'  missing:            {n_miss}')

    # By list
    print(f'\n=== per list ===')
    print(f'{"list":>5}  {"total":>5}  {"in_hp":>5}  {"missing":>7}')
    for ln in sorted(set(r['list'] for r in out_rows)):
        ls = [r for r in out_rows if r['list'] == ln]
        in_hp = sum(1 for r in ls if r['status'] in ('exact','fuzzy','diff_artist'))
        miss = len(ls) - in_hp
        print(f'  {ln:>3}  {len(ls):>5}  {in_hp:>5}  {miss:>7}')

    # First 20 missing for spot-check
    print(f'\nfirst 20 missing songs (so you can sanity-check):')
    for r in [r for r in out_rows if r['status'] == 'missing'][:20]:
        print(f'  list {r["list"]:>3}: {r["artist"]} — {r["title"]}')

    print(f'\nfull spreadsheet → {out_path}')


if __name__ == '__main__': main()
