#!/usr/bin/env python3
"""One source of truth for reading the Hookpad corpus.

Three rules that every analysis in this folder needs to apply the same way, and
that each got re-derived (and got wrong at least once) in a separate script:

  1. MERGE RE-STRIKES. One chord held for a bar and the same chord struck twice
     across two half-bars are the SAME THING. Layer 1 is chord-change
     durations; re-strikes are texture. 680 songs here contain at least one
     re-struck chord, so a script that quantises raw chord entries instead of
     merged runs is wrong about most of the library.
  2. EXCLUDE the user's own songs (mine*) and the generated workbenches
     (perms_*, music_*, date names). perms_abababcc is a permutation dump that
     otherwise buries every real match for that shape.
  3. MATCH NAMES CASE-INSENSITIVELY. A Hookpad rename that only changes
     capitalisation leaves the old filename on this case-insensitive disk;
     exact matching both drops the song and counts its file as an orphan.

Also: read the meter per song. 29 songs here are in 3 and 12 in 6, and
hardcoding four beats to the bar silently skips all of them.
"""
import json, glob, os, re

CORPUS = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
SCRATCH = re.compile(r'^(music_|perms_|mine|\d+-\d+-\d+)', re.I)


def is_scratch(name):
    return bool(SCRATCH.match(name))


def live_names():
    """Lowercased song names currently in the Hookpad account, or None if the
    cached list is missing (refresh: download_one.py --refresh-list)."""
    if not os.path.exists(LIST):
        return None
    return {s['song'].replace('/', '_').lower() for s in json.load(open(LIST))}


def identity(c):
    """What makes two chord entries the same chord. Includes adds and
    suspensions: Dm(add9)->Dm IS a change, which is the whole point of the
    push in Simple Kind of Life."""
    return (c.get('root'), c.get('type'), tuple(c.get('adds') or []),
            tuple(c.get('suspensions') or []), c.get('borrowed'),
            c.get('applied'), c.get('inversion'))


def merged(chords):
    """[{...}] -> [(chord, beat, duration)] with adjacent same-chord runs
    collapsed into one. Rule 1 above."""
    out = []
    for c in sorted(chords, key=lambda x: x['beat']):
        i = identity(c)
        if out and out[-1][0] == i and abs(out[-1][2] + out[-1][3] - c['beat']) < 1e-6:
            out[-1][3] += c['duration']
        else:
            out.append([i, c, c['beat'], c['duration']])
    return [(c, b, d) for _, c, b, d in out]


def songs(corpus=CORPUS, need_chords=True):
    """Yield (name, data, num_beats) for every live, non-scratch song."""
    live = live_names()
    for f in sorted(glob.glob(os.path.join(corpus, '*.json'))):
        name = os.path.basename(f)[:-5]
        if is_scratch(name) or (live is not None and name.lower() not in live):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if need_chords and not d.get('chords'):
            continue
        yield name, d, (d.get('meters') or [{}])[0].get('numBeats') or 4


def sections(d):
    """Yield (name, start_beat, end_beat). Hookpad beats are 1-based and a song
    with no markers is one unnamed section."""
    secs = sorted(d.get('sections') or [], key=lambda s: s['beat'])
    if not secs:
        secs = [{'beat': 1, 'name': '(whole)'}]
    for i, s in enumerate(secs):
        end = secs[i+1]['beat'] if i + 1 < len(secs) else (d.get('endBeat') or 10**9)
        yield s.get('name', '?'), s['beat'], end
