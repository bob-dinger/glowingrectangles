#!/usr/bin/env python3
"""Chord-rhythm census over a FIXED 2-bar window, not a minimised cell.

part_types.py collapses a part to its shortest repeating unit, which destroys
exactly what we want to see: four chords one-per-bar minimise to "one chord,
repeated", so 509 songs pile into a shape called `1` that has no internal
structure left. Here the window is fixed at two bars and the fingerprint is
WHERE the chord changes land inside it, counted in eighth notes (16 slots).
That keeps 1:1:1:1 distinct from 1, and it makes a push visible as an onset on
an odd slot instead of an even one.
"""
import json, glob, os, re, collections

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
# Lowercased: a song renamed in Hookpad only for capitalisation keeps its old
# filename on this (case-insensitive) disk, so exact matching drops it from the
# census AND counts it as a rename orphan. That hid 52 songs, 24 with chords.
SCRATCH = re.compile(r'^(music_|perms_|mine_\d|\d+-\d+-\d+)', re.I)
def is_scratch(name):
    """The user's own generated workbenches, not songs: perms_* permutation
    dumps (one has 288 "sections"), music_* riff projects, and date-named
    scratch files. They are real Hookpad entries, so the account list does not
    exclude them, but they skew every census."""
    return bool(SCRATCH.match(name))

live = {s['song'].replace('/', '_').lower()
        for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')))}


def merged(chords):
    out = []
    for c in sorted(chords, key=lambda x: x['beat']):
        lb = (c.get('root'), c.get('type'), tuple(c.get('adds') or []),
              c.get('borrowed'), c.get('applied'), tuple(c.get('suspensions') or []))
        if out and out[-1][0] == lb and abs(out[-1][1] + out[-1][2] - c['beat']) < 1e-6:
            out[-1][2] += c['duration']
        else:
            out.append([lb, c['beat'], c['duration']])
    return out


pat_songs = collections.defaultdict(set)
pat_ex = collections.defaultdict(list)

for f in glob.glob(f"{D}/*.json"):
    name = os.path.basename(f)[:-5]
    # the user's own scratch projects are all named music_<something>; they are
    # workbenches, not songs, and they skew every count
    if name.lower() not in live or is_scratch(name):
        continue
    try: d = json.load(open(f))
    except Exception: continue
    nb = (d.get('meters') or [{}])[0].get('numBeats', 4) or 4
    if nb != 4: continue                    # 2-bar window only defined for 4/4 here
    ch = d.get('chords') or []
    if not ch: continue
    secs = sorted([(s.get('beat', 0), s.get('name', '?')) for s in (d.get('sections') or [])]) or [(0,'all')]
    for i, (start, nm) in enumerate(secs):
        end = secs[i+1][0] if i+1 < len(secs) else 1e9
        runs = merged([c for c in ch if start <= c['beat'] < end])
        if len(runs) < 2: continue
        span = max(r[1]+r[2] for r in runs) - start
        nwin = int(span // 8)
        for w in range(nwin):
            w0 = start + w*8
            ons = sorted({round((r[1]-w0)*2) for r in runs if -1e-6 <= r[1]-w0 < 8})
            if not ons or ons[0] != 0: continue      # window must start on a change
            key = tuple(ons)
            pat_songs[key].add(name)
            if len(pat_ex[key]) < 5 and name not in pat_ex[key]:
                pat_ex[key].append(name)

ranked = sorted(pat_songs.items(), key=lambda kv: -len(kv[1]))
allsongs = set().union(*pat_songs.values())
print(f"  {len(pat_songs):,} distinct 2-bar patterns across {len(allsongs):,} songs")
print(f"  onsets in eighths, 0-15.  even slot = on a beat, odd slot = pushed/syncopated\n")
print(f"  {'onsets':<24}{'chords':>7}{'songs':>7}   examples")
for k, ss in ranked[:20]:
    ex = ", ".join(n.split('_')[-1][:17] for n in pat_ex[k][:3])
    print(f"  {str(list(k)):<24}{len(k):>7}{len(ss):>7}   {ex}")
cum=set()
print(f"\n  {'learn the top':>14}{'songs covered':>16}")
for i,(k,ss) in enumerate(ranked,1):
    cum|=ss
    if i in (1,2,3,5,8,12,20):
        print(f"  {i:>14}{len(cum):>10,}  ({100*len(cum)/len(allsongs):>4.0f}%)")
