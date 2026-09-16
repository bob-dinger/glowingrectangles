"""Load songs_to_learn.csv into parcels.songs, enriching with Hookpad JSON structure.

Usage:
    /Users/robert/Desktop/themap/themap_claude/.venv/bin/python load_songs_to_supabase.py
"""

import csv
import glob
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

SB_URL = os.environ['SUPABASE_URL']
SB_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SB = create_client(SB_URL, SB_KEY).schema('parcels')

CSV_PATH = '/Users/robert/Desktop/music/songs_to_learn.csv'
HOOKPAD_DIRS = [
    '/Users/robert/Desktop/music/hookpad_songs/hookpad_songs',   # legacy partial export
    '/Users/robert/Desktop/music/hookpad_songs_full',            # fresh API-pulled (preferred)
]

# Index hookpad json files by basename. New (API-pulled) files override legacy ones.
HOOKPAD_FILES = {}
for _d in HOOKPAD_DIRS:
    for f in glob.glob(os.path.join(_d, '*.json')):
        HOOKPAD_FILES[os.path.basename(f)] = f


def _norm(s):
    """Normalize for fuzzy matching: lowercase, alphanumeric only."""
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def _parse_hookpad_filename(basename):
    """'nirvana_drain you_o_.json' → ('nirvana', 'drain you')"""
    name = basename.removesuffix('.json')
    parts = name.split('_', 1)
    if len(parts) != 2:
        return None, None
    artist, rest = parts
    toks = rest.split('_')
    while len(toks) > 1 and len(toks[-1]) <= 3:
        toks.pop()
    title = '_'.join(toks)
    return artist.strip(), title.strip()


# (norm_artist, norm_title) → filepath
HOOKPAD_BY_AT = {}
for f in HOOKPAD_FILES.values():
    a, t = _parse_hookpad_filename(os.path.basename(f))
    if a and t:
        key = (_norm(a), _norm(t))
        HOOKPAD_BY_AT[key] = f
        # Also index just by title for fallback matching
        HOOKPAD_BY_AT.setdefault(('', _norm(t)), f)


def parse_key(s):
    if not s:
        return None, None
    s = s.strip()
    m = re.match(r'^([A-G][b#]?)\s*(m|major|minor|mixolydian|dorian|lydian|phrygian|locrian)?$', s, re.I)
    if not m:
        return None, None
    tonic = m.group(1)
    suffix = (m.group(2) or '').lower()
    scale = 'minor' if suffix in ('m', 'minor') else (suffix or 'major')
    return tonic, scale


def parse_structure_from_csv(s):
    """'Verse:8 | Chorus:8 | Bridge:4' → [{name:'Verse', bars:8}, ...]"""
    if not s:
        return None
    out = []
    for chunk in s.split('|'):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ':' in chunk:
            name, bars = chunk.rsplit(':', 1)
            try:
                out.append({'name': name.strip(), 'bars': int(bars.strip())})
            except ValueError:
                out.append({'name': chunk})
        else:
            out.append({'name': chunk})
    return out or None


ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

def to_roman(root_str, type_str):
    """Convert hookpad chord {root, type} into a roman-numeral token like 'I', 'vi', 'bVII'."""
    root_str = str(root_str or '')
    type_str = str(type_str or '')
    if not root_str:
        return None
    acc = ''
    rs = root_str
    while rs and rs[0] in 'b#':
        acc += rs[0]
        rs = rs[1:]
    if not rs.isdigit():
        return None
    deg = int(rs)
    if deg < 1 or deg > 7:
        return None
    base = ROMAN[deg]
    is_minor = type_str.lower().startswith('m') and not type_str.lower().startswith('maj')
    if is_minor:
        base = base.lower()
        suffix = type_str[1:]
    else:
        suffix = type_str
    return f"{acc}{base}{suffix}"


