#!/usr/bin/env python3
"""
When each card on the music index (_music/index.html) was created, in the order
the cards appear -> _music/index_dates.txt

    themap_venv/python index_dates.py

The index runs oldest -> newest (the ../guitar/ pages are their own group at the
top), so a NEW CARD GOES AT THE END. "Created" = the page's first git commit
(uncommitted = not yet). A card dated earlier than the card above it is flagged.
"""
import html, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'index_dates.txt')


def first_commit(path):
    out = subprocess.run(['git', 'log', '--diff-filter=A', '--follow', '--format=%ad', '--date=short', '--', path],
                         cwd=HERE, capture_output=True, text=True).stdout.split()
    return out[-1] if out else 'uncommitted'


def main():
    s = open(os.path.join(HERE, 'index.html')).read()
    cards = re.findall(r'<a href="([^"]+)" class="card">\s*<div class="card-icon">[^<]*</div>\s*'
                       r'<div class="card-title">([^<]*)</div>', s)
    rows = [(href, html.unescape(title), first_commit(href),
             'guitar' if href.startswith('../guitar/') else 'music') for href, title in cards]
    # the fewest cards to move: everything outside the longest run of
    # non-decreasing dates (per group) is out of place
    keep = set()
    for g in ('guitar', 'music'):
        ix = [i for i, r in enumerate(rows) if r[3] == g and r[2] != 'uncommitted']
        best = {}
        for k, i in enumerate(ix):
            prevs = [best[j] for j in ix[:k] if rows[j][2] <= rows[i][2]]
            best[i] = max(prevs, key=len, default=[]) + [i]
        keep |= set(max(best.values(), key=len, default=[]))
    lines, bad = [], []
    for i, (href, title, d, g) in enumerate(rows):
        flag = '' if i in keep or d == 'uncommitted' else '   <-- OUT OF ORDER'
        if flag: bad.append(title)
        lines.append(f'{i + 1:>3}  {d:<11}  {title:<34} {href}{flag}')
    head = ('Music index cards, top to bottom, with the date each page was first committed.\n'
            'Rule: the index runs oldest -> newest; a new card goes at the END (the ../guitar/\n'
            'pages are their own group at the top). Regenerate: themap_venv/python index_dates.py\n\n')
    open(OUT, 'w').write(head + '\n'.join(lines) + '\n')
    print(f'{OUT}: {len(cards)} cards' + (f'; out of order: {bad}' if bad else '; all in order'))


if __name__ == '__main__':
    main()
