#!/usr/bin/env python3
"""The live Hookpad songs that have no chords entered, as a worklist.

Excludes rename orphans (files whose name no longer matches anything in the
account) and the user's own music_* scratch projects.

The two columns that decide priority:
  melody notes      - a song with a melody already in is half-built
  sibling w/ chords - a variant (-hooktab, -simple, -C ...) of the same base
                      name that DOES have chords, so they can be copied over
"""
import json, glob, os, re, collections
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
# Lowercased: a song renamed in Hookpad only for capitalisation keeps its old
# filename on this (case-insensitive) disk, so exact matching drops it from the
# census AND counts it as a rename orphan. That hid 52 songs, 24 with chords.
SCRATCH = re.compile(r'^(music_|perms_|mine[_\d]|\d+-\d+-\d+)', re.I)
def is_scratch(name):
    """The user's own generated workbenches, not songs: perms_* permutation
    dumps (one has 288 "sections"), music_* riff projects, everything under
    mine_* and mine<number> (the user's own writing -- 60 files), and date-named scratch files. They are real Hookpad entries, so the account list does not
    exclude them, but they skew every census."""
    return bool(SCRATCH.match(name))

live = {s['song'].replace('/', '_').lower()
        for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')))}
TAG = re.compile(r'-(hooktab\d*|simple|melodies?|perfectMelody|mixolydian|right|wrong|'
                 r'double|solo|o|c|ly|\d+|[A-G]b?#?)$', re.I)
def base(n):
    prev = None
    while prev != n:
        prev = n; n = TAG.sub('', n)
    return n.strip('_- ')

rows, haschords = [], collections.defaultdict(bool)
info = {}
for f in glob.glob(f"{D}/*.json"):
    n = os.path.basename(f)[:-5]
    if n.lower() not in live or is_scratch(n): continue
    try: d = json.load(open(f))
    except Exception: continue
    ch = d.get('chords') or []
    haschords[base(n).lower()] |= bool(ch)
    info[n] = (d, ch)

for n, (d, ch) in sorted(info.items()):
    if ch: continue
    a, _, t = n.partition('_')
    notes = len(d.get('notes') or [])
    secs = len(d.get('sections') or [])
    k = (d.get('keys') or [{}])[0]
    tonic = k.get('tonic') if isinstance(k, dict) else None
    scale = k.get('scale') if isinstance(k, dict) else None
    bpm = (d.get('tempos') or [{}])[0].get('bpm')
    rows.append([a.title(), t.title(), n, notes, secs,
                 f"{tonic or ''} {scale or ''}".strip(),
                 bpm and round(bpm),
                 "yes" if haschords.get(base(n).lower()) else ""])

rows.sort(key=lambda r: (-r[3], r[0], r[1]))     # melody-first = closest to done

wb = Workbook(); ws = wb.active; ws.title = "Chordless"
cols = [("Artist",26),("Title",42),("Hookpad file",50),("Melody notes",13),
        ("Sections",10),("Key",14),("BPM",7),("Sibling has chords",18)]
ws.append([c for c,_ in cols])
for i,(_,w) in enumerate(cols,1): ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]: c.font = Font(bold=True)
ws.freeze_panes = "A2"
for r in rows: ws.append(r)

out = os.path.expanduser('~/Desktop/hookpad_chordless.xlsx')
wb.save(out)
withmel = sum(1 for r in rows if r[3] > 0)
withsib = sum(1 for r in rows if r[7])
print(f"  {len(rows):,} songs with no chords")
print(f"    {withmel:,} already have a melody entered")
print(f"    {withsib:,} have a sibling variant that DOES have chords")
print(f"  {out}")
