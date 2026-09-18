#!/usr/bin/env python3
"""
Find every section in the corpus whose bars match a shape.

A shape is a string of role letters, one per bar: ABABABCC is six bars
alternating two chords and then two of a third. Roles are positional, not
chords -- A is whatever chord the first bar holds -- so one shape finds the
pattern in every key and every palette at once.

    python3 find_shape.py ABABABCC
    python3 find_shape.py AABA --distinct 2
    python3 find_shape.py ABABABCD --songs-only

Roles must be distinct from each other by default: in ABABABCC, C cannot be A
or B, or you would match plain alternation. --loose drops that.

MIND THE METER. Bar length comes from each song's own meters[0].numBeats, not
from an assumption of four. 44 songs here are in 3 and 14 are in 6; hardcoding
4 silently skips every one of them, which is how Seashores of Old Mexico --
a known match, in 3/4 -- went missing from two earlier passes of this search.
"""
import argparse, collections, glob, json, os, sys

CORPUS = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
LET = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'A#'}


def label(c):
    """What to call a chord. Borrowed and applied chords are NOT the same
    chord as the plain degree -- F and F/4 are F and Bb -- so they get marked,
    or the shapes they form would be counted as repeats of the diatonic one."""
    s = LET.get(c['root'], f"?{c['root']}")
    if c.get('borrowed'): s += '*'
    if c.get('applied'):  s += f"/{c['applied']}"
    return s


def bars_of(section_beat, next_beat, chords, num_beats):
    """-> [chord per bar] or None if the section is not one-chord-per-bar.

    A bar qualifies only if exactly one chord starts on its downbeat. Sections
    with two chords in a bar, or chords landing off the grid, are not the thing
    a bar-level shape describes."""
    bars = {}
    for c in chords:
        if not (section_beat <= c['beat'] < next_beat): continue
        off = c['beat'] - section_beat
        if off % num_beats: return None
        b = int(off // num_beats)
        if b in bars: return None
        bars[b] = label(c)
    if not bars: return None
    return [bars.get(k) for k in range(max(bars) + 1)]


def matches(window, shape, distinct):
    roles = {}
    for ch, role in zip(window, shape):
        if role in roles:
            if roles[role] != ch: return None
        else:
            roles[role] = ch
    if distinct and len(set(roles.values())) != len(roles): return None
    return roles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shape', help='role letters, one per bar, e.g. ABABABCC')
    ap.add_argument('--corpus', default=CORPUS)
    ap.add_argument('--loose', action='store_true', help='allow two roles to be the same chord')
    ap.add_argument('--songs-only', action='store_true', help='skip scratch and perms files')
    ap.add_argument('--min', type=int, default=1, help='only show progressions used by >= N songs')
    a = ap.parse_args()
    shape = a.shape.upper()

    found = collections.defaultdict(set)
    meters = collections.Counter()
    for f in glob.glob(os.path.join(a.corpus, '*.json')):
        name = os.path.basename(f)
        if name.startswith('_'): continue
        song = name[:-5].split('-hooktab')[0]
        if a.songs_only and song.startswith(('mine', 'music_', 'perms', '6-', '7-', '8-', '9-')):
            continue
        try: d = json.load(open(f))
        except Exception: continue
        ch = sorted(d.get('chords') or [], key=lambda c: c['beat'])
        if not ch: continue
        nb = (d.get('meters') or [{}])[0].get('numBeats') or 4
        meters[nb] += 1
        secs = sorted(d.get('sections') or [], key=lambda s: s['beat']) or [{'beat':1,'name':'(whole)'}]
        for i, s in enumerate(secs):
            end = secs[i+1]['beat'] if i+1 < len(secs) else (d.get('endBeat') or 10**9)
            seq = bars_of(s['beat'], end, ch, nb)
            if not seq or len(seq) < len(shape): continue
            for st in range(len(seq) - len(shape) + 1):
                w = seq[st:st+len(shape)]
                if any(x is None for x in w): continue
                if matches(w, shape, not a.loose):
                    found[' '.join(w)].add((song, s['name'], nb))

    print(f'{shape} — {len(found)} distinct progressions '
          f'(bar lengths in corpus: {dict(sorted(meters.items()))})\n')
    for prog, who in sorted(found.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        songs = sorted({s for s, _, _ in who})
        if len(songs) < a.min: continue
        nbs = {n for _, _, n in who}
        meter = '' if nbs == {4} else f"  [{'/'.join(str(n) for n in sorted(nbs))}-beat bars]"
        secs = sorted({x for _, x, _ in who})
        print(f'  {prog:32}  {", ".join(songs)[:62]}{meter}')
        print(f'  {"":32}  ({", ".join(secs)[:60]})')


if __name__ == '__main__':
    main()
