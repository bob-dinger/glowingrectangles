"""Hands-off UG login: opens a browser, waits for a REAL login, auto-saves auth.

Detects login by watching for a genuine session cookie (httpOnly, non-analytics),
not tracking/Cloudflare cookies. Writes ~/Desktop/.ug_auth.json then exits.
Only saves on a real login signal (never on timeout).
"""
import os, time
from playwright.sync_api import sync_playwright

AUTH = os.path.expanduser('~/Desktop/.ug_auth.json')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def is_junk(name):
    n = name.lower()
    return (n.startswith('_') or 'cf' in n or n in ('test_cookie',) or n.startswith('__cf')
            or n.startswith('_ga') or n.startswith('_gcl') or n == '_gid' or n == '_fbp')

def auth_cookies(cookies):
    # real session cookies: httpOnly + not analytics/CF + reasonably named
    return [c for c in cookies if c.get('httpOnly') and not is_junk(c['name'])]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(user_agent=UA, viewport={'width': 1280, 'height': 900})
    page = ctx.new_page()
    page.goto('https://www.ultimate-guitar.com/login', wait_until='domcontentloaded')
    time.sleep(3)
    base_auth = {c['name'] for c in auth_cookies(ctx.cookies())}
    print('WAITING: log in to Ultimate Guitar in the browser window...', flush=True)

    deadline = time.time() + 600          # 10 min
    saved = False
    last_report = 0
    while time.time() < deadline:
        time.sleep(3)
        try:
            cookies = ctx.cookies(); url = page.url
        except Exception:
            print('browser closed before login detected', flush=True); break
        now_auth = {c['name'] for c in auth_cookies(cookies)}
        new = now_auth - base_auth
        if time.time() - last_report > 20:
            print(f'  ...still waiting (url={url[:40]}, session-cookies={sorted(now_auth)[:5]})', flush=True)
            last_report = time.time()
        # real login = a genuine session cookie appeared AND off the login page
        if new and 'login' not in url and 'ultimate-guitar.com' in url:
            time.sleep(4)
            ctx.storage_state(path=AUTH)
            print(f'SAVED auth -> {AUTH}  (session cookies: {sorted(new)})', flush=True)
            saved = True
            break

    if not saved:
        print('TIMED OUT — no real login detected. Nothing saved.', flush=True)
    browser.close()
