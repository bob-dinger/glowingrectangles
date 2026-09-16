"""Scrape every official tab URL from UG by slicing the catalog with decade + sort-order filters.

UG's explore page exposes ~10000 official tabs but caps pagination at 5000 results per filter.
We slice by decade; for decades larger than 5000 (2000s and 2010s) we scrape both
date_desc and date_asc orderings and dedupe — that covers the head AND tail of those slices.

Output ~/Desktop/ug_all_official.csv with columns: title, artist, url.
"""
import os, re, csv, sys, time
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT = os.path.expanduser('~/Desktop/ug_all_official.csv')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'

# Decades exposed via the explore filter
DECADES = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]
# Decades where total > 5000 cap; scrape with both desc and asc to capture top + bottom
NEEDS_BOTH_ORDERS = {2000, 2010}


def parse_slug(url):
    m = re.search(r'/tab/([^/]+)/([^/]+?)-official-\d+', url)
    if not m: return ('', '')
    return m.group(2).replace('-', ' '), m.group(1).replace('-', ' ')


def scrape_slice(page, base_url, label):
    """Paginate one filtered explore URL up to 100 pages or two consecutive empties."""
    found = []
    last_hit = 0
    for pn in range(1, 101):
        u = base_url + ('&' if '?' in base_url else '?') + f'page={pn}'
        try:
            page.goto(u, wait_until='domcontentloaded', timeout=25000)
            page.wait_for_timeout(1500)
            html = page.content()
        except Exception as e:
            print(f'    {label} page {pn}: ERR'); continue
        urls = []
        for m in re.findall(r'tabs\.ultimate-guitar\.com/tab/[^"\'\s]+', html):
            m = m.split('?')[0].split('#')[0]
            if '-official-' in m: urls.append(m)
        urls = list(dict.fromkeys(urls))
        if urls:
            found.extend(urls)
            last_hit = pn
        if not urls and pn - last_hit >= 2: break
        time.sleep(0.4)
    return found


def main():
    all_urls = set()
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for dec in DECADES:
            orders = ['date_desc', 'date_asc'] if dec in NEEDS_BOTH_ORDERS else [None]
            decade_urls = set()
            for order in orders:
                base = f'https://www.ultimate-guitar.com/explore?decade[]={dec}&type[]=Official'
                if order: base += f'&order={order}'
                label = f'{dec}s' + (f'/{order.split("_")[1]}' if order else '')
                found = scrape_slice(page, base, label)
                decade_urls.update(found)
                print(f'  {label}: +{len(found):>5} ({len(decade_urls)} unique this decade)')
            all_urls.update(decade_urls)
            print(f'  → decade {dec}s done; cumulative unique: {len(all_urls)}')
        browser.close()

    rows = []
    for u in sorted(all_urls):
        title, artist = parse_slug(u)
        rows.append({'title': title, 'artist': artist, 'url': 'https://' + u})

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['title','artist','url'])
        w.writeheader()
        for r in rows: w.writerow(r)
    print(f'\n{len(rows)} unique official tabs → {OUT}')


if __name__ == '__main__': main()
