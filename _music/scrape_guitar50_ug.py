"""For each song in Guitar 50: find its UG official tab URL + scrape tab text + try to capture MIDI.

Uses ~/Desktop/.ug_auth.json (refresh by re-running ug_login.py or re-pasting cookies).

Outputs:
    ~/Desktop/music/ug_tabs/{basename}.txt    — chord+lyric text
    ~/Desktop/music/ug_tabs/{basename}.mid    — MIDI/GP file if captured
    ~/Desktop/guitar50_ug_summary.txt         — per-song URL + notes
"""
import os, sys, json, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Import song list
from rebuild_studied_songs import USER_LIST

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
SUMMARY = os.path.expanduser('~/Desktop/guitar50_ug_summary.txt')
os.makedirs(OUT_DIR, exist_ok=True)

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'


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


def find_best_url(page, title, artist):
    """Use UG search to find the official tab URL for this song. Returns (url, kind)."""
    search_url = f'https://www.ultimate-guitar.com/search.php?title={title.replace(" ", "+")}&artist={artist.replace(" ", "+")}'
    page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(2000)
    html = page.content()
    # Extract all tab URLs from results
    urls = re.findall(r'https://tabs\.ultimate-guitar\.com/tab/[^"\'\s]+', html)
    # Dedupe, preserve order
    seen, uniq = set(), []
    for u in urls:
        u = u.split('?')[0].split('#')[0]
        if u not in seen:
            seen.add(u); uniq.append(u)
    # Prefer official > chords > tabs > guitar-pro
    def kind(u):
        if '-official-' in u: return ('official', 0)
        if '-chords-'   in u: return ('chords',   1)
        if '-tabs-'     in u: return ('tabs',     2)
        if '-guitar-pro-' in u or '-pro-' in u: return ('guitar-pro', 3)
        return ('other', 4)
    # Trust UG's search (we already passed artist in query); just sort by tab kind preference
    if not uniq: return None, None
    uniq.sort(key=lambda u: kind(u)[1])
    return uniq[0], kind(uniq[0])[0]


def extract_tab_text(page):
    """Find the chord/lyric text. UG embeds it in a JSON data attribute or a <pre>."""
    content = page.content()
    # Method 1: extract from window.UGAPP / store data attribute
    m = re.search(r'"wikiTab":\s*\{.*?"content":\s*"((?:\\.|[^"\\])*)"', content)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')
        except Exception:
            pass
    # Method 2: pre tag
    for sel in ['pre[class*="tab"]', 'pre._3wrCV', 'pre']:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = loc.inner_text(timeout=2000)
                if len(txt) > 100: return txt
        except Exception:
            continue
    return ''


def extract_metadata(page_text):
    """Pull tempo, key, capo, tuning from the page text."""
    meta = {}
    for line in page_text.split('\n')[:80]:
        for k, pat in [('tempo', r'Tempo[:\s]+(\d+)'),
                       ('key',   r'Key[:\s]+([A-G][#b]?m?(?:\s*(?:major|minor|m))?)'),
                       ('capo',  r'Capo[:\s]+(\S[^\n]*)'),
                       ('tuning', r'Tuning[:\s]+([^\n]+)')]:
            m = re.search(pat, line)
            if m: meta.setdefault(k, m.group(1).strip())
    return meta


def main():
    if not os.path.exists(AUTH):
        print(f'no auth at {AUTH} — re-paste cookies first.'); return

    rows = []
    midi_per_song = {}

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=AUTH, user_agent=UA)
        page = ctx.new_page()

        # Network capture for MIDI/GP files (always-on across navigations)
        captured = {}  # current_basename → list of (url, body)
        current_bn = [None]

        def on_response(resp):
            ru = resp.url.lower()
            if any(ext in ru for ext in ['.mid', '.midi', '.gp3', '.gp4', '.gp5', '.gpx']):
                if current_bn[0]:
                    try:
                        body = resp.body()
                        if body and len(body) > 100:
                            captured.setdefault(current_bn[0], []).append((resp.url, body))
                    except Exception: pass
        page.on('response', on_response)

        for i, (title, artist) in enumerate(USER_LIST, 1):
            bn = basename(title, artist)
            current_bn[0] = bn
            print(f'\n[{i}/{len(USER_LIST)}] {title} — {artist}  ({bn})')
            try:
                url, kind = find_best_url(page, title, artist)
                if not url:
                    print(f'  no UG match found'); rows.append({'title':title,'artist':artist,'basename':bn,'status':'no_match'})
                    time.sleep(2); continue
                print(f'  {kind}: {url}')
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(3000)
                # Try to click play / show backing track to trigger MIDI download
                for sel in ['button:has-text("Backing track")', 'button[aria-label*="lay"]', '[class*="play-button"]']:
                    try:
                        btn = page.locator(sel).first
                        if btn.count() > 0 and btn.is_visible(timeout=500):
                            btn.click(timeout=1500); page.wait_for_timeout(2500); break
                    except Exception: pass
                tab_text = extract_tab_text(page)
                if tab_text:
                    open(os.path.join(OUT_DIR, bn + '.txt'), 'w').write(tab_text)
                    meta = extract_metadata(tab_text)
                    print(f'  ✓ tab.txt ({len(tab_text)}b)  {meta}')
                else:
                    print(f'  ✗ no tab text extracted')
                # Save MIDI captures
                midi_count = len(captured.get(bn, []))
                if midi_count:
                    for j, (mu, body) in enumerate(captured[bn]):
                        ext = '.mid'
                        for e in ['.mid','.midi','.gp3','.gp4','.gp5','.gpx']:
                            if e in mu.lower(): ext = e; break
                        fname = f'{bn}{("_"+str(j)) if j else ""}{ext}'
                        open(os.path.join(OUT_DIR, fname), 'wb').write(body)
                    print(f'  ✓ {midi_count} MIDI/GP file(s)')
                rows.append({'title':title,'artist':artist,'basename':bn,'url':url,'kind':kind,
                             'tab_chars':len(tab_text),'midi_count':midi_count})
                time.sleep(3)   # throttle
            except Exception as e:
                print(f'  ERROR: {e}'); rows.append({'title':title,'artist':artist,'basename':bn,'status':f'error:{e}'})
                time.sleep(2)
        browser.close()

    # Write summary
    lines = ['# Guitar 50 — UG scrape summary', f'(ran on {time.strftime("%Y-%m-%d %H:%M")})', '']
    n_official = sum(1 for r in rows if r.get('kind') == 'official')
    n_tab = sum(1 for r in rows if r.get('tab_chars',0) > 100)
    n_midi = sum(1 for r in rows if r.get('midi_count',0) > 0)
    lines.append(f'official URLs: {n_official}/{len(USER_LIST)}')
    lines.append(f'tab text saved: {n_tab}/{len(USER_LIST)}')
    lines.append(f'MIDI/GP saved: {n_midi}/{len(USER_LIST)}')
    lines.append('')
    for r in rows:
        line = f'{r["title"]} — {r["artist"]}'
        if r.get('url'): line += f'\n  {r.get("kind","?")}: {r["url"]}'
        if r.get('tab_chars'): line += f'\n  tab: {r["tab_chars"]}b, midi: {r.get("midi_count",0)}'
        if r.get('status'): line += f'\n  status: {r["status"]}'
        lines.append(line); lines.append('')
    open(SUMMARY, 'w').write('\n'.join(lines))
    print(f'\nsummary → {SUMMARY}')


if __name__ == '__main__':
    main()
