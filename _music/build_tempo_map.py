#!/usr/bin/env python3
"""
The guitar pools by tempo: one circle per bpm_10 (70, 80, 90 ...), sized by how
many songs sit there; click one for its songs.

    themap_venv/python build_tempo_map.py          # G50-G250 -> tempo-map.html

Same data as the pool quizzes (build_pool_quiz.build_cards): the tempo is the
tracker's rounded bpm_10, the one the user memorises, with the exact bpm and the
Hookpad bpm beside it. Each song also carries its key, section lengths and the
palette word + shape of its first opening, so a tempo bucket can be learned as
a group the same way palette-map.html groups by chords.
"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pool_quiz as Q
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tempo-map.html')
POOLS = ['G50', 'G100', 'G150', 'G200', 'G250']


def collect():
    rows = []
    for pool in POOLS:
        cards, missing = Q.build_cards(pool)
        if missing: print(f'  {pool} unresolved: {missing}')
        for c in cards:
            tags = [t for p in c['prog'] for t in p.get('tags', [])]
            rows.append(dict(pool=pool, title=c['title'], artist=c['artist'], key=c['key'],
                             hpkey=c['letters'], bpm10=c['bpm10'], bpm=c['bpm'], hpbpm=c['hpbpm'],
                             form=c['form'], tag=tags[0] if tags else None,
                             hookpad=c['hookpad'], ug=c['ug'], ughow=c['ughow']))
    return rows


# The Beatles, by recording project (the Beatles2 sheet: 12 projects in session
# order, covers numbered C01..). Tempo is the tracker's listed BPM rounded to the
# nearest ten, falling back to Hookpad's; only beatles_* files can match, so a
# title shared with another artist ("Help!", "Money") cannot borrow their file.
BEATLES_OUT = os.path.join(HERE, 'beatles-tempo-map.html')
PROJECTS = ['PPM', 'WTB', 'AHDN', 'BFS', 'Help', 'RS', 'Rev', 'Pepper', 'MMT', 'White', 'LIB', 'Abbey']
CSV = os.path.expanduser('~/Desktop/music/songs_to_learn.csv')
# Beatles2 title -> the Hookpad file's title, where they differ too much to match
ALIAS = {"sgt. pepper's lonely hearts club band": 'sgt peppers', 'good morning, good morning': 'good morning',
         'kansas city - hey, hey, hey, hey': 'kansas city'}


def beatles_rows():
    wb = openpyxl.load_workbook(Q.TRACKER, read_only=True)
    listed = {Q.pp.norm(r['Title']): r for r in csv.DictReader(open(CSV))
              if 'beatles' in r['Artist'].lower()}
    files, library, catalog = Q.context()
    files = [f for f in files if os.path.basename(f).lower().startswith('beatles_')]
    rows, names, missing, proj = [], {}, [], None
    for n, txt in (r[:2] for r in wb['Beatles2'].iter_rows(values_only=True) if any(r)):
        m = re.match(r'Recording project (\d+): (.*?) \(', str(txt or ''))
        if m:
            proj = PROJECTS[int(m.group(1)) - 1]; names[proj] = f'{m.group(1)} · {m.group(2)}'
            continue
        if n is None or proj is None: continue
        date, _, title = str(txt).partition(':')
        title = title.strip()
        hit = listed.get(Q.pp.norm(title)) or listed.get(Q.pp.norm(re.sub(r'\s*\(.*\)', '', title)))
        bpm = float(hit['BPM']) if hit and hit['BPM'] else None
        r = ('beatles', ALIAS.get(title.lower(), title), hit['Key'] if hit else None, bpm, None, None)
        c = Q.card_for(r, files, library, catalog)
        if c is None and '(' in title:
            c = Q.card_for(('beatles', re.sub(r'\s*\(.*\)', '', title)) + r[2:], files, library, catalog)
        if c is None: missing.append(title); continue
        if bpm is None: bpm = c['hpbpm'] or (c.get('hptempos') or [None])[0]
        if not bpm: missing.append(title + ' (no tempo)'); continue
        bpm = int(bpm) if float(bpm) == int(bpm) else bpm
        tags = [t for p in c['prog'] for t in p.get('tags', [])]
        rows.append(dict(pool=proj, title=title, artist=date.strip(), key=c['key'] or c['letters'],
                         hpkey=c['letters'], bpm10=int(round(float(bpm) / 10) * 10), bpm=bpm, hpbpm=c['hpbpm'],
                         form=c['form'], tag=tags[0] if tags else None,
                         hookpad=c['hookpad'], ug=c['ug'], ughow=c['ughow']))
    return rows, names, missing


def write(out, rows, cfg, title, h1, poollab):
    page = open(os.path.join(HERE, 'tempo_map_template.html')).read()
    for k, v in (('__ROWS__', json.dumps(rows, ensure_ascii=False)), ('__CFG__', json.dumps(cfg, ensure_ascii=False)),
                 ('__TITLE__', title), ('__H1__', h1), ('__POOLLAB__', poollab)):
        page = page.replace(k, v)
    open(out, 'w').write(page)


def main():
    if '--beatles' in sys.argv:
        rows, names, missing = beatles_rows()
        n = len(PROJECTS)
        # early to late along one hue sweep, so the ring reads as a timeline
        cols = [f'hsl({int(210 - 260 * i / (n - 1)) % 360},62%,50%)' for i in range(n)]
        write(BEATLES_OUT, rows, dict(pools=PROJECTS, names=names, colors=cols, ls='tempomap:beatles'),
              'Beatles Tempo Map', 'Beatles tempo map<a href="tempo-map.html">guitar pools →</a>', 'projects')
        print(f'{BEATLES_OUT}\n  {len(rows)} songs   unresolved {len(missing)}: {missing}')
        return
    rows = collect()
    write(OUT, rows, dict(pools=POOLS, ls='tempomap'), 'Tempo Map',
          'Tempo map<a href="palette-map.html">palette map →</a><a href="beatles-tempo-map.html">beatles →</a>', 'pools')
    tempos = sorted({r['bpm10'] for r in rows if isinstance(r['bpm10'], (int, float))})
    print(f'{OUT}\n  {len(rows)} songs in {len(tempos)} tempos, {tempos[0]}-{tempos[-1]}'
          f'   no bpm_10: {sum(1 for r in rows if not isinstance(r["bpm10"], (int, float)))}')


if __name__ == '__main__':
    main()
