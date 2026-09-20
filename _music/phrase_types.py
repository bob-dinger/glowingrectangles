#!/usr/bin/env python3
"""Census of 8-bar PHRASE shapes at the chord-rhythm layer.

window_types.py counts 2-bar windows, which fragments anything phrase-level: a
flick that happens once per 8 bars shows up as three plain windows plus one odd
one, so a song lands in two buckets and neither describes it. Here each 8-bar
phrase is read as a WORD over window-letters -- Don't Look Back in Anger's verse
is [0,8] [0,8] [0,8] [0,8,11], i.e. AAAB -- which lands the rhythm layer in the
user's existing progression vocabulary (ender AAAB, vamp ABAB, shift AABB...).

All meters, unlike window_types.py: a 2-bar window is numBeats*2 beats wide, so
4/4 gives 16 eighth-slots and 3/4 gives 12. Hardcoding 4 drops 37 songs in 3.
"""
import json, glob, os, re, collections, sys

EXACT8 = '--exact8' in sys.argv  # only sections that ARE 8 bars, not chopped
SNAP   = '--snap'   in sys.argv  # ...and count 7- and 9-bar sections as eights

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
SHAPE = {'AAAA':'vamp/static', 'AAAB':'ender', 'ABAB':'vamp', 'AABB':'shift',
         'ABAC':'bounce', 'ABCB':'return', 'AABA':'blues/AABA', 'ABCD':'through'}

def merged(ch):
    out = []
    for c in sorted(ch, key=lambda x: x['beat']):
        lb = (c.get('root'), c.get('type'), tuple(c.get('adds') or []),
              c.get('borrowed'), c.get('applied'), tuple(c.get('suspensions') or []))
        if out and out[-1][0] == lb and abs(out[-1][1]+out[-1][2]-c['beat']) < 1e-6:
            out[-1][2] += c['duration']
        else:
            out.append([lb, c['beat'], c['duration']])
    return out

words = collections.defaultdict(set)
ex = collections.defaultdict(list)
letters = collections.defaultdict(collections.Counter)
meters = collections.Counter()

for f in glob.glob(f"{D}/*.json"):
    name = os.path.basename(f)[:-5]
    if name.lower() not in live or is_scratch(name): continue
    try: d = json.load(open(f))
    except Exception: continue
    nb = (d.get('meters') or [{}])[0].get('numBeats', 4) or 4
    W = nb * 2                                   # beats in a 2-bar window
    ch = d.get('chords') or []
    if not ch: continue
    secs = sorted([(s.get('beat',0), s.get('name','?')) for s in (d.get('sections') or [])]) or [(0,'all')]
    for i, (st, nm) in enumerate(secs):
        en = secs[i+1][0] if i+1 < len(secs) else 1e9
        runs = merged([c for c in ch if st <= c['beat'] < en])
        if len(runs) < 2: continue
        span = max(r[1]+r[2] for r in runs) - st
        nwin = int(span // W)
        if nwin < 4: continue
        # a 16-bar verse otherwise contributes two words and the song lands in
        # both; --exact8 keeps only sections that are exactly one 8-bar phrase
        if EXACT8:
            bars = span / nb
            if SNAP:
                # a section that is really 8 bars measures as 7 or 9 when it has
                # a pickup, or when the last chord rings past the section marker.
                # Window positions are unaffected, so take the first four either
                # way; only the measured span was ever off.
                if not (7 - 1e-6 <= bars <= 9 + 1e-6): continue
                nwin = 4
            elif nwin != 4 or abs(span - 8*nb) > 1e-6:
                continue
        wins = []
        for w in range(nwin):
            w0 = st + w*W
            wins.append(tuple(sorted({round((r[1]-w0)*2) for r in runs
                                      if -1e-6 <= r[1]-w0 < W})))
        for p in range(0, nwin - 3, 4):          # consecutive 8-bar phrases
            ph = wins[p:p+4]
            if not ph[0] or ph[0][0] != 0: continue
            seen, word = {}, ""
            for wd in ph:
                if wd not in seen: seen[wd] = chr(65+len(seen))
                word += seen[wd]
            words[word].add(name)
            meters[nb] += 1
            for wd, L in seen.items(): letters[word][(L, wd)] += 1
            if len(ex[word]) < 5 and name not in ex[word]: ex[word].append(name)

ranked = sorted(words.items(), key=lambda kv: -len(kv[1]))
tot = len(set().union(*words.values()))
print(f"  {sum(meters.values()):,} eight-bar phrases, {tot:,} songs, "
      f"meters {dict(meters)}\n")
print(f"  {'word':<8}{'name':<16}{'songs':>7}   examples")
for w, ss in ranked[:14]:
    e = ", ".join(n.split('_')[-1][:18] for n in ex[w][:3])
    print(f"  {w:<8}{SHAPE.get(w,''):<16}{len(ss):>7}   {e}")
cum = set()
print(f"\n  {'top':>6}{'songs':>10}")
for i,(w,ss) in enumerate(ranked,1):
    cum |= ss
    if i in (1,2,3,5,8,12):
        print(f"  {i:>6}{len(cum):>8,}  ({100*len(cum)/tot:>3.0f}%)")
