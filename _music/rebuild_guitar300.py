"""Rebuild Guitar300.html — sixth 50-song deep-study list (300 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar300.html')

USER_LIST_6 = [
    ("shelter from the storm", "bob dylan"), ("roses", "outkast"),
    ("for the movies", "buckcherry"), ("little red rodeo", "collin raye"),
    ("small town southern man", "alan jackson"), ("fine again", "seether"),
    ("chattahoochee", "alan jackson"),
    ("stuck in a moment you cant get out of", "u2"),
    ("because the night", "patti smith"), ("whats the frequency kenneth", "rem"),
    ("love song", "taylor swift"), ("breathe", "anna nalick"),
    ("little miss cant be wrong", "spin doctors"), ("young turks", "rod stewart"),
    ("something just like this", "chainsmokers"), ("american idiot", "green day"),
    ("my name is jonas", "weezer"), ("in too deep", "sum 41"),
    ("somebodys baby", "jackson browne"), ("sit next to me", "foster the people"),
    ("the last time", "rolling stones"), ("these dreams", "heart"),
    ("misunderstanding", "genesis"), ("come on feel the noise", "quiet riot"),
    ("surrender", "cheap trick"), ("neon rainbow", "alan jackson"),
    ("if i die young", "the band perry"), ("jane", "jefferson starship"),
    ("the rock show", "blink 182"), ("what if god was one of us", "joan osborne"),
    ("rebel rebel", "david bowie"), ("gypsy", "fleetwood mac"), ("vertigo", "u2"),
    ("roll to me", "del amitri"), ("dont take the girl", "tim mcgraw"),
    ("its your love", "tim mcgraw"), ("black balloon", "goo goo dolls"),
    ("shark in the water", "vv brown"), ("israels son", "silverchair"),
    ("please dont leave me", "pink"),
    ("lookin out my back door", "creedence clearwater revival"),
    ("down on the corner", "creedence clearwater revival"),
    ("standing outside the fire", "garth brooks"), ("is it any wonder", "keane"),
    ("hand in my pocket", "alanis morissette"), ("clarity", "zedd"),
    ("when i come around", "green day"), ("supernatural serious", "rem"),
    ("shattered", "oar"), ("highwayman", "the highwaymen"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_6:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 300</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
