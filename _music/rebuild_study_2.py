"""Rebuild study-2.html — second 50-song deep-study list.

Same pattern as rebuild_beatles_study.py: clone studied-songs.html template,
swap title + SONGS array.
"""
import glob
import json
import os
import re

from rebuild_studied_songs import slim_song, best_match

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar50.html')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Guitar100.html')

USER_LIST_2 = [
    ("shake me down", "cage the elephant"),
    ("in my place", "coldplay"),
    ("speed of sound", "coldplay"),
    ("the scientist", "coldplay"),
    ("Pumped Up Kicks", "foster the people"),
    ("Stacy's Mom", "fountains of wayne"),
    ("Seashores of Old Mexico", "george strait"),
    ("Dig", "Incubus"),
    ("radio gaga", "queen"),
    ("the times they are a changin", "bob dylan"),
    ("desolation row", "bob dylan"),
    ("tangled up in blue", "bob dylan"),
    ("dead leaves and the dirty ground", "the white stripes"),
    ("sweet home alabama", "lynyrd skynyrd"),
    ("real world", "matchbox 20"),
    ("mr. jones", "counting crows"),
    ("a long december", "counting crows"),
    ("hanginaround", "counting crows"),
    ("pancho and lefty", "townes van zandt"),
    ("about a girl", "nirvana"),
    ("come as you are", "nirvana"),
    ("the unforgiven", "metallica"),
    ("take a picture", "filter"),
    ("everybody's changing", "keane"),
    ("two tickets to paradise", "eddie money"),
    ("lightning bolt", "jake bugg"),
    ("roar", "katy perry"),
    ("birthday", "katy perry"),
    ("nothin but the taillights", "clint black"),
    ("All I Wanted", "Michelle Branch"),
    ("Everywhere", "Michelle Branch"),
    ("Lifes A Dance", "John Michael Montgomery"),
    ("meant to be", "bebe rexha"),
    ("atlantic city", "the band"),
    ("teenage dirtbag", "wheatus"),
    ("rich girl", "hall & oates"),
    ("rhinestone cowboy", "glen campbell"),
    ("one headlight", "the wallflowers"),
    ("enjoy the silence", "depeche mode"),
    ("it's my life", "no doubt"),
    ("roll with the changes", "reo speedwagon"),
    ("Jet Airliner", "steve miller band"),
    ("everything you want", "vertical horizon"),
    ("you wreck me", "tom petty"),
    ("high", "feeder"),
    ("islands in the stream", "dolly parton"),
    ("lyin eyes", "the eagles"),
    ("tears of a clown", "smokey robinson"),
    ("baby love", "supremes"),
    ("american girl", "trisha yearwood"),
]


def main():
    all_files = glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))
    songs_data = []
    for title, artist in USER_LIST_2:
        _, d = best_match(title, artist, all_files)
        if not d:
            songs_data.append({'title': title, 'artist': artist, 'found': False})
            continue
        songs_data.append(slim_song(title, artist, d))

    data = json.dumps(songs_data, separators=(',', ':'))
    html = open(TEMPLATE).read()
    html = re.sub(r'<title>[^<]*</title>', '<title>Guitar 100</title>', html, count=1)
    html = re.sub(r'const SONGS\s*=\s*.*?;', lambda m: f'const SONGS = {data};', html, count=1, flags=re.DOTALL)
    open(OUT, 'w').write(html)

    found = sum(1 for s in songs_data if s.get('found'))
    print(f'{found}/{len(songs_data)} songs found; → {OUT}')


if __name__ == '__main__':
    main()
