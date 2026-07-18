"""16-measure sections as four 4-bar phrases: label the form (AABA, AABC, ABAC...).

Runs the labelling TWICE — once over the chord progression, once over the melody —
because the two pillars often disagree, and the disagreement is the interesting part
(a section can be AABA in chords while its melody is AABC).
"""
import os, re, json, argparse
from collections import defaultdict
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label

BARS = 4          # phrase length in measures
PRIME = 0.55      # >= this much shared opening (by duration) = a prime (A'), not a new letter

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def coretok(t):
    """bare roman numeral — drop 7ths/adds/sus so A and A' don't split on a passing 7th."""
    if '°' in t:
        m = re.match(r'^(vii°7?(?:/[b#]*[ivxIVX]+)?)', t); return m.group(1) if m else t
    m = re.match(r'^([b#]*[ivxIVX]+(?:/[b#]*[ivxIVX]+)?)', t); return m.group(1) if m else t

def phrase_chords(hj, b0, b1, scale):
    """(token, start-offset, duration) for each chord in [b0,b1), clipped to the window."""
    out = []
    for c in hj.get('chords') or []:
        if not c.get('root') or not 1 <= c['root'] <= 7: continue
        cb, cd = c.get('beat', 0), c.get('duration', 1)
        s, e = max(cb, b0), min(cb + cd, b1)
        if e > s: out.append((coretok(chord_label(c, scale)), round(s - b0, 3), round(e - s, 3)))
    return tuple(sorted(out, key=lambda x: x[1]))

def phrase_notes(hj, b0, b1):
    """(scale-degree, octave, start-offset, duration) for melody notes starting in the window."""
    out = []
    for n in hj.get('notes') or []:
        nb = n.get('beat', 0)
        if not b0 <= nb < b1 or n.get('isRest'): continue
        sd = n.get('scaleDegree', n.get('sd'))
        if sd is None: continue
        out.append((str(sd), n.get('octave', n.get('o', 0)), round(nb - b0, 3), round(n.get('duration', 1), 3)))
    return tuple(sorted(out, key=lambda x: x[2]))

def overlap(a, b):
    """shared opening as a fraction of the longer phrase — how far they agree before diverging."""
    if not a or not b: return 1.0 if a == b else 0.0
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]: i += 1
    return i / max(len(a), len(b))

def melsim(a, b):
    """Melodic likeness, 0-1. Two sung phrases are 'the same' when they land on the same
    beats with the same contour — never note-identical, since the lyrics differ."""
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    ra, rb = {n[2] for n in a}, {n[2] for n in b}         # onsets = rhythm
    rhythm = len(ra & rb) / len(ra | rb)
    pa, pb = {n[2]: (n[0], n[1]) for n in a}, {n[2]: (n[0], n[1]) for n in b}
    shared = ra & rb
    pitch = sum(pa[o] == pb[o] for o in shared) / len(shared) if shared else 0.0
    return 0.6 * rhythm + 0.4 * pitch                      # rhythm carries the phrase identity

def label(phrases, sim=None, same=0.80):
    """assign letters: alike -> same letter, shared opening -> prime, else new letter.
    `sim` supplies fuzzy comparison (melody); without it, equality is exact (chords)."""
    reps, out = [], []          # reps: (letter, phrase) first sighting of each letter
    for p in phrases:
        hit = None
        for letter, rep in reps:
            if (sim(p, rep) >= same) if sim else (p == rep): hit = letter; break
        if hit is None:
            for letter, rep in reps:
                near = sim(p, rep) if sim else overlap(p, rep)
                if near >= PRIME: hit = letter + "'"; break
        if hit is None:
            hit = chr(ord('A') + len(reps)); reps.append((hit, p))
        out.append(hit)
    return ''.join(out)

