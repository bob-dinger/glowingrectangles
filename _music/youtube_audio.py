"""Record audio from YouTube for every song in the library, worst data first.

    youtube_audio.py --queue          # build the priority queue (no network)
    youtube_audio.py                  # work through it; resumable, stops on a 403
    youtube_audio.py --limit 40
    youtube_audio.py --billboard --queue   # Hot 100 queue: #1s, top 10, top 40, the rest
    youtube_audio.py --billboard           # work through it (after the library)

Queue order: Guitar50-150 by how bad their tempo/key/Hookpad data is, then
Guitar200-650 the same way, then every other song in hookpad_songs_full (one per
song: tempo/key copies fold together, mine_/perms_ scratch files are skipped).

Per song: songbpm page (studio length, plus its tempo and key, saved too) ->
top 6 YouTube results -> the one closest to the studio length, skipping
live/cover/lyric-edit titles -> best audio, no video. Files and the manifest
(link, channel, length, songbpm data) live in ~/Desktop/music/audio_work/youtube,
outside the repo. 30 s between songs, 5 s between songbpm pages.

--billboard: every Hot 100 song (~/Desktop/music/billboard/hot-100-current.csv,
utdata/rwd-billboard-data) not already in the library, biggest hits first, into
~/Desktop/music/audio_work/billboard. Studio length from the iTunes Search API
(earliest non-live release; songbpm is too small a site for 30,000 lookups, and
Spotify's API now needs a Premium account).

Stats, for every song: the YouTube numbers (views, likes, comments, upload date,
channel subscribers, tags, and the "most replayed" heatmap) in a sidecar
~/Desktop/music/audio_work/stats/<file>.json, the headline ones in the manifest
too; iTunes genre/album/release date/track number; songbpm's mood, energy,
danceability and time signature. youtube_stats.py backfills songs fetched
before this was added.
"""
import argparse, glob, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
import corpus as C
from same_progressions import same

OUT = os.path.expanduser('~/Desktop/music/audio_work/youtube')
D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
QUEUE = f'{OUT}/queue.json'
MANIFEST = f'{OUT}/library_manifest.json'
OLD = [f'{OUT}/pilot_manifest.json', f'{OUT}/batch1_manifest.json']
BB_CSV = os.path.expanduser('~/Desktop/music/billboard/hot-100-current.csv')
BB_OUT = os.path.expanduser('~/Desktop/music/audio_work/billboard')
STATS = os.path.expanduser('~/Desktop/music/audio_work/stats')
YT_FIELDS = ('view_count', 'like_count', 'comment_count', 'upload_date', 'release_date', 'release_year', 'channel_id', 'uploader',
             'channel_follower_count', 'channel_is_verified', 'age_limit', 'categories', 'tags', 'track', 'artist', 'album',
             'creators', 'alt_title', 'description', 'chapters', 'heatmap', 'availability')
YT_HEAD = dict(views='view_count', likes='like_count', comments='comment_count', uploaded='upload_date', subscribers='channel_follower_count')
BAD = re.compile(r'\b(live|covers?|karaoke|instrumental|remix(es)?|lessons?|reaction|8d|slowed|sped up|nightcore|tutorial|acoustic|unplugged|concerts?|sessions?|play ?along|chords|tabs?|backing track|guitar)\b', re.I)

FILTERED = re.compile(r'\b(sex|sexy|porno?|nude|naked|xxx\w*)\b', re.I)
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower().replace('&', 'and'))
art = lambda s: norm(re.sub(r'^the ', '', (s or '').lower().strip()))
slug = lambda s: re.sub(r'-+', '-', re.sub(r'[^a-z0-9]', '-', s.lower().replace("'", '').replace('&', ''))).strip('-')
ALIAS = {'electriclightorchestra': 'elo', 'redhotchilipeppers': 'rhcp', 'creedenceclearwaterrevival': 'ccr',
         'darylhallandjohnoates': 'hallandoates', 'hootieandtheblowfish': 'hootie', 'beatles': 'beatles',
         'presidentsoftheunitedstatesofamerica': 'presidentsoftheusa', 'jimihendrixexperience': 'jimihendrix'}
art = lambda s, _a=art: ALIAS.get(_a(s), _a(s))
key_of = lambda a, t: art(a) + '|' + norm(t)


