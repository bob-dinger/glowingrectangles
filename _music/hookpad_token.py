#!/usr/bin/env python3
"""
Grab a live Hookpad bearer token, so no session starts with DevTools.

Hookpad's API wants `Authorization: Bearer <token>`, and the documented way to
get one is to open DevTools on a Hookpad tab, find an API call and copy it as
cURL. That is a manual step at the front of every sync. This does it instead:
load Hookpad in the Playwright context that already has saved auth, watch the
requests it makes, and lift the header off the first API call.

    python3 hookpad_token.py              # write ~/.hookpad_token, print it
    python3 hookpad_token.py --quiet      # write it, print nothing
    python3 hookpad_token.py --show       # print the token only, no file

The token goes to ~/.hookpad_token with mode 600. It is a credential: keep it
out of the repo and out of any file the site serves.

If the saved auth has expired, run setup_hookpad_auth.py to log in once more.
"""
import argparse, os, sys, time

from playwright.sync_api import sync_playwright

STATE = os.path.expanduser('~/.hookpad_auth.json')
OUT = os.path.expanduser('~/.hookpad_token')
URL = 'https://hookpad.hooktheory.com'


def grab(timeout=45.0, headed=False):
    """-> token string, or None. Watches requests for an Authorization header."""
    found = []

    def on_request(r):
        if found:
            return
        # any hooktheory request carrying a bearer will do; the app sends the
        # same token to /v1/songs, /v1/users and the trends endpoints
        if 'hooktheory.com' not in r.url:
            return
        auth = (r.headers or {}).get('authorization') or ''
        if auth.lower().startswith('bearer ') and len(auth) > 20:
            found.append(auth.split(None, 1)[1].strip())

    with sync_playwright() as p:
        b = p.chromium.launch(headless=not headed)
        ctx = b.new_context(storage_state=STATE if os.path.exists(STATE) else None)
        pg = ctx.new_page()
        pg.on('request', on_request)
        try:
            pg.goto(URL, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            print(f'could not load Hookpad: {e}', file=sys.stderr)
        # the app fires its first authenticated call a beat after load
        end = time.time() + timeout
        while not found and time.time() < end:
            pg.wait_for_timeout(400)
        b.close()
    return found[0] if found else None


def read_saved():
    """The token other scripts should use, or None."""
    for src in (os.environ.get('HOOKPAD_TOKEN'),
                open(OUT).read().strip() if os.path.exists(OUT) else None):
        if src and src.strip():
            return src.strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true', help='write the file, print nothing')
    ap.add_argument('--show', action='store_true', help='print the token, write no file')
    ap.add_argument('--headed', action='store_true',
                    help='show the browser (use when the saved auth has expired)')
    ap.add_argument('--timeout', type=float, default=45.0)
    a = ap.parse_args()

    tok = grab(timeout=a.timeout, headed=a.headed)
    if not tok:
        print('no token seen. The saved auth at ~/.hookpad_auth.json has most '
              'likely expired — run setup_hookpad_auth.py to log in again, or '
              'try --headed to watch what happens.', file=sys.stderr)
        return 1

    if a.show:
        print(tok)
        return 0

    with open(OUT, 'w') as f:
        f.write(tok + '\n')
    os.chmod(OUT, 0o600)            # a credential, not a config value
    if not a.quiet:
        print(f'{tok[:8]}…{tok[-4:]}  ({len(tok)} chars) -> {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
