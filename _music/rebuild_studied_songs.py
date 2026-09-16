"""Rebuild studied-songs.html with current Hookpad data for the 50-song list.

Run after any Hookpad sync to refresh the inlined data:

    sync_hookpad.py --token ... --throttle 15
    rebuild_studied_songs.py
"""

import glob
import json
import os
import re

USER_LIST = [
    ("margaritaville", "jimmy buffett"),
    ("nineteen", "the old 97's"),
    ("fire escape", "fastball"),
    ("have you ever seen the rain", "ccr"),
    ("somewhere only we know", "keane"),
    ("mainstreet", "bob seger"),
    ("sister golden hair", "america"),
    ("More than a Feeling", "Boston"),
    ("louisiana Saturday night", "mel mcdaniel"),
    ("john deere green", "joe diffie"),
    ("Texas Time Travelin", "Cory Morrow"),
    ("nashville blues", "Cory Morrow"),
    ("won't back down", "tom petty"),
    ("little talks", "of monsters and men"),
    ("1979", "the smashing pumpkins"),
    ("island in the sun", "weezer"),
    ("under the bridge", "rhcp"),
    ("Interstate Love Song", "Stone Temple Pilots"),
    ("don't look back in anger", "oasis"),
    ("losing my religion", "rem"),
    ("she's in love with the boy", "trisha yearwood"),
    ("superposition", "young the giant"),
    ("10000 emerald pools", "borns"),
    ("maggie may", "rod stewart"),
    ("sunny came home", "shawn colvin"),
    ("heaven is a place on earth", "belinda carlisle"),
    ("my happiness", "powderfinger"),
    ("Ship to Wreck", "florence and the machine"),
    ("my friends", "Red Hot Chili Peppers"),
    ("pretty woman", "roy orbison"),
    ("proud mary", "ccr"),
    ("it ain't me", "kygo"),
    ("Lo Hi", "The Black Keys"),
    ("The Universal", "Blur"),
    ("a higher place", "tom petty"),
    ("wonderwall", "oasis"),
    ("Friday night blues", "john conlee"),
    ("Shadow Of The Day", "Linkin Park"),
    ("Small Town Saturday Night", "Hal Ketchum"),
    ("neon moon", "brooks and dunn"),
    ("smells like teen spirit", "nirvana"),
    ("I want it that way", "backstreet boys"),
    ("found out about you", "gin blossoms"),
    ("heads carolina tails california", "jo dee messina"),
    ("if it makes you happy", "sheryl crow"),
    ("my favorite mistake", "sheryl crow"),
    ("Malibu", "Hole"),
    ("imitation of life", "rem"),
    ("no rain", "blind melon"),
    ("Blue On Black", "Kenny Wayne Shepherd"),
]

ARTIST_ALIASES = {'rhcp': 'redhotchilipeppers', 'ccr': 'creedence'}
HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')


def norm(s):
    s = (s or '').lower().strip()
    if s.startswith('the '):
        s = s[4:]
    return re.sub(r'[^a-z0-9]', '', s)


def best_match(title, artist, all_files):
    tn = norm(title)
    an_options = [norm(artist)]
    if an_options[0] in ARTIST_ALIASES:
        an_options.append(ARTIST_ALIASES[an_options[0]])
    scored = []
    for f in all_files:
        bn = norm(os.path.basename(f))
        if tn not in bn:
            continue
        try:
            d = json.load(open(f, encoding='utf-8-sig'))
        except Exception:
            continue
        nc = len(d.get('chords') or [])
        ns = len(d.get('sections') or [])
        artist_match = any(a in bn for a in an_options)
        scored.append((artist_match, nc + ns * 5, f, d))
    if not scored:
        return None, None
    scored.sort(key=lambda x: (-int(x[0]), -x[1]))
    return scored[0][2], scored[0][3]


def slim_song(title, artist, d):
    raw_notes = d.get('notes') or []
    if not raw_notes:
        raw_notes = (d.get('polyphonicNotes') or [[]])[0]
    notes_slim = [
        {'sd': n.get('sd'), 'oct': n.get('octave', 0),
         'b': n.get('beat'), 'd': n.get('duration', 0.25)}
        for n in raw_notes if not n.get('isRest')
    ]
    chords_slim = []
    for c in d.get('chords', []):
        ch = {'r': c.get('root'), 'b': c.get('beat'),
              'd': c.get('duration', 4), 't': c.get('type')}
        if c.get('borrowed'):
            ch['bw'] = c['borrowed']
        if c.get('applied'):
            ch['ap'] = c['applied']
        chords_slim.append(ch)
    return {
        'title': title, 'artist': artist, 'found': True,
        'key': d.get('keys', [{}])[0],
        'keys': d.get('keys', [{}]),         # full key list — supports mid-song modulation
        'tempo': d.get('tempos', [{}])[0],
        'meter': d.get('meters', [{'numBeats': 4}])[0],
        'sections': d.get('sections', []),
        'chords': chords_slim, 'notes': notes_slim,
        'endBeat': d.get('endBeat'),
    }


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(HTML_PATH).read()
    new = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(HTML_PATH, 'w').write(new)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; html updated')


if __name__ == '__main__':
    main()
