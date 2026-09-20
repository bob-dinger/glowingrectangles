#!/usr/bin/env python3
"""Census of chord-rhythm part types across the Hookpad library.

Layer 1 only (see music_chord_riff_fingerprint): the identity of a part is its
sequence of CHORD-CHANGE durations, with same-chord re-strikes merged away.

For each section it finds the shortest repeating cell in that duration
sequence, so "[3,1] x8" and "[3,1] x4" collapse to the same named pattern at
different lengths. Ranking is by how many distinct SONGS use a cell, not how
many sections -- a song with four verses on one pattern should count once.

Meter is read per song. Hardcoding 4 beats/bar silently drops every 3/4 song.
"""
import json, glob, os, re, collections, sys
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
# Lowercased: a song renamed in Hookpad only for capitalisation keeps its old
# filename on this (case-insensitive) disk, so exact matching drops it from the
# census AND counts it as a rename orphan. That hid 52 songs, 24 with chords.

live = corpus.live_names()




def cell(durs):
    """Shortest repeating unit that covers most of the sequence.

    Exact division is too strict for real sections: Yellow Submarine's verse is
    [3,1] seven times and then a [4] to land on, which under an exact test is
    not a repeat at all and gets thrown away. So accept the shortest cell whose
    whole repeats cover >=70% of the events, and report the repeat count.
    """
    n = len(durs)
    for L in range(1, min(6, n // 2) + 1):
        reps = 0
        while (reps + 1) * L <= n and all(
                abs(durs[reps*L + i] - durs[i]) < 1e-6 for i in range(L)):
            reps += 1
        if reps >= 2 and reps * L >= 0.70 * n:
            return tuple(durs[:L]), reps
    return tuple(durs), 1


songs = collections.defaultdict(set)     # cell -> {song}
seclen = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)

for f in glob.glob(f"{D}/*.json"):
    name = os.path.basename(f)[:-5]
    if name.lower() not in live: continue
    if name.startswith(('chord-riffs', 'riffs', 'perms', 'blocks')): continue
    try: d = json.load(open(f))
    except Exception: continue
    nb = (d.get('meters') or [{}])[0].get('numBeats', 4) or 4
    ch = d.get('chords') or []
    if not ch: continue
    secs = sorted([(s.get('beat', 0), s.get('name', '?')) for s in (d.get('sections') or [])])
    if not secs: secs = [(0, 'all')]
    for i, (start, nm) in enumerate(secs):
        end = secs[i+1][0] if i + 1 < len(secs) else 1e9
        part = [c for c in ch if start <= c['beat'] < end]
        if len(part) < 4: continue
        m = corpus.merged(part)
        durs = [round(x[2], 3) for x in m]
        if len(durs) < 4: continue
        cl, reps = cell(durs)
        if len(cl) > 6: continue                    # not a cell, just a long part
        bars = round(sum(cl) / nb, 3)
        key = (cl, bars, nb)
        songs[key].add(name)
        seclen[key][reps] += 1
        if len(examples[key]) < 4 and name not in [e[0] for e in examples[key]]:
            examples[key].append((name, nm, reps))

rows = sorted(songs.items(), key=lambda kv: -len(kv[1]))
print(f"  {sum(len(v) for v in songs.values()):,} section-instances, "
      f"{len(songs):,} distinct cells, across {len(set().union(*songs.values())):,} songs\n")
print(f"  {'cell (beats)':<26}{'bars':>5}{'met':>5}{'songs':>7}   examples")
for key, ss in rows[:28]:
    cl, bars, nb = key
    cs = "-".join(str(int(x) if x == int(x) else x) for x in cl)
    ex = ", ".join(f"{n.split('_')[-1][:20]}" for n, _, _ in examples[key][:3])
    print(f"  {cs:<26}{bars:>5g}{nb:>5}{len(ss):>7}   {ex}")
