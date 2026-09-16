"""Open one or more songs in Hookpad via Playwright's bundled Chromium.

Usage:
    python open_in_hookpad.py "wide awake"
    python open_in_hookpad.py "wide awake" "roar" "birthday"

Uses Playwright's Chromium with a saved auth state at ~/.hookpad_auth.json.
Completely separate from Brave — your Brave is never touched.

First-time setup: run `python setup_hookpad_auth.py` to log in once.

Browser stays open until you close it. Script exits cleanly when the window closes.
"""
import os, sys, time
from playwright.sync_api import sync_playwright

STATE = os.path.expanduser("~/.hookpad_auth.json")
HOOKPAD_URL = "https://hookpad.hooktheory.com"


def open_song_in_tab(ctx, song_name, first_tab=False):
    """Open Hookpad in a new tab and load the given song."""
    page = ctx.pages[0] if first_tab and ctx.pages else ctx.new_page()
    page.bring_to_front()
    page.goto(HOOKPAD_URL, wait_until="domcontentloaded")
    page.wait_for_selector("button.button-menu[title*='open']", state="visible", timeout=20000)
    page.wait_for_timeout(2000)
    page.mouse.click(20, 200)
    page.wait_for_timeout(500)
    page.locator("button.button-menu[title*='open']").first.click()
    page.wait_for_timeout(600)
    page.locator(".popper-file >> :text-is('Open')").first.click()
    page.wait_for_timeout(2000)
    page.keyboard.type(song_name)
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    return page.title() or "(unknown)"


def main():
    songs = sys.argv[1:]
    if not songs:
        print("usage: open_in_hookpad.py <song-name> [<song-name> ...]")
        sys.exit(1)
    if not os.path.exists(STATE):
        print(f"No saved auth at {STATE}")
        print("→ Run `python setup_hookpad_auth.py` first to log in once.")
        sys.exit(1)

    print(f"opening {len(songs)} song(s) in Hookpad (Playwright Chromium)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=1600,1000"],
        )
        ctx = browser.new_context(storage_state=STATE, no_viewport=True)

        for i, song in enumerate(songs):
            print(f"  [{i+1}/{len(songs)}] {song} ...", end=" ", flush=True)
            try:
                loaded = open_song_in_tab(ctx, song, first_tab=(i == 0))
                print(f"loaded: {loaded!r}", flush=True)
            except Exception as e:
                print(f"FAILED: {e}", flush=True)

        print(f"\nall {len(songs)} song(s) opened. Close the Chromium window to exit.")
        try:
            while ctx.pages:
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            try: ctx.close()
            except Exception: pass
            try: browser.close()
            except Exception: pass


if __name__ == "__main__":
    main()
