"""Sync all Hookpad songs from the user's account to local JSON files.

Usage:
    sync_hookpad.py --token TOKEN [--out DIR] [--full] [--limit N]

Defaults to incremental: only fetches songs whose API dateModified is newer
than the local file's mtime (or missing locally). --full forces re-fetch all.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from hashids import Hashids
import hookpad_token

API = 'https://api.hooktheory.com/v1'
HASHIDS = Hashids(
    salt='XI0Y4UFrK6EPLnarrI4y',
    min_length=11,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
)


def list_all_songs(token):
    headers = {
        'authorization': f'Bearer {token}',
        'origin': 'https://hookpad.hooktheory.com',
        'referer': 'https://hookpad.hooktheory.com/',
    }
    out = []
    page = 1
    while True:
        r = requests.get(f'{API}/songs/h?per-page=100&page={page}', headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        out.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(3.0)   # generous throttle to avoid 429 on list calls
    return out


def fetch_song(token, numeric_id):
    slug = HASHIDS.encode(numeric_id)
    headers = {
        'authorization': f'Bearer {token}',
        'origin': 'https://hookpad.hooktheory.com',
        'referer': 'https://hookpad.hooktheory.com/',
    }
    url = f'{API}/songs/{slug}?fields=ID,xmlData,song,jsonData,isPrivate'
    # 429-aware: back off exponentially up to ~5 min total before giving up
    backoff = 30
    for attempt in range(4):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 429:
            print(f'    429 received — backing off {backoff}s (attempt {attempt+1}/4)')
            time.sleep(backoff)
            backoff *= 2
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f'gave up after 4 retries on song {numeric_id}')


def safe_filename(name):
    # Hookpad song names can contain '/' and other unsafe chars
    return name.replace('/', '_').replace('\x00', '')


def parse_api_dt(s):
    # '2026-05-09 22:07:50+00:00'
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', default=None,
               help='bearer token; defaults to $HOOKPAD_TOKEN or ~/.hookpad_token '
                    '(refresh with hookpad_token.py)')
    p.add_argument('--out', default='/Users/robert/Desktop/music/hookpad_songs_full')
    p.add_argument('--full', action='store_true', help='Re-fetch everything (default: incremental)')
    p.add_argument('--limit', type=int, help='Cap downloads (testing)')
    p.add_argument('--throttle', type=float, default=0.15)
    args = p.parse_args()

    # A pasted token was the manual step at the front of every sync.
    # hookpad_token.py lifts a live one off the authenticated browser.
    if not args.token:
        args.token = hookpad_token.read_saved()
    if not args.token:
        sys.exit("no token: run hookpad_token.py, or pass --token")

    os.makedirs(args.out, exist_ok=True)

    print('listing songs...')
    songs = list_all_songs(args.token)
    print(f'  {len(songs)} songs in account')

    # Decide which to fetch
    todo = []
    skipped = 0
    for s in songs:
        fname = os.path.join(args.out, safe_filename(s['song']) + '.json')
        if not args.full and os.path.exists(fname):
            api_dt = parse_api_dt(s['dateModified'])
            local_mtime = datetime.fromtimestamp(os.path.getmtime(fname), tz=timezone.utc)
            if api_dt and local_mtime >= api_dt:
                skipped += 1
                continue
        todo.append((s, fname))

    print(f'  to fetch: {len(todo)}, skip (up-to-date): {skipped}')
    if args.limit:
        todo = todo[:args.limit]
        print(f'  limited to {len(todo)}')

    if not todo:
        print('nothing to do.')
        return

    fetched = 0
    errors = []
    start = time.time()
    for i, (s, fname) in enumerate(todo, 1):
        try:
            data = fetch_song(args.token, s['ID'])
            json_data_str = data.get('jsonData')
            if not json_data_str:
                errors.append((s['ID'], s['song'], 'empty jsonData'))
                continue
            parsed = json.loads(json_data_str)
            with open(fname, 'w', encoding='utf-8') as fh:
                json.dump(parsed, fh, ensure_ascii=False)
            fetched += 1
            if i % 25 == 0 or i == len(todo):
                elapsed = time.time() - start
                rate = i / elapsed if elapsed else 0
                eta = (len(todo) - i) / rate if rate else 0
                print(f'  [{i}/{len(todo)}] fetched {fetched}, errors {len(errors)}, '
                      f'rate {rate:.1f}/s, ETA {eta:.0f}s')
        except Exception as ex:
            errors.append((s['ID'], s['song'], str(ex)[:120]))
        time.sleep(args.throttle)

    print(f'\ndone. fetched {fetched}, errors {len(errors)}')
    if errors:
        print('first 10 errors:')
        for e in errors[:10]:
            print(' ', e)


if __name__ == '__main__':
    main()
