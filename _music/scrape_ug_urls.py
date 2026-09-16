"""URL-only UG scraper. Takes a list name (USER_LIST, USER_LIST_2, etc.) and outputs URLs.

Skips tab page visit, MIDI capture — just hits UG search for each song.

Usage:
    python scrape_ug_urls.py USER_LIST_2 guitar100
        → outputs ~/Desktop/guitar100_ug_urls.txt
"""
import os, sys, re, time, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'

LIST_MAP = {
    'USER_LIST':    ('rebuild_studied_songs', 'guitar50'),
    'USER_LIST_2':  ('rebuild_study_2',       'guitar100'),
    'USER_LIST_3':  ('rebuild_guitar150',     'guitar150'),
    'USER_LIST_4':  ('rebuild_guitar200',     'guitar200'),
    'USER_LIST_5':  ('rebuild_guitar250',     'guitar250'),
    'USER_LIST_6':  ('rebuild_guitar300',     'guitar300'),
    'USER_LIST_7':  ('rebuild_guitar350',     'guitar350'),
    'USER_LIST_8':  ('rebuild_guitar400',     'guitar400'),
    'USER_LIST_9':  ('rebuild_guitar450',     'guitar450'),
    'USER_LIST_10': ('rebuild_guitar500',     'guitar500'),
    'USER_LIST_11': ('rebuild_guitar550',     'guitar550'),
}


def kind_rank(u):
    if '-official-' in u: return ('official', 0)
    if '-chords-'   in u: return ('chords',   1)
    if '-tabs-'     in u: return ('tabs',     2)
    if '-guitar-pro-' in u or '-pro-' in u: return ('guitar-pro', 3)
    return ('other', 4)


def main():
    if len(sys.argv) < 2:
        print('usage: scrape_ug_urls.py USER_LIST_2 [outname]'); sys.exit(1)
    list_var = sys.argv[1]
    if list_var not in LIST_MAP:
        print(f'unknown list: {list_var}'); sys.exit(1)
    module_name, default_outname = LIST_MAP[list_var]
    outname = sys.argv[2] if len(sys.argv) > 2 else default_outname
    out_path = os.path.expanduser(f'~/Desktop/{outname}_ug_urls.txt')

    mod = importlib.import_module(module_name)
    songs = getattr(mod, list_var)
    print(f'{len(songs)} songs from {module_name}.{list_var}')

    rows = []
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()
        for i, (title, artist) in enumerate(songs, 1):
            url = f'https://www.ultimate-guitar.com/search.php?title={title.replace(" ", "+")}&artist={artist.replace(" ", "+")}'
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=12000)
                page.wait_for_timeout(1200)
                html = page.content()
                tab_urls = re.findall(r'tabs\.ultimate-guitar\.com/tab/[^"\'\s]+', html)
                # Dedupe
                seen, uniq = set(), []
                for u in tab_urls:
                    u = u.split('?')[0].split('#')[0]
                    if u not in seen: seen.add(u); uniq.append(u)
                # Best by kind
                uniq.sort(key=lambda u: kind_rank(u)[1])
                if uniq:
                    best = 'https://' + uniq[0]
                    kind = kind_rank(uniq[0])[0]
                    print(f'  [{i:3}/{len(songs)}] {kind:10s}  {title[:30]:30s} — {artist[:20]:20s}')
                    rows.append((title, artist, kind, best))
                else:
                    print(f'  [{i:3}/{len(songs)}] NO MATCH   {title[:30]:30s} — {artist[:20]:20s}')
                    rows.append((title, artist, '', ''))
            except Exception as e:
                print(f'  [{i:3}/{len(songs)}] ERR: {e}')
                rows.append((title, artist, 'error', ''))
            time.sleep(1.5)
        browser.close()

    # Write a simple text file: title\tartist\tkind\turl
    with open(out_path, 'w') as f:
        f.write('title\tartist\tkind\turl\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    n_official = sum(1 for r in rows if r[2] == 'official')
    n_any = sum(1 for r in rows if r[3])
    print(f'\n{n_official}/{len(songs)} official, {n_any}/{len(songs)} any URL')
    print(f'wrote → {out_path}')


if __name__ == '__main__':
    main()
