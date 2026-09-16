"""Fetch .gp5 Guitar Pro files for UG official tabs and parse them.

Workflow per song:
  1. Visit official UG tab page → grab best_pro_tab_url
  2. Visit GP page → capture signed /download/public/ URL from network
  3. Fetch file via authenticated context → save as .gp5
  4. Parse with pyguitarpro → print summary

Usage: python fetch_ug_gp5.py <official_url> [<official_url> ...]
       python fetch_ug_gp5.py --test  (runs on the 10-song test set)
"""
import os, sys, re, json, guitarpro

def detect_ext(body):
    if body[:4] == b'BCFZ': return '.gpx'
    if body[:4] == b'ptab': return '.ptb'
    if body[:4] == b'PK\x03\x04': return '.gp'
    if b'FICHIER GUITAR PRO' in body[:32]:
        m = re.search(rb'v(\d)\.\d\d', body[:64])
        return f'.gp{m.group(1).decode()}' if m else '.gp5'
    return '.bin'
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT_DIR = os.path.expanduser('~/Desktop/midi_files_gp5')
os.makedirs(OUT_DIR, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'


def fetch_gp5_for_official(page, ctx, official_url):
    """Returns (gp_data_bytes, info_dict) or (None, error_dict)."""
    # 1. Visit official page to get best_pro_tab_url
    page.goto(official_url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(2500)
    try:
        gp_url = page.evaluate("window.UGAPP?.store?.page?.data?.best_pro_tab_url")
    except Exception:
        gp_url = None
    if not gp_url: return None, {'error': 'no_pro_url'}

    # 2. Visit GP page, capture download URL from network
    download_url = None
    def on_req(r):
        nonlocal download_url
        if '/download/public/' in r.url: download_url = r.url
    page.on('request', on_req)
    page.goto(gp_url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(3000)
    page.remove_listener('request', on_req)
    if not download_url: return None, {'error': 'no_download_url', 'gp_url': gp_url}

    # 3. Fetch file
    r = ctx.request.get(download_url, headers={'Referer': gp_url})
    body = r.body()
    disp = r.headers.get('content-disposition', '')
    if not body or len(body) < 100: return None, {'error': 'empty_body', 'gp_url': gp_url}
    fname_m = re.search(r'filename="([^"]+)"', disp)
    fname = fname_m.group(1) if fname_m else 'song.gp5'
    return body, {'gp_url': gp_url, 'download_url': download_url, 'filename': fname}


def summarize_gp(path):
    try:
        song = guitarpro.parse(path)
        return {
            'title': song.title, 'artist': song.artist,
            'key': song.key.name, 'tempo': song.tempo,
            'measures': len(song.measureHeaders),
            'tracks': [{'name': t.name, 'channel': t.channel.channel,
                        'notes': sum(len(beat.notes) for m in t.measures for v in m.voices for beat in v.beats)}
                       for t in song.tracks],
        }
    except Exception as e:
        return {'parse_error': str(e)[:100]}


def basename_from_url(url):
    m = re.search(r'/tab/([^/]+)/([^/]+)-official-\d+', url)
    if not m: return 'song'
    artist = m.group(1)
    if artist.startswith('the-'): artist = artist[4:]
    title = re.sub(r'-official-\d+', '', m.group(2))
    return f'{artist}_{title}'


TEST_URLS = [
    'https://tabs.ultimate-guitar.com/tab/america/sister-golden-hair-official-1956617',
    'https://tabs.ultimate-guitar.com/tab/creedence-clearwater-revival/have-you-ever-seen-the-rain-official-1946361',
    'https://tabs.ultimate-guitar.com/tab/oasis/wonderwall-official-1746957',
    'https://tabs.ultimate-guitar.com/tab/jimmy-buffett/margaritaville-official-2500125',
    'https://tabs.ultimate-guitar.com/tab/shawn-colvin/sunny-came-home-official-2278779',
    'https://tabs.ultimate-guitar.com/tab/the-killers/mr-brightside-official-1915707',
    'https://tabs.ultimate-guitar.com/tab/rod-stewart/maggie-may-official-2017413',
    'https://tabs.ultimate-guitar.com/tab/nirvana/smells-like-teen-spirit-official-1948517',
    'https://tabs.ultimate-guitar.com/tab/tom-petty/free-fallin-official-1893553',
    'https://tabs.ultimate-guitar.com/tab/oasis/dont-look-back-in-anger-official-2002293',
]


def main():
    args = sys.argv[1:]
    urls = TEST_URLS if '--test' in args else [a for a in args if a.startswith('http')]
    if not urls:
        print(__doc__); sys.exit(1)

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for i, url in enumerate(urls, 1):
            bn = basename_from_url(url)
            print(f'\n[{i}/{len(urls)}] {bn}')
            body, info = fetch_gp5_for_official(page, ctx, url)
            if not body:
                print(f'  ✗ {info.get("error","unknown")}'); continue
            ext = detect_ext(body)
            out_path = os.path.join(OUT_DIR, bn + ext)
            open(out_path, 'wb').write(body)
            if ext not in ('.gp3', '.gp4', '.gp5'):
                print(f'  ⚠ saved as {ext} (pyguitarpro can\'t parse)')
                continue
            summary = summarize_gp(out_path)
            if 'parse_error' in summary:
                print(f'  ✗ parse error: {summary["parse_error"]}')
            else:
                print(f'  ✓ {summary["title"]} — {summary["artist"]}')
                print(f'     key={summary["key"]}  tempo={summary["tempo"]}  measures={summary["measures"]}  tracks={len(summary["tracks"])}')
                for t in summary['tracks']:
                    drum = ' (DRUMS)' if t['channel'] == 9 else ''
                    print(f'       {t["name"][:30]:30s}  notes={t["notes"]:>4}{drum}')
        browser.close()


if __name__ == '__main__': main()
