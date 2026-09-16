"""One-time: log in to Hookpad in Playwright's Chromium and save the auth state.

Run this ONCE (or whenever your Hookpad session expires). A Chromium window opens,
loads Hookpad — log in there. When done, press Enter in this terminal. Your auth
state (cookies + localStorage) gets saved to ~/.hookpad_auth.json and reused by
future `open_in_hookpad.py` runs.

This script uses a temporary in-memory context, so no lock files / profile state get
left behind. Clean isolation from your Brave.
"""
import os
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
        input("[press Enter when you're logged in]")
        ctx.storage_state(path=STATE)
        ctx.close()
        browser.close()

    print(f"\n✓ Auth state saved to {STATE}")
    print("Now you can run: python open_in_hookpad.py 'wide awake' ...")


if __name__ == "__main__":
    main()
