"""Rebuild Guitar500.html — tenth 50-song deep-study list (500 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar500.html')

USER_LIST_10 = [
    ("absolutely", "nine days"), ("whatdya want from me", "adam lambert"),
    ("state of mind", "clint black"), ("summertime blues", "alan jackson"),
    ("livin on love", "alan jackson"), ("where have all the cowboys gone", "paula cole"),
    ("adalida", "george strait"), ("synchronicity 2", "the police"),
    ("walking on the moon", "the police"), ("rape me", "nirvana"),
    ("stay away", "nirvana"), ("sappy", "nirvana"),
    ("something in the way", "nirvana"), ("if youre not in it for love", "shania twain"),
    ("back on the chain gang", "the pretenders"), ("meant to live", "switchfoot"),
    ("the river", "garth brooks"), ("much too young", "garth brooks"),
    ("if tomorrow never comes", "garth brooks"),
    ("every day is a winding road", "sheryl crow"),
    ("we danced anyway", "deana carter"), ("strangers", "the kinks"),
    ("write this down", "george strait"), ("slow ride", "foghat"),
    ("some girls do", "sawyer brown"), ("thank god for you", "sawyer brown"),
    ("sunday morning", "maroon 5"), ("all my life", "kc and jojo"),
    ("never gonna leave this bed", "maroon 5"), ("who knew", "pink"),
    ("queen of my double wide trailer", "sammy kershaw"),
    ("she dont know shes beautiful", "sammy kershaw"),
    ("we are all made of stars", "moby"), ("love song", "the cure"),
    ("oh what a night", "four seasons"), ("walk like a man", "four seasons"),
    ("too much fun", "daryle singletary"), ("amie", "pure prairie league"),
    ("hemhorrage", "fuel"), ("carried away", "george strait"),
    ("black water", "doobie brothers"), ("what kind of fool", "lee roy parnell"),
    ("fist city", "loretta lynn"), ("god bless texas", "little texas"),
    ("where is my mind", "the pixies"), ("gigantic", "the pixies"),
    ("good", "better than ezra"), ("you learn", "alanis morissette"),
    ("the space between", "dave matthews band"), ("ooh la la", "rod stewart"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_10:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 500</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
