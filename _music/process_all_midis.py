"""Score every MIDI in midi_files2 as GOOD/OK/POOR, write enriched CSV, copy GOOD ones to midi_files3.

Inputs: ~/Desktop/midi_files2/ + ~/Desktop/midi_files2.csv
Outputs:
  ~/Desktop/midi_files3/                  - copies of GOOD MIDIs only
  ~/Desktop/midi_files_scored.csv         - full catalog + quality column + inferred fields
"""
import os, csv, shutil, mido, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_midi_samples import analyze

SRC_DIR = os.path.expanduser('~/Desktop/midi_files2')
GOOD_DIR = os.path.expanduser('~/Desktop/midi_files3')
CSV_IN  = os.path.expanduser('~/Desktop/midi_files2.csv')
CSV_OUT = os.path.expanduser('~/Desktop/midi_files_scored.csv')
os.makedirs(GOOD_DIR, exist_ok=True)

rows = list(csv.DictReader(open(CSV_IN)))
print(f'scoring {len(rows)} MIDIs…')

out_rows = []
n_good = n_ok = n_poor = n_err = 0
for i, r in enumerate(rows, 1):
    if i % 200 == 0: print(f'  [{i}/{len(rows)}]  GOOD:{n_good}  OK:{n_ok}  POOR:{n_poor}  ERR:{n_err}')
    new_name = r.get('new_name')
    if not new_name or r.get('error'):
        out_rows.append({**r, 'quality': 'POOR', 'inferred_key': '', 'flags': r.get('error','')})
        n_err += 1; continue
    path = os.path.join(SRC_DIR, new_name)
    if not os.path.exists(path):
        out_rows.append({**r, 'quality': 'POOR', 'inferred_key': '', 'flags': 'missing'})
        n_err += 1; continue
    a = analyze(path)
    if a.get('error'):
        out_rows.append({**r, 'quality': 'POOR', 'inferred_key': '', 'flags': a['error']})
        n_err += 1; continue
    q = a.get('quality', 'POOR')
    flags = ','.join(a.get('flags', []))
    out_rows.append({**r, 'quality': q, 'inferred_key': a.get('inferred_key',''), 'flags': flags})
    if q == 'GOOD':
        n_good += 1
        shutil.copy2(path, os.path.join(GOOD_DIR, new_name))
    elif q == 'OK': n_ok += 1
    else: n_poor += 1

# Write CSV
fields = list(rows[0].keys()) + ['quality', 'inferred_key', 'flags']
# Dedupe field names while preserving order
seen = set(); fields = [f for f in fields if not (f in seen or seen.add(f))]
with open(CSV_OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in out_rows:
        w.writerow({k: r.get(k, '') for k in fields})

print(f'\nfinal: GOOD={n_good}  OK={n_ok}  POOR={n_poor}  ERR={n_err}')
print(f'GOOD copied → {GOOD_DIR}')
print(f'scored catalog → {CSV_OUT}')
