"""Re-identify .bin files in midi_files_gp5/ and rename to correct extension. Validate parses."""
import os, re, glob
import guitarpro

DIR = os.path.expanduser('~/Desktop/midi_files_gp5')

def detect(body):
    if b'FICHIER GUITAR PRO' in body[:32]:
        m = re.search(rb'v(\d)\.\d\d', body[:64])
        return f'.gp{m.group(1).decode()}' if m else '.gp5'
    if body[:4] == b'BCFZ': return '.gpx'
    if body[:4] == b'ptab': return '.ptb'
    if body[:4] == b'PK\x03\x04': return '.gp'
    return None

renames = []
for f in sorted(glob.glob(os.path.join(DIR, '*.bin'))):
    body = open(f, 'rb').read(64)
    ext = detect(body)
    if not ext:
        print(f'?? unknown: {os.path.basename(f)}'); continue
    new = f[:-4] + ext
    os.rename(f, new)
    renames.append((os.path.basename(f), os.path.basename(new)))

by_ext = {}
for _, n in renames:
    e = os.path.splitext(n)[1]
    by_ext[e] = by_ext.get(e, 0) + 1
print(f'renamed {len(renames)} files:')
for e, c in sorted(by_ext.items()): print(f'  {e}: {c}')

# Now validate parses for all .gp3/.gp4/.gp5
ok = parse_err = 0
errs = []
for ext in ['.gp3', '.gp4', '.gp5']:
    for f in sorted(glob.glob(os.path.join(DIR, '*'+ext))):
        try:
            s = guitarpro.parse(f)
            _ = (s.tempo, len(s.measureHeaders), len(s.tracks))
            ok += 1
        except Exception as e:
            parse_err += 1
            errs.append((os.path.basename(f), str(e)[:80]))
print(f'\nparse: {ok} ok, {parse_err} errors')
for n, e in errs[:10]: print(f'  ✗ {n}: {e}')
