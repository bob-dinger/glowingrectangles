#!/usr/bin/env python3
"""
A flashcard quiz for one guitar pool: name the key, the tempo, the section
lengths and the progressions, then reveal and mark what you got.

Recall, not recognition, like drill.py, but without a Hookpad session per song.
Everything comes from the Hookpad files, read the same way the printed pool
sheet reads them (build_g50_rows.py): the chord letters are the ones you play
in the key in force at that section, and a progression that repeats is shown
once with its multiplier.

    themap_venv/python build_pool_quiz.py                 # G100
    themap_venv/python build_pool_quiz.py --pool G50
"""
import argparse, difflib, glob, html, json, os, re, sys
import openpyxl, unicodedata, urllib.parse
from hashids import Hashids
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import chord_key as ck
import pao_pools as pp
from build_g50_rows import SKIP

HERE = os.path.dirname(os.path.abspath(__file__))
TRACKER = os.path.expanduser('~/Desktop/music/songs_to_learn.xlsx')
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
PC = {n: i for i, n in enumerate(NAMES)}
PC.update({'Db': 1, 'Eb': 3, 'Gb': 6, 'Ab': 8, 'Bb': 10})


def resolve(artist, title, files):
    """sheet row -> Hookpad file. pp.find's token fallback is too loose here:
    it filed Real World under `matchbox.json` (a Beatles cover) and All You
    Wanted under `you.json`. Match on the TITLE, prefer the base file over
    -simple/-hooktab variants, break ties on the artist, then fuzzy."""
    want, art = pp.norm(title), pp.norm(artist)
    def parts(p):
        base, tag = pp.split_variant(os.path.splitext(os.path.basename(p))[0])
        a, _, t = base.partition('_')
        return pp.norm(a), pp.norm(t), tag
    rows = [(p,) + parts(p) for p in files]
    hits = [r for r in rows if r[2] == want]
    if not hits:
        best = difflib.get_close_matches(want, [r[2] for r in rows], 1, .8)
        hits = [r for r in rows if best and r[2] == best[0]]
    if not hits: return None
    hits.sort(key=lambda r: ({'right': 0, '': 1}.get(r[3].lower(), 2),   # -right, then base
                             -difflib.SequenceMatcher(None, art, r[1]).ratio(),
                             -os.path.getmtime(r[0])))
    return hits[0][0]


HOOKPAD_LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
HASHIDS = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
                  alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
UG_TABS = os.path.expanduser('~/Desktop/music/ug_tabs')
UG_CATALOGS = [os.path.expanduser('~/Desktop/music/ug_all_official.csv'),
               *sorted(glob.glob(os.path.expanduser('~/Desktop/dates/*/ug_all_official.csv')),
                       key=os.path.getmtime, reverse=True),
               os.path.expanduser('~/Desktop/ug_all_official.csv')]


def hookpad_url(path, library):
    """file -> its Hookpad session, via the library's numeric ID (newest wins)"""
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    hits = sorted((s for s in library if s.get('song', '').lower() == stem),
                  key=lambda s: s.get('dateModified', ''), reverse=True)
    return ('https://hookpad.hooktheory.com/?idOfUserSong=' + HASHIDS.encode(int(hits[0]['ID']))
            if hits else None)


def _t(x):
    x = unicodedata.normalize('NFKD', str(x or '')).lower()
    x = re.sub(r'\(.*?\)', '', x).replace('wanna', 'want to').replace('gonna', 'going to')
    return pp.norm(re.sub(r'^the[\s-]+', '', x.strip()))


def _words(x):
    x = unicodedata.normalize('NFKD', str(x or '')).lower().replace('-', ' ')
    w = set(re.findall(r'[a-z0-9]+', x))
    return (w - {'the', 'and', 'band', 'of', 'john'}) or w     # "The Band" is all stopwords


