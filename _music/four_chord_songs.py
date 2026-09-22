#!/usr/bin/env python3
"""Which songs use each named 4-chord palette.

A section counts for a group when the set of DIATONIC chords it uses is exactly
that group's four. Sections are deduped per song, so four verses on one palette
count once. Borrowed/applied chords are ignored for matching but reported, so a
section that is otherwise CATFISH with one A# still shows up -- that is usually
the interesting case rather than a disqualification.
"""
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

GROUPS = {
    'GOOSEFISH': (1,4,5,6), 'CATFISH': (1,2,4,5), 'SCOTTISH': (1,2,5,6),
    'CAMOUFLAGE': (1,3,4,5), 'FOXHOUND': (1,2,4,6), 'EXAMINATION': (1,3,5,6),
    'EVANGELIST': (2,4,5,6), 'FLUMMOX': (1,3,4,6), 'LOCOMOTIVE': (1,2,3,4),
    'CHECKMATE': (1,2,3,5), 'MISCHIEF': (3,4,5,6), 'CHIEFDOM': (2,3,4,5),
    'MASCOT': (1,2,3,6), 'MAJESTY': (2,3,5,6), 'MISFIT': (2,3,4,6),
}
BY_SET = {frozenset(v): k for k, v in GROUPS.items()}
# The GROUP definitions are in major white notes by construction -- GOOSEFISH
# IS C F G Am -- so this map renders the canonical form of a group, not the
# chords of any particular song. Matching is on DEGREE SETS, which are
# key-independent; in a minor song degrees 1 4 5 6 sound as Am Dm Em F.
NAME = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'Bdim'}

hits = collections.defaultdict(set)
outside = collections.defaultdict(set)
for name, d, nb in corpus.songs():
    for nm, st, en in corpus.sections(d):
        part = [c for c in d['chords'] if st <= c['beat'] < en]
        if len(part) < 4: continue
        dia, extra = set(), False
        for c in part:
            if c.get('borrowed') or c.get('applied'):
                extra = True
            else:
                dia.add(c.get('root'))
        g = BY_SET.get(frozenset(dia))
        if g:
            (outside if extra else hits)[g].add(name)

print(f"  {'word':<13}{'chords':<18}{'clean':>6}{'+borrowed':>11}   examples")
for g, degs in sorted(GROUPS.items(), key=lambda kv: -len(hits[kv[0]])):
    ch = ' '.join(NAME[x] for x in degs)
    ex = ', '.join(sorted(s.split('_')[-1][:20] for s in hits[g])[:3])
    print(f"  {g:<13}{ch:<18}{len(hits[g]):>6}{len(outside[g]):>11}   {ex}")

json.dump({g: sorted(hits[g] | outside[g]) for g in GROUPS},
          open(os.path.expanduser('~/Desktop/four_chord_songs.json'), 'w'), indent=1)
print(f"\n  full lists -> ~/Desktop/four_chord_songs.json")
