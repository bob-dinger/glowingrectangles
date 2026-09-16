"""Fetch tempo + key from songbpm.com for our Supabase song corpus.

Strategy: try a handful of URL-slug variants per song until one returns 200.
Songbpm displays canonical BPM + half-time + double-time, plus Spotify key/mode.

Output: ~/Desktop/songbpm_data.csv with columns
    artist, title, bpm, bpm_half, bpm_double, key, mode, source_url, status
"""
import os, re, csv, time, sys
import requests
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

OUT = os.path.expanduser('~/Desktop/songbpm_data.csv')
THROTTLE = 0.35       # base delay between requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Common artist aliases — songbpm follows Spotify's canonical artist names
ALIASES = {
    'ccr': 'creedence-clearwater-revival',
    'creedence-clearwater-revival': 'creedence-clearwater-revival',
    'rem': 'r-e-m',
    'r-e-m': 'r-e-m',
    'p-d': 'p-o-d',
    'p-o-d': 'p-o-d',
    'b-52s': 'the-b-52-s',
    'aha': 'a-ha',
    'a-ha': 'a-ha',
    'rhcp': 'red-hot-chili-peppers',
    'red-hot-chili-peppers': 'red-hot-chili-peppers',
    'ozzy-osbourne': 'ozzy-osbourne',
    'beatles': 'the-beatles',
    'the-beatles': 'the-beatles',
    'acdc': 'ac-dc',
    'ac-dc': 'ac-dc',
    '3-days-grace': 'three-days-grace',
    'onerepublic': 'onerepublic',
    'sonny-and-cher': 'sonny-cher',
}

NUMWORDS = {'0':'zero','1':'one','2':'two','3':'three','4':'four','5':'five',
            '6':'six','7':'seven','8':'eight','9':'nine','10':'ten'}
def numword_variants(s):
    """Swap a whole-number token to its English word and vice versa (e.g. '3 days'<->'three days')."""
    toks = s.split(); out = set(); inv = {v: k for k, v in NUMWORDS.items()}
    for i, t in enumerate(toks):
        if t in NUMWORDS:
            nt = toks[:]; nt[i] = NUMWORDS[t]; out.add(' '.join(nt))
        elif t.lower() in inv:
            nt = toks[:]; nt[i] = inv[t.lower()]; out.add(' '.join(nt))
    return out


def slugify(s, keep_apostrophe=False):
    s = s.lower()
    if not keep_apostrophe:
        s = s.replace("'", "").replace("’", "")
    s = re.sub(r'\s*&\s*', '-and-', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def artist_variants(artist):
    """Yield artist-slug candidates."""
    base = slugify(artist)
    yield ALIASES.get(base, base)
    if base.startswith('the-'):
        yield base[4:]
    else:
        yield 'the-' + base
    # songbpm often drops "and"/"&": "Sonny And Cher" -> "sonny-cher"
    noand = slugify(re.sub(r'\b(and)\b|&', ' ', artist, flags=re.I))
    if noand and noand != base:
        yield noand
    # number <-> word ("3 Days Grace" -> "three-days-grace")
    for nv in numword_variants(artist):
        yield ALIASES.get(slugify(nv), slugify(nv))
    # try first-word-only for compound artists (e.g., "bob-seger-the-silver-bullet-band" → "bob-seger")
    if base.count('-') >= 2:
        parts = base.split('-')
        for cutoff in (2, 3):
            if len(parts) > cutoff:
                yield '-'.join(parts[:cutoff])


def title_variants(title):
    base = slugify(title)
    yield base
    # apostrophe rendered as a separator: "School's Out" -> "school-s-out"
    if "'" in title or "’" in title:
        yield slugify(re.sub(r"['’]", ' ', title))
    # drop "and"/"&"
    noand = slugify(re.sub(r'\b(and)\b|&', ' ', title, flags=re.I))
    if noand and noand != base:
        yield noand
    # Strip parenthetical content
    t2 = re.sub(r'\s*\([^)]+\)\s*', '', title).strip()
    if t2 and t2 != title:
        yield slugify(t2)
    # Strip leading articles
    for art in ('the ', 'a ', 'an '):
        if title.lower().startswith(art):
            yield slugify(title[len(art):])


def fetch_one(artist, title):
    """Return (bpm, bpm_half, bpm_double, key, mode, url, status). On total miss, status='404'."""
    seen = set()
    last_status = 0
    for a in artist_variants(artist):
        for t in title_variants(title):
            key = (a, t)
            if key in seen: continue
            seen.add(key)
            url = f'https://songbpm.com/@{a}/{t}'
            try:
                r = requests.get(url, headers=HEADERS, timeout=12)
            except requests.RequestException:
                continue
            last_status = r.status_code
            if r.status_code != 200: continue
            body = r.text
            spans = re.findall(r'<span class="font-semibold[^"]*">([^<]+)</span>', body)
            bpm = half = double = music_key = mode = None
            for n in spans:
                n = n.strip()
                m = re.match(r'(\d+)\s*BPM', n)
                if m:
                    v = int(m.group(1))
                    if bpm is None: bpm = v
                    elif half is None: half = v
                    elif double is None: double = v
                elif re.match(r'^[A-G][#b]?$', n):
                    if music_key is None: music_key = n
                elif n in ('major', 'minor'):
                    if mode is None: mode = n
            if bpm is not None:
                return bpm, half, double, music_key, mode, url, 200
            time.sleep(0.1)
    return None, None, None, None, None, '', last_status


def main():
    SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    rows = (SB.schema('parcels').table('songs')
            .select('artist,title').not_.is_('hookpad_json', 'null').execute().data)
    print(f"fetching tempo for {len(rows)} songs ...")

    # Load existing output to resume
    done = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            for r in csv.DictReader(f):
                done[(r['artist'].lower(), r['title'].lower())] = r
        print(f"  resuming: {len(done)} already fetched")

    is_first = not os.path.exists(OUT)
    fields = ['artist', 'title', 'bpm', 'bpm_half', 'bpm_double', 'key', 'mode', 'source_url', 'status']
    fh = open(OUT, 'a', newline='')
    w = csv.DictWriter(fh, fieldnames=fields)
    if is_first: w.writeheader(); fh.flush()

    n_ok = n_miss = 0
    for i, r in enumerate(rows, 1):
        artist = r['artist'] or ''
        title = r['title'] or ''
        if (artist.lower(), title.lower()) in done:
            continue
        bpm, half, double, mk, mode, url, status = fetch_one(artist, title)
        w.writerow({
            'artist': artist, 'title': title,
            'bpm': bpm or '', 'bpm_half': half or '', 'bpm_double': double or '',
            'key': mk or '', 'mode': mode or '',
            'source_url': url, 'status': status,
        })
        fh.flush()
        if bpm: n_ok += 1
        else: n_miss += 1
        if i % 25 == 0 or i <= 5:
            print(f"  [{i:4}/{len(rows)}]  ok={n_ok}  miss={n_miss}  "
                  f"({artist[:25]} — {title[:30]} → {bpm or 'MISS'})", flush=True)
        time.sleep(THROTTLE)

    fh.close()
    print(f"\nfinal: {n_ok} hits, {n_miss} misses ({100*n_ok/(n_ok+n_miss):.1f}% coverage)")
    print(f"data → {OUT}")


if __name__ == '__main__':
    main()
