"""Batch-fetch Guitar Pro files for a list of UG official tabs.

Reads ~/Desktop/{name}_ug_urls.txt (TSV: title artist kind url), filters to -official- URLs,
fetches each .gp5/.gpx/.ptb file, saves to ~/Desktop/midi_files_gp5/, writes summary CSV.

Usage: python fetch_ug_gp5_batch.py guitar50 guitar100 ...
"""
import os, sys, re, csv, time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT_DIR = os.path.expanduser('~/Desktop/midi_files_gp5')
os.makedirs(OUT_DIR, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'


def kebab(s):
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s); s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s); return re.sub(r'-+', '-', s).strip('-_')

def basename(title, artist):
    a = kebab(artist)
    if a.startswith('the-'): a = a[4:]
    return f'{a}_{kebab(title)}'


def detect_format(body):
    """Return extension based on magic bytes (and embedded version string for GP3/4/5)."""
    if b'FICHIER GUITAR PRO' in body[:32]:
        # Embedded version like "v3.00", "v4.06", "v5.10"
        m = re.search(rb'v(\d)\.\d\d', body[:64])
        if m: return f'.gp{m.group(1).decode()}'
        return '.gp5'
    if body[:4] == b'BCFZ': return '.gpx'
    if body[:4] == b'ptab': return '.ptb'
    if body[:4] == b'PK\x03\x04': return '.gp'   # GP7+ zip
    if body[:4] == b'MThd': return '.mid'
    return '.bin'


def fetch_for_url(page, ctx, official_url):
    """Returns {status, format, size, gp_url, filename} or {status: error_code, ...}."""
    try:
        page.goto(official_url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(2500)
        gp_url = page.evaluate("window.UGAPP?.store?.page?.data?.best_pro_tab_url")
    except Exception as e:
        return {'status': f'err_official:{str(e)[:60]}'}
    if not gp_url: return {'status': 'no_pro_url'}

    download_url = None
    def on_req(r):
        nonlocal download_url
        if '/download/public/' in r.url: download_url = r.url
    page.on('request', on_req)
    try:
        page.goto(gp_url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(3000)
    except Exception as e:
        page.remove_listener('request', on_req)
        return {'status': f'err_gp_page:{str(e)[:60]}', 'gp_url': gp_url}
    page.remove_listener('request', on_req)
    if not download_url: return {'status': 'no_download_url', 'gp_url': gp_url}

    try:
        r = ctx.request.get(download_url, headers={'Referer': gp_url})
        body = r.body()
    except Exception as e:
        return {'status': f'err_download:{str(e)[:60]}', 'gp_url': gp_url}
    if not body or len(body) < 100:
        return {'status': 'empty_body', 'gp_url': gp_url}
    ext = detect_format(body)
    return {'status': 'ok', 'gp_url': gp_url, 'body': body, 'ext': ext, 'size': len(body)}


def main():
    list_names = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not list_names: print(__doc__); sys.exit(1)
    rows_to_process = []
    for name in list_names:
        path = os.path.expanduser(f'~/Desktop/{name}_ug_urls.txt')
        if not os.path.exists(path): print(f'no file: {path}'); continue
        for r in csv.DictReader(open(path), delimiter='\t'):
            if r.get('kind') == 'official' and r.get('url'):
                rows_to_process.append({'list': name, **r})
    print(f'{len(rows_to_process)} official URLs to fetch')

    summary = []
    counts = {'ok': 0, 'no_pro_url': 0, 'no_download_url': 0, 'other_err': 0}
    by_format = {}
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for i, r in enumerate(rows_to_process, 1):
            bn = basename(r['title'], r['artist'])
            out_base = os.path.join(OUT_DIR, bn)
            # Skip if any extension already exists
            if any(os.path.exists(out_base + e) for e in ['.gp5', '.gpx', '.ptb', '.gp', '.mid']):
                summary.append({**r, 'basename': bn, 'status': 'skip_exists'}); continue
            info = fetch_for_url(page, ctx, r['url'])
            entry = {**r, 'basename': bn, 'status': info['status'], 'gp_url': info.get('gp_url', ''),
                     'format': info.get('ext', ''), 'size': info.get('size', 0)}
            if info['status'] == 'ok':
                open(out_base + info['ext'], 'wb').write(info['body'])
                counts['ok'] += 1
                by_format[info['ext']] = by_format.get(info['ext'], 0) + 1
            elif info['status'] in counts:
                counts[info['status']] += 1
            else: counts['other_err'] += 1
            summary.append(entry)
            if i <= 3 or i % 10 == 0:
                print(f'  [{i:3}/{len(rows_to_process)}] {info["status"]:12s} {info.get("ext",""):5s} {bn}')
            time.sleep(0.8)
        browser.close()

    out_csv = os.path.expanduser('~/Desktop/ug_gp5_batch_results.csv')
    fields = ['list','title','artist','url','basename','status','format','size','gp_url']
    with open(out_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in summary: w.writerow({k: r.get(k, '') for k in fields})
    print(f'\ncounts: {counts}')
    print(f'by format: {by_format}')
    print(f'summary → {out_csv}')


if __name__ == '__main__': main()
