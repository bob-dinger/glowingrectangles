"""Rebuild Guitar350.html — seventh 50-song deep-study list (350 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar350.html')

USER_LIST_7 = [
    ("one", "u2"), ("clocks", "coldplay"), ("yellow", "coldplay"),
    ("zombie", "cranberries"), ("take on me", "aha"), ("tainted love", "soft cell"),
    ("every breath you take", "the police"), ("light my fire", "the doors"),
    ("all along the watchtower", "jimi hendrix"), ("hey joe", "jimi hendrix"),
    ("fortunate son", "creedence clearwater revival"),
    ("bad moon rising", "creedence clearwater revival"),
    ("mary janes last dance", "tom petty"), ("into the great wide open", "tom petty"),
    ("brown sugar", "rolling stones"), ("street fighting man", "rolling stones"),
    ("satisfaction", "rolling stones"), ("holiday", "green day"),
    ("basketcase", "green day"), ("wake me up when september ends", "green day"),
    ("welcome to paradise", "green day"), ("dammit", "blink 182"),
    ("whats my age again", "blink 182"), ("all apologies", "nirvana"),
    ("lounge act", "nirvana"), ("higher", "creed"),
    ("you shook me all night long", "acdc"), ("ho hey", "the lumineers"),
    ("lovefool", "the cardigans"), ("she drives me crazy", "fine young cannibals"),
    ("amber", "311"), ("your love", "the outfield"), ("pride", "u2"),
    ("solsbury hill", "peter gabriel"), ("who can it be now", "men at work"),
    ("heroes", "david bowie"), ("the man who sold the world", "david bowie"),
    ("lump", "presidents of the usa"), ("sex and candy", "marcy playground"),
    ("how bizarre", "omc"), ("the chain", "fleetwood mac"),
    ("hold me", "fleetwood mac"), ("hash pipe", "weezer"),
    ("the sweater song", "weezer"), ("whatever", "oasis"),
    ("blowin in the wind", "bob dylan"), ("mr tambourine man", "bob dylan"),
    ("mmm mmm mmm mmm", "crash test dummies"), ("tearin up my heart", "nsync"),
    ("trouble", "coldplay"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_7:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 350</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
