"""Scan the song corpus: reduce each song to its distinct-chord SET (scale-degree
roman tokens, extensions stripped), bucket by set size, rank sets by song count.
Feeds the chord_sets.json naming DB — pick an exemplar per set from the menu.
"""
import os, re, json, psycopg2
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def core(tok):
    """strip extensions/quality-adds -> core roman (keeps b/#, applied /X)."""
    m = re.match(r'^([b#]*[ivxIVX]+(?:/[b#]*[ivxIVX]+)?)', tok)
    return m.group(1) if m else tok

def song_set(hj):
    scale = (hj.get('keys') or [{}])[0].get('scale', 'major')
    scale = scale if scale in ('major', 'minor') else 'major'
    toks = set()
    for c in hj.get('chords') or []:
        r = c.get('root')
        if not r or r < 1 or r > 7:
            continue
        toks.add(core(chord_label(c, scale)))
    return frozenset(toks)

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("""select artist, title, hookpad_json from parcels.songs
        where has_chords and hookpad_json is not null""")
    rows = cur.fetchall(); c.close()

    seen = set()
    by_size = defaultdict(lambda: defaultdict(list))   # size -> set -> [song]
    for artist, title, hj in rows:
        if not title or (title or '').lower().endswith(('-hooktab', '-simple', '-hooktab2')):
            continue                                    # skip variants for the census
        k = norm((artist or '') + (title or ''))
        if k in seen:
            continue
        seen.add(k)
        s = song_set(hj)
        if 1 <= len(s) <= 8:
            by_size[len(s)][s].append(f'{artist} - {title}' if artist else title)

    for size in (2, 3, 4):
        buckets = sorted(by_size[size].items(), key=lambda kv: -len(kv[1]))
        total = sum(len(v) for v in by_size[size].values())
        print(f'\n{"="*70}\n{size}-CHORD SETS  ({len(buckets)} distinct sets across {total} songs)')
        for s, songs in buckets[:18]:
            roman = ' '.join(sorted(s, key=lambda x: (len(x), x)))
            ex = '; '.join(songs[:3])
            print(f'  [{len(songs):>3}]  {{{roman}}}   e.g. {ex[:70]}')

if __name__ == '__main__':
    main()
