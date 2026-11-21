"""Backfill the stats sidecars for songs downloaded before youtube_audio.py saved them.

    youtube_stats.py             # every manifest song with audio and no stats/<file>.json yet
    youtube_stats.py --limit 5

Per song: the YouTube record (views, likes, comments, upload date, subscribers,
tags, "most replayed" heatmap; metadata only, nothing downloaded), iTunes genre/
album/release date, and songbpm's mood/energy/danceability/time signature for
library songs. Written to ~/Desktop/music/audio_work/stats/<file>.json, the same
shape youtube_audio.py writes. Manifests are left alone (the downloader is
writing them). 25 s between songs, as it shares YouTube with the downloader;
stops on a 403 / bot check.
"""
import argparse, json, os, re, subprocess, sys, time
import youtube_audio as Y

MANIFESTS = [f'{Y.OUT}/{f}' for f in ('pilot_manifest.json', 'batch1_manifest.json', 'library_manifest.json', 'fixes_manifest.json')] + [f'{Y.BB_OUT}/manifest.json']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    rows = {}
    for f in MANIFESTS:
        if os.path.exists(f):
            for r in json.load(open(f)):
                if r.get('file') and r.get('url') and os.path.exists(r['file']): rows[r['file']] = (r, 'billboard' in f)
    side = lambda f: f'{Y.STATS}/{os.path.splitext(os.path.basename(f))[0]}.json'
    todo = [v for f, v in rows.items() if not os.path.exists(side(f))]
    print(len(todo), 'songs need stats of', len(rows), flush=True)
    for n, (r, bb) in enumerate(todo[:a.limit] if a.limit is not None else todo, 1):
        q = subprocess.run(['yt-dlp', '--skip-download', '--no-playlist', '-q', '--print', '%(.{' + ','.join(Y.YT_FIELDS) + '})j', r['url']],
                           capture_output=True, text=True)
        err = (q.stderr.strip().splitlines() or [''])[-1] if q.returncode else None
        if Y.blocked(err):
            sys.exit('YouTube is refusing: stopping')
        try: info = json.loads((q.stdout.strip().splitlines() or ['{}'])[-1])
        except ValueError: info = {}
        t = re.sub(r'\(.*?\)', '', r['title']).strip() or r['title']
        info.update(url=r['url'], fetched=time.strftime('%Y-%m-%d'), error=err, itunes=r.get('itunes') or Y.itunes_info(r['artist'], t),
                    songbpm=r.get('songbpm') if 'songbpm' in r else (None if bb else Y.songbpm(r['artist'], r['title'])[3]))
        head = Y.save_stats(r['file'], info)
        print(n, r['artist'], '-', r['title'], head, flush=True)
        time.sleep(25)


if __name__ == '__main__':
    main()
