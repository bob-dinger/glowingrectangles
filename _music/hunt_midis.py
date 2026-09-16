"""Hunt MIDI files from midis101.com for songs we don't have yet.

Reads ~/Desktop/song_coverage.csv, filters to songs without MIDI but with Hookpad.
For each: search midis101 → if match found, download to ~/Desktop/midi_files_new/

Usage:
    python hunt_midis.py [LIMIT]   # default: all priority songs
"""
import os, sys, csv, re, time, urllib.parse, requests

DST = os.path.expanduser('~/Desktop/midi_files_new')
SUMMARY = os.path.expanduser('~/Desktop/midi_hunt_results.csv')
os.makedirs(DST, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
SESS = requests.Session(); SESS.headers.update({'User-Agent': UA})


def kebab(s):
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    return re.sub(r'-+', '-', s).strip('-_')


def basename(title, artist):
    a = kebab(artist)
    if a.startswith('the-'): a = a[4:]
    return f'{a}_{kebab(title)}'


def normalize(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def search_midis101(title, artist):
    """Return (download_url, matched_name) or (None, None)."""
    q = urllib.parse.quote(f'{title} {artist}')
    try:
        r = SESS.get(f'https://midis101.com/search/{q}', timeout=8)
    except Exception: return None, None
    if r.status_code != 200: return None, None
    # Find result links
    matches = re.findall(r'href="(/free-midi/(\d+)-([^"]+))"', r.text)
    if not matches: return None, None
    # Score each: prefer one where both artist and title appear in slug
    nt = normalize(title); na = normalize(artist)
    best = None
    for href, mid, slug in matches:
        ns = normalize(slug)
        if nt in ns and na in ns: return f'https://midis101.com/download/{mid}-{slug}', slug
        if not best and nt in ns: best = (f'https://midis101.com/download/{mid}-{slug}', slug)
    return best if best else (None, None)


def main():
    args = sys.argv[1:]
    limit = int(args[0]) if args and args[0].isdigit() else None

    rows = [r for r in csv.DictReader(open(os.path.expanduser('~/Desktop/song_coverage.csv')))
            if r['hookpad'] == 'x' and r['midi'] != 'x']
    if limit: rows = rows[:limit]
    print(f'{len(rows)} priority songs to hunt MIDIs for')

    results = []; n_found = n_miss = 0
    for i, r in enumerate(rows, 1):
        bn = basename(r['title'], r['artist'])
        out_path = os.path.join(DST, bn + '.mid')
        if os.path.exists(out_path):
            results.append({**r, 'status': 'skip_exists', 'basename': bn})
            continue
        url, slug = search_midis101(r['title'], r['artist'])
        if not url:
            n_miss += 1
            results.append({**r, 'status': 'no_match', 'basename': bn})
            if i % 25 == 0: print(f'  [{i:4}/{len(rows)}] no match  {r["title"][:40]} — {r["artist"][:20]}')
            time.sleep(0.8); continue
        try:
            dl = SESS.get(url, timeout=15)
            body = dl.content
            if body[:4] != b'MThd':
                n_miss += 1
                results.append({**r, 'status': 'bad_midi', 'basename': bn, 'url': url})
                time.sleep(0.8); continue
            open(out_path, 'wb').write(body)
            n_found += 1
            results.append({**r, 'status': 'downloaded', 'basename': bn, 'url': url, 'size': len(body)})
            if i <= 3 or i % 25 == 0: print(f'  [{i:4}/{len(rows)}] ✓ {bn} ({len(body)}b) {slug}')
        except Exception as e:
            results.append({**r, 'status': f'error:{str(e)[:60]}', 'basename': bn})
        time.sleep(0.8)

    fields = ['title','artist','basename','status','url','size']
    with open(SUMMARY, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results: w.writerow({k: r.get(k, '') for k in fields})
    print(f'\nfound: {n_found}, missed: {n_miss}, total checked: {len(rows)}')
    print(f'downloads → {DST}')
    print(f'summary → {SUMMARY}')


if __name__ == '__main__':
    main()
