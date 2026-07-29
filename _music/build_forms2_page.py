"""Build _music/forms2.html — song-level form for the Guitar 50 + Guitar 100 lists,
derived from Ultimate Guitar tabs (the non-Beatles counterpart to forms.html).

Why this is a separate page from forms.html: the source is different in kind. forms.html
reads your own Hookpad files, so it has bar counts, chords and melody, and can draw a
piano roll. A UG tab gives the section NAMES and their ORDER and nothing else — no bar
math is possible. So the chips here carry no "(8)" bar count, and clicking a section
shows that slice of the raw tab text instead of a roll.

Two source formats, in preference order:
  1. `-chords-` tabs — plain text with `[Verse 1]` bracket headers. Preferred: they also
     give the chord/lyric body, so section text is available.
  2. `-official-` interactive tabs — no bracket headers, but the page's PARTS panel lists
     the sections in order. Scraped separately into `<file>.parts.txt` sidecars. Names
     only, no body text.

GOTCHA the hard way: a tab file's NAME proves nothing about its contents. The old scrapers
picked the first search hit with no artist check but saved under a basename built from the
user's list, so `fastball_fire-escape.txt` held Foster the People's song. 13 of these 100
were wrong that way. Every row here is joined by filename but the `# <url>` header is
re-checked against the expected artist, and mismatches are reported, not silently used.
"""
import os, re, csv, glob, json, difflib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'forms2.html')
TABS = os.path.expanduser('~/Desktop/music/ug_tabs')
LISTS = [('G50', 'Guitar 50', os.path.expanduser('~/Desktop/5-24-26/guitar50_ug_urls.txt')),
         ('G100', 'Guitar 100', os.path.expanduser('~/Desktop/5-24-26/guitar100_ug_urls.txt'))]

# artist shorthands the lists use that the tab filenames spell out
ALIAS = {'rhcp': 'red-hot-chili-peppers', 'ccr': 'creedence-clearwater-revival'}


def kebab(s):
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    return re.sub(r'-+', '-', s).strip('-_')


def artist_key(a):
    k = kebab(a)
    k = k[4:] if k.startswith('the-') else k
    return ALIAS.get(k, k)


def find_file(files, title, artist):
    """list row -> tab basename. Exact on <artist>_<title>, else fuzzy within the artist."""
    a, t = artist_key(artist), kebab(title)
    for c in (f'{a}_{t}', f'{kebab(artist)}_{t}'):
        if c in files:
            return c
    same = [k for k in files if k.split('_')[0] == a]
    m = difflib.get_close_matches(f'{a}_{t}', same or list(files), n=1, cutoff=0.82)
    return m[0] if m else None


def url_artist_ok(path, artist):
    """the `# <url>` header must name the artist we asked for — see module docstring"""
    m = re.search(r'/tab/([^/\s]+)/', open(path, errors='ignore').read(300))
    if not m:
        return True, ''          # bare-id urls carry no artist to check
    ua = m.group(1)
    ua = ua[4:] if ua.startswith('the-') else ua
    ea = artist_key(artist)
    ok = ea in ua or ua in ea or difflib.SequenceMatcher(None, ea, ua).ratio() >= 0.7
    return ok, ua


def kind(nm):
    """section name -> the colour bucket it belongs in (same vocabulary as forms.html)"""
    n = nm.lower()
    for k, v in (('intro', 'intro'), ('outro', 'outro'), ('coda', 'outro'), ('fade', 'outro'),
                 ('pre', 'pre'), ('post', 'pre'), ('verse', 'verse'),
                 ('bridge', 'bridge'), ('middle', 'bridge'), ('refrain', 'refrain'),
                 ('chorus', 'chorus'), ('solo', 'solo'), ('instrumental', 'solo'),
                 ('break', 'solo'), ('riff', 'solo'), ('theme', 'solo'),
                 ('interlude', 'link'), ('intrelude', 'link'), ('link', 'link')):
        if k in n:
            return v
    return 'other'


# the two forms we set out to count, longest first so the more specific one wins
TARGETS = [('VVCVCB', 'V V C V C B'), ('VCVCB', 'V C V C B')]


def sections_of(path, sidecar):
    """(section names, per-section raw text). Bracket headers if present, else PARTS."""
    txt = open(path, errors='ignore').read()
    # NOT anchored to end-of-line: plenty of tabs put the section's chords on the header
    # line itself ("[Verse] G---Am7-Em---C-"), and anchoring silently drops those sections
    hits = list(re.finditer(r'^\[([^\]]{1,40})\]', txt, re.M))
    if hits:
        names, bodies = [], []
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(txt)
            names.append(m.group(1).strip())
            bodies.append(txt[m.end():end].strip('\n'))
        return names, bodies, 'chords'
    if sidecar and os.path.exists(sidecar):
        # sidecar line 1 is the `# <url>` provenance comment
        names = [l.strip() for l in open(sidecar).read().split('\n')[1:] if l.strip()]
        return names, [''] * len(names), 'parts'
    return [], [], 'none'


