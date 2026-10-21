#!/usr/bin/env python3
"""
Every song in the Hookpad library with one-click YouTube searches for
"<artist> <song> guitar lesson" and "... guitar cover", plus the Hookpad link.

    themap_venv/python build_lessons_page.py      # -> guitar-lessons.html

Same song set as the palette / tempo pages (build_palette_groups.library_files:
not the user's own songs, workbenches or -variants), named from the guitar list
when the song is on one, else from the file.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openpyxl
import build_palette_groups as PG
import build_pool_quiz as Q

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'guitar-lessons.html')


def main():
    files, library, _ = Q.context()
    wb = openpyxl.load_workbook(Q.TRACKER, read_only=True)
    listed = PG.listed_songs(wb, files)
    rows = []
    for path in PG.library_files(files, listed):
        stem = os.path.splitext(os.path.basename(path))[0]
        if path not in listed and '_' not in stem: continue      # no artist = a scratch file (Min3E)
        lst, title, artist = listed.get(path) or (None, *(stem.split('_', 1)[::-1] if '_' in stem else (stem, '')))
        if title == title.lower(): title = Q.title_case(title)
        if artist == artist.lower(): artist = Q.title_case(artist)
        rows.append(dict(t=title.strip(), a=artist.strip(), p=PG.group(lst, stem), l=lst or '',
                         h=Q.hookpad_url(path, library) or ''))
    rows.sort(key=lambda r: (re.sub(r'^the ', '', r['a'].lower()), r['t'].lower()))
    page = open(os.path.join(HERE, 'guitar_lessons_template.html')).read()
    open(OUT, 'w').write(page.replace('__ROWS__', json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
                             .replace('__POOLS__', json.dumps(PG.GROUPS)))
    print(f'{OUT}: {len(rows)} songs, {len({r["a"] for r in rows})} artists')


if __name__ == '__main__':
    main()
