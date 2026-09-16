"""Rebuild Guitar400.html — eighth 50-song deep-study list (400 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar400.html')

USER_LIST_8 = [
    ("give your heart a break", "demi lovato"), ("trouble", "taylor swift"),
    ("talking body", "tove lo"), ("someday", "sugar ray"),
    ("every morning", "sugar ray"), ("wonder", "natalie merchant"),
    ("closer to the heart", "rush"), ("times like these", "foo fighters"),
    ("big me", "foo fighters"), ("breakfast in america", "supertramp"),
    ("good times bad times", "led zeppelin"), ("when the levee breaks", "led zeppelin"),
    ("mercury blues", "alan jackson"), ("dont rock the jukebox", "alan jackson"),
    ("still make cheyenne", "george strait"), ("amarillo by morning", "george strait"),
    ("wide open spaces", "dixie chicks"), ("unanswered prayers", "garth brooks"),
    ("the dance", "garth brooks"), ("a good run of bad luck", "clint black"),
    ("no one needs to know", "shania twain"), ("broken", "seether"),
    ("december", "collective soul"), ("ring ring", "abba"),
    ("live forever", "oasis"), ("fly away", "lenny kravitz"),
    ("lady", "lenny kravitz"), ("you get what you give", "new radicals"),
    ("travelin band", "creedence clearwater revival"),
    ("lodi", "creedence clearwater revival"),
    ("wholl stop the rain", "creedence clearwater revival"),
    ("imagine", "john lennon"), ("woman", "john lennon"),
    ("venus", "shocking blue"), ("jumpin jack flash", "rolling stones"),
    ("thank you", "dido"), ("let it go", "james bay"),
    ("animal", "pearl jam"), ("higher love", "steve winwood"),
    ("just the two of us", "bill withers"), ("hold on", "wilson phillips"),
    ("open your heart", "madonna"), ("borderline", "madonna"),
    ("dumb", "nirvana"), ("stop dragging my heart around", "tom petty"),
    ("she", "green day"), ("hey man nice shot", "filter"),
    ("cherub rock", "smashing pumpkins"), ("today", "smashing pumpkins"),
    ("ocean breathes salty", "modest mouse"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_8:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 400</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
