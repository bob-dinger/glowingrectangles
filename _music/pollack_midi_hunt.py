"""Batch-download Beatles MIDIs from midis101.com for the no-melody target songs
we don't already have locally. Gentle throttle. Writes a manifest.

Usage: python3 pollack_midi_hunt.py [LIMIT] [--throttle N]
"""
import os, sys, re, csv, time, glob, urllib.parse, requests, difflib
import psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

DST = os.path.expanduser('~/Desktop/midi_files_beatles_new')
MANIFEST = os.path.expanduser('~/Desktop/midi_files_beatles_new/_manifest.csv')
os.makedirs(DST, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA})

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def local_have():
    have = set()
    for d in ['~/Desktop/midi_files3', '~/Desktop/midi_files', '~/Desktop/midis', DST]:
        for p in glob.glob(os.path.expanduser(d) + '/**/*.mid', recursive=True):
            b = os.path.basename(p).rsplit('.mid', 1)[0]
            b = re.sub(r'^(beatles[-_]midis?[-_]|beatles[-_]|the[-_]beatles[-_])', '', b, flags=re.I)
            have.add(norm(b))
    return have

def targets():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select distinct title from parcels.songs where artist ilike '%beatl%' and has_sections and not has_melody")
    seen = {}
    for (t,) in cur.fetchall(): seen.setdefault(norm(t), t)
    return list(seen.values())

def search(title):
    q = urllib.parse.quote(f'{title} beatles')
    try: r = S.get(f'https://midis101.com/search/{q}', timeout=12)
    except Exception: return None, None
    if r.status_code != 200: return None, None
    m = re.findall(r'href="(/free-midi/(\d+)-([^"]+))"', r.text)
    nt = norm(title)
    cands = [(mid, slug) for href, mid, slug in m if nt in norm(slug) and 'beatl' in norm(slug)]
    if not cands:
        cands = [(mid, slug) for href, mid, slug in m if nt in norm(slug)]
    if not cands: return None, None
    # prefer the shortest slug that contains the title (least extra context)
    cands.sort(key=lambda x: len(x[1]))
    mid, slug = cands[0]
    return f'https://midis101.com/download/{mid}-{slug}', slug

def download(url, dest):
    try: r = S.get(url, timeout=20)
    except Exception: return 'err'
    if r.status_code != 200: return f'http{r.status_code}'
    if r.content[:4] != b'MThd': return 'not-midi'
    open(dest, 'wb').write(r.content)
    return 'ok'

def main():
    limit = None; throttle = 3.0
    args = sys.argv[1:]
    skip = False
    for i, a in enumerate(args):
        if skip: skip = False; continue
        if a == '--throttle': throttle = float(args[i+1]); skip = True
        elif a.isdigit(): limit = int(a)
    have = local_have()
    tg = [t for t in targets() if norm(t) not in have]
    if limit: tg = tg[:limit]
    print(f'{len(tg)} songs to hunt (throttle {throttle}s) -> {DST}\n')
    rows = []
    for i, title in enumerate(tg, 1):
        url, slug = search(title)
        status = 'no-match'
        if url:
            dest = os.path.join(DST, f'beatles_{norm(title)}.mid')
            status = download(url, dest)
        print(f'  [{i}/{len(tg)}] {title[:34]:34s} {status:10s} {slug or ""}')
        rows.append({'title': title, 'slug': slug or '', 'url': url or '', 'status': status})
        if i < len(tg): time.sleep(throttle)
    with open(MANIFEST, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['title', 'slug', 'url', 'status']); w.writeheader(); w.writerows(rows)
    ok = sum(1 for r in rows if r['status'] == 'ok')
    print(f'\n{ok}/{len(rows)} downloaded. manifest -> {MANIFEST}')

if __name__ == '__main__':
    main()
