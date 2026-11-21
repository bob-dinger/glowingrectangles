"""One-time: log in to Hookpad in Playwright's Chromium and save the auth state.

Run this ONCE (or whenever your Hookpad session expires). A Chromium window opens,
loads Hookpad — log in there. When done, press Enter in this terminal. Your auth
state (cookies + localStorage) gets saved to ~/.hookpad_auth.json and reused by
future `open_in_hookpad.py` runs.

This script uses a temporary in-memory context, so no lock files / profile state get
left behind. Clean isolation from your Brave.
"""
import os, sys, time
from playwright.sync_api import sync_playwright

STATE = os.path.expanduser("~/.hookpad_auth.json")


def main():
    print("Opening Chromium. Log in to Hookpad in the window.")
    print("When you're logged in (and you can see your projects), come back here")
    print("and press Enter — that captures your auth state.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--window-size=1400,900"])
        ctx = browser.new_context(no_viewport=True)
        page = ctx.new_page()
        page.goto("https://hookpad.hooktheory.com")
        if sys.stdin.isatty():
            input("[press Enter when you're logged in]")
        else:
            # no keyboard (Claude Code's ! prompt, or run in the background): save
            # the login every few seconds and log what the app asks the API, so
            # whoever started this can test the saved login and stop it when good
            def on_response(r):
                if 'hooktheory.com' in r.url and r.request.resource_type in ('xhr', 'fetch'):
                    print(f'  {r.status} {r.request.method} {r.url[:110]}', flush=True)
            ctx.on('response', on_response)
            print('[saving the login every 5s for 15 minutes]', flush=True)
            end = time.time() + 900
            while time.time() < end:
                ctx.pages[0].wait_for_timeout(5000) if ctx.pages else time.sleep(5)
                ctx.storage_state(path=STATE)
        ctx.storage_state(path=STATE)
        ctx.close()
        browser.close()

    print(f"\n✓ Auth state saved to {STATE}")
    print("Now you can run: python open_in_hookpad.py 'wide awake' ...")


if __name__ == "__main__":
    main()
