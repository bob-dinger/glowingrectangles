#!/usr/bin/env python3
"""
_music/permutations-120.html — all 120 orderings of three chords from six.

Numbered combo.perm: the 20 combinations run in degree order (I ii iii IV V
vi) and the six orderings inside each sort by that same index, so 1.1 is
C-Dm-Em and 8.3 is F-C-G. Usage is overlaid, because 102 of the 120 never
happen and the point of the page is seeing which corner of the space music
lives in.

    python3 build_perms_page.py
"""
import argparse, collections, html, itertools, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import build_rhythm_library as brl
import pao_pools as pp

HERE = os.path.dirname(os.path.abspath(__file__))
SIX = ['C', 'Dm', 'Em', 'F', 'G', 'Am']
IX = {c: i for i, c in enumerate(SIX)}
RN = {'C':'I', 'Dm':'ii', 'Em':'iii', 'F':'IV', 'G':'V', 'Am':'vi'}


def perms(c):
    return sorted(itertools.permutations(c), key=lambda p: [IX[x] for x in p])


def usage(pools):
    """Two counts, because they answer different questions.

    `exact` = sections whose whole chord cell IS these three. `runs` = every
    consecutive run of three inside any cell, wrapping the end to the start
    since a progression is a loop with no real beginning.

    The distinction matters: C-G-Am is never a complete three-chord section
    but appears 77 times inside C-G-Am-F. Counting only the first makes ten
    perfectly ordinary trios look unused, which is false.
    """
    use = collections.Counter(); runs = collections.Counter()
    ex = collections.defaultdict(list)
    idx = pp.build_index()
    for s in brl.slugs_for(pools):
        path = pp.find(s, idx)
        if not path: continue
        try: _, _, _, secs = B.bars_for(path)
        except Exception: continue
        art, _, ttl = pp.strip_tags(os.path.basename(path).rsplit('.', 1)[0]).partition('_')
        seen = set()
        for name, bb in secs:
            if (name, tuple(bb)) in seen: continue
            seen.add((name, tuple(bb)))
            core, _, tail = B.phrase_chords(bb)
            seq = core + tail
            seq = [c for c in seq if c in SIX]
            if len(seq) == 3 and len(set(seq)) == 3:
                use[tuple(seq)] += 1
            n = len(seq)
            if n < 3: continue
            for i in range(n if n > 3 else 1):
                w = tuple(seq[(i+j) % n] for j in range(3))
                if len(set(w)) == 3:
                    runs[w] += 1
                    if len(ex[w]) < 1:
                        ex[w].append((ttl.replace('-', ' ').title(), name))
    return use, runs, ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100,BEATLES')
    ap.add_argument('--out', default=os.path.join(HERE, 'permutations-120.html'))
    a = ap.parse_args()
    use, runs, ex = usage(set(a.pools.split(',')))
    combos = list(itertools.combinations(SIX, 3))
    def esc(s): return html.escape(str(s))

    used = sum(1 for p in itertools.permutations(SIX, 3) if use.get(p))
    inruns = sum(1 for p in itertools.permutations(SIX, 3) if runs.get(p))
    secs = sum(use.values())
    dead = [i for i, c in enumerate(combos, 1)
            if not any(use.get(p) for p in perms(c))]

    cells = []
    for ci, c in enumerate(combos, 1):
        live = sum(use.get(p, 0) for p in perms(c))
        rows = ''
        for pi_, p in enumerate(perms(c), 1):
            u, r = use.get(p, 0), runs.get(p, 0)
            song = f'<u>{esc(ex[p][0][0])}</u>' if ex.get(p) else ''
            rows += (f'<div class="p{" on" if u else ""}">'
                     f'<b>{ci}.{pi_}</b>'
                     f'<span>{esc("-".join(p))}</span>'
                     f'<em>{esc("-".join(RN[x] for x in p))}</em>'
                     f'<i>{u or "&middot;"}</i><ins>{r or "&middot;"}</ins>'
                     f'{song}</div>')
        cells.append(
            f'<div class="combo{" dead" if not live else ""}">'
            f'<h3>{ci}<span>{esc("-".join(c))}</span>'
            f'<b>{live if live else "not on its own"}</b></h3>{rows}</div>')

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>120 orderings</title><style>
  *{{box-sizing:border-box}}
  html,body{{margin:0;background:#1a1a2e;color:#e0e0e0;
    font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:13px}}
  .wrap{{padding:14px 20px 30px}}
  .top{{display:flex;align-items:baseline;gap:16px}}
  h1{{font-size:19px;margin:0;font-weight:500}}
  .top span{{font-size:11.5px;color:#6a6a8a}}
  .meta{{color:#6a6a8a;font-size:11.5px;margin:3px 0 10px;max-width:760px;line-height:1.5}}
  .big{{display:flex;align-items:center;gap:26px;padding:9px 0;margin-bottom:12px;
    border-top:1px solid #2a2a4a;border-bottom:1px solid #2a2a4a}}
  .hero{{display:flex;align-items:baseline;gap:11px}}
  .hero b{{font-size:54px;line-height:.82;font-weight:700;color:#7da3e8;letter-spacing:-.04em}}
  .hero span{{font-size:11px;color:#8a8ab0;text-transform:uppercase;
    letter-spacing:.1em;line-height:1.5}}
  .b{{display:flex;flex-direction:column}}
  .b b{{font-size:19px;font-weight:600;color:#fff;line-height:1}}
  .b span{{font-size:9.5px;color:#6a6a8a;text-transform:uppercase;
    letter-spacing:.09em;margin-top:3px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:10px}}
  .combo{{background:#20203a;border:1px solid #2a2a4a;border-radius:7px;padding:8px 10px}}
  .combo{{border-left:4px solid #3a6ea8}}
  .combo.dead{{border-left-color:#4a4a62}}
  .combo h3{{margin:0 0 6px;font-size:12px;font-weight:600;display:flex;
    align-items:baseline;gap:7px;color:#5a5a7a}}
  .combo h3 span{{color:#fff;font-size:13.5px;font-family:ui-monospace,Menlo,monospace}}
  .combo h3 b{{margin-left:auto;font-size:10px;color:#7da3e8;font-weight:600}}
  .combo.dead h3 b{{color:#9a9ab8;font-weight:600;text-transform:uppercase;
    letter-spacing:.08em;font-size:9px}}
  .p{{display:flex;align-items:baseline;gap:6px;padding:3px 4px;font-size:11.5px;
    color:#b0b0c8;border-bottom:1px solid #23233a;border-radius:3px}}
  .p:last-child{{border-bottom:none}}
  .p b{{width:30px;font-weight:500;color:#7a7a98;font-variant-numeric:tabular-nums}}
  .p span{{width:78px;font-family:ui-monospace,Menlo,monospace}}
  .p em{{font-style:normal;width:56px;font-size:10px;color:#82829e}}
  .p i{{font-style:normal;margin-left:auto;font-weight:700;color:#e0b060;
    font-size:12px;font-variant-numeric:tabular-nums;width:26px;text-align:right}}
  .p ins{{text-decoration:none;font-weight:600;color:#7da3e8;font-size:12px;
    width:34px;text-align:right;font-variant-numeric:tabular-nums}}
  .p u{{text-decoration:none;flex-basis:100%;font-size:10px;color:#61617f;
    padding-left:36px}}
  /* the used ones are the highlight: warm background, gold number, white
     chords. Nothing is dimmed, so an unused ordering is still readable. */
  .p.on{{background:#2f2a1e;color:#f0e8d8}}
  .p.on b{{color:#e0b060}} .p.on span{{color:#fff;font-weight:600}}
  .p.on em{{color:#b8a888}} .p.on i{{color:#e0b060}}
  .p.on u{{color:#a89878}}
  .foot{{font-size:11px;color:#5a5a7a;margin-top:14px;line-height:1.55;max-width:820px}}
  .foot b{{color:#8a8ab0}}
</style></head><body><div class="wrap">
  <div class="top"><h1>Every ordering of three</h1>
    <span>20 combinations &times; 6 orderings &mdash; C Dm Em F G Am</span></div>
  <p class="meta">Numbered <b>combo.ordering</b>. The combinations run in degree
    order, and the six orderings inside each sort the same way, so 1.1 is
    C&ndash;Dm&ndash;Em and 8.3 is F&ndash;C&ndash;G. The count is how many
    distinct song-sections use that exact order.</p>
  <div class="big">
    <div class="hero"><b>{used}</b><span>of 120 stand alone<br>as a whole part</span></div>
    <div class="b" style="color:#7da3e8"><b style="color:#7da3e8">{inruns}</b>
      <span>appear inside longer progressions</span></div>
    <div class="b"><b>{secs}</b><span>three-chord sections</span></div>
    <div class="b"><b>{len(dead)}</b><span>trios never stand alone</span></div>
  </div>
  <div class="grid">{''.join(cells)}</div>
  <p class="foot"><b>Combo 8 (C&ndash;F&ndash;G) is the outlier</b> &mdash; four of
    its six orderings stand alone as complete parts, which no other trio manages.
    Ten trios never stand alone: {esc(', '.join(map(str, dead)))} &mdash; grey spine
    rather than blue. They all still occur inside longer progressions. Runs wrap
    the end of a loop to its start, since a progression has no real first chord.
    Counted once per song-section across guitar50,
    guitar100 and the Beatles.</p>
</div></body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{used}/120 used, {len(dead)} dead combos -> {a.out}')


if __name__ == '__main__':
    main()
