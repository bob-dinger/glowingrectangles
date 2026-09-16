#!/Users/robert/Desktop/themap/themap_claude/.venv/bin/python
"""
Put a Brave profile in front of you, starting it if it is not running.

    brave_profile.py robert
    brave_profile.py adam https://news.ycombinator.com

Brave has eleven profiles here and only two or three are usually open, so the
common case is that the one you want has no window at all. `open -a "Brave
Browser"` cannot help — it goes to whatever window is frontmost, in whatever
profile that happens to be.

Names are the ones on the profile menu (robert, adam, glowing gardens, TheMap),
not the `Profile N` directories underneath them.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brave_tabs as bt


def main():
    if len(sys.argv) < 2:
        names = bt.profile_names()
        running = bt.running_profiles()
        for d, n in sorted(names.items(), key=lambda x: x[1].lower()):
            print(f"{n:32} {d:12} {'open' if d in running else ''}")
        return 0

    args = sys.argv[1:]
    url = args.pop() if args and args[-1].startswith('http') else None
    result = bt.open_profile(' '.join(args), url)
    if result is None:
        print(f'no Brave profile called "{" ".join(args)}"')
        return 1
    profile, what = result
    label = bt.profile_names().get(profile, profile)
    print(f'{label}  ({what})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