def build_queue(badness):
    """badness: [score, list, title, artist, why] for the Guitar list songs (worst first)."""
    q, seen = [], set()
    for tier in (lambda l: l <= 150, lambda l: l > 150):
        for s, l, t, a, why in sorted(badness, key=lambda x: -x[0]):
            if tier(l) and key_of(a, t) not in seen:
                seen.add(key_of(a, t)); q.append(dict(title=t, artist=a, src=f'Guitar{l}', why=why))
    lists = []
    for i in range(50, 700, 50):
        f = f'Guitar{i}.html'
        if os.path.exists(f):
            lists += [(i, m.group(1), m.group(2)) for m in re.finditer(r'\{"title":"([^"]*)","artist":"([^"]*)"', open(f).read())]
    for i, t, a in lists:                       # list songs with nothing wrong
        if key_of(a, t) not in seen:
            seen.add(key_of(a, t)); q.append(dict(title=t, artist=a, src=f'Guitar{i}', why=''))
    a_ = art
    titles = {}                                  # title -> artists already queued, to catch spelled-out duplicates
    for x in q: titles.setdefault(norm(x['title']), set()).add(a_(x['artist']))
    PART = re.compile(r'^(verse|chorus|bridge|pre-?chorus|intro|outro|riff|solo|section|\d+)$', re.I)
    for f in sorted(glob.glob(D + '/*.json')):
        n = same(os.path.basename(f)[:-5])
        if C.SCRATCH.match(n) or '_' not in n: continue
        a, t = n.split('_', 1)
        t = t.split('_')[0].strip()                 # section clips (paradise_chorus_8_75) and old export tags (_ly_o_)
        t = re.sub(r'(?<=[a-z])\d+$', '', t).strip()     # tempo copies saved as superposition90
        if len(norm(t)) < 2 or PART.match(t) or re.fullmatch(r'\d+', norm(a)) or len(norm(a)) < 2: continue
        if key_of(a, t) in seen or a_(a) in titles.get(norm(t), ()): continue
        seen.add(key_of(a, t)); titles.setdefault(norm(t), set()).add(a_(a))
        q.append(dict(title=t, artist=a, src='library', why=''))
    return q


def songbpm(a, t):
    """(length s, bpm, key, extra) from songbpm.com, or Nones; extra = mood, energy, danceability, time signature"""
    tries = [slug(a), slug(re.sub(r'^the ', '', a, flags=re.I)), slug(re.split(r'\s(?:&|and the)\s', a)[0])]
    for aa in dict.fromkeys(tries):
        try:
            req = urllib.request.Request(f'https://songbpm.com/@{aa}/{slug(t)}', headers={'User-Agent': 'Mozilla/5.0'})
            h = urllib.request.urlopen(req, timeout=30).read().decode('utf8', 'ignore')
        except Exception:
            time.sleep(5); continue
        h = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)))
        m = re.search(r'Duration\s+(\d+):(\d\d)', h); b = re.search(r'Tempo \(BPM\) (\d+)', h)
        k = re.search(r'Key (\S+) Duration', h); md = re.search(r'key and an? (major|minor) mode', h)
        time.sleep(5)
        if m:
            mood = re.search(r' is an? (\w+) song by', h); en = re.search(r'It has (.+?) energy and is (.+?) danceable', h)
            ts = re.search(r'time signature of (\d+) beats', h)
            extra = dict(mood=mood and mood.group(1), energy=en and en.group(1), danceable=en and en.group(2), beats_per_bar=ts and int(ts.group(1)))
            return int(m.group(1)) * 60 + int(m.group(2)), int(b.group(1)) if b else None, \
                (k.group(1) + (' ' + md.group(1) if md else '')) if k else None, extra
    return None, None, None, None


def itunes_len(a, t):
    """studio length (s) of the earliest non-live iTunes release by a matching artist, or None"""
    i = itunes_info(a, t)
    return i and i['len']


def itunes_info(a, t):
    """the earliest non-live iTunes release by a matching artist: length, genre, album, release date, track number; or None"""
    try:
        u = 'https://itunes.apple.com/search?' + urllib.parse.urlencode(dict(term=f'{a} {t}', entity='song', limit=15, country='US'))
        res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read())['results']
    except Exception:
        return None
    finally:
        time.sleep(3.5)                                   # Apple asks for about 20 calls a minute
    lead = art(re.split(r'\s(?:featuring|feat\.|with|&|x|and)\s', a, flags=re.I)[0])[:5]
    ok = [r for r in res if r.get('trackTimeMillis') and lead in art(r.get('artistName', ''))
          and not BAD.search(r.get('trackName', '') + ' ' + r.get('collectionName', '')) and norm(t)[:6] in norm(r.get('trackName', ''))]
    if not ok: return None
    r = min(ok, key=lambda r: r.get('releaseDate', '9'))
    return dict(len=r['trackTimeMillis'] // 1000, genre=r.get('primaryGenreName'), album=r.get('collectionName'), released=r.get('releaseDate', '')[:10],
                track_no=r.get('trackNumber'), tracks=r.get('trackCount'), explicit=r.get('trackExplicitness'), itunes_artist=r.get('artistName'),
                itunes_track=r.get('trackName'), itunes_id=r.get('trackId'))


