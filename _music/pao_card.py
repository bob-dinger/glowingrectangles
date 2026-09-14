#!/usr/bin/env python3
"""
One card, on demand. For when you are learning a particular thing and want a
picture for it — not a batch.

    pao_card.py "Am F C G" --title "Have You Ever Seen the Rain" --part chorus
    pao_card.py "C G F G" --title "Heaven Is a Place on Earth" --pick   # choose from 5
    pao_card.py "F C G" --title Wonderwall --hide            # flashcard, no chords shown

Writes to ~/Desktop/pao-cards/ with the caption composited on.
"""
import argparse, base64, os, random, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_options as po
import pao_images as pi
import pao_label as pl
import requests

import bars as B
import pao_pools as pp

COST = 0.07          # roughly, per gpt-image-1 render at 1024


def phrases_of(song, section):
    """-> (stem, section name, form string, [(letter, chords, reps, tail), ...])

    A card is never a whole section: a section is a FORM over phrases, so you
    want one picture per DISTINCT phrase plus the letters. Nashville Blues'
    verse is two pictures and "ABAB", not one impossible picture of sixteen
    chords. This is the bar model from bars.py wired into the tool that
    actually spends money on images.
    """
    path = pp.find(song, pp.build_index())
    if not path: sys.exit(f'no hookpad file for {song!r}')
    _, _, _, secs = B.bars_for(path)
    stem = pp.strip_tags(os.path.splitext(os.path.basename(path))[0])
    for name, bb in secs:
        if section and section.lower() not in str(name).lower(): continue
        f = (B.forms(bb) or [None])[0]
        if not f: continue
        if not B.sayable(f):
            # no repeating phrase: draw the line as consecutive 4-slot scenes
            core, reps, tail = B.phrase_chords(bb)
            runs = [(chr(65+i//4), core[i:i+4], 1, [])
                    for i in range(0, len(core), 4)]
            return stem, name, f'a run of {len(core)}', runs
        seen, out = {}, []
        for lab, ch in zip(f['labs'], f['chunks']):
            if lab in seen: continue
            seen[lab] = 1
            core, reps, tail = B.phrase_chords(ch)
            out.append((lab, core, reps, tail))
        return stem, name, ' '.join(f['labs']), out
    sys.exit(f'no section matching {section!r}')


def render(scene, title, part, prog, out_dir, model, size, hide, style=None,
           context=None, keep_raw=True, picture=None):
    os.makedirs(out_dir, exist_ok=True)
    # Keep the unlabelled render plus a sidecar of everything the caption
    # needs. Captions get revised often (the form letters became the full
    # section in bar format, for instance) and without the raw, revising one
    # means paying to generate the picture again. Disk is cheaper than the API.
    raw_dir = os.path.join(out_dir, 'raw')
    if keep_raw: os.makedirs(raw_dir, exist_ok=True)
    stem = pi.safe(title) + (f'__{pi.safe(part)}' if part else '')
    raw_path = os.path.join(raw_dir if keep_raw else out_dir, stem + '.raw.png')
    out_path = os.path.join(out_dir, stem + '.png')
    r = requests.post(pi.ENDPOINT, timeout=180,
                      json={'model': model, 'prompt': f'{scene}. {style or pi.STYLE}.',
                            'size': size, 'n': 1},
                      headers={'Authorization': f'Bearer {pi.api_key()}',
                               'Content-Type': 'application/json'})
    if r.status_code != 200:
        sys.exit(f'API {r.status_code}: {r.text[:300]}')
    d = r.json()['data'][0]
    img = (base64.b64decode(d['b64_json']) if 'b64_json' in d
           else requests.get(d['url'], timeout=120).content)
    open(raw_path, 'wb').write(img)
    if keep_raw:
        import json as _json
        _json.dump(dict(song=title, part=part, scene=scene, prog=prog,
                        context=context, show_prog=not hide, picture=picture),
                   open(os.path.join(raw_dir, stem + '.json'), 'w'), indent=1)
    pl.label(raw_path, out_path, title, part or '\u2014', scene, prog,
             show_prog=not hide, context=context, picture=picture)
    if not keep_raw: os.remove(raw_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('progression', nargs='?', default=None)
    ap.add_argument('--song', default=None,
                    help='read the phrases from a song instead of a progression')
    ap.add_argument('--section', default=None)
    ap.add_argument('--go', action='store_true',
                    help='actually spend money; without it you get the plan only')
    ap.add_argument('--title', default='')
    ap.add_argument('--part', default='')
    ap.add_argument('--scene', default='', help='write the scene yourself')
    ap.add_argument('--pick', action='store_true', help='offer 5 scenes, pick one')
    ap.add_argument('--hide', action='store_true', help='omit chords from the caption')
    ap.add_argument('--full', default='', help='real progression for the caption, '
                    'when the drawn cell is only its repeating core')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/pao-cards'))
    ap.add_argument('--model', default='gpt-image-1')
    ap.add_argument('--size', default='1024x1024')
    a = ap.parse_args()

    # ---- song mode: one card per distinct phrase in the section's form ----
    if a.song:
        stem, name, form, ph = phrases_of(a.song, a.section)
        art, _, ttl = stem.partition('_')
        title = ttl.replace('-', ' ').title()
        rng = random.Random(a.seed)
        print(f'\n  {title} \u2014 {name}     form: {form}')
        plan = []
        for lab, core, reps, tail in ph:
            prog = '-'.join(core) + (f' x{reps}' if reps > 1 else '')
            if tail: prog += ' then ' + '-'.join(tail)
            scene = a.scene or pi.scene_for(core, rng)
            plan.append((lab, prog, scene))
            print(f'\n    {lab}  {prog}\n        {scene}')
        print(f'\n  {len(plan)} image{"s" if len(plan)!=1 else ""} '
              f'\u2248 ${len(plan)*COST:.2f}')
        if not a.go:
            print('  (plan only \u2014 add --go to render)\n'); return
        for lab, prog, scene in plan:
            p = render(scene, title, f'{name} {lab}', f'{prog}   [{form}]',
                       a.out, a.model, a.size, a.hide)
            print(f'  -> {p}')
        return

    if not a.progression: sys.exit('give a progression, or --song')
    seq = po.parse(a.progression)
    prog = '-'.join(seq)
    rng = random.Random()

    if a.scene:
        scene = a.scene
    elif a.pick:
        opts = [pi.scene_for(seq, rng) for _ in range(5)]
        for i, s in enumerate(opts, 1): print(f'  {i}. {s}')
        try:
            n = int(input('\n  which? (1-5, or 0 to reroll) ') or 1)
        except (ValueError, EOFError):
            n = 1
        if n == 0:
            return main()
        scene = opts[max(1, min(5, n)) - 1]
    else:
        scene = pi.scene_for(seq, rng)

    print(f'\n  {prog}\n  {scene}\n')

    os.makedirs(a.out, exist_ok=True)
    stem = pi.safe(a.title or prog) + (f'__{pi.safe(a.part)}' if a.part else '')
    raw_path = os.path.join(a.out, stem + '.raw.png')
    out_path = os.path.join(a.out, stem + '.png')

    key = pi.api_key()
    body = {'model': a.model, 'prompt': f'{scene}. {pi.STYLE}.',
            'size': a.size, 'n': 1}
    r = requests.post(pi.ENDPOINT, json=body, timeout=180,
                      headers={'Authorization': f'Bearer {key}',
                               'Content-Type': 'application/json'})
    if r.status_code != 200:
        sys.exit(f'API {r.status_code}: {r.text[:300]}')
    d = r.json()['data'][0]
    img = (base64.b64decode(d['b64_json']) if 'b64_json' in d
           else requests.get(d['url'], timeout=120).content)
    open(raw_path, 'wb').write(img)

    pl.label(raw_path, out_path, a.title or prog, a.part or '—', scene,
             a.full or prog, show_prog=not a.hide)
    os.remove(raw_path)
    print(f'  -> {out_path}')


if __name__ == '__main__':
    main()
