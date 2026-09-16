"""Search HookTheory's TheoryTab database directly via its public Meilisearch API.

The index (`theorytabs`, ~76.6k docs) has one document PER SONG SECTION, each with
full chord data (chordRel = roman, chordAbs = absolute, SInD = scale-degrees),
key, section name, and YouTube id. Faceting/filtering is disabled server-side, so
we search by text and dedupe in Python. Max 1000 hits per query.

Usage:
    hooktheory_search.py "song or artist text"      # search, group by artist
    hooktheory_search.py --artist "Radiohead"       # one artist's song list
    hooktheory_search.py --artist "Radiohead" --chords   # + per-section chords
"""
import sys, re, json, requests
from collections import defaultdict

def _norm_artist(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower().replace('&', 'and'))

HOST = 'https://search.hooktheory.com'
KEY = 'YHXUiQCa6024e2a88cb48f226a94d16db0c20d993e0a424cfde7834b697445bdf280ce88'
INDEX = 'theorytabs'
H = {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'}

def search(q, limit=1000, attrs=None):
    body = {'q': q, 'limit': limit}
    if attrs: body['attributesToRetrieve'] = attrs
    r = requests.post(f'{HOST}/indexes/{INDEX}/search', headers=H, json=body, timeout=30)
    r.raise_for_status()
    return r.json().get('hits', [])

def artist_catalog(artist):
    """All sections HookTheory has for an exact artist -> {song: [sections]}."""
    hits = search(artist, limit=1000)
    a = _norm_artist(artist)
    songs = defaultdict(list)
    for h in hits:
        if _norm_artist(h.get('artist', '')) == a:
            songs[h['song']].append(h)
    return songs

def theorytab_url(artist, song):
    slug = lambda s: __import__('re').sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return f'https://www.hooktheory.com/theorytab/view/{slug(artist)}/{slug(song)}'

if __name__ == '__main__':
    args = sys.argv[1:]
    if '--artist' in args:
        artist = args[args.index('--artist') + 1]
        show_chords = '--chords' in args
        cat = artist_catalog(artist)
        print(f'{artist}: {len(cat)} distinct songs, {sum(len(v) for v in cat.values())} sections\n')
        for song in sorted(cat):
            secs = cat[song]
            key = secs[0].get('key', '?')
            print(f'  {song}  [{key}]  ({len(secs)} sections: {", ".join(s.get("section","?") for s in secs)})')
            if show_chords:
                for s in secs:
                    prog = s.get('chordRel', '').replace('qq', ' ').strip()
                    print(f'      {s.get("section","?"):10} {prog}')
    elif args:
        q = ' '.join(args)
        hits = search(q, limit=1000)
        by_artist = defaultdict(set)
        for h in hits:
            by_artist[h.get('artist', '?')].add(h.get('song', '?'))
        print(f'"{q}": {len(hits)} sections across {len(by_artist)} artists\n')
        for artist in sorted(by_artist, key=lambda a: -len(by_artist[a]))[:25]:
            print(f'  {artist} ({len(by_artist[artist])}): {", ".join(sorted(by_artist[artist])[:8])}')
    else:
        print(__doc__)
