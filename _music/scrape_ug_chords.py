"""Fetch chord text from UG official tab URLs.

Reads a list of URLs from one of the ~/Desktop/guitar*_ug_urls.txt files (TSV: title artist kind url)
and saves each as ~/Desktop/music/ug_tabs/{basename}.txt — the same format your UG parser expects.

Usage:
    python scrape_ug_chords.py guitar50          # uses ~/Desktop/guitar50_ug_urls.txt
    python scrape_ug_chords.py --csv beatles_by_project   # uses CSV with title,artist,ug_url cols
"""
import os, sys, re, time, csv
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
    s = re.sub(r'-+', '-', s).strip('-_')
    return s


def basename(title, artist):
    a = kebab(artist)
    if a.startswith('the-'): a = a[4:]
    return f'{a}_{kebab(title)}'


def load_rows(name_or_path):
    # Try desktop URL TSV first
    p = os.path.expanduser(f'~/Desktop/{name_or_path}_ug_urls.txt')
    if os.path.exists(p):
        out = []
        for r in csv.DictReader(open(p), delimiter='\t'):
            if r.get('url'):
                out.append({'title': r['title'], 'artist': r['artist'], 'url': r['url'], 'kind': r.get('kind','')})
        return out
    # Try as CSV path
    p2 = os.path.expanduser(f'~/Desktop/{name_or_path}.csv')
    if os.path.exists(p2):
        out = []
        for r in csv.DictReader(open(p2)):
            if r.get('ug_url'):
                title = r.get('title') or ''
                artist = r.get('artist') or 'beatles'  # default for beatles_by_project
                out.append({'title': title, 'artist': artist, 'url': r['ug_url'], 'kind': r.get('ug_kind','')})
        return out
    return None


def scrape(page, url):
    page.goto(url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(2500)
    # Click "Chords" button if present (official tabs default to interactive Tab view)
    try:
        btn = page.locator('button:has-text("Chords")').first
        if btn.count() and btn.is_visible(timeout=600):
            btn.click(timeout=1500)
            page.wait_for_timeout(1500)
    except Exception: pass
    # Pull metadata header (Tuning/Key/Capo). UG class names change, so regex the rendered HTML.
    meta = ''
    try:
        html = page.content()
        # Match each label+value pair: <span>Label:</span><span/a>value</...>
        parts = []
        for label in ['Tuning', 'Key', 'Capo']:
            m = re.search(rf'>{label}:?\s*</span>\s*<(?:span|a)[^>]*>([^<]+)<', html)
            if m: parts.append(f'{label}: {m.group(1).strip()}')
        meta = '  '.join(parts)
    except Exception: pass
    # Extract chord/lyric text from <pre>
    try:
        pre = page.locator('pre').first
        if pre.count():
            txt = pre.inner_text(timeout=2000)
            txt = txt.replace('\r\n', '\n').replace('\r', '\n')
            if len(txt) > 50:
                return f'{meta}\n\n{txt}' if meta else txt
    except Exception: pass
    return ''


def main():
    args = sys.argv[1:]
    use_csv = False
    if '--csv' in args: args.remove('--csv'); use_csv = True
    if not args: print('usage: scrape_ug_chords.py <name>'); sys.exit(1)
    name = args[0]
    rows = load_rows(name)
    if not rows: print(f'no URL list found for "{name}"'); sys.exit(1)
    print(f'{len(rows)} URLs to scrape')

    n_ok = n_skip = 0
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for i, r in enumerate(rows, 1):
            bn = basename(r['title'], r['artist'])
            out_path = os.path.join(OUT_DIR, bn + '.txt')
            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                # Skip only if file already has Key: metadata (otherwise re-scrape to backfill it)
                if 'Key:' in open(out_path).read()[:500]:
                    n_skip += 1
                    if i % 25 == 0: print(f'  [{i:3}/{len(rows)}] skip (has Key): {bn}')
                    continue
            try:
                txt = scrape(page, r['url'])
                if txt:
                    # Prepend source URL as a comment so the file remembers where it came from
                    open(out_path, 'w').write(f"# {r['url']}\n\n{txt}")
                    n_ok += 1
                    if i <= 3 or i % 25 == 0: print(f'  [{i:3}/{len(rows)}] ✓ {bn} ({len(txt)}b)')
                else:
                    print(f'  [{i:3}/{len(rows)}] ✗ no chords for {bn}')
            except Exception as e:
                print(f'  [{i:3}/{len(rows)}] ERR {bn}: {e}')
            time.sleep(1.5)
        browser.close()
    print(f'\nscraped {n_ok} new, skipped {n_skip} existing → {OUT_DIR}')


if __name__ == '__main__':
    main()
