"""Rebuild Beatles-Study.html from all hookpad_songs_full/beatles_*.json files.

Generates a Beatles-Study.html mirror of studied-songs.html (same template, same
rendering, just a different inlined SONGS array). Re-run after any Hookpad sync.
"""

import glob
import json
import os
import re

from rebuild_studied_songs import slim_song

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Beatles-Study.html')


def parse_title(fname):
    """beatles_a hard days night.json → 'a hard days night' (suffixes stripped)."""
    name = os.path.basename(fname).removeprefix('beatles_').removesuffix('.json')
    name = re.sub(r'-(right|Right|RIGHT)$', '', name)
    name = re.sub(r'(_[a-z]{1,3})+_?$', '', name)
    return name.strip()


def richness(d):
    return len(d.get('sections') or []) + len(d.get('chords') or []) + len(d.get('notes') or [])


def main():
    files = sorted(glob.glob(os.path.join(HOOKPAD_DIR, 'beatles_*.json')))

    best = {}  # cleaned-title-lower → (richness, title, filepath, parsed-json)
    for f in files:
        title = parse_title(f)
        try:
            d = json.load(open(f, encoding='utf-8-sig'))
        except Exception:
            continue
        r = richness(d)
        key = title.lower()
        if key not in best or r > best[key][0]:
            best[key] = (r, title, f, d)

    songs_data = []
    for _, title, _, d in sorted(best.values(), key=lambda x: x[1].lower()):
        songs_data.append(slim_song(title, 'The Beatles', d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Beatles Study</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    print(f'{len(songs_data)} Beatles songs → {OUT}')


if __name__ == '__main__':
    main()
