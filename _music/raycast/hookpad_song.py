#!/Users/robert/Desktop/themap/themap_claude/.venv/bin/python
# @raycast.schemaVersion 1
# @raycast.title Hookpad song
# @raycast.mode compact
# @raycast.packageName Music
# @raycast.icon 🎸
# @raycast.argument1 { "type": "text", "placeholder": "song or artist" }
# @raycast.description Focus the open Hookpad tab for a song, or open it in Brave
"""
Type part of a song name, get it in front of you.

Two paths, in this order:
  1. the song is already open in Brave -> focus that tab (no network at all)
  2. it is not open -> resolve name -> numeric ID -> hashid slug, open the URL

Path 1 matters because 40-odd Hookpad tabs are usually already open, and
re-opening a song you have edited would lose the edit.
"""
import json, os, re, subprocess, sys

CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
BRAVE = 'Brave Browser'
sys.path.insert(0, os.path.expanduser('~/Desktop/glowinggardens_claude/_music'))


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def osa(script, *args):
    r = subprocess.run(['/usr/bin/osascript', '-'] + list(args),
                       input=script, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


LIST_TABS = '''
tell application "Brave Browser"
  set out to ""
  repeat with w from 1 to (count windows)
    repeat with t from 1 to (count tabs of window w)
      try
        if (URL of tab t of window w) contains "hookpad" then
          set out to out & w & "\t" & t & "\t" & (title of tab t of window w) & "\n"
        end if
      end try
    end repeat
  end repeat
  return out
end tell
'''


def score(hay, q):
    """Lower is better; None means no match at all."""
    h = norm(hay)
    if not h or q not in h:
        return None
    artist, _, title = hay.partition('_')
    t = norm(title) or h
    if t == q:      return 0        # the title, exactly
    if t.startswith(q): return 1    # the title starts with what you typed
    if h.startswith(q): return 2    # the artist does
    return 3                        # somewhere in there


def open_tabs():
    out, _ = osa(LIST_TABS)
    rows = []
    for line in out.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 3:
            rows.append((int(parts[0]), int(parts[1]), '\t'.join(parts[2:])))
    return rows


def hookpad_window():
    """The window holding the most Hookpad tabs -- i.e. the one in the profile
    that is signed in. None if Hookpad is not open anywhere."""
    counts = {}
    for w, _t, _title in open_tabs():
        counts[w] = counts.get(w, 0) + 1
    return max(counts, key=counts.get) if counts else None


def focus(w, t):
    osa(f'''
tell application "Brave Browser"
  set active tab index of window {w} to {t}
  set index of window {w} to 1
  activate
end tell''')


def main():
    q = norm(' '.join(sys.argv[1:]))
    if not q:
        print('type a few letters'); return 0

    # 1. already open?
    best = None
    for w, t, title in open_tabs():
        # Hookpad appends " - Edited"; it is not part of the song name
        clean = re.sub(r'\s*-\s*Edited\s*$', '', title)
        s = score(clean, q)
        if s is not None and (best is None or s < best[0]):
            best = (s, w, t, clean)
    if best:
        focus(best[1], best[2])
        print(f'{best[3]}  (open)')
        return 0

    # 2. not open: resolve through the song list and open the URL
    if not os.path.exists(CACHE):
        print('not open, and no song-list cache — run '
              'download_one.py --refresh-list')
        return 1
    songs = json.load(open(CACHE))
    hits = []
    for s in songs:
        sc = score(s.get('song', ''), q)
        if sc is not None:
            hits.append((sc, s))
    if not hits:
        print(f'no song matching "{q}"')
        return 1
    hits.sort(key=lambda x: (x[0], x[1].get('song', '')))
    sc, song = hits[0]

    try:
        from download_one import HASHIDS
    except Exception as e:
        print(f'cannot build the slug: {e}')
        return 1
    # the param is idOfUserSong -- idOfSong is a different (public) namespace;
    # taken from drill.py, which is the working reference
    url = f'https://hookpad.hooktheory.com/?idOfUserSong={HASHIDS.encode(int(song["ID"]))}'

    # The song only loads in the Brave profile that is logged in to Hookpad,
    # and four profiles hold hooktheory cookies, so `open -a Brave` lands in
    # whichever window happens to be frontmost and shows "Untitled". Put the
    # tab in the window that already holds Hookpad tabs instead -- that window
    # IS the right profile, with nothing to configure. Window indices shift as
    # windows are activated, so it has to be resolved at call time.
    w = hookpad_window()
    if w is None:
        print(f'{song["song"]}: no Hookpad window open. Open Hookpad once in '
              f'the profile you use for it, then try again.')
        return 1
    osa(f'''
tell application "Brave Browser"
  tell window {w}
    make new tab at end of tabs with properties {{URL:"{url}"}}
    set active tab index to (count tabs)
  end tell
  set index of window {w} to 1
  activate
end tell''')
    extra = f'  (+{len(hits) - 1} more)' if len(hits) > 1 else ''
    print(f'{song["song"]}  (opening){extra}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