def sections(hj, want):
    """yield (name, b0, b1, measures, beats-per-bar) for every span of `want` measures.

    A 16-bar form isn't always one Hookpad section — Things We Said Today carries it as
    verse(8)+pre-chorus(4)+chorus(4). So scan runs of consecutive sections too, and only
    fall back to a run when no single section already covers that span.
    """
    npb = ((hj.get('meters') or [{}])[0].get('numBeats')) or 4
    secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
    if not secs: return
    end = hj.get('endBeat', 0) + 1
    bounds = [(s.get('name', ''), s.get('beat', 0),
               secs[i + 1]['beat'] if i + 1 < len(secs) else end) for i, s in enumerate(secs)]
    singles = set()
    for nm, b0, b1 in bounds:
        if b1 > b0 and (b1 - b0) % npb == 0 and (b1 - b0) // npb == want:
            singles.add(b0)
            yield nm, b0, b1, want, npb
    for i in range(len(bounds)):
        if bounds[i][1] in singles: continue
        for j in range(i + 1, min(i + 4, len(bounds))):     # runs of 2-4 sections
            b0, b1 = bounds[i][1], bounds[j][2]
            if (b1 - b0) % npb: break
            m = (b1 - b0) // npb
            if m > want: break
            if m == want:
                yield '+'.join(b[0][:8] for b in bounds[i:j + 1]), b0, b1, want, npb
                break

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artist', default='beatle')
    ap.add_argument('--measures', type=int, default=16)
    ap.add_argument('--form', help='only show this form, e.g. AABA')
    ap.add_argument('--json', help='write full results here')
    a = ap.parse_args()

    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select artist,title,hookpad_json from parcels.songs "
                "where has_chords and hookpad_json is not null and lower(artist) like %s", ('%' + a.artist.lower() + '%',))
    rows = cur.fetchall(); c.close()
    # duplicate rows per song are common; keep the most fully-transcribed one
    rows.sort(key=lambda r: -(len((r[2] or {}).get('notes') or []) + len((r[2] or {}).get('chords') or [])))

    seen, out = set(), []
    for artist, title, hj in rows:
        t = (title or '').strip()
        # skip the -simple/-hooktab/-Right style variants; keep one row per song
        if not t or re.search(r'[-_](simple|hooktab|right|wrong|\d+|[A-G]b?|mixolydian|ly_o_COMPLETED)$', t, re.I): continue
        k = norm(t)
        if k in seen: continue
        seen.add(k)
        scale = (hj.get('keys') or [{}])[0].get('scale', 'major')
        scale = scale if scale in ('major', 'minor') else 'major'
        dupe = set()
        for name, b0, b1, meas, npb in sections(hj, a.measures):
            step = BARS * npb
            wins = [(b0 + i * step, b0 + (i + 1) * step) for i in range((b1 - b0) // step)]
            if len(wins) < 2: continue
            ch_ph = [phrase_chords(hj, w0, w1, scale) for w0, w1 in wins]
            # a song's 3 identical verses are one form, not three
            sig = (norm(name), tuple(ch_ph))
            if sig in dupe: continue
            dupe.add(sig)
            ch = label(ch_ph)
            mel_ph = [phrase_notes(hj, w0, w1) for w0, w1 in wins]
            mel = label(mel_ph, sim=melsim) if any(mel_ph) else ''
            out.append({'artist': artist, 'title': t, 'sec': name, 'beat': b0,
                        'grouped': '+' in name,
                        'chord_form': ch, 'melody_form': mel,
                        'romans': [' '.join(x[0] for x in phrase_chords(hj, w0, w1, scale)) for w0, w1 in wins]})

    if a.form: out = [o for o in out if a.form in (o['chord_form'], o['melody_form'])]
    single = [o for o in out if not o['grouped']]
    tally = defaultdict(int)
    for o in single: tally[o['chord_form']] += 1
    print(f"{len(seen)} songs · {len(single)} {a.measures}-measure sections "
          f"(+{len(out)-len(single)} spans stitched from consecutive sections)\n")
    print('chord form   n   (single sections only)')
    for f, n in sorted(tally.items(), key=lambda kv: -kv[1])[:14]:
        print(f'  {f:<10} {n}')
    for grp, rows_ in (('SECTIONS', single), ('STITCHED SPANS', [o for o in out if o['grouped']])):
        print(f'\n--- {grp} ---')
        for o in sorted(rows_, key=lambda o: (o['chord_form'], o['title'].lower())):
            mm = '(no melody)' if not o['melody_form'] else \
                 ('= chords' if o['melody_form'] == o['chord_form'] else o['melody_form'])
            print(f"chords {o['chord_form']:<7} melody {mm:<12} {o['title'][:32]:<34} {o['sec'][:18]}")
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)
        print(f'\nwrote {a.json}')

if __name__ == '__main__':
    main()
