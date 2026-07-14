"""Targeted Hookpad refresh — pull a SPECIFIC set of songs (not the whole library)
and patch them straight into Supabase with recomputed has_* flags.

Resolves requested songs against a cached account song-list (no list call unless
--refresh-list), fetches each by ID, writes the JSON to the export dir, and — with
--supabase — updates parcels.songs.hookpad_json + has_sections/melody/chords for
just those rows.

Usage:
    update_songs.py --token T --project "Please Please Me" --supabase
    update_songs.py --token T --names "do you want to know a secret" misery --supabase
    update_songs.py --token T --file songs.txt --supabase
    update_songs.py --token T --refresh-list      # rebuild the song-list cache (~30s)

Song matching is by normalized substring on the Hookpad song name (e.g.
"beatles_do you want to know a secret"), so titles alone match Beatles entries.
"""
import os, re, sys, json, time, argparse, glob
import requests
from hashids import Hashids
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

API = 'https://api.hooktheory.com/v1'
HASHIDS = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
                  alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
OUT_DIR = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
LIST_CACHE = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
KEEP_KEYS = {'notes', 'chords', 'keys', 'sections', 'tempos', 'meters',
             'endBeat', 'activeMelodyIndex', 'inactiveNotes', 'breaks', 'lyrics'}

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def hdr(token):
    return {'authorization': f'Bearer {token}', 'origin': 'https://hookpad.hooktheory.com',
            'referer': 'https://hookpad.hooktheory.com/'}

def list_all(token):
    out, page = [], 1
    while True:
        r = requests.get(f'{API}/songs/h?per-page=100&page={page}', headers=hdr(token), timeout=30)
        r.raise_for_status(); data = r.json()
        if not data: break
        out.extend(data)
        if len(data) < 100: break
        page += 1; time.sleep(3.0)
    return out

def load_list(token, refresh=False):
    if not refresh and os.path.exists(LIST_CACHE):
        return json.load(open(LIST_CACHE))
    print('listing account songs (cached for next time)...')
    songs = list_all(token)
    json.dump(songs, open(LIST_CACHE, 'w'))
    print(f'  cached {len(songs)} songs -> {LIST_CACHE}')
    return songs

def fetch(token, numeric_id):
    slug = HASHIDS.encode(numeric_id)
    backoff = 30
    for _ in range(4):
        r = requests.get(f'{API}/songs/{slug}?fields=ID,song,jsonData', headers=hdr(token), timeout=30)
        if r.status_code == 429:
            print(f'    429 — backing off {backoff}s'); time.sleep(backoff); backoff *= 2; continue
        r.raise_for_status(); return r.json()
    raise RuntimeError(f'gave up on {numeric_id}')

def safe(name): return name.replace('/', '_').replace('\x00', '')

def strip(d): return {k: d[k] for k in KEEP_KEYS if k in d}

# ---- request resolution -----------------------------------------------------

def project_songs(project):
    """Read the songs.html project grouping -> list of title strings."""
    html = open(os.path.join(os.path.dirname(__file__), 'songs.html')).read()
    m = re.search(re.escape(project) + r'\s*<span class="proj-count">\d+</span></div>(.*?)'
                  r'(?:<div class="proj-subhead">|</div></div>)', html, re.S)
    if not m: return []
    return re.findall(r'song-title">([^<]*)</span>', m.group(1))

def _title_part(name):
    """'beatles_do you want...' -> 'do you want...' (drop the artist_ prefix)."""
    return name.split('_', 1)[1] if '_' in name else name

def resolve(requests_list, catalog):
    """Match each requested string to a catalog entry. Prefer an exact match on
    the title part (after 'artist_'), then a whole-title substring, so short
    queries like 'anna' don't grab 'toto_rosanna'."""
    matched, misses = [], []
    for req in requests_list:
        nq = norm(req)
        if not nq: misses.append(req); continue
        exact = [s for s in catalog if norm(_title_part(s['song'])) == nq]
        sub   = [s for s in catalog if nq in norm(_title_part(s['song']))]
        hits = exact or sub
        if hits:
            hits.sort(key=lambda s: len(s['song']))     # prefer the tightest name
            matched.append(hits[0])
        else:
            misses.append(req)
    # dedupe by ID
    seen, uniq = set(), []
    for s in matched:
        if s['ID'] not in seen: seen.add(s['ID']); uniq.append(s)
    return uniq, misses

# ---- supabase patch (targeted) ---------------------------------------------

