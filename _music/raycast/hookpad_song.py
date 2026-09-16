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
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/Desktop/glowinggardens_claude/_music'))
import brave_tabs as bt

CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
HOOKPAD = 'hookpad'


def main():
    q = bt.norm(' '.join(sys.argv[1:]))
    if not q:
        print('type a few letters'); return 0

    # 1. already open?
    best = None
    for w, t, title in bt.tabs_matching(HOOKPAD):
        # Hookpad appends " - Edited"; it is not part of the song name
        clean = re.sub(r'\s*-\s*Edited\s*$', '', title)
        s = bt.score(clean, q)
        if s is not None and (best is None or s < best[0]):
            best = (s, w, t, clean)
    if best:
        bt.focus(best[1], best[2])
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
        sc = bt.score(s.get('song', ''), q)
        if sc is None:
            continue
        # a pool song outranks an identically-scoring stranger: "malibu" is
        # hole_malibu (G50), not miley cyrus_malibu
        if bt.pooled(s.get('song', '')):
            sc -= 5
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
    w = bt.window_with_most(HOOKPAD)
    if w is None:
        print(f'{song["song"]}: no Hookpad window open. Open Hookpad once in '
              f'the profile you use for it, then try again.')
        return 1
    bt.new_tab(w, url)
    extra = f'  (+{len(hits) - 1} more)' if len(hits) > 1 else ''
    print(f'{song["song"]}  (opening){extra}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
