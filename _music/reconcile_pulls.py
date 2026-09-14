#!/usr/bin/env python3
"""
After a re-pull, archive the superseded copies.

download_one.py names a file from the song title alone, so it cannot overwrite
an existing file carrying tag suffixes (_o, _c, _ly, _j). The result is two
files for one song, and pp.find() returns whichever the glob reaches first —
so the analysis can silently keep reading the stale copy.

Those suffixes are safe to lose: every reference to them in this directory is
inside a strip-for-matching helper. Nothing reads them for meaning.

    python3 reconcile_pulls.py --since "2026-09-14"        # dry run
    python3 reconcile_pulls.py --since "2026-09-14" --go
"""
import argparse, datetime, glob, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_pools as pp

EXPORT = os.path.expanduser('~/Desktop/music/hookpad_songs_full')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', required=True, help='YYYY-MM-DD; files newer are "new"')
    ap.add_argument('--dir', default=EXPORT)
    ap.add_argument('--archive', default=None)
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()
    cutoff = datetime.datetime.strptime(a.since, '%Y-%m-%d').timestamp()
    arch = a.archive or os.path.join(a.dir, 'superseded')

    files = glob.glob(os.path.join(a.dir, '*.json'))
    groups = {}
    for p in files:
        k = pp.norm(pp.strip_tags(os.path.splitext(os.path.basename(p))[0]))
        groups.setdefault(k, []).append(p)

    pairs = []
    for k, ps in groups.items():
        if len(ps) < 2: continue
        new = [p for p in ps if os.path.getmtime(p) >= cutoff]
        old = [p for p in ps if os.path.getmtime(p) < cutoff]
        if not new or not old: continue          # not a pull duplicate
        pairs.append((sorted(new)[0], old))

    print(f'{len(pairs)} songs have a freshly pulled copy plus older ones\n')
    n = 0
    for new, old in sorted(pairs):
        print(f'  keep    {os.path.basename(new)}')
        for o in old:
            age = datetime.datetime.fromtimestamp(os.path.getmtime(o))
            print(f'  archive {os.path.basename(o)}   ({age:%Y-%m-%d})')
            n += 1
            if a.go:
                os.makedirs(arch, exist_ok=True)
                shutil.move(o, os.path.join(arch, os.path.basename(o)))
    print(f'\n{n} files {"moved to " + arch if a.go else "would be archived (dry run)"}')
    if not a.go: print('add --go to do it')


if __name__ == '__main__':
    main()
