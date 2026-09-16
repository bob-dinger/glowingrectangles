#!/Users/robert/Desktop/themap/themap_claude/.venv/bin/python
"""
Type part of a song name, get its Ultimate Guitar tab open in Brave.

Three paths, in order:
  1. a UG tab for it is already open  -> focus that tab, no network
  2. it is in the local official-tabs catalog -> open the tab URL directly
  3. not in the catalog -> open a UG search for it

The catalog (24,840 official tabs: title, artist, url) was scraped by
scrape_ug_all_official.py. It lives in a dated archive folder that has moved
once already, so it is located by glob with the newest winning, rather than
hardcoded.

Artist comes from the Hookpad song list where possible — typing "wonderwall"
resolves to oasis_wonderwall, which makes both the catalog lookup and the
search fall on the right song instead of a cover.
"""
import csv
import glob
import re
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brave_tabs as bt

HOOKPAD_LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
CATALOGS = [
    os.path.expanduser('~/Desktop/music/ug_all_official.csv'),
    *sorted(glob.glob(os.path.expanduser('~/Desktop/dates/*/ug_all_official.csv')),
            key=os.path.getmtime, reverse=True),
    os.path.expanduser('~/Desktop/ug_all_official.csv'),
]
UG = 'ultimate-guitar.com'


def tidy(title):
    """UG tab titles are shouty boilerplate: "(1) OFFICIAL MALIBU CHORDS &
    TABS by Hole @ Ultimate-Guitar.Com". Keep the song and the artist."""
    t = re.sub(r'^\(\d+\)\s*', '', title)
    t = re.sub(r'\s*@\s*Ultimate-Guitar\.Com.*$', '', t, flags=re.I)
    t = re.sub(r'\bOFFICIAL\s+', '', t, flags=re.I)
    t = re.sub(r'\s+(CHORDS|TABS|TAB)(\s*&\s*(CHORDS|TABS|TAB))*\b', '', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return t or title


def catalog():
    for p in CATALOGS:
        if os.path.exists(p):
            with open(p, newline='') as f:
                return p, list(csv.DictReader(f))
    return None, []


def hookpad_artist_title(q):
    """-> (artist, title) from the Hookpad library, or (None, None)."""
    if not os.path.exists(HOOKPAD_LIST):
        return None, None
    best = None
    for s in json.load(open(HOOKPAD_LIST)):
        name = s.get('song', '')
        sc = bt.score(name, q)
        if sc is None:
            continue
        # a pool song outranks an identically-scoring stranger
        if bt.pooled(name):
            sc -= 5
        if best is None or sc < best[0]:
            best = (sc, name)
    if not best:
        return None, None
    artist, _, title = best[1].partition('_')
    return (artist or None), (title or None)


def main():
    q = bt.norm(' '.join(sys.argv[1:]))
    if not q:
        print('type a few letters'); return 0

    # 1. already open?
    best = None
    for w, t, title in bt.tabs_matching(UG):
        sc = bt.score(title, q)
        if sc is not None and (best is None or sc < best[0]):
            best = (sc, w, t, title)
    if best:
        bt.focus(best[1], best[2])
        print(f'{tidy(best[3])}  (open)')
        return 0

    artist, title = hookpad_artist_title(q)

    # 2. in the local catalog?
    path, rows = catalog()
    hits = []
    for r in rows:
        hay = f"{r.get('artist','')}_{r.get('title','')}"
        sc = bt.score(hay, q)
        if sc is None:
            continue
        # a known artist breaks ties between covers of the same title
        if artist and bt.norm(r.get('artist', '')) == bt.norm(artist):
            sc -= 10
        hits.append((sc, r))

    if hits:
        hits.sort(key=lambda x: (x[0], x[1].get('artist', '')))
        sc, r = hits[0]
        url = r['url']
        label = f"{r.get('artist','?')} — {r.get('title','?')}"
    elif title:
        url = ('https://www.ultimate-guitar.com/search.php?'
               + urllib.parse.urlencode({'title': title, 'artist': artist or ''}))
        label = f'search: {title}' + (f' / {artist}' if artist else '')
    else:
        url = ('https://www.ultimate-guitar.com/search.php?'
               + urllib.parse.urlencode({'title': ' '.join(sys.argv[1:])}))
        label = f"search: {' '.join(sys.argv[1:])}"

    # UG is only logged in on one Brave profile, and `open -a Brave` would land
    # in whatever window is frontmost — so reuse a window that already has UG.
    w = bt.window_with_most(UG)
    if w is None:
        print(f'{label}: no Ultimate Guitar window open. Open UG once in the '
              f'profile you use for it, then try again.')
        return 1
    bt.new_tab(w, url)
    extra = f'  (+{len(hits) - 1} more)' if len(hits) > 1 else ''
    print(f'{label}{extra}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
