#!/usr/bin/env python3
"""
A section as a FORM over phrases, and one scene per distinct phrase.

This is the fix for the thing that made the old card tool useless on real
songs. A section is not a chord list: am-G-C, am-G-C, am-G-F, am-G-C is not a
twelve-chord progression, it is AABA over a three-chord phrase. So you need
two pictures (A and B) plus the letters — never one impossible picture of
twelve chords.

Phrases are also where the slot count finally works out. A PAO scene holds
four slots; phrases are three or four chords; sections are sixteen. Scope the
scene to the phrase and almost everything fits.

    python3 pao_section.py "nashville blues"
    python3 pao_section.py "maggie may" --section chorus --pick 3
    python3 pao_section.py "texas time travelin" --bars 2
"""
import argparse, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp
import pao_options as po

render = B.render_bar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('--section', default=None)
    ap.add_argument('--bars', type=int, default=0,
                    help='force the phrase length in bars (default: derived)')
    ap.add_argument('--pick', type=int, default=1, help='scenes per phrase')
    ap.add_argument('--seed', type=int, default=None)
    a = ap.parse_args()

    path = B.find_song(a.song) if hasattr(B, 'find_song') else pp.find(a.song, pp.build_index())
    if not path: sys.exit(f'no hookpad file for {a.song!r}')
    tonic, scale, bpb, secs = B.bars_for(path)
    rng = random.Random(a.seed)

    stem = pp.strip_tags(os.path.splitext(os.path.basename(path))[0])
    print(f'\n{stem}   key {tonic} {scale}   {bpb:g} beats/bar')

    for name, bars in secs:
        if a.section and a.section.lower() not in str(name).lower(): continue
        fs = B.forms(bars)
        if not fs: continue
        f = next((x for x in fs if x['n'] == a.bars), fs[0]) if a.bars else fs[0]

        # A winning 1-bar reading means nothing repeated at 2, 3, 4 or 8 bars
        # — so there is no form here, just a line. Maggie May's pre-chorus
        # walks F C F G Dm Em Dm C and never comes back; five one-chord
        # "pictures" would be a worse memory than one drawn sentence.
        # ...and the same is true of a "form" with eight letters. A form is
        # something you can say aloud — AABA, ABAC. ABCBDEFA is a through-
        # composed line wearing letters, so it takes the run treatment too.
        if not B.sayable(f):
            core, reps, tail = B.phrase_chords(bars)
            print(f'\n  {name}   {len(bars)} bars   no repeating phrase — '
                  f'one run of {len(core)}')
            print(f'    {" | ".join(render(b) for b in bars)}')
            print(f'    {"-".join(core)}')
            for _ in range(a.pick):
                bits = [po.sentence([(c, rng.choice(po.W[c][po.ROLES[s]]))
                                     for s, c in enumerate(core[i:i+4])])
                        for i in range(0, len(core), 4)]
                print(f'    -> {", then ".join(bits)}')
            n_pic = (len(core) + 3) // 4
            print(f'\n    to learn: {n_pic} picture{"s" if n_pic != 1 else ""} in order')
            continue

        hd = ' '.join(render(b) for b in f['head'])
        tl = ' '.join(render(b) for b in f['tail'])
        print(f'\n  {name}   {len(bars)} bars   {f["n"]}-bar phrases   form: '
              + (f'({hd}) ' if hd else '') + ' '.join(f['labs'])
              + (f' then ({tl})' if tl else ''))

        by_letter = {}
        for lab, ch in zip(f['labs'], f['chunks']):
            by_letter.setdefault(lab, ch)
        for lab, ch in sorted(by_letter.items()):
            core, reps, tail = B.phrase_chords(ch)
            cells = ' | '.join(B.render_bar(b) for b in ch)
            rep = (f'  ×{reps}' if reps > 1 else '') + \
                  (f' then {"-".join(tail)}' if tail else '')
            print(f'\n    {lab} = | {cells} |{rep}')
            if not core:
                print('        (no chords)'); continue
            print(f'        {"-".join(core)}   {len(core)} slot'
                  f'{"s" if len(core) != 1 else ""}')
            for _ in range(a.pick):
                bits = [po.sentence([(c, rng.choice(po.W[c][po.ROLES[s]]))
                                     for s, c in enumerate(core[i:i+4])])
                        for i in range(0, len(core), 4)]
                print(f'        -> {", then ".join(bits)}')

        print(f'\n    to learn: {len(by_letter)} picture'
              f'{"s" if len(by_letter) != 1 else ""} + "{"".join(f["labs"])}"')


if __name__ == '__main__':
    main()
