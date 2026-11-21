"""Lyrics for every downloaded song, from LRCLIB (lrclib.net: free, open, no key).

    lyrics_fetch.py              # every manifest song with audio and no lyrics/<file>.json yet
    lyrics_fetch.py --limit 5
    lyrics_fetch.py --queue library     # every song in the library queue, audio or not
    lyrics_fetch.py --queue billboard   # every Hot 100 song (~32,000; about a day and a half)

Per song: /api/get by artist + title + length (the YouTube upload's), then a
/api/search fallback (closest length, matching artist). Keeps the plain text
and, when LRCLIB has them, the synced lines ([mm:ss.xx] per line), which give
the audio aligner its starting points. Written to
~/Desktop/music/audio_work/lyrics/<file>.json, outside the repo (copyrighted
text stays local, like the audio). 2 s between requests. Queue songs without
audio are named the way youtube_audio.py would name their audio file, so the
two meet up when the audio arrives.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
import youtube_audio as Y

LYR = os.path.expanduser('~/Desktop/music/audio_work/lyrics')
MANIFESTS = [f'{Y.OUT}/{f}' for f in ('fixes_manifest.json', 'pilot_manifest.json', 'batch1_manifest.json', 'library_manifest.json')] + [f'{Y.BB_OUT}/manifest.json']
API = 'https://lrclib.net/api'
UA = {'User-Agent': 'glowinggardens-music (personal, local study)'}
STAMP = re.compile(r'^\[\d+:\d\d(?:\.\d+)?\]\s?', re.M)


def call(path, **q):
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(f'{API}/{path}?' + urllib.parse.urlencode(q), headers=UA), timeout=30).read())
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        if e.code == 429: sys.exit('LRCLIB rate limit: stopping')
        return None
    except Exception:
        return None
    finally:
        time.sleep(2)


def find(artist, title, secs):
    t = re.sub(r'\(.*?\)', '', title).strip() or title
    q = dict(artist_name=artist, track_name=t)
    if secs: q['duration'] = round(secs)
    d = call('get', **q)
    if d and (d.get('plainLyrics') or d.get('instrumental')): return d, 'get'
    res = call('search', track_name=t, artist_name=artist) or []
    lead = Y.art(re.split(r'\s(?:featuring|feat\.|with|&|x|and)\s', artist, flags=re.I)[0])[:5]
    ok = [r for r in res if r.get('plainLyrics') and lead in Y.art(r.get('artistName', '')) and Y.norm(t)[:6] in Y.norm(r.get('trackName', ''))]
    if not ok: return None, None
    return min(ok, key=lambda r: abs((r.get('duration') or 0) - (secs or r.get('duration') or 0))), 'search'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--queue', choices=('library', 'billboard'))
    a = ap.parse_args()
    os.makedirs(LYR, exist_ok=True)
    rows = {}
    for f in MANIFESTS:
        if os.path.exists(f):
            for r in json.load(open(f)):
                if r.get('file') and os.path.exists(r['file']) and r['file'] not in rows: rows[r['file']] = r
    out = lambda f: f'{LYR}/{os.path.splitext(os.path.basename(f))[0]}.json'
    if a.queue:
        q = json.load(open(Y.QUEUE if a.queue == 'library' else f'{Y.BB_OUT}/queue.json'))
        rows = {f'{Y.slug(x["artist"] + "_" + x["title"])[:120]}.m4a': x for x in q}
        have = {(Y.art(j.get('artist')), Y.norm(j.get('title'))) for j in (json.load(open(f'{LYR}/{n}')) for n in os.listdir(LYR) if n.endswith('.json'))}
        rows = {f: x for f, x in rows.items() if (Y.art(x['artist']), Y.norm(x['title'])) not in have}
    todo = [r for f, r in rows.items() if not os.path.exists(out(f))]
    for f, r in rows.items(): r.setdefault('file', f)
    print(len(todo), 'songs need lyrics of', len(rows), flush=True)
    found = 0
    for n, r in enumerate(todo[:a.limit] if a.limit is not None else todo, 1):
        d, how = find(r['artist'], r['title'], r.get('yt_len') or r.get('ref_len'))
        rec = dict(artist=r['artist'], title=r['title'], found=bool(d), fetched=time.strftime('%Y-%m-%d'))
        if d:
            found += 1
            rec.update(how=how, lrclib_id=d.get('id'), lrclib_artist=d.get('artistName'), lrclib_track=d.get('trackName'), album=d.get('albumName'),
                       duration=d.get('duration'), instrumental=d.get('instrumental'), plain=STAMP.sub('', d.get('plainLyrics') or ''),
                       synced=d.get('syncedLyrics'))
        json.dump(rec, open(out(r['file']), 'w'), ensure_ascii=False, indent=1)
        print(n, r['artist'], '-', r['title'], how or 'NOT FOUND', 'synced' if d and d.get('syncedLyrics') else '', flush=True)
    print(f'{found} found', flush=True)


if __name__ == '__main__':
    main()
