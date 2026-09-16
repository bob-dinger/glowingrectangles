"""Rebuild Guitar550.html — eleventh study list (currently 45 songs; will fill to 50 later)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar550.html')

USER_LIST_11 = [
    ("smile", "uncle kracker"), ("next to you next to me", "shenandoah"),
    ("on a plain", "nirvana"), ("breed", "nirvana"), ("sliver", "nirvana"),
    ("blew", "nirvana"), ("dallas", "alan jackson"),
    ("tall tall trees", "alan jackson"), ("blue clear sky", "george strait"),
    ("all my exes live in texas", "george strait"),
    ("ocean front property", "george strait"),
    ("stay together for the kids", "blink 182"),
    ("here comes your man", "pixies"), ("showdown", "elo"),
    ("old man", "neil young"),
    ("i still havent found what im looking for", "u2"),
    ("its in his kiss", "betty everett"),
    ("that aint no way to go", "brooks and dunn"),
    ("stay the night", "zedd"), ("everybody talks", "neon trees"),
    ("name", "goo goo dolls"), ("sit still look pretty", "daya"),
    ("safe and sound", "capitol cities"),
    ("stop in the name of love", "the supremes"),
    ("drown", "smashing pumpkins"), ("old flame", "alabama"),
    ("coming home", "diddy"), ("12:51", "the strokes"),
    ("whistle", "flo rida"), ("circles", "post malone"),
    ("pillow talk", "zayn"), ("kings and queens", "ava max"),
    ("my house", "flo rida"), ("wild ones", "flo rida"),
    ("thats the way it is", "celine dion"), ("jealous", "nick jonas"),
    ("electric feel", "mgmt"), ("never my love", "the association"),
    ("fourth time around", "bob dylan"),
    ("rollin with the flow", "charlie rich"),
    ("this land is your land", "woody guthrie"),
    ("nobody wins", "radney foster"),
    ("hit em up style", "blu cantrell"),
    ("straight tequlia night", "john anderson"),
    ("i saw the light", "hank williams"),
    ("back in black", "acdc"),
    ("semi charmed life", "third eye blind"),
    ("california girls", "katy perry"),
    ("hurricane", "bob dylan"),
    ("reeling in the years", "steely dan"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_11:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 550</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
