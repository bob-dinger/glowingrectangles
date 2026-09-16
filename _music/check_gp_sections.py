"""Check how many parsed GP files have section markers, and what they look like."""
import os, glob, guitarpro
DIR = os.path.expanduser('~/Desktop/midi_files_gp5')

files = []
for ext in ('.gp3','.gp4','.gp5'):
    files.extend(sorted(glob.glob(os.path.join(DIR, '*'+ext))))

with_markers = 0
without = 0
sample_shown = 0
for f in files:
    try: s = guitarpro.parse(f)
    except: continue
    markers = [(i+1, h.marker.title) for i,h in enumerate(s.measureHeaders) if h.marker]
    if markers:
        with_markers += 1
        if sample_shown < 5:
            print(f'\n{os.path.basename(f)}  ({len(s.measureHeaders)} measures, tempo={s.tempo})')
            for m, t in markers: print(f'  m{m:3d}: {t}')
            sample_shown += 1
    else:
        without += 1

print(f'\n=== {with_markers}/{with_markers+without} files have section markers ===')
