#!/usr/bin/env python
"""Add / list YouTube URLs on parcels.songs.youtube_urls (a JSONB array).

Each entry is an object: {"url": ..., "kind": "cover"|"lesson"|"performance"|"other", "title": ...}
kind/title are optional. Dedupes by url (ignoring ?t=, &list= noise).

Usage:
    python add_youtube.py <slug> <url> [kind] [title]
    python add_youtube.py --list <slug>
    python add_youtube.py --batch file.tsv     # lines: slug <TAB> url <TAB> kind <TAB> title
"""
import os, sys, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'],
                   os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ['SUPABASE_KEY'])
TBL = sb.schema('parcels').table('songs')

def vid(u):
    m = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})', u or '')
    return m.group(1) if m else (u or '').strip()

def get(slug):
    r = TBL.select('slug,title,youtube_urls').eq('slug', slug).execute()
    return r.data[0] if r.data else None

def add(slug, url, kind=None, title=None):
    row = get(slug)
    if not row:
        print(f'  ! no such slug: {slug}'); return False
    cur = row.get('youtube_urls') or []
    if any(vid(e.get('url')) == vid(url) for e in cur if isinstance(e, dict)):
        print(f'  = already present on {slug}: {url}'); return False
    entry = {'url': url}
    if kind:  entry['kind'] = kind
    if title: entry['title'] = title
    cur.append(entry)
    TBL.update({'youtube_urls': cur}).eq('slug', slug).execute()
    print(f'  + {slug}  <- {kind or "url"}: {url}')
    return True

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    if a[0] == '--list':
        row = get(a[1])
        print(json.dumps(row.get('youtube_urls') if row else 'NOT FOUND', indent=2))
        return
    if a[0] == '--batch':
        n = 0
        for ln in open(a[1]):
            parts = ln.rstrip('\n').split('\t')
            if len(parts) < 2 or not parts[0].strip(): continue
            n += add(parts[0].strip(), parts[1].strip(),
                     parts[2].strip() if len(parts) > 2 else None,
                     parts[3].strip() if len(parts) > 3 else None)
        print(f'added {n}')
        return
    add(a[0], a[1], a[2] if len(a) > 2 else None, a[3] if len(a) > 3 else None)

if __name__ == '__main__':
    main()
