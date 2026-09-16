"""Dump all Hookpad song names to a CSV for review/dedup.

Usage: python dump_hookpad_names.py <bearer_token>
Output: ~/Desktop/hookpad_song_names.csv
"""
import sys, os, csv, time, requests

API = 'https://api.hooktheory.com/v1'
OUT = os.path.expanduser('~/Desktop/hookpad_song_names.csv')


def list_all(token):
    headers = {
        'authorization': f'Bearer {token}',
        'origin': 'https://hookpad.hooktheory.com',
        'referer': 'https://hookpad.hooktheory.com/',
    }
    out = []
    page = 1
    while True:
        r = requests.get(f'{API}/songs/h?per-page=100&page={page}', headers=headers, timeout=30)
        if r.status_code == 401:
            print('  ✗ 401 unauthorized — token expired or wrong'); sys.exit(2)
        r.raise_for_status()
        data = r.json()
        if not data: break
        out.extend(data)
        print(f'  page {page}: +{len(data)} songs (total {len(out)})')
        if len(data) < 100: break
        page += 1
        time.sleep(3.0)
    return out


def main():
    if len(sys.argv) < 2: print('usage: dump_hookpad_names.py <bearer_token>'); sys.exit(1)
    songs = list_all(sys.argv[1])
    print(f'\nfetched {len(songs)} songs')

    # Sort by name (case-insensitive) so dupes group together
    songs.sort(key=lambda s: (s.get('song') or '').lower())

    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['name', 'id', 'date_modified'])
        for s in songs:
            w.writerow([s.get('song', ''), s.get('ID', ''), s.get('dateModified', '')])

    # Quick dup stats
    from collections import Counter
    names = Counter((s.get('song') or '').strip().lower() for s in songs)
    dups = {n: c for n, c in names.items() if c > 1}
    print(f'\n{len(dups)} duplicate names ({sum(dups.values())} rows in dupe groups)')
    print(f'top 10 most-duplicated:')
    for n, c in sorted(dups.items(), key=lambda x: -x[1])[:10]:
        print(f'  {c:>3}× {n}')
    print(f'\nspreadsheet → {OUT}')


if __name__ == '__main__': main()
