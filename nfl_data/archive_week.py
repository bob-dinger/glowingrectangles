#!/usr/bin/env python3
"""
Snapshot this week's nflverse files before they get overwritten.

nflverse publishes ONE file per dataset per season and rewrites it in place as
games are played. So play_by_play_2026.csv today is not the file it was last
Tuesday, and there is no way to get the earlier version back. If you want to
look at what week 3 looked like before week 4 was added — or to check whether
a figure you published has since been revised — you need your own copy.

Writes nfl_data/archive/<YYYY-MM-DD>/ and skips a dataset whose bytes are
unchanged since the last snapshot, so running it daily costs almost nothing.

    python3 archive_week.py
    python3 archive_week.py --season 2026 --only pbp,ftn_charting
"""
import argparse, datetime, hashlib, os, shutil, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 'https://github.com/nflverse/nflverse-data/releases/download'

# release tag -> file stem. Only the ones that actually change in-season.
SETS = {
    'pbp':            'play_by_play',
    'ftn_charting':   'ftn_charting',
    'snap_counts':    'snap_counts',
    'stats_player':   'stats_player_week',
    'stats_team':     'stats_team_week',
    'injuries':       'injuries',
    'weekly_rosters': 'roster_weekly',
    'depth_charts':   'depth_charts',
    'pfr_advstats_pass': 'advstats_week_pass',
    'pfr_advstats_rush': 'advstats_week_rush',
    'pfr_advstats_rec':  'advstats_week_rec',
    'pfr_advstats_def':  'advstats_week_def',
}
TAG = {k: ('pfr_advstats' if k.startswith('pfr_advstats') else k) for k in SETS}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def latest_prior(name, today):
    """the newest previous snapshot of this file, if any"""
    root = os.path.join(HERE, 'archive')
    if not os.path.isdir(root): return None
    for d in sorted(os.listdir(root), reverse=True):
        if d >= today: continue
        p = os.path.join(root, d, name)
        if os.path.exists(p): return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', default=str(datetime.date.today().year))
    ap.add_argument('--only', default=None, help='comma list of keys')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    keys = a.only.split(',') if a.only else list(SETS)
    out = os.path.join(HERE, 'archive', a.date)
    os.makedirs(out, exist_ok=True)

    new = same = miss = 0
    for k in keys:
        if k not in SETS: print(f'  ? unknown set {k}'); continue
        # prefer .csv.gz: depth_charts alone is 48 MB raw and ~10 MB gzipped,
        # and a daily archive of the raw files would add gigabytes a season
        got = None
        for ext in ('.csv.gz', '.csv'):
            name = f'{SETS[k]}_{a.season}{ext}'
            url = f'{BASE}/{TAG[k]}/{name}'
            dest = os.path.join(out, name)
            try:
                with urllib.request.urlopen(url, timeout=180) as r, open(dest, 'wb') as f:
                    shutil.copyfileobj(r, f)
                got = name
                break
            except Exception:
                if os.path.exists(dest): os.remove(dest)
        if not got:
            print(f'  -- {SETS[k]}_{a.season:<28} unavailable')
            miss += 1
            continue
        name = got
        prior = latest_prior(name, a.date)
        if prior and sha(prior) == sha(dest):
            os.remove(dest)
            print(f'     {name:<34} unchanged since {os.path.basename(os.path.dirname(prior))}')
            same += 1
        else:
            kb = os.path.getsize(dest) / 1024
            print(f'  NEW {name:<34} {kb:>8.0f} KB')
            new += 1
    if not os.listdir(out): os.rmdir(out)
    print(f'\n{new} new, {same} unchanged, {miss} unavailable  ->  '
          f'{out if new else "(nothing to keep)"}')


if __name__ == '__main__':
    main()
