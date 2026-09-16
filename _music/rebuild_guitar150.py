"""Rebuild Guitar150.html — third 50-song deep-study list (50 total).

User's 30 picks + 20 curated picks. Same template as Guitar50 + Guitar100.
"""
import glob
import json
import os
import re

from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar150.html')

USER_LIST_3 = [
    # User's 30 (rolling-in-the-deep spelling corrected from "rollin")
    ("mykonos", "fleet foxes"),
    ("just like heaven", "the cure"),
    ("friday i'm in love", "the cure"),
    ("fernando", "abba"),
    ("africa", "toto"),
    ("everlong", "foo fighters"),
    ("sour girl", "stone temple pilots"),
    ("my girl", "temptations"),
    ("jaded", "aerosmith"),
    ("heart of gold", "neil young"),
    ("logical song", "supertramp"),
    ("give a little bit", "supertramp"),
    ("stairway to heaven", "led zeppelin"),
    ("over the hills and far away", "led zeppelin"),
    ("longview", "green day"),
    ("rolling in the deep", "adele"),
    ("hey brother", "avicii"),
    ("rock around the clock", "bill haley"),
    ("sleepwalker", "wallflowers"),
    ("the high road", "broken bells"),
    ("dreams", "fleetwood mac"),
    ("silver springs", "fleetwood mac"),
    ("landslide", "fleetwood mac"),
    ("let the mystery be", "iris dement"),
    ("too little too late", "jojo"),
    ("smile like you mean it", "the killers"),
    ("time to pretend", "mgmt"),
    ("malibu", "miley cyrus"),
    ("baby's got her blue jeans on", "mel mcdaniel"),
    ("top of the world", "juliana theory"),
    # 20 curated picks
    ("american pie", "don mclean"),
    ("piano man", "billy joel"),
    ("southern cross", "crosby still nash"),
    ("limelight", "rush"),
    ("shake it off", "taylor swift"),
    ("blank space", "taylor swift"),
    ("complicated", "avril lavigne"),
    ("november rain", "guns n roses"),
    ("lithium", "nirvana"),
    ("jane says", "janes addiction"),
    ("two princes", "spin doctors"),
    ("closing time", "semisonic"),
    ("6th avenue heartache", "wallflowers"),
    ("billie jean", "michael jackson"),
    ("walking on a dream", "empire of the sun"),
    ("love song", "sara bareilles"),
    ("spiderwebs", "no doubt"),
    ("100 years", "five for fighting"),
    ("its the end of the world as we know it", "rem"),
    ("centerfold", "j geils band"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_3:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 150</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