def ug_url(artist, titles, catalog, aliases=()):
    """-> (url, how). Only accept a link whose artist AND title both match:
    ug_tabs' line-1 URLs are often a cover or another song entirely (The
    Script filed under Billy Joel). Official catalog first, then a vetted
    ug_tabs URL, else a UG search.

    Titles are tried as the sheet spells them AND as the Hookpad file does
    ("rollin in the deep" vs "rolling"), and one may contain the other
    ("the longest time" / "for the longest time"), but only for titles long
    enough that containment means something."""
    ts = {_t(t) for t in titles if t}
    def title_ok(rt):
        r = _t(rt)
        # a catalog title may run on past ours: "habits" = "habits (stay high)"
        return any(r == t or (min(len(r), len(t)) >= 10 and (r in t or t in r))
                   or (len(t) >= 5 and r.startswith(t)) for t in ts)
    # artists match on any shared name word ("Daryl Hall & John Oates" is
    # "hall oates" in the catalog) or squashed ("rem" / "r.e.m.")
    ALIAS = {'dolly parton': 'kenny rogers', 'david bowie': 'queen'}
    names = [artist, *aliases, ALIAS.get(str(artist).lower(), '')]
    aw = set().union(*(_words(n) for n in names if n))
    an = {pp.norm(n) for n in names if n}
    def artist_ok(ra):
        n = pp.norm(unicodedata.normalize('NFKD', str(ra or '')))
        return bool(aw & _words(ra)) or any(n and (n == x or (len(x) > 3 and (n in x or x in n))) for x in an)
    ok = lambda ra, rt: title_ok(rt) and artist_ok(ra)
    for r in catalog:
        if ok(r.get('artist'), r.get('title')):
            return r['url'], 'official'
    for f in glob.glob(os.path.join(UG_TABS, '*.txt')):
        if not any(t[:8] in pp.norm(os.path.basename(f)) for t in ts): continue
        line = open(f, errors='ignore').readline()
        m = re.search(r'https?://\S*ultimate-guitar\.com/\S+', line)
        if not m: continue
        u = m.group(0)
        parts = u.split('/tab/')[-1].split('/') if '/tab/' in u else []
        if len(parts) >= 2 and ok(parts[0], re.sub(r'-(official|chords|tabs?)-\d+$', '', parts[1])):
            return u, 'tab'
    return ('https://www.ultimate-guitar.com/search.php?'
            + urllib.parse.urlencode({'search_type': 'title', 'value': f'{artist} {titles[0]}'})), 'search'


def title_case(s):
    # str.title() capitalises after an apostrophe, giving "Won'T Back Down"
    return re.sub(r"[A-Za-z']+", lambda m: m.group(0)[0].upper() + m.group(0)[1:],
                  s.replace('-', ' ').lower())


MODE = {
    'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10], 'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10], 'harmonicMinor': [0, 2, 3, 5, 7, 8, 11],
    'melodicMinor': [0, 2, 3, 5, 7, 9, 11], 'phrygianDominant': [0, 1, 4, 5, 7, 8, 10]}
# the parent major's tonic sits this far below a mode's tonic -- colours are by
# degree of the parent major, so a minor song's i is purple like any vi
PARENT = {'major': 0, 'dorian': 2, 'phrygian': 4, 'lydian': 5, 'mixolydian': 7,
          'minor': 9, 'locrian': 11}
PITCH_DEG = {0: 1, 2: 2, 4: 3, 5: 4, 7: 5, 9: 6, 11: 7}


