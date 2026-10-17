#!/usr/bin/env python3
"""
Tempo quiz: see a song, name its tempo (bpm_10), hear it, and see who else
lives at that tempo.

    themap_venv/python build_tempo_quiz.py          # G50-G250 -> tempo-quiz.html

Same rows as tempo-map.html (build_tempo_map.collect), so the answer is the
tracker's rounded bpm_10, the one the user memorises, with the exact listed bpm
and the Hookpad bpm beside it. Songs without a bpm_10 are left out.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_tempo_map as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'tempo-quiz.html')


def main():
    rows = [r for r in M.collect() if isinstance(r['bpm10'], (int, float))]
    keep = ('pool', 'title', 'artist', 'key', 'bpm10', 'bpm', 'hpbpm', 'hookpad', 'ug', 'ughow')
    rows = [{k: r[k] for k in keep} for r in rows]
    page = open(os.path.join(HERE, 'tempo_quiz_template.html')).read()
    open(OUT, 'w').write(page.replace('__ROWS__', json.dumps(rows, ensure_ascii=False))
                             .replace('__POOLS__', json.dumps(M.POOLS)))
    print(f'{OUT}\n  {len(rows)} songs')


if __name__ == '__main__':
    main()
