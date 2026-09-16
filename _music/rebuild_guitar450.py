"""Rebuild Guitar450.html — ninth 50-song deep-study list (450 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar450.html')

USER_LIST_9 = [
    ("never let you go", "third eye blind"), ("all star", "smash mouth"),
    ("eye of the tiger", "survivor"), ("uptown girl", "billy joel"),
    ("happy", "pharrell williams"), ("closer", "chainsmokers"),
    ("torn", "natalie imbruglia"), ("time after time", "cyndi lauper"),
    ("im a believer", "the monkees"), ("cheap thrills", "sia"),
    ("chandelier", "sia"), ("tonight tonight", "smashing pumpkins"),
    ("bullet with butterfly wings", "smashing pumpkins"), ("boom clap", "charli xcx"),
    ("bad blood", "taylor swift"), ("material girl", "madonna"),
    ("timber", "kesha"), ("die young", "kesha"),
    ("aint no sunshine", "bill withers"), ("underneath it all", "no doubt"),
    ("walkin on the sun", "smash mouth"), ("break on through", "the doors"),
    ("wouldnt it be nice", "beach boys"), ("god only knows", "beach boys"),
    ("in my room", "beach boys"), ("aint too proud to beg", "the temptations"),
    ("where did our love go", "the supremes"), ("you keep me hangin on", "the supremes"),
    ("come sail away", "styx"), ("talk", "coldplay"),
    ("violet hill", "coldplay"), ("lovin touchin squeezin", "journey"),
    ("oh sherrie", "steve perry"), ("fell in love with a girl", "the white stripes"),
    ("hanging by a moment", "lifehouse"), ("the reason", "hoobastank"),
    ("breakfast at tiffanys", "deep blue something"),
    ("there she goes", "sixpence none the richer"), ("runaway train", "soul asylum"),
    ("shine", "collective soul"), ("brand new man", "brooks and dunn"),
    ("my happy ending", "avril lavigne"), ("caring is creepy", "the shins"),
    ("say so", "doja cat"), ("minority", "green day"),
    ("helena beat", "foster the people"), ("dont stop", "foster the people"),
    ("gold dust woman", "fleetwood mac"), ("hunger strike", "temple of the dog"),
    ("in a gadda da vida", "iron butterfly"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_9:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 450</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
