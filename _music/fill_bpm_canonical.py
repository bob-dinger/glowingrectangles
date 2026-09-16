"""Fill bpm_canonical for songs that are missing it, from songbpm.com.

Reuses fetch_songbpm.fetch_one (slug-variant scrape). For each song with a
hookpad_json but no bpm_canonical, fetch songbpm's main BPM (the felt/canonical
tempo, which reconciles half/double), write it to parcels.songs.bpm_canonical
(source='songbpm'), and log to ~/Desktop/songbpm_data.csv. Resume-safe: a
re-run only touches rows still null.
"""
import os, csv, time
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2
import fetch_songbpm as fb   # reuse fetch_one + slug logic

CSV = os.path.expanduser('~/Desktop/songbpm_data.csv')
THROTTLE = 0.4

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    c.autocommit = True
    cur = c.cursor()
    cur.execute("""select id,artist,title from parcels.songs
                   where bpm_canonical is null and hookpad_json is not null
                     and lower(coalesce(artist,'')) not in ('mine','song','music','riffs','chord-riffs','1979')
                     and lower(coalesce(title,''))  !~ '^(verse|chorus|bridge|intro|outro|pre-?chorus|solo|section|try|part|riff|break|refrain)[ 0-9]*$'
                   order by artist,title""")
    rows = cur.fetchall()
    print(f"filling bpm_canonical for {len(rows)} real songs missing it (junk/section files skipped)", flush=True)

    is_first = not os.path.exists(CSV)
    fh = open(CSV, 'a', newline='')
    w = csv.DictWriter(fh, fieldnames=['artist','title','bpm','bpm_half','bpm_double','key','mode','source_url','status'])
    if is_first: w.writeheader(); fh.flush()

    ok = miss = 0
    for i, (sid, artist, title) in enumerate(rows, 1):
        bpm, half, double, mk, mode, url, status = fb.fetch_one(artist or '', title or '')
        w.writerow({'artist':artist,'title':title,'bpm':bpm or '','bpm_half':half or '','bpm_double':double or '',
                    'key':mk or '','mode':mode or '','source_url':url,'status':status}); fh.flush()
        if bpm:
            cur.execute("update parcels.songs set bpm_canonical=%s, bpm_canonical_source='songbpm', updated_at=now() where id=%s", (bpm, sid))
            ok += 1
        else:
            miss += 1
        if i % 25 == 0 or i <= 5:
            print(f"  [{i:4}/{len(rows)}] ok={ok} miss={miss}  ({(artist or '')[:22]} — {(title or '')[:26]} -> {bpm or 'MISS'})", flush=True)
        time.sleep(THROTTLE)

    fh.close(); c.close()
    print(f"\nDONE: filled {ok}, missed {miss}  ({100*ok/max(1,ok+miss):.0f}% hit rate)", flush=True)

if __name__ == '__main__':
    main()
