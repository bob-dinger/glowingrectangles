"""Rebuild Guitar200.html — fourth 50-song deep-study list (200 total)."""
import glob
import json
import os
import re

from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar200.html')

USER_LIST_4 = [
    ("here i go again", "whitesnake"),
    ("i wanna be sedated", "ramones"),
    ("learning to fly", "tom petty"),
    ("lola", "the kinks"),
    ("you really got me now", "the kinks"),
    ("polly", "nirvana"),
    ("in bloom", "nirvana"),
    ("the world has turned and left me here", "weezer"),
    ("buddy holly", "weezer"),
    ("seven nation army", "the white stripes"),
    ("mr brightside", "the killers"),
    ("when you were young", "the killers"),
    ("pompeii", "bastille"),
    ("like a stone", "audioslave"),
    ("jeremy", "pearl jam"),
    ("nothing else matters", "metallica"),
    ("hero of the day", "metallica"),
    ("highway to hell", "acdc"),
    ("aint talkin bout love", "van halen"),
    ("starlight", "muse"),
    ("youre so vain", "carly simon"),
    ("summer of 69", "bryan adams"),
    ("king of pain", "the police"),
    ("dancing in the dark", "bruce springsteen"),
    ("start me up", "the rolling stones"),
    ("walking in memphis", "marc cohn"),
    ("champagne supernova", "oasis"),
    ("the way", "fastball"),
    ("slide", "goo goo dolls"),
    ("how you remind me", "nickelback"),
    ("ray of light", "madonna"),
    ("la isla bonita", "madonna"),
    ("waterloo", "abba"),
    ("inside out", "eve 6"),
    ("stuck in the middle with you", "stealers wheel"),
    ("another day in paradise", "phil collins"),
    ("take me home tonight", "eddie money"),
    ("man in the mirror", "michael jackson"),
    ("as long as you love me", "backstreet boys"),
    ("set fire to the rain", "adele"),
    ("white flag", "dido"),
    ("wildest dreams", "taylor swift"),
    ("wide awake", "katy perry"),
    ("dynamite", "taio cruz"),
    ("riptide", "vance joy"),
    ("get lucky", "daft punk"),
    ("habits", "tove lo"),
    ("she will be loved", "maroon 5"),
    ("building a mystery", "sarah mclachlan"),
    ("youre a god", "vertical horizon"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_4:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 200</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
