#!/usr/bin/env python3
"""
A card for an eight-bar phrase built on an alternating pair that resolves home.

These phrases are not eight chords to memorise — they are TWO, alternating,
then the tonic. So the scene shows two figures trading something back and
forth, then both arriving somewhere. The melody's cadence tone is carried by
HEIGHT: the tonic sits on the ground, the third at waist height, the fifth
overhead. That gives the picture a second channel — identity for the chords,
vertical position for the melody.

    pao_phrase.py --engine "Dm G" --home C --cadence 1 \
                  --title "Maggie May" --part chorus
    pao_phrase.py --engine "F G" --home C --cadence 1 \
                  --title "Neon Moon" --part chorus --dry-run
"""
import argparse, base64, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_options as po
import pao_images as pi
import pao_label as pl
import requests

HEIGHT = {
    '1': 'resting on the ground at the very bottom of the frame',
    '3': 'held at waist height in the middle of the frame',
    '5': 'raised high overhead near the top of the frame',
}
CADENCE_NAME = {'1': 'lands on the tonic', '3': 'lands on the third',
                '5': 'lands on the fifth'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True, help='the alternating pair, e.g. "Dm G"')
    ap.add_argument('--home', default='C')
    ap.add_argument('--cadence', default='1', choices=['1', '3', '5'])
    ap.add_argument('--title', default='')
    ap.add_argument('--part', default='')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/pao-cards'))
    ap.add_argument('--model', default='gpt-image-1')
    ap.add_argument('--size', default='1024x1024')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    pair = po.parse(a.engine)
    if len(pair) != 2:
        sys.exit('--engine needs exactly two different chords')
    home = po.parse(a.home)[0]
    rng = random.Random()

    def art(w):                       # a / an, and leave plurals alone
        if w.endswith('s') and not w.endswith('ss'): return w
        return ('an ' if w[0] in 'aeiou' else 'a ') + w

    # objects that are inherently plural read badly as "a goggles"
    singular = [w for w in po.W[home]['object']
                if not (w.endswith('s') and not w.endswith('ss'))]
    who1 = rng.choice(po.W[pair[0]]['person'])
    who2 = rng.choice(po.W[pair[1]]['person'])
    thing = rng.choice(singular or po.W[home]['object'])
    where = rng.choice(po.W[home]['place'])

    scene = (f'{art(who1).capitalize()} and {art(who2)} passing '
             f'{art(thing)} back and forth to each other in {art(where)}, '
             f'with the {thing} {HEIGHT[a.cadence]}')
    prog = f'{pair[0]}-{pair[1]} x3, then {home}-{home}'
    caption = (f'{pair[0]} and {pair[1]} trading, home on {home}, '
               f'melody {CADENCE_NAME[a.cadence]}')

    print(f'\n  {prog}\n  {scene}\n')
    if a.dry_run:
        return

    os.makedirs(a.out, exist_ok=True)
    stem = pi.safe(a.title or prog) + (f'__{pi.safe(a.part)}' if a.part else '')
    raw, out = (os.path.join(a.out, stem + s) for s in ('.raw.png', '.png'))

    body = {'model': a.model, 'prompt': f'{scene}. {pi.STYLE}.',
            'size': a.size, 'n': 1}
    r = requests.post(pi.ENDPOINT, json=body, timeout=180,
                      headers={'Authorization': f'Bearer {pi.api_key()}',
                               'Content-Type': 'application/json'})
    if r.status_code != 200:
        sys.exit(f'API {r.status_code}: {r.text[:300]}')
    d = r.json()['data'][0]
    img = (base64.b64decode(d['b64_json']) if 'b64_json' in d
           else requests.get(d['url'], timeout=120).content)
    open(raw, 'wb').write(img)
    pl.label(raw, out, a.title or prog, a.part or '—', caption, prog)
    os.remove(raw)
    print(f'  -> {out}')


if __name__ == '__main__':
    main()