def billboard_queue():
    import csv
    songs = {}
    for r in csv.DictReader(open(BB_CSV)):
        d = songs.setdefault((r['title'], r['performer']), dict(peak=101, weeks=0, first=r['chart_week']))
        d['peak'] = min(d['peak'], int(r['current_week'])); d['weeks'] += 1; d['first'] = min(d['first'], r['chart_week'])
    lib = json.load(open(QUEUE))
    have = {}
    for x in lib: have.setdefault(norm(re.sub(r'\(.*?\)', '', x['title'])), []).append(art(x['artist']))
    def in_lib(t, p):                            # double A-sides ("Come Together/Something") count if either side is in
        return any(a[:5] in art(p) for side in t.split('/') for a in have.get(norm(re.sub(r'\(.*?\)', '', side)), []) if len(a) >= 3)
    tier = lambda pk: 0 if pk == 1 else 1 if pk <= 10 else 2 if pk <= 40 else 3
    q = [dict(title=t, artist=p, src=f"hot100 peak {d['peak']}", why=f"{d['weeks']} weeks, first {d['first']}")
         for (t, p), d in sorted(songs.items(), key=lambda kv: (tier(kv[1]['peak']), -kv[1]['weeks'])) if not in_lib(t, p)]
    return q


def fetch(item, out=OUT, lengths='songbpm'):
    a, t = item['artist'], item['title']
    it = itunes_info(a, re.sub(r'\(.*?\)', '', t).strip() or t)
    if lengths == 'itunes':
        ref, sb_bpm, sb_key, sb_x = it and it['len'], None, None, None
    else:
        ref, sb_bpm, sb_key, sb_x = songbpm(a, t)
    p = subprocess.run(['yt-dlp', '--flat-playlist', '--print', '%(duration)s|%(channel)s|%(title)s|%(webpage_url)s',
                        f'ytsearch6:{a} {t}'], capture_output=True, text=True)
    if not p.stdout.strip() and FILTERED.search(f'{a} {t}'):
        # YouTube's search returns nothing at all for some words ("Sex and Candy", Porno for Pyros): search without
        # them, then keep only results whose title still has the song's other words
        q = FILTERED.sub(' ', f'{a} {t}')
        p = subprocess.run(['yt-dlp', '--flat-playlist', '--print', '%(duration)s|%(channel)s|%(title)s|%(webpage_url)s',
                            f'ytsearch10:{q}'], capture_output=True, text=True)
        need = norm(FILTERED.sub('', t)) or norm(t)
        p.stdout = '\n'.join(l for l in p.stdout.splitlines() if need in norm(l.split('|')[2] if l.count('|') >= 3 else ''))
    cands = []
    for line in p.stdout.splitlines():
        parts = line.split('|')
        if len(parts) < 4 or parts[0] in ('NA', 'None', ''): continue
        if float(parts[0]) > 900: continue          # a whole album or a compilation, not the song (Magical Mystery Tour, 2026-11-09)
        ti = '|'.join(parts[2:-1])
        cands.append(dict(len=float(parts[0]), channel=parts[1], yt_title=ti, url=parts[-1], bad=bool(BAD.search(ti)) and not BAD.search(t)))
    r = dict(item, ref_len=ref, songbpm_bpm=sb_bpm, songbpm_key=sb_key, songbpm=sb_x, itunes=it, cands=len(cands))
    if not cands:
        r['error'] = 'no search results ' + (p.stderr.strip().splitlines() or [''])[-1]
        return r
    pool = [c for c in cands if not c['bad']] or cands
    official = lambda c: bool(re.search(r'official|- topic|vevo', c['yt_title'] + ' ' + c['channel'], re.I)) or art(a)[:5] in norm(c['channel'])
    score = lambda c: (abs(c['len'] - ref) if ref else 0) + (0 if official(c) else 4) + pool.index(c) * (0 if ref else 1)
    for pick in sorted(pool, key=score)[:3]:      # an age-restricted or removed upload falls through to the next best
        time.sleep(5)
        q = subprocess.run(['yt-dlp', '--no-playlist', '-q', '-f', 'bestaudio[ext=m4a]/bestaudio', '-o', f'{out}/{slug(a + "_" + t)[:120]}.%(ext)s',
                            '--print', 'after_move:%(.{filepath,' + ','.join(YT_FIELDS) + '})j', pick['url']], capture_output=True, text=True)
        err = (q.stderr.strip().splitlines() or [''])[-1] if q.returncode else None
        info = {}
        if not err:
            try: info = json.loads((q.stdout.strip().splitlines() or ['{}'])[-1])
            except ValueError: pass
        r.update(yt_title=pick['yt_title'], channel=pick['channel'], url=pick['url'], yt_len=pick['len'],
                 file=None if err else info.get('filepath'), len_ok=None if not ref else abs(pick['len'] - ref) <= 10, error=err)
        if r['file']:
            r['yt'] = save_stats(r['file'], dict(info, url=pick['url'], fetched=time.strftime('%Y-%m-%d'), itunes=it, songbpm=sb_x))
        if not err or blocked(err) or not re.search(r'confirm your age|unavailable|private video|removed|copyright', err, re.I):
            break
    return r


