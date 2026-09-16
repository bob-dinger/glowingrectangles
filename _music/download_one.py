"""Download a single Hookpad song by slug, numeric ID, or (cached) name search.

Usage:
    download_one.py --token TOKEN --slug Abm_nv_zoak
    download_one.py --token TOKEN --id 746665
    download_one.py --token TOKEN --name "under the bridge"
    download_one.py --token TOKEN --refresh-list      # rebuild local song-list cache (15 calls, ~30s)

Output goes to ~/Desktop/music/hookpad_songs_full/<song>.json by default.
"""

import argparse
import json
import os
import sys
import time

import requests
from hashids import Hashids
import hookpad_token

API = 'https://api.hooktheory.com/v1'
HASHIDS = Hashids(
    salt='XI0Y4UFrK6EPLnarrI4y',
    min_length=11,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
)
LIST_CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
DEFAULT_OUT = '/Users/robert/Desktop/music/hookpad_songs_full'


def headers(token):
    return {
        'authorization': f'Bearer {token}',
        'origin': 'https://hookpad.hooktheory.com',
        'referer': 'https://hookpad.hooktheory.com/',
    }


def fetch_song_by_slug(token, slug):
    url = f'{API}/songs/{slug}?fields=ID,xmlData,song,jsonData,isPrivate'
    r = requests.get(url, headers=headers(token), timeout=30)
    if r.status_code == 429:
        sys.exit('429 rate-limited. Wait a bit and try again.')
    r.raise_for_status()
    return r.json()


def refresh_list(token):
    print('refreshing list (~15 pages, ~30s with throttle)...')
    out = []
    page = 1
    while True:
        r = requests.get(f'{API}/songs/h?per-page=100&page={page}', headers=headers(token), timeout=30)
        if r.status_code == 429:
            sys.exit('429 rate-limited mid-list. Wait, then re-run --refresh-list.')
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        out.extend(data)
        print(f'  page {page}: total {len(out)}')
        if len(data) < 100:
            break
        page += 1
        time.sleep(2.0)   # generous throttle to avoid 429
    os.makedirs(os.path.dirname(LIST_CACHE), exist_ok=True)
    with open(LIST_CACHE, 'w') as fh:
        json.dump(out, fh)
    print(f'cached {len(out)} songs → {LIST_CACHE}')
    return out


def load_list_cache():
    if not os.path.exists(LIST_CACHE):
        return None
    with open(LIST_CACHE) as fh:
        return json.load(fh)


def find_by_name(name, songs):
    needle = name.lower()
    return [s for s in songs if needle in s['song'].lower()]


def safe_filename(name):
    return name.replace('/', '_').replace('\x00', '')


def save_song(data, out_dir):
    json_data_str = data.get('jsonData')
    if not json_data_str:
        sys.exit('response had empty jsonData')
    parsed = json.loads(json_data_str)
    os.makedirs(out_dir, exist_ok=True)
    fname = os.path.join(out_dir, safe_filename(data['song']) + '.json')
    with open(fname, 'w', encoding='utf-8') as fh:
        json.dump(parsed, fh, ensure_ascii=False)
    return fname


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', default=None,
               help='bearer token; defaults to $HOOKPAD_TOKEN or ~/.hookpad_token '
                    '(refresh with hookpad_token.py)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--slug', help='Hookpad slug (e.g., Abm_nv_zoak)')
    g.add_argument('--id', type=int, help='Numeric song ID')
    g.add_argument('--name', help='Substring of song name (uses local list cache)')
    g.add_argument('--refresh-list', action='store_true', help='Rebuild song-list cache')
    p.add_argument('--out', default=DEFAULT_OUT)
    args = p.parse_args()

    # A pasted token was the manual step at the front of every sync.
    # hookpad_token.py lifts a live one off the authenticated browser.
    if not args.token:
        args.token = hookpad_token.read_saved()
    if not args.token:
        sys.exit("no token: run hookpad_token.py, or pass --token")

    if args.refresh_list:
        refresh_list(args.token)
        return

    if args.slug:
        slug = args.slug
        print(f'fetching slug {slug}...')
    elif args.id:
        slug = HASHIDS.encode(args.id)
        print(f'id {args.id} → slug {slug}')
    elif args.name:
        cache = load_list_cache()
        if cache is None:
            sys.exit('No list cache. Run with --refresh-list first.')
        matches = find_by_name(args.name, cache)
        if not matches:
            sys.exit(f'no songs match "{args.name}"')
        if len(matches) > 1:
            print(f'{len(matches)} matches:')
            for i, m in enumerate(matches[:20]):
                print(f'  [{i}] {m["song"]}  (modified {m["dateModified"]})')
            if len(matches) > 20:
                print(f'  … and {len(matches)-20} more')
            sys.exit('refine --name to a unique substring')
        slug = HASHIDS.encode(matches[0]['ID'])
        print(f'matched: {matches[0]["song"]} (id {matches[0]["ID"]} → slug {slug})')

    data = fetch_song_by_slug(args.token, slug)
    fname = save_song(data, args.out)
    print(f'saved → {fname}')


if __name__ == '__main__':
    main()
