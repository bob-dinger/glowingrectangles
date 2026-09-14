#!/usr/bin/env python3
"""
Render N phrase-cards, hardest sections first.

Takes the difficulty ranking from hard_list.py, expands each section into its
distinct phrases (the bar model — one picture per phrase, not per section),
and renders until it hits the budget. Skips anything already on disk.

    python3 pao_batch.py --n 25              # plan only
    python3 pao_batch.py --n 25 --go         # render
"""
import argparse, collections, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import hard_list as hl
import pao_card as pc
import pao_images as pi
import pao_pools as pp
import chord_key as ck

import random


def build_plan(pools=('G50','G100'), n=999, seed=7, style='mix',
               out=None, redo=True):
    """The same plan main() renders, as data. pao_relabel calls this so a
    caption can be rebuilt from the song rather than from whatever string was
    stored when the card was made — otherwise every caption change needs a
    new sidecar and the old cards are stranded."""
    secs = hl.sections(set(pools))
    freq = collections.Counter()
    for s in secs:
        for c in {tuple(B.phrase_chords(ch)[0]) for ch in s['f']['chunks']}:
            freq[c] += 1
    ranked = sorted(secs, key=lambda s: -hl.score(s, freq)[0])
    rng = random.Random(seed)
    plan, seen = [], set()
    for s in ranked:
        if len(plan) >= n: break
        f = s['f']
        stem_ = os.path.splitext(s['song'])[0]
        art, _, ttl = stem_.partition('_')
        title = pp.strip_tags(ttl).replace('-', ' ').title()
        form = ' '.join(f['labs'])
        tonic, sc_ = s['key'].split()[0], s['key'].split()[-1]
        bars_all = ck.line(tonic, sc_, s['bars'])
        done = {}
        for lab, ch in zip(f['labs'], f['chunks']):
            if lab in done or len(plan) >= n: continue
            done[lab] = 1
            cell, reps, tail_bars = B.cell_of(list(ch))
            core, _, tail = B.phrase_chords(ch)
            if len(core) + len(tail) < 3: continue
            prog = ck.line(tonic, sc_, cell)
            if reps > 1: prog += f'  x{reps}'
            if tail_bars: prog += '  then ' + ck.line(tonic, sc_, tail_bars)
            part = f"{s['part']} {lab}"
            stem = pi.safe(title) + '__' + pi.safe(part)
            if stem in seen: continue
            if not redo and out and os.path.exists(os.path.join(out, stem + '.png')):
                continue
            seen.add(stem)
            plan.append(dict(title=title, part=part, prog=prog, form=form,
                             scene=pi.scene_for(core + tail, rng), stem=stem,
                             style=pi.style_for(style, title),
                             style_name=pi.style_name(style, title),
                             context=bars_all,
                             # only worth printing when the song is NOT in C —
                             # otherwise it repeats the line directly above it
                             picture=(None if tonic == 'C' else
                                      'picture: ' + '\u2013'.join(core + tail)),
                             key=f'key of {tonic}'))
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=25)
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/pao-cards'))
    ap.add_argument('--go', action='store_true')
    ap.add_argument('--redo', action='store_true',
                    help='regenerate cards that already exist')
    ap.add_argument('--throttle', type=float, default=3.0)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--min-chords', type=int, default=3,
                    dest='min_chords', help='skip phrases shorter than this')
    ap.add_argument('--style', default='mix',
                    help="one of pao_images.STYLES, or 'mix' for one per song")
    ap.add_argument('--model', default='gpt-image-1')
    ap.add_argument('--size', default='1024x1024')
    a = ap.parse_args()

    secs = hl.sections(set(a.pools.split(',')))
    freq = collections.Counter()
    for s in secs:
        for c in {tuple(B.phrase_chords(ch)[0]) for ch in s['f']['chunks']}:
            freq[c] += 1
    ranked = sorted(secs, key=lambda s: -hl.score(s, freq)[0])

    rng = random.Random(a.seed)
    plan, seen = [], set()
    for s in ranked:
        if len(plan) >= a.n: break
        f = s['f']
        stem_ = os.path.splitext(s['song'])[0]          # song carries '.json'
        art, _, ttl = stem_.partition('_')
        title = pp.strip_tags(ttl).replace('-', ' ').title()
        form = ' '.join(f['labs'])
        # the WHOLE section in bar format, as context under the phrase. More
        # use than the form letters, which the user can read off it anyway.
        tonic, sc_ = s['key'].split()[0], s['key'].split()[-1]
        bars_all = ck.line(tonic, sc_, s['bars'])
        done = {}
        for lab, ch in zip(f['labs'], f['chunks']):
            if lab in done or len(plan) >= a.n: continue
            done[lab] = 1
            cell, reps, tail_bars = B.cell_of(list(ch))
            core, _, tail = B.phrase_chords(ch)
            # A short phrase needs no mnemonic. "A king" to remember C is a
            # picture of something you already know, and two chords is barely
            # better — you do not forget F-G. Three is where a picture starts
            # earning its 7 cents.
            if len(core) + len(tail) < a.min_chords: continue
            # Show the BAR LAYOUT, not a flat chord list. "| C Dm | G |"
            # says C for two beats, Dm for two, G for a whole bar — which is
            # the rhythm at the level that defines the progression's identity
            # (where the changes fall), and it is already in the bar model.
            prog = ck.line(tonic, sc_, cell)
            if reps > 1: prog += f'  x{reps}'
            if tail_bars: prog += '  then ' + ck.line(tonic, sc_, tail_bars)
            picture = (None if tonic == 'C' else
                       'picture: ' + '\u2013'.join(core + tail))
            part = f"{s['part']} {lab}"
            stem = pi.safe(title) + '__' + pi.safe(part)
            if stem in seen: continue
            if not a.redo and os.path.exists(os.path.join(a.out, stem + '.png')):
                continue
            seen.add(stem)
            plan.append(dict(title=title, part=part, prog=prog, form=form,
                             # pass the WHOLE cell: scene_for chains extra chords into a second
                             # sentence, whereas core[:4] silently dropped them and
                             # produced a card encoding the wrong progression
                             scene=pi.scene_for(core + tail, rng), stem=stem,
                             style=pi.style_for(a.style, title),
                             style_name=pi.style_name(a.style, title),
                             context=bars_all, picture=picture,
                             key=f'key of {tonic}'))

    print(f'\n{len(plan)} images  ≈ ${len(plan)*pc.COST:.2f}\n')
    last = None
    for i, p in enumerate(plan, 1):
        if p['title'] != last:
            print(f"\n  {p['title']}")
            last = p['title']
        print(f"    {i:>2}. {p['part']:<19} {p['prog']:<26} "
              f"{p['style_name']:<10} {p['scene'][:44]}")
    if not a.go:
        print('\n  (plan only — add --go to render)\n'); return

    print()
    for i, p in enumerate(plan, 1):
        try:
            out = pc.render(p['scene'], p['title'], f"{p['part']}  ·  {p['key']}",
                            p['prog'], a.out, a.model, a.size, False,
                            p['style'], p['context'], picture=p['picture'])
            print(f"  {i:>2}/{len(plan)}  {os.path.basename(out)}")
        except SystemExit as e:
            print(f'  {i:>2}/{len(plan)}  FAILED: {e}'); break
        time.sleep(a.throttle)
    print(f'\n-> {a.out}')


if __name__ == '__main__':
    main()
