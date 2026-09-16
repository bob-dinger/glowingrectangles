"""Rebuild Guitar250.html — fifth 50-song deep-study list (250 total)."""
import glob, json, os, re
from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar250.html')

USER_LIST_5 = [
    ("dream on", "aerosmith"), ("bohemian rhapsody", "queen"), ("dancing queen", "abba"),
    ("beat it", "michael jackson"), ("brown eyed girl", "van morrison"),
    ("under pressure", "david bowie"), ("for the longest time", "billy joel"),
    ("message in a bottle", "the police"), ("dont fear the reaper", "blue oyster cult"),
    ("bittersweet symphony", "the verve"), ("enter sandman", "metallica"),
    ("free fallin", "tom petty"), ("refugee", "tom petty"), ("jump", "van halen"),
    ("heart shaped box", "nirvana"), ("lean on me", "bill withers"),
    ("you cant hurry love", "supremes"), ("bette davis eyes", "kim carnes"),
    ("just what i needed", "the cars"), ("midnight rider", "allman brothers"),
    ("fields of gold", "sting"), ("ants marching", "dave matthews band"),
    ("mandolin rain", "bruce hornsby"), ("heaven", "bryan adams"),
    ("say it aint so", "weezer"), ("shiny happy people", "rem"),
    ("boulevard of broken dreams", "green day"), ("good riddance", "green day"),
    ("kiss me", "sixpence none the richer"), ("fireflies", "owl city"),
    ("soak up the sun", "sheryl crow"), ("wagon wheel", "old crow medicine show"),
    ("blurry", "puddle of mudd"), ("all the right moves", "onerepublic"),
    ("21 guns", "green day"), ("baby baby", "amy grant"), ("new slang", "the shins"),
    ("i saw the sign", "ace of base"), ("all that she wants", "ace of base"),
    ("the middle", "zedd"), ("head over feet", "alanis morissette"),
    ("battle of new orleans", "johnny horton"), ("you belong with me", "taylor swift"),
    ("girls just wanna have fun", "cyndi lauper"), ("daydream believer", "the monkees"),
    ("hey soul sister", "train"), ("kryptonite", "3 doors down"),
    ("up around the bend", "creedence clearwater revival"), ("band on the run", "wings"),
    ("float on", "modest mouse"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_5:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 250</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