def _kebab(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', (s or '').lower())).strip('-')

def existing_hooktab_titles():
    """Set of normalized titles for -hooktab rows already in Supabase."""
    import psycopg2
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select title from parcels.songs where title ilike '%hooktab%'")
    titles = {norm(t) for (t,) in cur.fetchall()}
    c.close()
    return titles

def new_hooktab_targets(catalog):
    """Catalog -hooktab songs not yet in Supabase (by normalized title part)."""
    have = existing_hooktab_titles()
    out = []
    for s in catalog:
        if 'hooktab' not in norm(s.get('song')):
            continue
        nt = norm(_title_part(s['song']))
        if any(nt == h or nt in h or h in nt for h in have):
            continue
        out.append(s)
    out.sort(key=lambda s: s.get('dateModified', ''), reverse=True)
    return out

def patch_supabase(fetched):
    """fetched: list of (song_name, stripped_json). Update the matching
    parcels.songs rows (by artist+normalized title); INSERT a new row when the
    song isn't in Supabase yet (freshly-added Hookpad songs). Returns (updated, inserted)."""
    import psycopg2
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor(); updated = inserted = 0
    for item in fetched:
        name, sj = item[0], item[1]
        hp_url = item[2] if len(item) > 2 else None   # reconstructed Hookpad URL (optional)
        artist, title = (name.split('_', 1) if '_' in name else (None, name))
        artist = (artist or '').strip() or None
        title = title.strip()
        ns = len(sj.get('sections') or []); nn = len(sj.get('notes') or []); nc = len(sj.get('chords') or [])
        cur.execute("""update parcels.songs set hookpad_json=%s,
              has_sections=%s, has_melody=%s, has_chords=%s,
              hookpad_url=coalesce(nullif(%s,''), hookpad_url), updated_at=now()
              where lower(regexp_replace(title,'[^a-zA-Z0-9]','','g'))=%s
              and (%s is null or artist ilike %s)""",
            (json.dumps(sj), ns > 0, nn > 0, nc > 0, hp_url or '', norm(title),
             artist, f'%{artist}%' if artist else None))
        if cur.rowcount:
            updated += cur.rowcount; continue
        # no existing row -> insert
        slug = f"{_kebab(artist)}_{_kebab(title)}" if artist else _kebab(title)
        try:
            cur.execute("""insert into parcels.songs
                  (title, artist, slug, hookpad_json, has_sections, has_melody, has_chords,
                   hookpad_url, in_hookpad, source, updated_at)
                  values (%s,%s,%s,%s,%s,%s,%s,%s,true,%s,now())
                  on conflict (slug) do update set hookpad_json=excluded.hookpad_json,
                   has_sections=excluded.has_sections, has_melody=excluded.has_melody,
                   has_chords=excluded.has_chords,
                   hookpad_url=coalesce(nullif(excluded.hookpad_url,''), parcels.songs.hookpad_url),
                   updated_at=now()""",
                (title, artist, slug, json.dumps(sj), ns > 0, nn > 0, nc > 0, hp_url or None, name + '.json'))
            inserted += 1
        except Exception as e:
            print(f'    ! insert failed for {name!r}: {str(e)[:120]}')
            c.rollback(); continue
    c.commit(); c.close()
    return updated, inserted

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token', required=True)
    p.add_argument('--names', nargs='*', default=[])
    p.add_argument('--project')
    p.add_argument('--artist', help='refresh every catalog song whose name starts with this (e.g. beatles)')
    p.add_argument('--file')
    p.add_argument('--supabase', action='store_true', help='also patch parcels.songs + flags')
    p.add_argument('--hooktab', action='store_true',
                   help='diff every -hooktab catalog song vs Supabase and pull only the new ones (implies --supabase)')
    p.add_argument('--refresh-list', action='store_true')
    p.add_argument('--throttle', type=float, default=6.0)
    a = p.parse_args()

    # --hooktab needs a fresh list (a stale cache would miss just-added songs) and always writes to Supabase
    catalog = load_list(a.token, refresh=a.refresh_list or a.hooktab)

    if a.hooktab:
        a.supabase = True
        targets = new_hooktab_targets(catalog)
        misses = []
        print(f'{len(targets)} new -hooktab songs to pull (not yet in Supabase)')
        for s in targets:
            print(f'    {s.get("dateModified","?")[:10]}  {s["song"]}')
    elif a.artist:
        na = norm(a.artist)
        targets, misses = [s for s in catalog if norm(s['song']).startswith(na)], []
        print(f'{len(targets)} catalog songs match artist {a.artist!r}')
    else:
        reqs = list(a.names)
        if a.project: reqs += project_songs(a.project)
        if a.file: reqs += [l.strip() for l in open(a.file) if l.strip()]
        if not reqs:
            print('nothing requested (use --names / --project / --artist / --file)'); return
        targets, misses = resolve(reqs, catalog)
        print(f'resolved {len(targets)}/{len(reqs)} requested songs' +
              (f'  (no match: {misses})' if misses else ''))

    fetched = []
    for i, s in enumerate(targets, 1):
        try:
            data = fetch(a.token, s['ID'])
            parsed = json.loads(data['jsonData'])
            fname = os.path.join(OUT_DIR, safe(s['song']) + '.json')
            json.dump(parsed, open(fname, 'w'), ensure_ascii=False)
            hp_url = f"https://hookpad.hooktheory.com/?idOfUserSong={HASHIDS.encode(s['ID'])}"
            fetched.append((s['song'], strip(parsed), hp_url))
            sj = fetched[-1][1]
            print(f'  [{i}/{len(targets)}] {s["song"][:40]:40} '
                  f'sect={len(sj.get("sections",[]))} mel={len(sj.get("notes",[]))} chd={len(sj.get("chords",[]))}')
        except Exception as e:
            print(f'  [{i}/{len(targets)}] {s["song"][:40]:40} ERROR {e}')
        if i < len(targets): time.sleep(a.throttle)

    if a.supabase and fetched:
        upd, ins = patch_supabase(fetched)
        print(f'\nSupabase: {upd} rows updated, {ins} new rows inserted (hookpad_json + has_* flags)')
    print('done.')

if __name__ == '__main__':
    main()
