#!/usr/bin/env python3
"""
Add each song's CURRENT Hookpad bpm to ~/Desktop/tempos.csv and say what
needs changing.

Reads the local Hookpad export (not Supabase, which can be stale) and
classifies the relationship between what Hookpad has and what songbpm says:

    match     within 3% — leave it alone
    HALF      Hookpad is running at half the felt tempo
    DOUBLE    Hookpad is running at double
    DIFFERS   neither, and not a half/double artefact — look at it
    multi     the song has more than one tempo marking

    python3 tempos_compare.py
"""
import csv, glob, json, os, re

EXPORT = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
CSV    = os.path.expanduser('~/Desktop/tempos.csv')
TAGS   = ('_o', '_c', '_ly', '_j', '_')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def strip_tags(stem):
    s = stem.strip('_')
    changed = True
    while changed:
        changed = False
        for t in TAGS:
            if s.endswith(t):
                s, changed = s[:-len(t)], True
        n = re.sub(r'-[0-9a-f]{6}$', '', s)
        if n != s: s, changed = n, True
    return s


def index():
    """normalised 'artisttitle' -> list of file paths"""
    idx = {}
    for p in glob.glob(os.path.join(EXPORT, '*.json')):
        key = norm(strip_tags(os.path.splitext(os.path.basename(p))[0]))
        idx.setdefault(key, []).append(p)
    return idx


def find(artist, title, idx):
    a, t = norm(artist), norm(title)
    want = a + t
    if want in idx: return idx[want]
    # substring both ways — filenames carry extra words and so do titles
    hits = [p for k, ps in idx.items() if a and t and a in k and t in k for p in ps]
    if hits: return hits
    # title alone, when the guitar list and Hookpad credit different artists
    hits = [p for k, ps in idx.items() if t and len(t) >= 8 and t in k for p in ps]
    return hits


def tempos_of(path):
    try:
        d = json.load(open(path))
    except Exception:
        return []
    return [t.get('bpm') for t in (d.get('tempos') or []) if t.get('bpm')]


def verdict(hp, sb):
    if not hp or not sb: return ''
    r = hp / sb
    if 0.97 <= r <= 1.03: return 'match'
    if 0.47 <= r <= 0.53: return 'HALF'
    if 1.90 <= r <= 2.10: return 'DOUBLE'
    return 'DIFFERS'


def main():
    idx = index()
    rows = list(csv.DictReader(open(CSV)))
    for r in rows:
        paths = find(r['artist'], r['title'], idx)
        bpms = []
        for p in paths[:1]:                      # first match only
            bpms = tempos_of(p)
        r['hookpad_file'] = os.path.basename(paths[0]) if paths else ''
        r['hookpad_bpm']  = bpms[0] if bpms else ''
        r['hookpad_multi'] = 'multi:' + ','.join(str(b) for b in bpms) if len(bpms) > 1 else ''
        try:
            r['verdict'] = verdict(float(r['hookpad_bpm']), float(r['bpm']))
        except (TypeError, ValueError):
            r['verdict'] = 'no hookpad file' if not paths else 'no songbpm'

    fields = list(rows[0].keys())
    with open(CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    print(f"{'song':<32}{'your key':<16}{'sbpm':>6}{'hookpad':>9}  verdict")
    print('-' * 84)
    for r in rows:
        print(f"{r['title'][:30]:<32}{r['your_key'][:14]:<16}"
              f"{(r['bpm'] or '—'):>6}{(str(r['hookpad_bpm']) or '—'):>9}  "
              f"{r['verdict']}{' ' + r['hookpad_multi'] if r['hookpad_multi'] else ''}")

    import collections
    print('\n' + str(dict(collections.Counter(r['verdict'] for r in rows))))
    print(f'-> {CSV}')


if __name__ == '__main__':
    main()
