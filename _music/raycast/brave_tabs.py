#!/usr/bin/env python3
"""
Brave tab helpers, shared by the Raycast song commands.

The thing worth knowing: a logged-in site only works in the Brave PROFILE that
holds its session, and AppleScript cannot report which profile a window
belongs to. Cookies do not settle it either — four of ten profiles hold
hooktheory cookies, several hold ultimate-guitar ones. So never use
`open -a "Brave Browser"`, which lands in whatever window is frontmost and
silently shows a logged-out page.

Instead put the new tab in a window that already has a tab for that site. That
window IS the signed-in profile, with nothing to configure and nothing that
can drift out of sync. Window indices shift as windows get activated, so the
window has to be resolved on every call.
"""
import functools
import json
import os
import re
import subprocess

MUSIC = os.path.expanduser('~/Desktop/glowinggardens_claude/_music')


def osa(script):
    r = subprocess.run(['/usr/bin/osascript', '-'], input=script,
                       capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def tabs_matching(url_substr):
    """-> [(window_index, tab_index, title), ...] for tabs whose URL contains it."""
    out, _ = osa(f'''
tell application "Brave Browser"
  set out to ""
  repeat with w from 1 to (count windows)
    repeat with t from 1 to (count tabs of window w)
      try
        if (URL of tab t of window w) contains "{url_substr}" then
          set out to out & w & "\t" & t & "\t" & (title of tab t of window w) & "\n"
        end if
      end try
    end repeat
  end repeat
  return out
end tell''')
    rows = []
    for line in out.split('\n'):
        p = line.split('\t')
        if len(p) >= 3:
            rows.append((int(p[0]), int(p[1]), '\t'.join(p[2:])))
    return rows


def window_with_most(url_substr):
    """The window holding the most tabs for that site — i.e. the signed-in
    profile. None if the site is not open anywhere."""
    counts = {}
    for w, _t, _title in tabs_matching(url_substr):
        counts[w] = counts.get(w, 0) + 1
    return max(counts, key=counts.get) if counts else None


def focus(w, t):
    osa(f'''
tell application "Brave Browser"
  set active tab index of window {w} to {t}
  set index of window {w} to 1
  activate
end tell''')


def new_tab(w, url):
    osa(f'''
tell application "Brave Browser"
  tell window {w}
    make new tab at end of tabs with properties {{URL:"{url}"}}
    set active tab index to (count tabs)
  end tell
  set index of window {w} to 1
  activate
end tell''')


def score(hay, q):
    """How well `hay` ('artist_title' or a tab title) matches query q.
    Lower is better; None means no match."""
    h = norm(hay)
    if not h or q not in h:
        return None
    _artist, _, title = hay.partition('_')
    t = norm(title) or h
    if t == q:          return 0     # the title, exactly
    if t.startswith(q): return 1     # the title starts with what you typed
    if h.startswith(q): return 2     # the artist does
    return 3                         # somewhere in there


@functools.lru_cache(maxsize=1)
def pool_keys():
    """Normalised 'artist_title' keys for every song in a guitar pool.

    Needed as a tiebreak: "malibu" matches both hole_malibu (which is in G50,
    the one being learned) and miley cyrus_malibu equally well, so without
    this it comes down to file order. What is in a pool is what the user is
    working on, so it wins.
    """
    try:
        import sys
        sys.path.insert(0, MUSIC)
        import pao_pools as pp
        pm = json.load(open(pp.POOLS))
        return frozenset(pp.norm(pp.strip_tags(s)) for s in pm)
    except Exception:
        return frozenset()


def pooled(name):
    """Is this 'artist_title' one of the pool songs?"""
    return norm(name) in pool_keys()
