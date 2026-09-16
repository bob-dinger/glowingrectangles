"""List Hookpad songs that are NOT in any Guitar 50-600 list (excluding Beatles).

Inverse of guitar550_vs_hookpad.py.

Inputs:
    ~/Desktop/5-24-26/guitar{50..550}_ug_urls.txt   (TSV: title, artist, kind, url)
    ~/Desktop/5-24-26/Guitar600_keys_tempos.txt     (TSV: title, artist, key, extra, bpm, nearest)
    ~/Desktop/dates/5-29-26/hookpad_song_names.csv  (name="artist_title", id, date_modified)

Output:
    ~/Desktop/hookpad_not_in_guitar.csv
"""
import csv, os, re, glob
from collections import defaultdict

GUITAR_DIR = os.path.expanduser('~/Desktop/5-24-26')
G600 = os.path.expanduser('~/Desktop/5-24-26/Guitar600_keys_tempos.txt')
HP = os.path.expanduser('~/Desktop/hookpad_song_names.csv')
OUT = os.path.expanduser('~/Desktop/hookpad_not_in_guitar.csv')


def norm(s):
    s = (s or '').lower()
    s = re.sub(r"['']", '', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


_ARTIST_ALIASES = {
    'creedence clearwater revival': 'ccr',
    'red hot chili peppers': 'rhcp',
    'lynyrd skynyrd': 'lynryd skynyrd',
    'the band': 'band',
    'guns n roses': 'gnr',
}

def norm_artist(s):
    n = norm(s)
    if n.startswith('the '): n = n[4:]
    return _ARTIST_ALIASES.get(n, n)


def artist_overlap(a1, a2):
    if not a1 or not a2: return False
    if a1 == a2 or a1 in a2 or a2 in a1: return True
    w1 = {w for w in a1.split() if len(w) >= 3}
    w2 = {w for w in a2.split() if len(w) >= 3}
    return bool(w1 & w2)


def load_guitar():
    """Return guitar index: norm_title -> list of (norm_artist, label)."""
    by_title = defaultdict(list)
    total = set()
    # url lists
    for path in glob.glob(os.path.join(GUITAR_DIR, 'guitar*_ug_urls.txt')):
        for r in csv.DictReader(open(path), delimiter='\t'):
            t, a = norm(r.get('title')), norm_artist(r.get('artist'))
            if t:
                by_title[t].append((a, f'{r.get("artist")} - {r.get("title")}'))
                total.add((a, t))
    # Guitar600
    if os.path.exists(G600):
        for r in csv.DictReader(open(G600), delimiter='\t'):
            t, a = norm(r.get('title')), norm_artist(r.get('artist'))
            if t:
                by_title[t].append((a, f'{r.get("artist")} - {r.get("title")}'))
                total.add((a, t))
    return by_title, total


def in_guitar(nart, ntit, by_title):
    # exact title + artist overlap
    for a, _ in by_title.get(ntit, []):
        if artist_overlap(nart, a): return True
    # compressed title match (handles "12:51" vs "1251") + artist overlap
    tc = ntit.replace(' ', '')
    if len(tc) >= 5:
        for gt, lst in by_title.items():
            gc = gt.replace(' ', '')
            if tc == gc or (abs(len(tc) - len(gc)) <= 1 and (tc in gc or gc in tc)):
                for a, _ in lst:
                    if artist_overlap(nart, a): return True
    # word-overlap title (70%) + artist overlap
    tw = {w for w in ntit.split() if len(w) >= 3}
    if tw:
        need = max(1, int(0.7 * len(tw)))
        for gt, lst in by_title.items():
            gw = {w for w in gt.split() if len(w) >= 3}
            if gw and len(tw & gw) >= need:
                for a, _ in lst:
                    if artist_overlap(nart, a): return True
    return False


def main():
    by_title, total = load_guitar()
    print(f'{len(total)} unique songs across guitar lists (50-600)')

    # Load + dedupe hookpad, excluding beatles
    seen = set()
    hp = []
    n_beatles = 0
    for r in csv.DictReader(open(HP)):
        name = (r.get('name') or '').strip()
        if not name: continue
        parts = name.split('_', 1)
        art, tit = (parts[0], parts[1]) if len(parts) == 2 else ('', name)
        na, nt = norm_artist(art), norm(tit)
        if 'beatles' in na or 'beatles' in norm(name):
            n_beatles += 1; continue
        key = (na, nt)
        if key in seen: continue
        seen.add(key)
        hp.append({'artist': art, 'title': tit, 'na': na, 'nt': nt, 'name': name})

    print(f'{len(hp)} unique non-Beatles Hookpad songs ({n_beatles} Beatles rows skipped)')

    missing = [s for s in hp if not in_guitar(s['na'], s['nt'], by_title)]
    print(f'\n{len(missing)} Hookpad songs NOT in any guitar list:\n')

    missing.sort(key=lambda s: (s['na'], s['nt']))
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['artist', 'title', 'hookpad_name'])
        for s in missing:
            w.writerow([s['artist'], s['title'], s['name']])
            print(f'  {s["artist"]} — {s["title"]}')

    print(f'\nfull list ({len(missing)} songs) -> {OUT}')


if __name__ == '__main__': main()
