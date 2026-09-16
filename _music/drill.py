#!/usr/bin/env python3
"""
Guitar drill: rebuild a song from memory, then check yourself.

Opens a Brave window with:
  tab 1  a BLANK Hookpad session (focused) — you set key, tempo, chords, structure
  tab 2+ the real song(s), behind it — only look after you have tried

Direct ?idOfUserSong= URLs via the hashid slug. No browser automation.

    python3 drill.py                  # next unseen song from G50
    python3 drill.py --pool G100
    python3 drill.py --n 3            # queue three
    python3 drill.py --song blur_the-universal
    python3 drill.py --status         # progress per pool
    python3 drill.py --reset G50
    python3 drill.py --dry-run        # print the URLs, open nothing
"""
import argparse, json, os, random, re, subprocess, sys

from hashids import Hashids

HERE = os.path.dirname(os.path.abspath(__file__))
POOLS = os.path.join(HERE, 'pool_map.json')
LIST_CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
PROGRESS = os.path.expanduser('~/.guitar_drill.json')
BLANK = 'https://hookpad.hooktheory.com/'

HASHIDS = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
                  alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                           'abcdefghijklmnopqrstuvwxyz-_')

TAGS = ('_o', '_c', '_ly', '_j')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def strip_tags(slug):
    """pool_map slugs carry trailing tags and sometimes a hex disambiguator,
    in either order — e.g. `..._ly_o-f7854e`. Keep peeling until nothing left."""
    s, changed = slug, True
    while changed:
        changed = False
        for t in TAGS:
            if s.endswith(t):
                s, changed = s[: -len(t)], True
        stripped = re.sub(r'-[0-9a-f]{6}$', '', s)
        if stripped != s:
            s, changed = stripped, True
    return s


def load_pools():
    out = {}
    for slug, pool in json.load(open(POOLS)).items():
        out.setdefault(pool, []).append(slug)
    for v in out.values():
        v.sort()
    return out


def load_progress():
    if os.path.exists(PROGRESS):
        try: return json.load(open(PROGRESS))
        except Exception: pass
    return {}


def resolve(slug, songs):
    """pool slug -> hookpad URL, using the synced song list."""
    nq = norm(strip_tags(slug))
    if not nq: return None
    exact = [s for s in songs if norm(s['song']) == nq]
    part  = [s for s in songs if nq in norm(s['song'])] if not exact else []
    both  = exact or part
    if not both:                       # cache name contained in the slug
        both = [s for s in songs if norm(s['song']) and norm(s['song']) in nq]
    if not both:
        # Title-only, ignoring the artist. The guitar list and the Hookpad
        # file often credit different performers — "Atlantic City" is filed
        # under the-band, not bruce-springsteen. Only accept it when exactly
        # one song in the library has that title, so a common title like
        # "Crazy" can never silently grab the wrong file.
        title = norm(strip_tags(slug).partition('_')[2])
        if len(title) >= 8:
            hits = [s for s in songs if norm(s['song'].partition('_')[2]) == title]
            if len(set(h['song'] for h in hits)) == 1:
                both = hits
    if not both:
        # fuzzy last resort — catches dropped words like
        # "tom-petty_won-t-back-down" vs "tom petty_i won't back down"
        import difflib
        scored = [(difflib.SequenceMatcher(None, nq, norm(s['song'])).ratio(), s)
                  for s in songs]
        scored.sort(key=lambda t: -t[0])
        if scored and scored[0][0] >= 0.86:
            both = [scored[0][1]]
    if not both: return None
    both.sort(key=lambda s: s.get('dateModified', ''), reverse=True)
    m = both[0]
    return m['song'], f"https://hookpad.hooktheory.com/?idOfUserSong={HASHIDS.encode(m['ID'])}"


def nice(slug):
    s = strip_tags(slug)
    artist, _, title = s.partition('_')
    return (f"{title.replace('-', ' ').title()} — "
            f"{artist.replace('-', ' ').title()}") if title else s


def pick(pool, songs, count, prog, shuffle):
    done = set(prog.get(pool, []))
    left = [s for s in songs if s not in done]
    if not left:
        print(f'  (finished all {len(songs)} in {pool} — new lap)')
        prog[pool] = []
        left = list(songs)
    if shuffle: random.shuffle(left)
    return left[:count]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', default='G50')
    ap.add_argument('--n', type=int, default=1)
    ap.add_argument('--song', default=None)
    ap.add_argument('--profile', default='Profile 9')
    ap.add_argument('--random', dest='shuffle', action='store_true', default=True)
    ap.add_argument('--in-order', dest='shuffle', action='store_false')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--gaps', action='store_true',
                    help='list pool songs with no Hookpad file yet')
    ap.add_argument('--reset', metavar='POOL')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    pools, prog = load_pools(), load_progress()

    if a.reset:
        prog[a.reset] = []
        json.dump(prog, open(PROGRESS, 'w'), indent=2)
        print(f'reset {a.reset}'); return

    if a.status:
        print(f"{'pool':<8}{'done':>6}{'total':>7}")
        for k in sorted(pools, key=lambda s: int(s[1:])):
            print(f'{k:<8}{len(prog.get(k, [])):>6}{len(pools[k]):>7}')
        return

    if not os.path.exists(LIST_CACHE):
        sys.exit(f'song list cache missing at {LIST_CACHE}\n-> run sync_hookpad.py')
    songs = json.load(open(LIST_CACHE))

    if a.gaps:
        keys = sorted(pools, key=lambda s: int(s[1:]))
        keys = [a.pool] if a.pool in pools and a.pool != 'G50' else keys
        total = 0
        for k in keys:
            miss = [s for s in pools[k] if not resolve(s, songs)]
            if miss:
                print(f'\n{k}  ({len(miss)} of {len(pools[k])} not in Hookpad)')
                for m in miss: print('   ', nice(m))
                total += len(miss)
        print(f'\n{total} songs across those pools have no Hookpad file yet.')
        return

    if a.song:
        chosen, pool = [a.song], None
    else:
        pool = a.pool
        if pool not in pools:
            sys.exit('unknown pool. try: ' + ', '.join(sorted(pools)))
        chosen = pick(pool, pools[pool], a.n, prog, a.shuffle)

    print(f'\n  DRILL — {pool or "single"}')
    urls, missing = [], []
    for slug in chosen:
        hit = resolve(slug, songs)
        if hit:
            name, url = hit
            print(f'    • {nice(slug)}')
            urls.append(url)
        else:
            print(f'    • {nice(slug)}   [NO HOOKPAD MATCH]')
            missing.append(slug)

    if a.dry_run:
        print()
        for u in urls: print('   ', u)
        return
    if not urls:
        sys.exit('\n  nothing resolved — is the song list cache stale?')

    print('\n  Build it from memory: key, tempo, chords, structure.')
    print('  The reference tabs are behind the blank one.\n')

    # blank FIRST so it is the focused tab and you cannot see the answer first
    cmd = ['open', '-na', 'Brave Browser', '--args',
           f'--profile-directory={a.profile}', '--new-window', BLANK, *urls]
    subprocess.run(cmd, check=True)
    print(f'  opened {len(urls)+1} tabs in Brave {a.profile!r}')

    if pool:
        prog.setdefault(pool, []).extend(s for s in chosen if s not in missing)
        json.dump(prog, open(PROGRESS, 'w'), indent=2)
        print(f'  progress: {len(prog[pool])}/{len(pools[pool])} of {pool}')


if __name__ == '__main__':
    main()
