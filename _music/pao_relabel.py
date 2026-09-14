#!/usr/bin/env python3
"""
Rebuild every card's caption from the kept raw artwork. Costs nothing.

Captions change — the form letters became the full section in bar format,
then the chords became the ACTUAL chords with the key stated. Each of those
would mean regenerating the artwork at 7 cents a card if the raws were not
kept. This recomputes the caption from the song data (via pao_batch.build_plan)
rather than replaying whatever string happened to be stored, so cards made
under an older format still get the current one.

    python3 pao_relabel.py
"""
import argparse, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_batch as pb
import pao_label as pl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.expanduser('~/Desktop/pao-cards'))
    ap.add_argument('--pools', default='G50,G100')
    a = ap.parse_args()
    raw_dir = os.path.join(a.dir, 'raw')
    raws = {os.path.basename(p)[:-len('.raw.png')]
            for p in glob.glob(os.path.join(raw_dir, '*.raw.png'))}
    if not raws: sys.exit(f'no kept raws in {raw_dir}')

    plan = {p['stem']: p for p in pb.build_plan(tuple(a.pools.split(',')))}
    done, orphan = 0, []
    for stem in sorted(raws):
        p = plan.get(stem)
        if not p: orphan.append(stem); continue
        pl.label(os.path.join(raw_dir, stem + '.raw.png'),
                 os.path.join(a.dir, stem + '.png'),
                 p['title'], f"{p['part']}  \u00b7  {p['key']}", p['scene'],
                 p['prog'], show_prog=True, context=p['context'],
                 picture=p['picture'])
        json.dump(dict(song=p['title'], part=p['part'], scene=p['scene'],
                       prog=p['prog'], context=p['context'],
                       picture=p['picture'], key=p['key'], show_prog=True),
                  open(os.path.join(raw_dir, stem + '.json'), 'w'), indent=1)
        done += 1
    print(f'relabelled {done} cards  (free)')
    if orphan:
        print(f'{len(orphan)} raws no longer in the plan: {", ".join(orphan[:5])}')


if __name__ == '__main__':
    main()