def enrich_from_hookpad(source_filename, artist=None, title=None):
    """Pull (bars per section + chord-by-chord progression) from the hookpad JSON."""
    path = None
    if source_filename and source_filename in HOOKPAD_FILES:
        path = HOOKPAD_FILES[source_filename]
    elif title:
        # Fallback: match by (artist, title) then by title alone
        path = HOOKPAD_BY_AT.get((_norm(artist), _norm(title)))
        if not path:
            path = HOOKPAD_BY_AT.get(('', _norm(title)))
    if not path:
        return None
    try:
        d = json.load(open(path, encoding='utf-8-sig'))
    except Exception:
        return None
    sections = d.get('sections') or []
    if not sections:
        return None
    meter = (d.get('meters') or [{'numBeats': 4}])[0]
    beats_per_bar = meter.get('numBeats', 4) or 4
    end_beat = d.get('endBeat')
    chords = d.get('chords') or []

    bounds = list(sections) + ([{'beat': end_beat, 'name': '<end>'}] if end_beat else [])
    out = []
    for i in range(len(bounds) - 1):
        s = bounds[i]
        e = bounds[i + 1]
        bars = round((e['beat'] - s['beat']) / beats_per_bar)
        section_chords = []
        for ch in chords:
            if ch.get('isRest'):
                continue
            beat = ch.get('beat')
            if beat is None:
                continue
            if s['beat'] <= beat < e['beat']:
                token = to_roman(str(ch.get('root', '')), ch.get('type', ''))
                if token:
                    section_chords.append(token)
        entry = {'name': s.get('name', '?'), 'bars': bars}
        if section_chords:
            entry['chords'] = section_chords
        out.append(entry)
    return out or None


def parse_int(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def parse_bool(v):
    return str(v or '').strip().lower() in ('y', 'yes', 'true', '1', 'x')


def parse_date(v):
    v = (v or '').strip()
    if not v:
        return None
    # Accept YYYY-MM-DD as-is; otherwise let postgres reject and we set to None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
        return v
    return None


def main():
    rows = []
    with open(CSV_PATH, encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            title = (r.get('Title') or '').strip()
            if not title:
                continue
            tonic, scale = parse_key(r.get('Key'))
            source = (r.get('Source') or '').strip() or None

            artist = (r.get('Artist') or '').strip() or None
            structure = enrich_from_hookpad(source, artist, title) or parse_structure_from_csv(r.get('Structure'))

            rows.append({
                'title': title,
                'artist': artist,
                'key_tonic': tonic,
                'key_scale': scale,
                'bpm': parse_int(r.get('BPM')),
                'duration_sec': parse_int(r.get('Duration (sec)') or r.get('Duration')),
                'measures': parse_int(r.get('Measures')),
                'structure': structure,
                'learned': parse_bool(r.get('Learned')),
                'date_learned': parse_date(r.get('Date Learned')),
                'notes': (r.get('Notes') or '').strip() or None,
                'in_hookpad': parse_bool(r.get('In Hookpad')),
                'hookpad_status': (r.get('Hookpad Status') or '').strip() or None,
                'source': source,
            })

    # Dedupe by the same key as the unique index
    seen = {}
    for r in rows:
        k = (r['title'].lower(), (r['artist'] or '').lower(), r['source'] or '')
        seen[k] = r
    rows = list(seen.values())

    print(f'parsed {len(rows)} unique rows from CSV')
    have_structure = sum(1 for r in rows if r['structure'])
    print(f'  with structure: {have_structure}')
    print(f'  example: {json.dumps(rows[0], indent=2, default=str)[:500]}')

    if '--dry-run' in sys.argv:
        print('dry-run mode — exiting')
        return

    # Wipe existing rows for clean reload (first import)
    if '--wipe' in sys.argv:
        print('deleting existing rows...')
        SB.table('songs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

    BATCH = 100
    inserted = 0
    errors = []
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        try:
            SB.table('songs').insert(batch).execute()
            inserted += len(batch)
            print(f'  inserted {inserted}/{len(rows)}')
        except Exception as ex:
            errors.append((i, str(ex)[:200]))
            print(f'  ERROR at batch {i}: {ex}')

    print(f'\ndone. inserted: {inserted}, errors: {len(errors)}')


if __name__ == '__main__':
    main()