def key_of(txt):
    m = re.search(r'Key:\s*([A-G][#b]?m?)', txt)
    return m.group(1) if m else ''


def links_index():
    """slug-ish key -> (hookpad_url, ug_url) from parcels.songs.

    Returns two dicts: one keyed on <artist>_<title>, one keyed on title alone.
    The title-only map is a fallback for rows filed under a different artist than
    the guitar lists use — the lists credit the writer where Supabase credits whoever
    charted it (Seashores of Old Mexico is under Merle Haggard not George Strait,
    Pancho and Lefty under Willie Nelson not Townes Van Zandt). Only consulted when
    exactly one song has that title, so it can't silently grab the wrong one.
    """
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
        c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
                             user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                             port=os.environ.get('DB_PORT', 5432))
        cur = c.cursor()
        cur.execute('select slug, title, artist, hookpad_url, ug_url from parcels.songs')
        rows = cur.fetchall()
        c.close()
    except Exception as e:
        print(f'  ! no Supabase ({e}) — building without Hookpad links')
        return {}, {}
    by, bytitle = {}, defaultdict(dict)
    for slug, t, a, hp, ug in rows:
        v = (hp, ug)
        if slug:
            by.setdefault(re.sub(r'_o-[0-9a-f]{6}$', '', slug), v)   # strip dedupe suffix
        by.setdefault(f'{artist_key(a)}_{kebab(t)}', v)
        # keyed by artist so a song stored twice as variants collapses to one entry;
        # two DIFFERENT artists sharing a title still counts as ambiguous and is dropped
        bytitle[kebab(t)].setdefault(artist_key(a), v)
    return by, {k: next(iter(v.values())) for k, v in bytitle.items() if len(v) == 1}


def find_links(by, bytitle, title, artist):
    k = f'{artist_key(artist)}_{kebab(title)}'
    if k in by: return by[k]
    m = difflib.get_close_matches(k, list(by), n=1, cutoff=0.86)
    if m: return by[m[0]]
    return bytitle.get(kebab(title), (None, None))


def main():
    files = {os.path.basename(p)[:-4]: p for p in glob.glob(TABS + '/*.txt')
             if not p.endswith('.parts.txt')}
    by, bytitle = links_index()
    pools, problems = [], []
    for pid, pname, path in LISTS:
        songs = []
        for r in csv.DictReader(open(path), delimiter='\t'):
            title, artist = r['title'].strip(), r['artist'].strip()
            key = find_file(files, title, artist)
            if not key:
                problems.append((pid, title, artist, 'no tab file'))
                continue
            ok, ua = url_artist_ok(files[key], artist)
            if not ok:
                problems.append((pid, title, artist, f'url artist is "{ua}"'))
            names, bodies, src = sections_of(files[key], os.path.join(TABS, key + '.parts.txt'))
            if not names:
                problems.append((pid, title, artist, 'no section labels in tab'))
                continue
            # UG transcribers sometimes stack the same header twice for a repeat; that is
            # one thing to look at, not two. Distinct names (Verse 1 / Verse 2) always stay.
            secs, prev = [], None
            for nm, bd in zip(names, bodies):
                if nm.lower() == prev:
                    continue
                prev = nm.lower()
                # NOTE: deliberately no tab body text. This page is committed and
                # glowingrectangles.io serves /_music/ publicly, so the lyrics and chord
                # bodies in the UG tabs stay out of the repo. Section names and their
                # order are facts about the song, and are all this page needs.
                secs.append({'name': nm, 'kind': kind(nm)})
            core = ''.join({'verse': 'V', 'chorus': 'C', 'bridge': 'B'}[s['kind']]
                           for s in secs if s['kind'] in ('verse', 'chorus', 'bridge'))
            match = next((lbl for pat, lbl in TARGETS if core.startswith(pat)), '')
            head = open(files[key], errors='ignore').read(400)
            hp, db_ug = find_links(by, bytitle, title, artist)
            # link to the tab this form was actually read from, not whatever Supabase
            # has on file — otherwise the page could show one tab's form and link to another
            m = re.search(r'https://tabs\.ultimate-guitar\.com/tab/\S+', head)
            ug = m.group(0).strip() if m else db_ug
            songs.append({'title': title, 'artist': artist, 'file': key, 'src': src,
                          'key': key_of(head), 'hp': hp, 'ug': ug,
                          'sections': secs, 'core': core, 'match': match,
                          'shape': ' '.join(s['kind'] for s in secs
                                            if s['kind'] in ('verse', 'chorus', 'bridge',
                                                             'refrain', 'solo'))})
        pools.append({'id': pid, 'name': pname, 'songs': songs})

    allsongs = [s for p in pools for s in p['songs']]
    for i, s in enumerate(allsongs):
        s['i'] = i
    shapes = Counter(s['shape'] for s in allsongs)
    for s in allsongs:
        s['shared'] = shapes[s['shape']]
    # songs are emitted once and pools hold indices into them — the combined "Both lists"
    # view would otherwise duplicate every song and double the page
    groups = [{'id': p['id'], 'name': p['name'], 'ix': [s['i'] for s in p['songs']]}
              for p in pools]
    groups.append({'id': 'ALL', 'name': 'Both lists', 'ix': [s['i'] for s in allsongs]})

    open(OUT, 'w').write(PAGE.replace('__DATA__', json.dumps({'songs': allsongs,
                                                             'groups': groups})))
    nug = sum(1 for s in allsongs if s['ug'])
    nhp = sum(1 for s in allsongs if s['hp'])
    print(f'wrote {OUT}  |  {len(allsongs)} songs  |  {nug} UG links, {nhp} Hookpad links')
    for s in allsongs:
        if not s['hp'] or not s['ug']:
            print(f'   no link: {s["title"][:32]:34} {s["artist"][:20]:22} '
                  f'{"" if s["ug"] else "UG "}{"" if s["hp"] else "HP"}')
    for p in pools:
        n = sum(1 for s in p['songs'] if s['match'])
        print(f'   {p["name"]:<12} {len(p["songs"]):>3} songs   '
              f'{sum(1 for s in p["songs"] if s["match"] == "V V C V C B")} VVCVCB, '
              f'{sum(1 for s in p["songs"] if s["match"] == "V C V C B")} VCVCB')
    if problems:
        print(f'\n{len(problems)} rows need attention:')
        for pid, t, a, why in problems:
            print(f'   {pid:<5} {t[:32]:<34} {a[:20]:<22} {why}')


PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Song Structures · Guitar 50 + 100</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:225px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff}
#side h1{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#888;padding:14px 16px 6px;margin:0}
.srow{padding:8px 16px;cursor:pointer;border-bottom:1px solid #f0f0f4;display:flex;justify-content:space-between;gap:8px}
.srow:hover{background:#eef}.srow.on{background:#2a2a44;color:#fff}
.srow .n{font-size:11px;color:#aaa}.srow.on .n{color:#dde}
#side .note{font-size:11px;color:#999;padding:10px 16px;line-height:1.5;border-top:1px solid #eee}
#main{flex:1;overflow-y:auto;padding:20px 26px}
h2{margin:0 0 4px;font-size:20px}
.meta{color:#888;font-size:12px;margin-bottom:12px}
.opts{display:flex;gap:16px;align-items:center;margin-bottom:14px;font-size:12px;color:#556;flex-wrap:wrap}
.opts label{cursor:pointer;user-select:none}
.opts select{font:12px -apple-system,sans-serif;padding:3px 6px;border:1px solid #ccd;border-radius:6px;background:#fff}
.song{display:flex;align-items:baseline;gap:10px;padding:6px 0;border-bottom:1px solid #ededf2}
.song .t{width:250px;flex:none;font-weight:600;font-size:13px}
.song .t .sub{display:block;font-weight:400;font-size:10px;color:#aaa}
.lnk{display:inline-block;font-size:9px;font-weight:700;letter-spacing:.03em;text-decoration:none;
  border-radius:3px;padding:1px 5px;margin-left:4px;vertical-align:1px}
.lnk.ug{color:#8a5a00;background:#fdf0d5}.lnk.ug:hover{background:#f8e0a8}
.lnk.hp{color:#1a5f8a;background:#dceaf5}.lnk.hp:hover{background:#c2dcef}
.seq{display:flex;flex-wrap:wrap;gap:3px;align-items:center}
.sec{font-size:10px;font-weight:700;color:#fff;border-radius:4px;padding:2px 7px;white-space:nowrap;
  text-shadow:0 1px 2px rgba(0,0,0,.35)}
.k-verse{background:#5090f0}.k-bridge{background:#e8734a}.k-refrain{background:#50c878}
.k-chorus{background:#2e9e5b}.k-intro{background:#b8bcc8}.k-outro{background:#8c90a0}
.k-solo{background:#a878d8}.k-link{background:#d8c860}.k-pre{background:#7fb5e8}
.k-other{background:#fff;color:#889;border:1px solid #ccd;text-shadow:none}
.legend{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.badge{font-size:10px;color:#8a2be2;background:#f3ecff;border-radius:4px;padding:1px 6px;margin-left:6px}
.mbadge{font-size:10px;font-weight:700;color:#0a7c4a;background:#dbf5e6;border-radius:4px;padding:1px 6px;margin-left:6px}
.srcp{font-size:9px;color:#b0a0d0;background:#f2eefc;border-radius:3px;padding:0 4px;margin-left:5px}
</style></head><body><div id=wrap>
<div id=side><h1>Lists</h1><div id=list></div>
  <div class=note>Sections come from Ultimate Guitar tabs, so there are no bar counts —
  a UG tab gives the order of sections and nothing more. Labels are transcriber
  conventions: many tabs write a chorus once and say &ldquo;repeat chorus,&rdquo; so
  repeats run low here. Hover a chip for the tab&rsquo;s own name for that section.</div>
</div>
<div id=main>
  <h2 id=ttl></h2><div class=meta id=sub></div>
  <div class=opts>
    <label><input type=checkbox id=hideIO> hide intro / outro</label>
    <label><input type=checkbox id=sortShape> group by shape</label>
    <label>form
      <select id=only>
        <option value="">all songs</option>
        <option value="V V C V C B">V V C V C B</option>
        <option value="V C V C B">V C V C B</option>
      </select></label>
  </div>
  <div class=legend>
    <span class="sec k-verse">verse</span><span class="sec k-chorus">chorus</span>
    <span class="sec k-bridge">bridge</span><span class="sec k-pre">pre</span>
    <span class="sec k-solo">solo</span><span class="sec k-intro">intro</span>
    <span class="sec k-outro">outro</span><span class="sec k-link">link</span>
  </div>
  <div id=body></div>
</div></div>
<script>
const D=__DATA__, SONGS=D.songs, G=D.groups;
const songsOf=g=>g.ix.map(i=>SONGS[i]);
let SI=0;
const L=document.getElementById('list');
G.forEach((p,i)=>{const r=document.createElement('div');r.className='srow';r.dataset.i=i;
  r.innerHTML=`<span>${p.name}</span><span class=n>${p.ix.length}</span>`;
  r.onclick=()=>sel(i);L.appendChild(r);});
const hideIO=document.getElementById('hideIO'),sortShape=document.getElementById('sortShape'),
      only=document.getElementById('only');
hideIO.onchange=sortShape.onchange=only.onchange=()=>sel(SI);
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
function sel(i){SI=i;
  document.querySelectorAll('.srow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
  const p=G[i], all=songsOf(p);
  let songs=all.slice();
  if(only.value) songs=songs.filter(o=>o.match===only.value);
  if(sortShape.checked) songs.sort((a,b)=>a.shape.localeCompare(b.shape)||a.title.localeCompare(b.title));
  document.getElementById('ttl').textContent=p.name;
  const nv=all.filter(o=>o.match==='V V C V C B').length,
        nc=all.filter(o=>o.match==='V C V C B').length;
  document.getElementById('sub').textContent=
    `${songs.length} of ${all.length} shown · ${nv} are V V C V C B, ${nc} are V C V C B · sections from Ultimate Guitar tabs`;
  document.getElementById('body').innerHTML=songs.map(o=>{
    const secs=o.sections.filter(x=>!(hideIO.checked&&(x.kind==='intro'||x.kind==='outro')));
    const chips=secs.map(x=>
      `<span class="sec k-${x.kind}" title="${esc(x.name)}">${x.kind}</span>`).join('');
    const sh=o.shared>1?`<span class=badge>${o.shared} share this shape</span>`:'';
    const mb=o.match?`<span class=mbadge>${o.match}</span>`:'';
    const sp=o.src==='parts'?`<span class=srcp title="from the official tab's PARTS panel — names only">parts</span>`:'';
    const L=(o.ug?`<a class="lnk ug" href="${o.ug}" target=_blank rel=noopener title="Ultimate Guitar tab this form came from">UG</a>`:'')
           +(o.hp?`<a class="lnk hp" href="${o.hp}" target=_blank rel=noopener title="open in Hookpad">HP</a>`:'');
    return `<div class=song><div class=t>${esc(o.title)}<span class=sub>${esc(o.artist)}${o.key?' · '+o.key:''}${L}</span></div>
            <div class=seq>${chips}${mb}${sh}${sp}</div></div>`;}).join('')
    || '<div class=meta>no songs match that form in this list</div>';}
sel(0);
</script></body></html>"""

if __name__ == '__main__':
    main()