def chord_letter(c, tonic, scale):
    """Hookpad chord -> [the chord as you play it, colour degree].

    Exact, not the nine-image rounding the cards use (that turns bIII into Em).
    Follows chord_label's rules: an applied chord is always major (applied=7 is
    the leading-tone diminished below its target); a bare degree-7 triad in a
    major key is the subtonic bVII, not vii-dim; borrowed chords take the
    borrowed mode's degree and quality."""
    ints = MODE.get(scale, MODE['major'])
    r = int(c.get('root') or 1)
    ap = int(c.get('applied') or 0)
    bor = c.get('borrowed') or ''
    # a CUSTOM borrowed scale comes as a list: the semitones above the tonic of
    # scale degrees 1-7, IN DEGREE ORDER (not sorted -- If I Fell's starts at
    # -1). Just What I Needed's [1,2,4,6,8,9,11] puts degree 3 on E with G# as
    # its third: an E major chord, not the Em a bare root=3 would be
    if isinstance(bor, list):
        bor = [int(x) % 12 for x in bor] if len(bor) == 7 else ''
    elif not isinstance(bor, str): bor = ''
    t = int(c.get('type') or 5) if str(c.get('type') or 5).isdigit() else 5
    T = PC.get(tonic, 0)
    if ap == 7:                                  # vii-dim of the target degree
        root, q = (T + ints[r - 1] - 1) % 12, 'dim'
        sev = 9 if t == 7 else None
    elif ap:                                     # V of / IV of / ... : major
        root, q = (T + ints[ap - 1] + MODE['major'][r - 1]) % 12, ''
        sev = 10 if t == 7 else None
    else:
        m = bor if isinstance(bor, list) else MODE.get(bor, ints) if bor else ints
        if not bor and r == 7 and scale == 'major': m = MODE['mixolydian']
        root = (T + m[r - 1]) % 12
        third = (m[(r + 1) % 7] - m[r - 1]) % 12
        fifth = (m[(r + 3) % 7] - m[r - 1]) % 12
        q = 'm' if third == 3 else ''
        if fifth == 6: q = 'dim'
        if fifth == 8: q = 'aug'
        sev = (m[(r + 5) % 7] - m[r - 1]) % 12 if t == 7 else None
    alts = [str(x) for x in c.get('alterations') or []]
    if '#5' in alts and q == 'dim': q = 'm'; alts.remove('#5')
    elif 'b5' in alts and q == 'm': q = 'dim'; alts.remove('b5')
    name = NAMES[root]
    sus = c.get('suspensions') or []
    om = c.get('omits') or []
    if sus: name += 'sus' + ''.join(str(x) for x in sus)
    elif 3 in om and not (c.get('adds') or []): name += '5'
    else: name += q
    if sev is not None:
        name += ('maj7' if sev == 11 and q != 'dim' else
                 '°7' if (q == 'dim' and sev == 9) else 'm7b5' if q == 'dim' else '7')
        name = name.replace('dim°7', '°7').replace('dimm7b5', 'm7b5')
    elif t in (9, 11, 13): name += str(t)
    for x in c.get('adds') or []: name += f'add{x}'
    name += ''.join(alts)
    ref = (T - PARENT.get(scale, 0)) % 12
    return [name, PITCH_DEG.get((root - ref) % 12, 0)]


def key_name(tonic, scale):
    return f'{tonic} {scale}'


