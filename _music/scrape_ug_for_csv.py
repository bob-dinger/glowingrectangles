"""For each (title, artist) in a CSV, search UG → pick best URL → scrape chord text.

Combines scrape_ug_urls + scrape_ug_chords into one pass. Saves chord text to
~/Desktop/music/ug_tabs/{basename}.txt and writes a URL summary CSV.

Usage:
    python scrape_ug_for_csv.py <input.csv> <out_name>
    python scrape_ug_for_csv.py ~/Desktop/hookpad_need_ug.csv hookpad_need
"""
import os, sys, csv, re, time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
os.makedirs(OUT_DIR, exist_ok=True)


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


def kind_rank(u):
    if '-official-' in u: return ('official', 0)
    if '-chords-' in u:   return ('chords',   1)
    if '-tabs-' in u:     return ('tabs',     2)
    if '-pro-' in u:      return ('guitar-pro', 3)
    return ('other', 4)


def find_best_url(page, title, artist):
    url = f'https://www.ultimate-guitar.com/search.php?title={title.replace(" ","+")}&artist={artist.replace(" ","+")}'
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(1200)
        html = page.content()
    except Exception: return None, None
    tab_urls = re.findall(r'tabs\.ultimate-guitar\.com/tab/[^"\'\s]+', html)
    seen, uniq = set(), []
    for u in tab_urls:
        u = u.split('?')[0].split('#')[0]
        if u not in seen: seen.add(u); uniq.append(u)
    if not uniq: return None, None
    uniq.sort(key=lambda u: kind_rank(u)[1])
    return 'https://' + uniq[0], kind_rank(uniq[0])[0]


def scrape_chord_text(page, url):
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(2200)
    except Exception: return ''
    # Click Chords button
    try:
        btn = page.locator('button:has-text("Chords")').first
        if btn.count() and btn.is_visible(timeout=600):
            btn.click(timeout=1500)
            page.wait_for_timeout(1200)
    except Exception: pass
    # Get metadata
    meta = ''
    try:
        m = page.locator('.CCUPL').first
        if m.count(): meta = re.sub(r'\s+', ' ', m.inner_text(timeout=1500)).strip()
    except Exception: pass
    try:
        pre = page.locator('pre').first
        if pre.count():
            txt = pre.inner_text(timeout=2000).replace('\r\n', '\n').replace('\r', '\n')
            if len(txt) > 50: return f'{meta}\n\n{txt}' if meta else txt
    except Exception: pass
    return ''


def main():
    args = sys.argv[1:]
    if len(args) < 2: print('usage: scrape_ug_for_csv.py <input.csv> <out_name>'); sys.exit(1)
    in_csv = os.path.expanduser(args[0])
    out_name = args[1]
    summary_path = os.path.expanduser(f'~/Desktop/{out_name}_ug_results.csv')

    rows = list(csv.DictReader(open(in_csv)))
    print(f'{len(rows)} songs to search…')

    results = []
    n_scraped = n_skip = n_nourl = n_noscrape = 0
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for i, r in enumerate(rows, 1):
            title = r['title']; artist = r['artist']
            bn = basename(title, artist)
            out_path = os.path.join(OUT_DIR, bn + '.txt')
            if os.path.exists(out_path) and 'Key:' in open(out_path).read()[:500]:
                n_skip += 1
                results.append({**r, 'status': 'skip_exists', 'basename': bn})
                continue
            url, kind = find_best_url(page, title, artist)
            if not url:
                n_nourl += 1
                results.append({**r, 'status': 'no_url', 'basename': bn})
                if i % 25 == 0: print(f'  [{i:4}/{len(rows)}] no URL  {title[:40]} — {artist[:20]}')
                time.sleep(1)
                continue
            txt = scrape_chord_text(page, url)
            if txt:
                open(out_path, 'w').write(f'# {url}\n\n{txt}')
                n_scraped += 1
                results.append({**r, 'status': 'ok', 'basename': bn, 'url': url, 'kind': kind})
                if i <= 3 or i % 25 == 0: print(f'  [{i:4}/{len(rows)}] {kind:10s} ✓ {bn}')
            else:
                n_noscrape += 1
                results.append({**r, 'status': 'no_chord_text', 'basename': bn, 'url': url, 'kind': kind})
            time.sleep(1.5)
        browser.close()

    fields = list(rows[0].keys()) + ['basename','status','url','kind']
    seen = set(); fields = [f for f in fields if not (f in seen or seen.add(f))]
    with open(summary_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results: w.writerow({k: r.get(k, '') for k in fields})
    print(f'\nscraped: {n_scraped}, skipped existing: {n_skip}, no URL: {n_nourl}, no text: {n_noscrape}')
    print(f'summary → {summary_path}')


if __name__ == '__main__':
    main()
