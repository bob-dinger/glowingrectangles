"""Fetch a UG tab (including Pro+ official tabs + MIDI if available) using saved auth.

Requires: ~/Desktop/music/.ug_auth.json (run ug_login.py first).

Usage:
    python fetch_ug.py <UG_URL>                              # auto-derive basename
    python fetch_ug.py <UG_URL> --basename <slug-basename>   # explicit name
    python fetch_ug.py <UG_URL> --visible                    # show browser (debug)

Saves to ~/Desktop/music/ug_tabs/:
    {basename}.txt      tab text (chord + lyric lines)
    {basename}.mid      MIDI file if found
    {basename}.html     full page HTML (debug, only if --visible)
"""
import os, re, sys, json
from playwright.sync_api import sync_playwright

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
OUT_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
os.makedirs(OUT_DIR, exist_ok=True)


def derive_basename(url):
    """https://tabs.ultimate-guitar.com/tab/hole/malibu-official-2278851 → 'hole_malibu'"""
    m = re.search(r'/tab/([^/]+)/([^/?#]+)', url)
    if not m: return 'song'
    artist = m.group(1).replace('-', ' ').strip()
    song = m.group(2)
    # Strip trailing -official-NNNN / -chords-NNNN / -tabs-NNNN
    song = re.sub(r'-(official|chords|tabs|pro|guitar-pro)?-?\d+$', '', song).replace('-', ' ').strip()
    return f'{artist}_{song}'.lower()


def extract_tab_text(page):
    """Find the chord/lyric pre block. UG renders tab text in a <pre> inside a known container."""
    # Try several known selectors
    for sel in ['pre._3wrCV', 'pre[class*="tab"]', 'pre', 'div._3WSCh pre']:
        loc = page.locator(sel).first
        if loc.count() > 0:
            try:
                txt = loc.inner_text(timeout=2000)
                if len(txt) > 100: return txt
            except Exception:
                continue
    # Fallback: look in JSON data attributes (UG sometimes embeds tab data here)
    content = page.content()
    m = re.search(r'"wikiTab":\s*\{[^}]*"content":\s*"([^"]+)"', content)
    if m:
        # Unescape JSON-encoded text
        return json.loads(f'"{m.group(1)}"')
    return ''


def main():
    args = sys.argv[1:]
    visible = '--visible' in args; args = [a for a in args if a != '--visible']
    basename = None
    if '--basename' in args:
        i = args.index('--basename'); basename = args[i+1]; args = args[:i] + args[i+2:]
    if not args:
        print('usage: fetch_ug.py <URL> [--basename NAME] [--visible]'); sys.exit(1)
    url = args[0]
    if not basename: basename = derive_basename(url)
    print(f'basename: {basename}')

    if not os.path.exists(AUTH):
        print(f'No auth file at {AUTH}. Run ug_login.py first.'); sys.exit(1)

    midi_blobs = []
    interesting_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible)
        ctx = browser.new_context(
            storage_state=AUTH,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = ctx.new_page()

        # Capture network responses for MIDI / audio / .mid / .gp* files
        def on_response(resp):
            ru = resp.url.lower()
            if any(ext in ru for ext in ['.mid', '.midi', '.gp3', '.gp4', '.gp5', '.gpx', '.gp']):
                try:
                    body = resp.body()
                    if body and len(body) > 100:
                        midi_blobs.append((resp.url, body))
                        print(f'  captured MIDI/GP: {resp.url[:80]} ({len(body)} bytes)')
                except Exception:
                    pass
            elif any(t in ru for t in ['midi', 'audio_url', 'tab_view', 'tab_pro']):
                interesting_urls.append(resp.url)
        page.on('response', on_response)

        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(5000)  # let JS load + audio init

        # If page redirected to a paywall (-/pro/), bail with diagnostic
        if '/pro/' in page.url and '/tab/' not in page.url:
            print(f'⚠ redirected to paywall: {page.url}')
            print('  This means UG isn\'t recognizing the session as Pro+. Re-run ug_login.py.')
        else:
            print(f'final URL: {page.url}')

        # Save HTML for debugging
        if visible:
            open(os.path.join(OUT_DIR, basename + '.html'), 'w').write(page.content())

        # Extract tab text
        tab_text = extract_tab_text(page)
        if tab_text:
            open(os.path.join(OUT_DIR, basename + '.txt'), 'w').write(tab_text)
            print(f'✓ saved {basename}.txt  ({len(tab_text)} chars)')
        else:
            print(f'✗ no tab text found')

        # Try to trigger MIDI player by clicking "Play" if present (some pages lazy-load MIDI)
        for play_sel in ['button[aria-label*="lay"]', 'button:has-text("Play")', '[class*="play-button"]']:
            try:
                btn = page.locator(play_sel).first
                if btn.count() > 0 and btn.is_visible(timeout=1000):
                    btn.click(timeout=2000)
                    print(f'  clicked play: {play_sel}')
                    page.wait_for_timeout(3000)
                    break
            except Exception:
                pass

        browser.close()

    # Save any captured MIDI
    if midi_blobs:
        for i, (u, body) in enumerate(midi_blobs):
            ext = '.mid'
            for e in ['.mid', '.midi', '.gp3', '.gp4', '.gp5', '.gpx', '.gp']:
                if e in u.lower(): ext = e; break
            fname = f'{basename}{"_"+str(i) if i else ""}{ext}'
            open(os.path.join(OUT_DIR, fname), 'wb').write(body)
            print(f'✓ saved {fname}  ({len(body)} bytes)')
    else:
        print('no MIDI/GP captured.')
        if interesting_urls:
            print(f'  but saw these interesting URLs (might be audio/MIDI sources):')
            for u in interesting_urls[:5]: print(f'    {u}')


if __name__ == '__main__':
    main()
