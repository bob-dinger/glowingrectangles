#!/usr/bin/env python3
"""Melody shape for every section of the 405 complete songs (G50-G250 + Beatles).

parcels.melodies has palettes for 464 sections; this derives the same measures
for all 2,533 straight from the Hookpad files. The core rule is
annotate_melody.py's and reproduces its output on 129 of 143 checkable rows
(90%) -- the rest look like hand corrections, which that script invites.

    core     degrees holding >= 15% of the section's note DURATION
    reach    everything else the melody touches
    stretch  diatonic span, low note to high, in steps
    home     the single degree with the most time
    landing  the last sounding note, and the chord under it
"""
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

WANT = {'G50', 'G100', 'G150', 'G200', 'G250'}
# the parts that carry a song. The user: "I'm not as interested in outros and
# intros and solos. we do need pre-chorus's however."
ROLES = ['pre-chorus', 'chorus', 'verse', 'bridge']
STEP = {'1':0, '2':1, '3':2, '4':3, '5':4, '6':5, '7':6}

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

def deg(sd):
    m = re.search(r'\d', str(sd))
    return m.group(0) if m else None

pool = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pool_map.json')))
P = {norm(debase(k)): v for k, v in pool.items() if v in WANT}

rows = []
for name, d, nb in corpus.songs():
    artist, _, title = name.partition('_')
    grp = P.get(norm(debase(name)))
    if not (grp or artist.lower().startswith('beatles')):
        continue
    bpm = (d.get('tempos') or [{}])[0].get('bpm')
    if not (d.get('notes') and d.get('sections') and bpm and round(bpm) != 120):
        continue
    notes = [n for n in d['notes'] if not n.get('isRest')]
    seen_mel = set()
    for sec, st, en in corpus.sections(d):
        r = None
        low = re.sub(r'\b(i{1,3}|iv|v|\d+|first|second|third|final|last|half|alt)\b',
                     '', sec.lower().strip()).replace('prechorus', 'pre-chorus')
        for k in ROLES:
            if k in low: r = k; break
        if not r:
            continue
        ns = sorted([n for n in notes if st <= n['beat'] < en], key=lambda n: n['beat'])
        if len(ns) < 4:
            continue
        # a song with three identical verses is one melody to learn
        sig = tuple((str(n.get('sd')), n.get('octave'), round(n['beat'] - st, 3),
                     n['duration']) for n in ns)
        if sig in seen_mel:
            continue
        seen_mel.add(sig)
        dur = collections.Counter()
        for n in ns:
            dur[str(n.get('sd'))] += n['duration']
        tot = sum(dur.values())
        ranked = sorted(dur.items(), key=lambda kv: -kv[1])
        core = [k for k, v in ranked if v / tot >= 0.15]
        reach = [k for k, v in ranked if v / tot < 0.15]
        idx = [STEP.get(deg(n['sd']), 0) + 7 * int(n.get('octave', 0)) for n in ns]
        last = ns[-1]
        under = None
        for c in sorted(d['chords'], key=lambda c: c['beat']):
            if corpus.is_unreadable(c):
                continue
            if c['beat'] <= last['beat'] + 1e-6:
                under = c
            else:
                break
        rows.append({
            'group': grp or 'beatles', 'artist': artist.title(), 'song': title.title(),
            'section': sec, 'role': r, 'bpm': round(bpm), 'mode': corpus.mode_at(d, st),
            'core': core, 'reach': reach, 'stretch': max(idx) - min(idx) + 1,
            'home': ranked[0][0], 'landing': str(last.get('sd')),
            'chord': corpus.chord_name(under, corpus.mode_at(d, under['beat'])) if under else '?',
            'notes': len(ns), 'file': name,
        })

json.dump(rows, open(os.path.expanduser('~/Desktop/melody_map.json'), 'w'), indent=1)
print(f"  {len(rows):,} sections from {len({r['file'] for r in rows}):,} songs")
cs = collections.Counter(tuple(sorted(r['core'], key=lambda s:(len(s),s))) for r in rows)
print(f"  {len(cs):,} distinct core sets; sizes "
      f"{dict(sorted(collections.Counter(len(r['core']) for r in rows).items()))}\n")
print(f"  {'core':<14}{'sections':>9}")
for k, v in cs.most_common(10):
    print(f"  {' '.join(k):<14}{v:>9}")
print(f"\n  -> ~/Desktop/melody_map.json")
