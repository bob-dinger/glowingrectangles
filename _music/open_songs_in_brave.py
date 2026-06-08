"""Open N Hookpad songs as direct-URL tabs in Brave. No Playwright, no
File-menu dance — just translate "song name" -> Hookpad ID -> slug ->
?idOfUserSong=... URL, then `open` Brave with all URLs.

Usage:
    python open_songs_in_brave.py "song one" "song two" ...
    python open_songs_in_brave.py --profile "Profile 9" "song1" "song2"
"""
import os, sys, json, re, argparse, subprocess
from hashids import Hashids

LIST_CACHE = os.path.expanduser("~/Desktop/music/.hookpad_song_list.json")
HASHIDS = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
                  alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_song(query, all_songs):
    """Return the best matching Hookpad list entry, or None."""
    nq = norm(query)
    if not nq: return None
    # exact + substring matches
    exact, substr = [], []
    for s in all_songs:
        nm = norm(s["song"])
        if nm == nq: exact.append(s)
        elif nq in nm: substr.append(s)
    pool = exact or substr
    if not pool: return None
    # tie-break: most recently modified
    pool.sort(key=lambda s: s.get("dateModified", ""), reverse=True)
    return pool[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("songs", nargs="+", help="song search terms")
    p.add_argument("--profile", default="Profile 9", help='Brave profile dir (default "Profile 9")')
    p.add_argument("--new-window", action="store_true", default=True,
                   help="open in a new window (default true)")
    args = p.parse_args()

    if not os.path.exists(LIST_CACHE):
        print(f"Hookpad list cache missing at {LIST_CACHE}")
        print("Run sync_hookpad.py first.")
        sys.exit(1)
    all_songs = json.load(open(LIST_CACHE))

    urls, missing = [], []
    for q in args.songs:
        match = find_song(q, all_songs)
        if not match:
            missing.append(q)
            continue
        slug = HASHIDS.encode(match["ID"])
        urls.append((q, match["song"], f"https://hookpad.hooktheory.com/?idOfUserSong={slug}"))

    print(f"resolved {len(urls)}/{len(args.songs)} song(s):")
    for q, name, url in urls:
        print(f"  {q!r:<35} -> {name!r:<35} -> {url}")
    if missing:
        print(f"\nmissing (no Hookpad match):")
        for q in missing: print(f"  - {q}")

    if not urls:
        print("nothing to open"); sys.exit(2)

    cmd = ['open', '-na', 'Brave Browser', '--args',
           f'--profile-directory={args.profile}']
    if args.new_window: cmd.append('--new-window')
    cmd.extend(u for _, _, u in urls)
    subprocess.run(cmd, check=True)
    print(f"\nopened {len(urls)} tab(s) in Brave Profile {args.profile!r}")


if __name__ == "__main__":
    main()
