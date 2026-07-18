"""Re-frame a song at double (or half) the metric level and emit a Hookpad paste.

Same music, different notation: Interstate Love Song's verse is 6.5 measures at 84bpm,
which is exactly 13 measures at 168. Nothing about the sound changes — only what counts
as a bar. Saved as a `<base>-double` variant so it sits next to the original.

Beat coordinates are 1-INDEXED in Hookpad, so scaling is (beat-1)*F+1, not beat*F.

  python double_song.py --title "Interstate Love Song"
  python double_song.py --title "Piggies" --factor 0.5     # halve instead
  python double_song.py --candidates                        # find songs worth doubling
"""
import os, re, json, argparse
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

OUTDIR = os.path.expanduser('~/Desktop/double_pastes')

def conn():
    return psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
                            user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                            port=os.environ.get('DB_PORT', 5432))

def num(x):
    """keep whole values as ints — Hookpad rejects 4.0 where it wants 4"""
    if x is None: return None
    f = float(x)
    return int(f) if f == int(f) else f

def scale_beat(b, F): return num((float(b) - 1) * F + 1)
def scale_dur(d, F):  return num(float(d) * F)

def double(hj, F):
    """scale every beat coordinate and duration; tempo moves the opposite way"""
    out = {'version': 1}
    out['chords'] = [{'root': c.get('root'), 'beat': scale_beat(c.get('beat', 1), F),
                      'duration': scale_dur(c.get('duration', 1), F),
                      'type': int(c.get('type', 5)) if str(c.get('type', 5)).lstrip('-').isdigit() else c.get('type'),
                      'inversion': c.get('inversion', 0), 'applied': c.get('applied', 0),
                      'adds': c.get('adds', []), 'omits': c.get('omits', []),
                      'alterations': c.get('alterations', []), 'suspensions': c.get('suspensions', []),
                      'substitutions': c.get('substitutions', []), 'pedal': c.get('pedal'),
                      'alternate': c.get('alternate', 0), 'borrowed': c.get('borrowed', ''),
                      'isRest': c.get('isRest', False), 'recordingEndBeat': None}
                     for c in (hj.get('chords') or [])]
    out['notes'] = [{'sd': str(n.get('sd')), 'octave': int(n.get('octave', 0)),
                     'beat': scale_beat(n.get('beat', 1), F),
                     'duration': scale_dur(n.get('duration', 1), F),
                     'isRest': n.get('isRest', False), 'recordingEndBeat': None}
                    for n in (hj.get('notes') or [])]
    out['keys'] = [{'beat': scale_beat(k.get('beat', 1), F), 'scale': k.get('scale', 'major'),
                    'tonic': k.get('tonic', 0)} for k in (hj.get('keys') or [{'beat': 1}])]
    # the whole point: bars get shorter, so the pulse gets faster by the same factor
    out['tempos'] = [{'beat': scale_beat(t.get('beat', 1), F), 'bpm': num(t.get('bpm', 120) * F),
                      'swingFactor': t.get('swingFactor', 0), 'swingBeat': t.get('swingBeat', 0.5)}
                     for t in (hj.get('tempos') or [{'beat': 1, 'bpm': 120}])]
    out['meters'] = [{'beat': scale_beat(m.get('beat', 1), F), 'numBeats': m.get('numBeats', 4),
                      'beatUnit': m.get('beatUnit', 1)} for m in (hj.get('meters') or [{'beat': 1}])]
    out['breaks'] = [{'beat': scale_beat(b['beat'], F)} for b in (hj.get('breaks') or [])]
    out['sections'] = [{'beat': scale_beat(s.get('beat', 1), F), 'name': s.get('name', '')}
                       for s in (hj.get('sections') or [])]
    out['endBeat'] = scale_beat(hj.get('endBeat', 1), F)
    out['audioTracks'] = []
    return out

def measures(hj):
    """(section name, measures) using the meter — fractional counts are the tell"""
    npb = ((hj.get('meters') or [{}])[0].get('numBeats')) or 4
    secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
    end = hj.get('endBeat', 0) + 1
    return [(s.get('name', ''), ((secs[i+1]['beat'] if i+1 < len(secs) else end) - s['beat']) / npb)
            for i, s in enumerate(secs)]

def candidates(cur, limit=30):
    """songs whose sections land on half-measures — the doubling signature"""
    cur.execute("select artist,title,bpm,hookpad_json from parcels.songs "
                "where has_chords and hookpad_json is not null")
    out = []
    for a, t, bpm, hj in cur.fetchall():
        if not t or re.search(r'[-_](simple|hooktab|double|half)$', t, re.I): continue
        ms = [m for _, m in measures(hj) if m > 0.5]
        if not ms: continue
        half = sum(1 for m in ms if abs(m * 2 - round(m * 2)) < .01 and abs(m - round(m)) > .01)
        if half >= 2:
            out.append((half, len(ms), a or '', t, bpm,
                        ', '.join(f'{n[:8]}={m:g}' for n, m in measures(hj) if m > 0.5)[:70]))
    out.sort(key=lambda r: -r[0])
    return out[:limit]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title'); ap.add_argument('--factor', type=float, default=2.0)
    ap.add_argument('--candidates', action='store_true')
    a = ap.parse_args()
    c = conn(); cur = c.cursor()

    if a.candidates:
        rows = candidates(cur)
        print(f'{len(rows)} songs with half-measure sections (doubling candidates)\n')
        for half, tot, art, t, bpm, secs in rows:
            print(f'{half}/{tot} odd  {art[:16]:18} {t[:26]:28} {str(bpm):>5}bpm  {secs}')
        c.close(); return

    cur.execute("select artist,title,bpm,hookpad_json from parcels.songs where lower(title) like %s "
                "and hookpad_json is not null order by jsonb_array_length(coalesce(hookpad_json->'notes','[]')) desc",
                ('%' + a.title.lower() + '%',))
    got = cur.fetchall(); c.close()
    if not got: print(f'no song matching {a.title!r}'); return
    art, title, bpm, hj = got[0]
    F = a.factor
    tag = 'double' if F == 2 else ('half' if F == 0.5 else f'x{F:g}')
    print(f'{art} / {title}  ({len(got)} row(s), using the most complete)')
    print(f'  before: {(hj.get("tempos") or [{}])[0].get("bpm", bpm)} bpm')
    for n, m in measures(hj):
        if m > 0.25: print(f'     {n[:14]:16} {m:g} bars')
    new = double(hj, F)
    print(f'  after:  {new["tempos"][0]["bpm"]} bpm')
    for n, m in measures(new):
        if m > 0.25: print(f'     {n[:14]:16} {m:g} bars')
    os.makedirs(OUTDIR, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    # .txt so it opens as plain text for copying — never .json
    path = os.path.join(OUTDIR, f'{slug}-{tag}.txt')
    open(path, 'w').write(json.dumps(new, separators=(',', ':')))
    print(f'\nwrote {path}\n  paste into an empty Hookpad song, save as "{title}-{tag}"')

if __name__ == '__main__':
    main()
