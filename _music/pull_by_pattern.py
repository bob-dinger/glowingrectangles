"""Pull every cached Hookpad song whose name matches a pattern, by ID (zero list
calls). Throttled with 429 backoff. Reusable as the user keeps adding variants.

    python pull_by_pattern.py --token TOKEN --suffix -hooktab
    python pull_by_pattern.py --token TOKEN --contains simple
"""
import argparse, json, os, sys, time, requests
from hashids import Hashids
import hookpad_token

API = 'https://api.hooktheory.com/v1'
HASHIDS = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
                  alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
OUT = os.path.expanduser('~/Desktop/music/hookpad_songs_full')


def headers(token):
    return {'authorization': f'Bearer {token}', 'origin': 'https://hookpad.hooktheory.com',
            'referer': 'https://hookpad.hooktheory.com/'}


def fetch(token, slug, tries=3):
    for i in range(tries):
        r = requests.get(f'{API}/songs/{slug}?fields=ID,xmlData,song,jsonData,isPrivate',
                         headers=headers(token), timeout=30)
        if r.status_code == 429:
            print(f'    429 — backing off 30s ({i+1}/{tries})'); time.sleep(30); continue
        r.raise_for_status()
        return r.json()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', default=None,
                help='bearer token; defaults to $HOOKPAD_TOKEN or ~/.hookpad_token '
                     '(refresh with hookpad_token.py)')
    ap.add_argument('--suffix'); ap.add_argument('--contains')
    ap.add_argument('--throttle', type=float, default=7.0)
    a = ap.parse_args()
    # A pasted token was the manual step at the front of every sync.
    # hookpad_token.py lifts a live one off the authenticated browser.
    if not a.token:
        a.token = hookpad_token.read_saved()
    if not a.token:
        sys.exit("no token: run hookpad_token.py, or pass --token")

    cache = json.load(open(CACHE))
    def match(nm):
        nm = nm.lower().rstrip()
        if a.suffix: return nm.endswith(a.suffix.lower())
        if a.contains: return a.contains.lower() in nm
        return False
    hits = [s for s in cache if match(s['song'])]
    print(f'{len(hits)} songs match; pulling to {OUT}')
    os.makedirs(OUT, exist_ok=True)
    ok = 0
    for i, s in enumerate(hits):
        slug = HASHIDS.encode(s['ID'])
        try:
            data = fetch(a.token, slug)
            if not data or not data.get('jsonData'):
                print(f'  [{i+1}/{len(hits)}] EMPTY {s["song"]}'); continue
            parsed = json.loads(data['jsonData'])
            fn = os.path.join(OUT, data['song'].replace('/', '_') + '.json')
            json.dump(parsed, open(fn, 'w'), ensure_ascii=False)
            ok += 1
            print(f'  [{i+1}/{len(hits)}] {s["song"]}')
        except Exception as e:
            print(f'  [{i+1}/{len(hits)}] ERR {s["song"]}: {str(e)[:40]}')
        if i < len(hits) - 1:
            time.sleep(a.throttle)
    print(f'\ndone: {ok}/{len(hits)} pulled')


if __name__ == '__main__':
    main()
