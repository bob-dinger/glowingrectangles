#!/usr/bin/env python3
"""
Pull canonical / half / double BPM from songbpm.com for a hand-listed set of
songs, keeping the key the user already has alongside it.

songbpm publishes all three tempo readings, which is the point: Hookpad's bpm
is unreliable on half/double-time, so we want the canonical figure plus both
alternatives rather than a single number to argue with.

    python3 tempos_list.py
    python3 tempos_list.py --throttle 2

Writes ~/Desktop/tempos.csv and prints a table.
"""
import argparse, csv, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_songbpm as fb

# (artist as songbpm knows it, title, the key the user already has)
SONGS = [
    ('Cage the Elephant',        'Shake Me Down',                 'A#, A'),
    ('Coldplay',                 'In My Place',                   'A'),
    ('Coldplay',                 'Speed of Sound',                'Bm'),
    ('Coldplay',                 'The Scientist',                 'F'),
    ('Foster the People',        'Pumped Up Kicks',               'Fm'),
    ('Fountains of Wayne',       "Stacy's Mom",                   'Bm'),
    ('George Strait',            'Seashores of Old Mexico',       'F#m'),
    ('Incubus',                  'Dig',                           'B'),
    ('Queen',                    'Radio Ga Ga',                   'F'),
    ('Bob Dylan',                "The Times They Are A-Changin'", 'G'),
    ('Bob Dylan',                'Desolation Row',                'E'),
    ('Bob Dylan',                'Tangled Up in Blue',            'Am'),
    ('The White Stripes',        'Dead Leaves and the Dirty Ground', 'A mix'),
    ('Lynyrd Skynyrd',           'Sweet Home Alabama',            'G'),
    ('Matchbox Twenty',          'Real World',                    'A#'),
    ('Counting Crows',           'Mr. Jones',                     'C'),
    ('Counting Crows',           'A Long December',               'F'),
    ('Counting Crows',           'Hanginaround',                  'C'),
    ('Willie Nelson',            'Pancho and Lefty',              'D'),
    ('Nirvana',                  'About a Girl',                  'Em (G)'),
    ('Nirvana',                  'Come as You Are',               'Em'),
    ('Metallica',                'The Unforgiven',                'Am'),
    ('Filter',                   'Take a Picture',                'D'),
    ('Keane',                    "Everybody's Changing",          'C'),
    ('Eddie Money',              'Two Tickets to Paradise',       'A'),
    ('Jake Bugg',                'Lightning Bolt',                'A'),
    ('Katy Perry',               'Roar',                          'A#, G'),
    ('Katy Perry',               'Birthday',                      'E'),
    ('Clint Black',              "Nothin' but the Taillights",    'G'),
    ('Michelle Branch',          'All You Wanted',                'G# (G) capo 1'),
    ('Michelle Branch',          'Everywhere',                    'G'),
    ('John Michael Montgomery',  "Life's a Dance",                'C'),
    ('Bebe Rexha',               'Meant to Be',                   'A#, G (capo 3)'),
    ('The Band',                 'Atlantic City',                 'A'),
    ('Wheatus',                  'Teenage Dirtbag',               'E'),
    ('Hall & Oates',             'Rich Girl',                     'F'),
    ('Glen Campbell',            'Rhinestone Cowboy',             'C'),
    ('The Wallflowers',          'One Headlight',                 'D'),
    ('Depeche Mode',             'Enjoy the Silence',             'Cm'),
    ('No Doubt',                 "It's My Life",                  'E -> C#'),
    ('REO Speedwagon',           'Roll with the Changes',         'G mix'),
    ('Steve Miller Band',        'Jet Airliner',                  'F'),
    ('Vertical Horizon',         'Everything You Want',           'D#m'),
    ('Tom Petty',                'You Wreck Me',                  'A#'),
    ('Feeder',                   'High',                          'G'),
    ('Dolly Parton',             'Islands in the Stream',         'C'),
    ('Eagles',                   "Lyin' Eyes",                    'G'),
    ('Smokey Robinson',          'The Tears of a Clown',          'D'),
    ('The Supremes',             'Baby Love',                     'C'),
    ('Trisha Yearwood',          'American Girl',                 'C'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--throttle', type=float, default=1.2,
                    help='seconds between songs (be kind to songbpm)')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/tempos.csv'))
    a = ap.parse_args()

    rows, misses = [], []
    for i, (artist, title, key) in enumerate(SONGS, 1):
        print(f'  [{i:>2}/{len(SONGS)}] {title} — {artist} ... ', end='', flush=True)
        try:
            bpm, half, double, sp_key, mode, url, status = fb.fetch_one(artist, title)
        except Exception as e:
            bpm = half = double = sp_key = mode = None; url, status = '', f'ERR {e}'
        if bpm:
            print(f'{bpm} bpm', flush=True)
        else:
            print(f'MISS ({status})', flush=True)
            misses.append(f'{title} — {artist}')
        rows.append(dict(artist=artist, title=title, your_key=key, bpm=bpm,
                         bpm_half=half, bpm_double=double,
                         songbpm_key=sp_key, songbpm_mode=mode,
                         url=url, status=status))
        time.sleep(a.throttle)

    with open(a.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    got = sum(1 for r in rows if r['bpm'])
    print(f'\n{got}/{len(rows)} resolved -> {a.out}')
    if misses:
        print('\nmisses (fix the artist/title spelling and re-run those):')
        for m in misses: print('   -', m)


if __name__ == '__main__':
    main()
