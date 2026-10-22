#!/usr/bin/env python3
"""
The 24 orders of the axis chords (C G Am F, the GOOSEFISH palette) -> axis-map.html

    themap_venv/python axis_map.py

Every four-bar block of every section is read the way runners_sheet reads it
(intros/outros, the user's own songs and variants left out; chords in C through
the relative major, so a minor song's Am F C G sits with every other one). A
block counts when it uses exactly C G Am F; its order is the order the chords
first sound. 24 orders = 6 loops x 4 starting chords: C G Am F looped is also
G Am F C, Am F C G and F C G Am, so the page puts a loop's four rotations on
one row.
"""
import glob, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_palette_groups as P
import runners_sheet as R

AXIS = {'C', 'G', 'Am', 'F'}


def main():
    ids = {}
    for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json'))):
        ids.setdefault(s['song'].lower(), s['ID'])
    rows = []
    tmp = os.path.join(tempfile.mkdtemp(), 's.json')
    for f in sorted(glob.glob(R.D + '/*.json')):
        song = os.path.basename(f)[:-5]
        if R.SCRATCH.match(song) or R.VARIANT.search(song): continue
        try:
            d, bpb = R.blocks(f)
            json.dump(d, open(tmp, 'w'))
            ops = list(P.openings(tmp))
        except Exception:
            continue
        for o in ops:
            ch = R.order(o)
            if len(ch) != 4 or set(ch) != AXIS: continue
            sec, bar = o['section'].rsplit(' @', 1)
            artist, title = song.split('_', 1) if '_' in song else ('', song)
            rows.append(dict(song=song, title=P.Q.title_case(title), artist=P.Q.title_case(artist),
                             section=sec, bar=int(bar), chords=ch, cbars=o['cbars'], key=o['key'],
                             cell=o['cellbars'], pushed=o['pushed'],
                             url=f'https://hookpad.hooktheory.com/?idOfUserSong={R.HASH.encode(ids[song.lower()])}'
                                 if song.lower() in ids else ''))
    # one instance per (song, order): a repeated chorus is one entry
    seen, uniq = set(), []
    for r in rows:
        k = (r['song'], tuple(r['chords']))
        if k not in seen: seen.add(k); uniq.append(r)
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = open(os.path.join(here, 'axis_map_template.html')).read()
    open(os.path.join(here, 'axis-map.html'), 'w').write(tpl.replace('__ROWS__', json.dumps(uniq, ensure_ascii=False)))
    counts = {}
    for r in uniq: counts.setdefault(' '.join(r['chords']), set()).add(r['song'])
    print(f'axis-map.html: {len(uniq)} song-orders, {len({r["song"] for r in uniq})} songs, {len(counts)}/24 orders found')
    for k, v in sorted(counts.items(), key=lambda kv: -len(kv[1])): print(f'   {k:14} {len(v)}')


if __name__ == '__main__':
    main()
