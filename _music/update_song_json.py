"""Backfill parcels.songs with hookpad_json (raw) + slug, for the URL-driven song viewer.

Safe to re-run: UPDATEs only the two new columns, does NOT touch user-edited fields.

Prereq SQL (run once in Supabase SQL editor):
    ALTER TABLE parcels.songs
      ADD COLUMN IF NOT EXISTS hookpad_json JSONB,
      ADD COLUMN IF NOT EXISTS slug TEXT;
    CREATE UNIQUE INDEX IF NOT EXISTS songs_slug_idx ON parcels.songs(slug);
"""
import os, re, json, glob, sys
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HOOKPAD_DIRS = [
    os.path.expanduser('~/Desktop/music/hookpad_songs_full'),
    os.path.expanduser('~/Desktop/music/hookpad_songs/hookpad_songs'),
]

# Only these top-level keys are needed for rendering — everything else (xmlData, etc.) is dropped to save space.
KEEP_KEYS = {
    'notes', 'chords', 'keys', 'sections', 'tempos', 'meters',
    'endBeat', 'activeMelodyIndex', 'inactiveNotes',
    'breaks',   # line-break positions in the Hookpad UI (list of {beat: N})
    'lyrics',   # lyric data attached to notes
}


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def _parse_hookpad_filename(basename):
    name = basename.removesuffix('.json')
    parts = name.split('_', 1)
    if len(parts) != 2: return None, None
    artist, rest = parts
    toks = rest.split('_')
    while len(toks) > 1 and len(toks[-1]) <= 3: toks.pop()
    return artist.strip(), '_'.join(toks).strip()


def make_slug(basename):
    """Hookpad filename basename → URL-safe slug. 'Alan Jackson_Dallas.json' → 'alan-jackson_dallas'."""
    s = basename.removesuffix('.json').strip().lower()
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-_')
    return s


def strip_hookpad(d):
    """Keep only the keys we need for visualization."""
    return {k: v for k, v in d.items() if k in KEEP_KEYS}


def main():
    # Build file index. Same basename can exist in multiple HOOKPAD_DIRS (e.g., legacy dir + full dir).
    # Always prefer the most-recently-modified copy.
    files = {}
    for d in HOOKPAD_DIRS:
        for f in glob.glob(os.path.join(d, '*.json')):
            bn = os.path.basename(f)
            cur = files.get(bn)
            if cur is None or os.path.getmtime(f) > os.path.getmtime(cur):
                files[bn] = f
    by_at = {}
    for f in files.values():
        a, t = _parse_hookpad_filename(os.path.basename(f))
        if not (a and t): continue
        for key in [(_norm(a), _norm(t)), ('', _norm(t))]:
            cur = by_at.get(key)
            if cur is None or os.path.getmtime(f) > os.path.getmtime(cur):
                by_at[key] = f
    print(f'indexed {len(files)} hookpad files')

    # Service role bypasses RLS / column GRANTs for the bulk update.
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

    # Pull all rows; we'll match each to a file
    rows = sb.schema('parcels').table('songs').select('id,title,artist,source').execute().data
    print(f'found {len(rows)} rows in parcels.songs')

    matched = unmatched = updated = 0
    seen_slugs = {}   # slug → row_id (detect collisions)
    for r in rows:
        # Gather all candidate files (source match + name match), then pick the most-recently-modified one.
        # Critical: source might point to an older file that was re-pulled with different casing; prefer the
        # fresh pull always.
        candidates = []
        src = r.get('source')
        if src and src in files:
            candidates.append(files[src])
        key = (_norm(r.get('artist')), _norm(r.get('title')))
        for k in [key, ('', _norm(r.get('title')))]:
            f = by_at.get(k)
            if f and f not in candidates:
                candidates.append(f)
        if not candidates:
            unmatched += 1
            continue
        path = max(candidates, key=lambda p: os.path.getmtime(p))
        matched += 1

        try:
            d = json.load(open(path, encoding='utf-8-sig'))
        except Exception as e:
            print(f'  skip {r["title"]}: read error {e}')
            continue

        stripped = strip_hookpad(d)
        if not stripped.get('chords') and not stripped.get('notes'):
            # nothing to visualize
            continue

        slug = make_slug(os.path.basename(path))
        if slug in seen_slugs:
            # collision — append part of the id to disambiguate
            slug = f'{slug}-{r["id"][:6]}'
        seen_slugs[slug] = r['id']

        try:
            sb.schema('parcels').table('songs').update({
                'hookpad_json': stripped,
                'slug': slug,
            }).eq('id', r['id']).execute()
            updated += 1
            if updated % 100 == 0:
                print(f'  updated {updated}…')
        except Exception as e:
            print(f'  update failed for {r["title"]}: {e}')

    print(f'\nupdate phase: matched {matched}, unmatched {unmatched}, updated {updated}')

    # ---------- Orphan import: insert rows for Hookpad files without a Supabase row ----------
    # Build set of all slugs currently in Supabase (fresh after the update pass)
    existing_slugs = set()
    page = 0
    while True:
        r = sb.schema('parcels').table('songs').select('slug').not_.is_('slug', 'null').range(page*1000, page*1000+999).execute()
        rows = r.data or []
        for x in rows: existing_slugs.add(x['slug'])
        if len(rows) < 1000: break
        page += 1
    print(f'\nexisting slugs in supabase: {len(existing_slugs)}')

    orphan_batch, inserted = [], 0
    BATCH_SIZE = 50
    for basename, path in files.items():
        slug = make_slug(basename)
        if slug in existing_slugs: continue

        a, t = _parse_hookpad_filename(basename)
        if not a or not t: continue

        try:
            d = json.load(open(path, encoding='utf-8-sig'))
        except Exception:
            continue
        stripped = strip_hookpad(d)
        if not stripped.get('chords') and not stripped.get('notes'): continue

        orphan_batch.append({
            'title': t, 'artist': a, 'slug': slug,
            'hookpad_json': stripped, 'in_hookpad': True, 'source': basename,
        })
        existing_slugs.add(slug)

        if len(orphan_batch) >= BATCH_SIZE:
            try:
                sb.schema('parcels').table('songs').insert(orphan_batch).execute()
                inserted += len(orphan_batch)
                print(f'  inserted {inserted}…')
            except Exception as e:
                print(f'  insert batch failed: {e}')
            orphan_batch = []

    if orphan_batch:
        try:
            sb.schema('parcels').table('songs').insert(orphan_batch).execute()
            inserted += len(orphan_batch)
        except Exception as e:
            print(f'  final insert failed: {e}')

    print(f'orphan phase: inserted {inserted} new rows')


if __name__ == '__main__':
    main()