def save_stats(file, info):
    """the whole YouTube record to stats/<file>.json; the headline numbers back for the manifest"""
    os.makedirs(STATS, exist_ok=True)
    info.pop('filepath', None)
    json.dump(info, open(f'{STATS}/{os.path.splitext(os.path.basename(file))[0]}.json', 'w'))
    return {k: info.get(v) for k, v in YT_HEAD.items()}


def blocked(err):
    """a real bot check or rate limit (stop everything), not one age-restricted or removed video"""
    return bool(err) and bool(re.search(r"HTTP Error 403|not a bot|confirm you.re not|HTTP Error 429|Too Many Requests", err, re.I))


def refresh_page():
    """rebuild ~/Desktop/music/listen.html so new downloads show up"""
    try:
        import listen_page; listen_page.main()
    except Exception as e:
        print('listen page not rebuilt:', e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--queue', action='store_true', help='(re)build the queue from the badness ranking and the library')
    ap.add_argument('--badness', default=None, help='badness ranking JSON ([score, list, title, artist, why] rows)')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--billboard', action='store_true', help='the Hot 100 instead of the library')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.billboard:
        os.makedirs(BB_OUT, exist_ok=True)
        BQ, BM = f'{BB_OUT}/queue.json', f'{BB_OUT}/manifest.json'
        if a.queue:
            q = billboard_queue(); json.dump(q, open(BQ, 'w'), indent=1)
            print(len(q), 'Hot 100 songs queued (not in the library):', sum(x['src'] == 'hot100 peak 1' for x in q), '#1s')
            return
        q = json.load(open(BQ)); man = json.load(open(BM)) if os.path.exists(BM) else []
        done = {(r['title'], r['artist']) for r in man}
        todo = [x for x in q if (x['title'], x['artist']) not in done]
        print(len(todo), 'to fetch of', len(q))
        for n, item in enumerate(todo[:a.limit] if a.limit is not None else todo, 1):
            r = fetch(item, BB_OUT, 'itunes')
            man.append(r); json.dump(man, open(BM, 'w'), indent=1)
            if n % 25 == 0: refresh_page()
            print(json.dumps({k: r.get(k) for k in ('title', 'artist', 'yt_title', 'yt_len', 'ref_len', 'len_ok', 'error')}), flush=True)
            if blocked(r.get('error')):
                sys.exit('YouTube is refusing downloads: stopping')
            time.sleep(16)
        return
    if a.queue:
        q = build_queue(json.load(open(a.badness)) if a.badness else [])
        json.dump(q, open(QUEUE, 'w'), indent=1)
        print(len(q), 'songs queued:', sum(x['src'] != 'library' for x in q), 'from the Guitar lists,', sum(x['src'] == 'library' for x in q), 'from the library')
        return
    q = json.load(open(QUEUE))
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else []
    got = [r for f in OLD + [MANIFEST] if os.path.exists(f) for r in json.load(open(f)) if r.get('file') or r.get('error')]
    RENAMED = {norm("XXX's and OOO's (An American Girl)"): 'americangirl', norm('All You Wanted'): 'alliwanted',
               norm('The Tears of a Clown'): 'tearsofaclown', norm("I Won't Back Down"): 'wontbackdown', norm('Lovesong'): 'lovesong',
               norm('Whataya Want from Me'): 'whatdyawantfromme', norm('10,000 Emerald Pools'): '10emeraldspools'}
    def same_song(r, x):
        t1, t2 = {norm(r['title']), RENAMED.get(norm(r['title']))}, norm(x['title'])
        a1, a2 = art(r['artist']), art(x['artist'])
        return t2 in t1 and (a1[:4] in a2 or a2[:4] in a1 or a1[:3] == a2[:3])
    todo = [x for x in q if not any(same_song(r, x) for r in got)]
    print(len(todo), 'to fetch of', len(q))
    for i, item in enumerate(todo[:a.limit] if a.limit is not None else todo, 1):
        r = fetch(item)
        man.append(r); json.dump(man, open(MANIFEST, 'w'), indent=1)
        if i % 25 == 0: refresh_page()
        print(json.dumps({k: r.get(k) for k in ('title', 'artist', 'yt_title', 'yt_len', 'ref_len', 'len_ok', 'error')}), flush=True)
        if blocked(r.get('error')):
            sys.exit('YouTube is refusing downloads: stopping')
        time.sleep(30)


if __name__ == '__main__':
    main()
