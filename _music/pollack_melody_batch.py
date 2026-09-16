"""Batch-extract melodies for the no-melody Beatles targets.

For each target: locate its MIDI (downloaded or local), read its Hookpad key,
extract the melody line, write a melody-only paste to ~/Desktop/pollack_pastes/,
and report a quality flag so low-confidence extractions are easy to spot.
"""
import os, re, glob, json
import psycopg2
from dotenv import load_dotenv
from midi_melody_extract import build
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

OUT = os.path.expanduser('~/Desktop/pollack_pastes')
MIDI_DIRS = ['~/Desktop/midi_files_beatles_new', '~/Desktop/midi_files3',
             '~/Desktop/midi_files', '~/Desktop/midis', '~/Desktop']
os.makedirs(OUT, exist_ok=True)

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def index_midis():
    idx = {}
    for d in MIDI_DIRS:
        for p in glob.glob(os.path.expanduser(d) + '/**/*.mid', recursive=True):
            b = os.path.basename(p).rsplit('.mid', 1)[0]
            b = re.sub(r'^(beatles[-_]midis?[-_]|beatles[-_]|the[-_]beatles[-_])', '', b, flags=re.I)
            idx.setdefault(norm(b), p)               # first wins (downloaded dir is first)
    return idx

def find_midi(title, idx):
    nt = norm(title)
    if nt in idx: return idx[nt]
    for k, p in idx.items():                          # substring fallback
        if nt and (nt in k or k in nt) and len(k) > 6: return p
    return None

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("""select distinct on (lower(title)) title, key_tonic, key_scale
        from parcels.songs where artist ilike '%beatl%' and has_sections and not has_melody
        order by lower(title)""")
    targets = cur.fetchall()
    idx = index_midis()
    rows = []
    for title, kt, ks in targets:
        midi = find_midi(title, idx)
        if not midi:
            rows.append((title, 'NO-MIDI', None)); continue
        if not kt:
            rows.append((title, 'NO-KEY', os.path.basename(midi))); continue
        tonic = kt.split()[0] if ' ' in kt else kt
        scale = (ks or 'major')
        try:
            res = build(midi, tonic, scale,
                        os.path.join(OUT, 'melody_' + norm(title) + '.txt'), quiet=True)
        except Exception as e:
            rows.append((title, f'ERR:{e}', os.path.basename(midi))); continue
        if not res:
            rows.append((title, 'NO-TRACK', os.path.basename(midi))); continue
        obj, m = res
        # quality flag
        if m['named_melody'] and m['mono'] >= 0.6: q = 'good'
        elif m['named_melody'] or m['mono'] >= 0.75: q = 'ok'
        else: q = 'check'
        rows.append((title, q, m))
    # report
    order = {'good': 0, 'ok': 1, 'check': 2}
    def sortkey(r): return (order.get(r[1], 3), r[0])
    print(f"{'FLAG':6} {'TITLE':34} {'TRACK':18} notes mono named")
    for title, flag, m in sorted(rows, key=sortkey):
        if isinstance(m, dict):
            print(f"{flag:6} {title[:34]:34} {str(m['track'])[:18]:18} {m['n_notes']:>5} {m['mono']:.0%}  {m['named_melody']}")
        else:
            print(f"{flag:6} {title[:34]:34} {m or ''}")
    good = sum(1 for _, f, _ in rows if f == 'good')
    ok = sum(1 for _, f, _ in rows if f == 'ok')
    check = sum(1 for _, f, _ in rows if f == 'check')
    prob = sum(1 for _, f, _ in rows if f not in ('good', 'ok', 'check'))
    print(f"\ngood={good}  ok={ok}  check={check}  problem={prob}  (of {len(rows)})")

if __name__ == '__main__':
    main()
