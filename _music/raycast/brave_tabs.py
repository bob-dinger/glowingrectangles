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

When the site is not open anywhere there is no window to borrow, so the
profile has to be named outright — `--profile-directory`. Which one is
answered by visit history rather than cookies: the profile actually used has
hundreds of visits to the site, the rest have one or two.
"""
import functools
import json
import os
import re
import sqlite3
import subprocess
import urllib.parse

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


def raise_window(w):
    """Bring a window forward without changing which tab is active."""
    osa(f'''
tell application "Brave Browser"
  set index of window {w} to 1
  activate
end tell''')


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


BRAVE = os.path.expanduser(
    '~/Library/Application Support/BraveSoftware/Brave-Browser')


def profile_dirs():
    """Every profile directory name, as `--profile-directory` wants it.

    Read from Local State rather than globbed, because the names are not all
    `Profile N` — one of them is literally `hookpad`."""
    try:
        state = json.load(open(os.path.join(BRAVE, 'Local State')))
        return list(state['profile']['info_cache'].keys())
    except Exception:
        return ['Default'] + [f'Profile {i}' for i in range(1, 10)]


@functools.lru_cache(maxsize=8)
def profile_for(url_substr):
    """The profile signed in to a site, decided by how much it has been used.

    Cookie presence does not settle this — four profiles hold hooktheory
    cookies and five hold ultimate-guitar ones, mostly from a stray visit
    years ago. Visits are lopsided in a way cookies are not: Profile 3 has
    428 hookpad visits and 501 UG ones, every other profile has at most five.

    The History file is locked while Brave runs; opening it `immutable=1`
    reads it in place without a copy and without touching the lock.
    """
    best = None
    for name in profile_dirs():
        path = os.path.join(BRAVE, name, 'History')
        if not os.path.exists(path):
            continue
        try:
            con = sqlite3.connect(
                'file:' + urllib.parse.quote(path) + '?immutable=1', uri=True)
            n, last = con.execute(
                'select count(*), max(last_visit_time) from urls '
                'where url like ?', (f'%{url_substr}%',)).fetchone()
            con.close()
        except Exception:
            continue
        if n and (best is None or (n, last or 0) > (best[1], best[2])):
            best = (name, n, last or 0)
    return best[0] if best else None


def profile_names():
    """-> {directory: display name}. The two differ, and confusingly: the
    directory `hookpad` is displayed as "Personal", while `Profile 9` is the
    one displayed as "hookpad"."""
    try:
        state = json.load(open(os.path.join(BRAVE, 'Local State')))
        return {k: v.get('name', k)
                for k, v in state['profile']['info_cache'].items()}
    except Exception:
        return {}


def resolve_profile(name):
    """A profile directory from whatever the user typed — "robert", "adam",
    "glowing gardens", or the directory name itself."""
    q = norm(name)
    if not q:
        return None
    names = profile_names()
    for want in (lambda d, n: norm(d) == q or norm(n) == q,
                 lambda d, n: norm(n).startswith(q) or norm(d).startswith(q),
                 lambda d, n: q in norm(n) or q in norm(d)):
        for d, n in names.items():
            if want(d, n):
                return d
    return None


def running_profiles():
    """Which profiles have a browser window right now.

    Brave keeps an open file handle on a running profile's `Sessions`
    directory, so lsof on the main browser process answers this directly —
    nothing else does. Profiles that merely exist on disk do not show up.
    """
    try:
        pids = subprocess.run(['/usr/bin/pgrep', '-x', 'Brave Browser'],
                              capture_output=True, text=True).stdout.split()
        if not pids:
            return set()
        out = subprocess.run(['/usr/sbin/lsof', '-p', ','.join(pids[:4])],
                             capture_output=True, text=True).stdout
    except Exception:
        return set()
    return set(re.findall(r'Brave-Browser/([^/]+)/Sessions', out))


def window_profile_map():
    """-> {window index: profile directory}.

    AppleScript cannot report which profile a window belongs to, so the tabs
    answer it instead: a window's URLs are in its own profile's history and
    generally in no other. Only running profiles are candidates, which keeps
    this to a couple of queries and stops a stale history from winning.
    """
    running = running_profiles()
    if not running:
        return {}
    out, _ = osa('''
tell application "Brave Browser"
  set o to ""
  repeat with w from 1 to (count windows)
    repeat with t from 1 to (count tabs of window w)
      try
        set o to o & w & "\t" & (URL of tab t of window w) & "\n"
      end try
    end repeat
  end repeat
  return o
end tell''')
    wins = {}
    for line in out.split('\n'):
        parts = line.split('\t')
        if len(parts) == 2 and parts[1].startswith('http'):
            wins.setdefault(int(parts[0]), []).append(parts[1])

    mapping = {}
    for w, urls in wins.items():
        sample = urls[:8]
        best, best_n = None, 0
        for prof in running:
            path = os.path.join(BRAVE, prof, 'History')
            if not os.path.exists(path):
                continue
            try:
                con = sqlite3.connect(
                    'file:' + urllib.parse.quote(path) + '?immutable=1',
                    uri=True)
                n = sum(bool(con.execute('select 1 from urls where url=? limit 1',
                                         (u,)).fetchone()) for u in sample)
                con.close()
            except Exception:
                continue
            if n > best_n:
                best, best_n = prof, n
        if best:
            mapping[w] = best
    return mapping


def window_for_profile(profile):
    """The window belonging to a profile, or None if it has none open."""
    for w, prof in window_profile_map().items():
        if prof == profile:
            return w
    return None


def open_in_profile(profile, url=None):
    """Start a named profile — the window Brave has not got open yet.

    Brave forwards the command line to the instance already running, so this
    does not start a second browser, and the profile comes back with its whole
    restored session."""
    args = ['/usr/bin/open', '-na', 'Brave Browser', '--args',
            f'--profile-directory={profile}']
    subprocess.run(args + ([url] if url else []))


def open_profile(name, url=None):
    """Put a profile in front of the user, opening it if it is not running.

    -> (profile directory, 'focused'|'opened'), or None if the name matches no
    profile. Focusing matters: launching a profile that already has a window
    gives you a second one rather than the one you meant."""
    profile = resolve_profile(name)
    if profile is None:
        return None
    w = window_for_profile(profile)
    if w is not None:
        new_tab(w, url) if url else raise_window(w)
        return profile, 'focused'
    open_in_profile(profile, url)
    return profile, 'opened' 


def open_url(url_substr, url):
    """Put a URL in front of the user in the profile that can actually load it.

    Borrow a window that already has the site if there is one — that window IS
    the right profile, and the tab lands next to the others. Otherwise name
    the profile explicitly. Returns what it did, or None if the site has never
    been visited in any profile.
    """
    w = window_with_most(url_substr)
    if w is not None:
        new_tab(w, url)
        return 'tab'
    profile = profile_for(url_substr)
    if profile is None:
        return None
    # the profile may be running with the site simply not open in it, in which
    # case the tab belongs in the window it already has
    open_profile(profile, url)
    return profile


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