def song(path, row):
    artist, title, skey, bpm, hp_bpm, bpm10 = row[:6]
    if title == title.lower(): title = title_case(title)      # newer sheets are all lowercase
    if artist == artist.lower(): artist = title_case(artist)
    d = json.load(open(path))
    bpb = B.beats_per_bar(d)
    keys = d.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    secs = sorted(d.get('sections') or [], key=lambda s: s.get('beat', 1))
    end = d.get('endBeat') or 0
    art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')

    # chords are spelled exactly as the Hookpad file has them, in its own key --
    # the user plays from Hookpad, so transposing into the sheet's key (tried
    # first) gave You Wreck Me as D# A# F when Hookpad says F C G
    k0 = keys[0]
    play = lambda t: t
    chords = sorted((c for c in d.get('chords') or [] if not c.get('isRest')),
                    key=lambda c: c.get('beat', 0))

    breaks = sorted(b['beat'] for b in d.get('breaks') or [] if b.get('beat') is not None)
    form, groups = [], {}
    for i, s in enumerate(secs):
        nm = str(s.get('name', '?')).strip()
        lo = s.get('beat', 1)
        hi = secs[i + 1]['beat'] if i + 1 < len(secs) else (end or 10**9)
        inside = [c for c in chords if lo <= c['beat'] < hi]
        if nm.lower() in SKIP or not inside: continue
        # the FORM: playing order, length from the section boundaries
        n = (hi - lo) / bpb
        form.append([nm, int(n) if n == int(n) else round(n, 1)])

        # the PROGRESSION: what sounds in each bar. A chord held across bars
        # fills them all; bars after the last chord ends are not counted.
        st, ss = ck.key_at(keys, lo)
        st = play(st)
        nbar = int(-(-(min(max(c['beat'] + c.get('duration', 0) for c in inside), hi) - lo) // bpb))
        cells = []
        for j in range(nbar):
            b0, b1 = lo + j * bpb, lo + (j + 1) * bpb
            bar = []
            for c in inside:
                if c['beat'] < b1 and c['beat'] + c.get('duration', 0) > b0 + 1e-6:
                    nm_c = chord_letter(c, st, ss)
                    if not bar or bar[-1][0] != nm_c[0]: bar.append(nm_c)
            # a chord carried in from the previous bar only counts if it is
            # still the one sounding on the downbeat
            cells.append(bar)
        lead = 0
        while cells and not cells[0]: cells.pop(0); lead += 1
        # Hookpad's own line breaks, as bar positions in this row, so a long
        # section reads in the same lines it has in Hookpad (Nothin' but the
        # Taillights' 20-bar chorus is 8 / 8 / 4 there)
        lines = sorted({int(round((b - lo) / bpb)) - lead for b in breaks if lo < b < hi})
        lines = [x for x in lines if 0 < x < len(cells)]
        times = 1
        for p in range(1, len(cells) // 2 + 1):
            if len(cells) % p: continue
            if all(cells[i:i + p] == cells[:p] for i in range(p, len(cells), p)):
                times = len(cells) // p; cells = cells[:p]; break
        if times > 1: lines = []                 # one pass of a loop needs no lines
        k = json.dumps(cells)
        if k in groups:
            g = groups[k]
            if nm not in g['parts']: g['parts'].append(nm)
            g['times'] = max(g['times'], times)
            continue
        groups[k] = dict(parts=[nm], bars=cells, times=times, lines=lines,
                         key=key_name(st, ss) if (st, ss) != (play(k0['tonic']), k0.get('scale', 'major')) else '')

    tempos = sorted(d.get('tempos') or [], key=lambda t: t.get('beat', 1))
    keylist = []
    for k in sorted(keys, key=lambda k: k.get('beat', 1)):
        kn = key_name(k.get('tonic', 'C'), k.get('scale', 'major'))
        if kn not in keylist: keylist.append(kn)
    return dict(title=title, artist=artist, key=str(skey or keylist[0]),
                letters=key_name(play(k0['tonic']), k0.get('scale', 'major')),
                hpkeys=keylist, bpm10=bpm10, bpm=bpm, hpbpm=hp_bpm,
                hptempos=[t['bpm'] for t in tempos if t.get('bpm')][:3],
                file=os.path.basename(path),
                meter='' if bpb == 4 else f"{int(bpb)}/4",
                form=form, prog=list(groups.values()))


def build_cards(pool):
    """the pool's tracker rows -> (cards, unresolved titles); shared with build_tempo_map"""
    wb = openpyxl.load_workbook(TRACKER, read_only=True)
    sheet = next(n for n in wb.sheetnames if n.replace(' ', '') == 'Guitar' + pool[1:])
    rows = [r for r in wb[sheet].iter_rows(values_only=True) if any(r)]
    # the sheets disagree on layout: Guitar100 is artist,title,your_key,bpm,
    # hookpad_bpm,bpm_10 and Guitar150-250 are song,band,key,bpm,bpm_10
    head = [str(h or '').strip().lower() for h in rows[0]]
    col = lambda *names: next((head.index(n) for n in names if n in head), None)
    ix = [col('artist', 'band'), col('title', 'song'), col('your_key', 'key'),
          col('bpm'), col('hookpad_bpm'), col('bpm_10')]
    assert ix[0] is not None and ix[1] is not None, head
    rows = [rows[0]] + [tuple(r[i] if i is not None and i < len(r) else None for i in ix)
                        for r in rows[1:]]
    library = json.load(open(HOOKPAD_LIST))
    # the export keeps a file for every song ever renamed or deleted, so only
    # files whose name is still in the library count: Dancing Queen otherwise
    # resolved to the old file the user deleted in favour of -hooktab
    live = {s.get('song', '').lower() for s in library}
    files = [f for f in glob.glob(os.path.join(pp.EXPORT, '*.json'))
             if os.path.splitext(os.path.basename(f))[0].lower() in live]
    catalog = []
    for p in UG_CATALOGS:
        if os.path.exists(p):
            import csv
            catalog = list(csv.DictReader(open(p, newline=''))); break
    cards, missing = [], []
    for r in rows[1:]:
        path = resolve(r[0], r[1], files)
        if not path: missing.append(r[1]); continue
        c = song(path, r)
        c['hookpad'] = hookpad_url(path, library)
        # the opening's palette word and shape, as on palette-groups.html, so
        # each round also practises placing the song in a group you know
        import build_palette_groups as PG
        op = {}
        for o in PG.openings(path):
            op.setdefault(o['section'], o)
        for p in c['prog']:
            tags = []
            for nm in p['parts']:
                o = op.get(nm)
                if not o: continue
                t = {'word': o['word'] or ' '.join(o['palette']), 'named': bool(o['word']),
                     'shape': o['shape'] or 'other', 'how': (f"{o['cellbars']:g}-bar ×{o['reps']}" if o['shape'] and o['reps'] > 1 else '')}
                if t not in tags: tags.append(t)
            p['tags'] = tags
        fa, _, ft = pp.split_variant(os.path.splitext(os.path.basename(path))[0])[0].partition('_')
        c['ug'], c['ughow'] = ug_url(r[0], [r[1], ft], catalog, aliases=[fa])
        c['id'] = pp.norm(f'{r[0]}_{r[1]}')
        cards.append(c)
    cards.sort(key=lambda c: c['title'].lower())
    return cards, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', default='G100')
    ap.add_argument('--out')
    a = ap.parse_args()
    out = a.out or os.path.join(HERE, f'{a.pool.lower()}-quiz.html')
    cards, missing = build_cards(a.pool)
    page = open(os.path.join(HERE, 'pool_quiz_template.html')).read()
    pools = sorted({os.path.basename(f).split('-')[0].upper()
                    for f in glob.glob(os.path.join(HERE, 'g*-quiz.html'))} | {a.pool.upper()},
                   key=lambda p: int(p[1:]))
    nav = ''.join(f'<a href="{p.lower()}-quiz.html" class="{"on" if p == a.pool.upper() else ""}">{p}</a>'
                  for p in pools)
    page = (page.replace('__NAV__', nav).replace('__POOL__', html.escape(a.pool))
                .replace('__CARDS__', json.dumps(cards, ensure_ascii=False)))
    open(out, 'w').write(page)
    print(f'{out}\n  {len(cards)} songs'
          + (f', unresolved: {missing}' if missing else ''))
    for c in cards:
        print(f"  {c['title'][:30]:30} {c['key']:16} letters in {c['letters']:10} "
              f"{str(c['bpm10']):>4}  hp={'ok' if c['hookpad'] else 'NONE'} ug={c['ughow']:8} {c['file']}"
              + ('' if c['prog'] else '   ! NO CHORDS'))


if __name__ == '__main__':
    main()
