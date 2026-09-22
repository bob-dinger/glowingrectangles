#!/usr/bin/env python3
"""A second metric version of every G50-G250 song, as paste-ready .txt files.

Not error-correction (music_doubling_variants) -- the point is to see the same
song at another metric level. The user: "seeing the same thing in two or three
ways is good for me."

Direction: aim the typical chord at one bar. Chords shorter than a bar get
DOUBLED (bars shorten, tempo doubles, a half-bar chord becomes a whole one);
chords longer than a bar get HALVED. When the chord is already a bar, pick by
tempo so the result stays countable.

Out: ~/Desktop/hookpad_halved/<band_song>-<newbpm>.txt  -- .txt because Hookpad
paste files must be (feedback_paste_files_txt), and the tempo suffix matches the
naming already used for interstate love song-168 and mainstreet-150.
"""
import json, re, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import corpus
from double_song import double, num

OUT = os.path.expanduser('~/Desktop/hookpad_halved')
WANT = {'G50', 'G100', 'G150', 'G200', 'G250'}

def norm(s):
    s = s.lower(); s = re.sub(r"[''`]", '', s); s = re.sub(r'\band\b', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)

def debase(x):
    prev = None
    while prev != x:
        prev = x
        x = re.sub(r'-[0-9a-f]{6}$', '', x)
        x = re.sub(r'_(o|c|ly|j|s|m|r|x)$', '', x)
    return x

pool = json.load(open(os.path.join(HERE, 'pool_map.json')))
P = {}
for slug, g in pool.items():
    if g in WANT:
        P.setdefault(norm(debase(slug)), g)

os.makedirs(OUT, exist_ok=True)
made, skipped = [], []
for name, d, nb in corpus.songs():
    g = P.get(norm(debase(name)))
    if not g:
        continue
    runs = []
    for _, st, en in corpus.sections(d):
        runs += [dur/nb for _, _, dur in
                 corpus.merged([c for c in d['chords'] if st <= c['beat'] < en])]
    if not runs:
        skipped.append((name, 'no chord runs')); continue
    mode = collections.Counter(round(r*4)/4 for r in runs).most_common(1)[0][0]
    bpm = (d.get('tempos') or [{}])[0].get('bpm')
    if not bpm:
        skipped.append((name, 'no tempo')); continue
    # BOTH directions. Picking one meant guessing which reading the user
    # wanted, and the guess was wrong for most of them: aiming every song at
    # one-chord-per-bar doubled songs like Dancing Queen (99, chords every half
    # bar) to 198, when 99 is exactly how it is felt. The tempo in the filename
    # already tells the two apart, so there is nothing to decide here.
    for F in (2.0, 0.5):
        out = double(d, F)
        # No decimal tempos. An odd bpm halves to x.5 (99 -> 49.5), which is an
        # awkward filename and not a value the user wants stored. Rounding
        # drifts the variant under 1% from the original, which is nothing next
        # to the 10-bpm grid the library is being standardised to -- and the
        # rounded value goes in the FILE too, so the name never lies about it.
        new = int(round(bpm * F))
        for t in out['tempos']:
            t['bpm'] = new
        fn = f"{name}-{new}.txt"
        open(os.path.join(OUT, fn), 'w').write(json.dumps(out, separators=(',', ':')))
        made.append((g, name, round(bpm), new, 'double' if F == 2 else 'halve', mode))

made.sort(key=lambda r: (sorted(WANT, key=lambda x: int(x[1:])).index(r[0]), r[1]))
c = collections.Counter(r[4] for r in made)
print(f"  {len(made)} files written to {OUT}")
print(f"    {c['double']} doubled, {c['halve']} halved")
for g in sorted(WANT, key=lambda x: int(x[1:])):
    print(f"    {g:<6}{sum(1 for r in made if r[0]==g):>4}")
if skipped:
    print(f"  skipped {len(skipped)}: " + ", ".join(f"{n} ({why})" for n, why in skipped[:4]))
