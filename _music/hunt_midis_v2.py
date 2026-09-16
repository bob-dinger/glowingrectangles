"""Multi-source MIDI hunter using Playwright (handles JS-rendered sites).

Sources tried per song (first hit wins):
  1. midis101.com   — direct requests (fast, already covered ~329)
  2. freemidi.org   — Playwright, JS-rendered
  3. cprato.com     — direct, sometimes good for popular songs
"""
import os, sys, csv, re, time, urllib.parse, requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

DST = os.path.expanduser('~/Desktop/midi_files_new2')
SUMMARY = os.path.expanduser('~/Desktop/midi_hunt2_results.csv')
os.makedirs(DST, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'
SESS = requests.Session(); SESS.headers.update({'User-Agent': UA})


def kebab(s):
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    return re.sub(r'-+', '-', s).strip('-_')

def basename(title, artist):
    a = kebab(artist)
    if a.startswith('the-'): a = a[4:]
    return f'{a}_{kebab(title)}'

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def try_midis101(title, artist):
    q = urllib.parse.quote(f'{title} {artist}')
    try:
        r = SESS.get(f'https://midis101.com/search/{q}', timeout=8)
        if r.status_code != 200: return None
    except Exception: return None
    matches = re.findall(r'href="(/free-midi/(\d+)-([^"]+))"', r.text)
    nt = normalize(title); na = normalize(artist)
    for href, mid, slug in matches:
        ns = normalize(slug)
        if nt in ns and na in ns:
            try:
                dl = SESS.get(f'https://midis101.com/download/{mid}-{slug}', timeout=15)
                if dl.content[:4] == b'MThd': return ('midis101', dl.content)
            except Exception: pass
    return None


def try_cprato(title, artist):
    """cprato.com hosts free MIDIs at predictable URLs."""
    slug = f'{kebab(artist).replace("-","_")}_{kebab(title).replace("-","_")}'
    for ext in ['.mid', '.MID']:
        for url_pat in [
            f'https://www.cprato.com/en/midi/free/{slug}{ext}',
            f'https://www.cprato.com/midi/free/{slug}{ext}',
        ]:
            try:
                r = SESS.get(url_pat, timeout=6, allow_redirects=True)
                if r.status_code == 200 and r.content[:4] == b'MThd':
                    return ('cprato', r.content)
            except Exception: pass
    return None


def try_freemidi_playwright(page, title, artist):
    q = urllib.parse.quote(f'{title} {artist}')
    try:
        page.goto(f'https://freemidi.org/search?q={q}', wait_until='domcontentloaded', timeout=12000)
        page.wait_for_timeout(1500)
        # Find song results — they're in <div class="search-result-row"> typically
        links = page.locator('a[href*="/getter-"]').all()
        nt = normalize(title); na = normalize(artist)
        for link in links[:10]:
            try:
                href = link.get_attribute('href')
                text = (link.inner_text(timeout=300) or '').lower()
                if (nt in normalize(text)) and (na in normalize(text) or len(links) <= 3):
                    # Visit the song page
                    full = href if href.startswith('http') else 'https://freemidi.org' + href
                    page.goto(full, wait_until='domcontentloaded', timeout=10000)
                    page.wait_for_timeout(1000)
                    # Find download link
                    dl_link = page.locator('a[href*="getter-"], a:has-text("Download")').first
                    if dl_link.count():
                        dl_href = dl_link.get_attribute('href')
                        full_dl = dl_href if dl_href.startswith('http') else 'https://freemidi.org' + dl_href
                        try:
                            dl = SESS.get(full_dl, timeout=12,
                                          headers={'Referer': full, 'User-Agent': UA},
                                          cookies={c['name']: c['value'] for c in page.context.cookies()})
                            if dl.content[:4] == b'MThd':
                                return ('freemidi', dl.content)
                        except Exception: pass
            except Exception: continue
    except Exception: pass
    return None


def main():
    args = sys.argv[1:]
    limit = int(args[0]) if args and args[0].isdigit() else None

    rows = [r for r in csv.DictReader(open(os.path.expanduser('~/Desktop/song_coverage.csv')))
            if r['hookpad'] == 'x' and r['midi'] != 'x']
    if limit: rows = rows[:limit]
    print(f'{len(rows)} songs to hunt MIDIs for')

    results = []
    n_found = {'midis101': 0, 'cprato': 0, 'freemidi': 0}
    n_miss = 0

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        for i, r in enumerate(rows, 1):
            bn = basename(r['title'], r['artist'])
            out_path = os.path.join(DST, bn + '.mid')
            if os.path.exists(out_path):
                results.append({**r, 'status':'skip_exists', 'basename':bn}); continue
            found = None
            for fn in [try_midis101, try_cprato]:
                try: found = fn(r['title'], r['artist'])
                except Exception: pass
                if found: break
            if not found:
                try: found = try_freemidi_playwright(page, r['title'], r['artist'])
                except Exception: pass
            if found:
                src, body = found
                open(out_path, 'wb').write(body)
                n_found[src] = n_found.get(src, 0) + 1
                results.append({**r, 'status':'ok', 'basename':bn, 'source':src, 'size':len(body)})
                if i <= 3 or i % 25 == 0: print(f'  [{i:4}/{len(rows)}] ✓ {src:8s} {bn}')
            else:
                n_miss += 1
                results.append({**r, 'status':'no_match', 'basename':bn})
                if i % 25 == 0: print(f'  [{i:4}/{len(rows)}] ✗ {bn}')
            time.sleep(0.8)
        browser.close()

    fields = ['title','artist','basename','status','source','size']
    with open(SUMMARY, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in results: w.writerow({k: r.get(k,'') for k in fields})
    print(f'\nfound by source: {n_found}')
    print(f'missed: {n_miss}, downloaded → {DST}')
    print(f'summary → {SUMMARY}')


if __name__ == '__main__': main()
