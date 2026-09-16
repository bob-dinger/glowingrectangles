"""Batch-export all GP files (with sections + chord data) to Hookpad paste JSON.

Outputs to ~/Desktop/gp_pastes/{basename}.json
Writes summary CSV with per-song stats.
"""
import os, sys, glob, csv, traceback
sys.path.insert(0, os.path.dirname(__file__))

from gp_to_hookpad import gp_to_hookpad_paste
import json

OUT_DIR = os.path.expanduser('~/Desktop/gp_pastes')
SUMMARY = os.path.expanduser('~/Desktop/gp_pastes_summary.csv')
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    src = os.path.expanduser('~/Desktop/midi_files_gp5')
    paths = []
    for ext in ('.gp3','.gp4','.gp5','.gp','.gpx'):
        paths.extend(sorted(glob.glob(os.path.join(src, '*' + ext))))
    print(f'{len(paths)} GP files to attempt')

    rows = []
    for i, p in enumerate(paths, 1):
        bn = os.path.splitext(os.path.basename(p))[0]
        out = os.path.join(OUT_DIR, bn + '.txt')
        row = {'basename': bn, 'ext': os.path.splitext(p)[1]}
        try:
            paste = gp_to_hookpad_paste(p)
            n_chords = len(paste['chords'])
            n_notes = len(paste['notes'])
            n_sections = len(paste['sections'])
            row.update({
                'status': 'ok' if (n_chords > 0 and n_sections > 0) else 'thin',
                'chords': n_chords, 'notes': n_notes, 'sections': n_sections,
                'tempo': paste['tempos'][0]['bpm'],
                'key': paste['keys'][0]['tonic'] + ' ' + paste['keys'][0]['scale'],
                'meter': f'{paste["meters"][0]["numBeats"]}/4',
                'end_beat': paste['endBeat'],
            })
            if n_chords > 0 and n_sections > 0:
                open(out, 'w').write(json.dumps(paste, separators=(',', ':')))
        except Exception as e:
            row['status'] = 'error'
            row['error'] = f'{type(e).__name__}: {str(e)[:100]}'
        rows.append(row)
        if i <= 5 or i % 50 == 0:
            print(f'  [{i:3}/{len(paths)}] {row["status"]:6s} {bn} '
                  f'chords={row.get("chords","-")} sections={row.get("sections","-")}')

    fields = ['basename','ext','status','chords','notes','sections','tempo','key','meter','end_beat','error']
    with open(SUMMARY, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, '') for k in fields})

    # Summary stats
    from collections import Counter
    by_status = Counter(r['status'] for r in rows)
    print(f'\n=== status counts: {dict(by_status)} ===')
    by_ext_status = Counter((r['ext'], r['status']) for r in rows)
    for ext in sorted(set(r['ext'] for r in rows)):
        cnts = {s: by_ext_status[(ext, s)] for s in ('ok','thin','error')}
        print(f'  {ext}: {cnts}')
    print(f'\npastes written → {OUT_DIR}')
    print(f'summary → {SUMMARY}')

if __name__ == '__main__': main()
