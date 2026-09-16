"""One-time UG login.

Opens a real Chrome window. Log in to ultimate-guitar.com normally.
When done, come back to the terminal and press Enter. Cookies/session are saved
to ~/Desktop/music/.ug_auth.json — used by fetch_ug.py for headless scraping.
"""
import os
from playwright.sync_api import sync_playwright

AUTH_PATH = os.path.expanduser('~/Desktop/.ug_auth.json')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 900},
    )
    page = ctx.new_page()
    page.goto('https://www.ultimate-guitar.com/login')
    print('\n👆 Log in to Ultimate Guitar in the browser window that just opened.')
    print('When you see the homepage / your account is logged in, return here and press Enter.\n')
    input('Press Enter when logged in: ')
    ctx.storage_state(path=AUTH_PATH)
    print(f'✓ saved auth to {AUTH_PATH}')
    browser.close()
