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
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pool_quiz as Q

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tempo-map.html')
POOLS = ['G50', 'G100', 'G150', 'G200', 'G250']


def main():
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
    page = open(os.path.join(HERE, 'tempo_map_template.html')).read()
    open(OUT, 'w').write(page.replace('__ROWS__', json.dumps(rows, ensure_ascii=False)))
    tempos = sorted({r['bpm10'] for r in rows if isinstance(r['bpm10'], (int, float))})
    print(f'{OUT}\n  {len(rows)} songs in {len(tempos)} tempos, {tempos[0]}-{tempos[-1]}'
          f'   no bpm_10: {sum(1 for r in rows if not isinstance(r["bpm10"], (int, float)))}')


if __name__ == '__main__':
    main()
