#!/usr/bin/env python3
"""
_music/thirteen.html — the thirteen rhythms that cover 86% of everything.

The full library is 37 shapes; this is the part worth learning. Each one is
drawn across four bars and named, because a shape you can say is a shape you
can recall.

    python3 build_thirteen.py
"""
import argparse, html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rhythm_library as brl

HERE = os.path.dirname(os.path.abspath(__file__))

# a name for each, so it can be said aloud rather than spelled out
NAMES = {
 '4-4-4-4': 'one per bar',
 '2-2-2-2-2-2-2-2': 'two per bar',
 '2-2-4-2-2-4': 'two then a whole',
 '4-2-2-4-2-2': 'a whole then two',
 '2-2-2-2-2-2-4': 'two per bar, landing',
 '3.5-4.5-3.5-4.5': 'the Mr Jones',
 '4-4-4-1.5-2.5': 'push at the end',
 '8-8': 'two bars each',
 '1.5-2-2-2.5-1.5-2-2-2.5': 'the Fire Escape',
 '1.5-2.5-1.5-2.5-1.5-2.5-1.5-2.5': 'short-long',
 '2.5-1.5-2.5-1.5-2.5-1.5-2.5-1.5': 'long-short',
 '8-4-4': 'hold, then two',
 '2-1-1-2-1-1-2-1-1-2-1-1': 'the Lightning Bolt',
 '4-4-4-2-1-1': 'the Get Back',
 '2-1.5-4.5-3.5-4.5': "the Hard Day's Night",
 '3-1-3-1-3-1-3-1': 'the Yellow Submarine',
 '4-4-2-2-4': 'split the third bar',
 '4-4-4-2-2': 'split the last bar',
 '4-4-2-2-2-2': 'open, then double',
 '2-2-2-2-4-4': 'double, then open',
 '4-2-2-4-4': 'split, then open',
 '2-2-4-4-4': 'split the first bar',
 '1.5-2.5-1.5-2.5-1.5-2.5-1.5-2.5': 'short-long',
 '16': 'one chord, four bars',
 '4-4-8': 'two, then hold',
}


def kind(k):
    offs, at = [], 0.0
    for x in k.split('-')[:-1]:
        at += float(x); offs.append(at)
    if all(abs(o % 2) < .01 for o in offs): return 'grid'
    if all(abs(o % 1) < .01 for o in offs): return 'beat'
    return 'push'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=13)
    ap.add_argument('--pools', default='G50,G100,BEATLES')
    ap.add_argument('--out', default=os.path.join(HERE, 'thirteen.html'))
    a = ap.parse_args()
    tot, pat, ex = brl.collect(set(a.pools.split(',')))
    top = pat.most_common(a.n)
    cov = sum(v for _, v in top) / tot
    def esc(s): return html.escape(str(s))

    def bar(k):
        durs = [float(x) for x in k.split('-')]
        segs, at = [], 0.0
        for i, d in enumerate(durs):
            off = ' off' if abs(at % 2) > .01 else ''
            segs.append(f'<i class="s{i%4}{off}" style="left:{at/16*100:.4f}%;'
                        f'width:{d/16*100:.4f}%"></i>')
            at += d
        ticks = ''.join(f'<u style="left:{b/16*100:.4f}%"'
                        f'{" class=bar" if b % 4 == 0 else ""}></u>'
                        for b in range(1, 16))
        return f'<div class="rb">{ticks}{"".join(segs)}</div>'

    rows = ''.join(
        f'<div class="r {kind(k)}">'
        f'<div class="rk">{i}</div>'
        f'<div class="rn">{esc(NAMES.get(k, k))}'
        f'<em>{esc(k)}</em></div>'
        f'<div class="rbar">{bar(k)}</div>'
        f'<div class="rp">{v/tot*100:.0f}<span>%</span></div>'
        f'<div class="rs">{esc(ex[k][0][0])}</div>'
        f'</div>' for i, (k, v) in enumerate(top, 1))

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The thirteen</title><style>
  *{{box-sizing:border-box}}
  html,body{{height:100%;margin:0;background:#1a1a2e;color:#e0e0e0;
    font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
  .wrap{{height:100vh;display:flex;flex-direction:column;padding:13px 26px 10px}}
  .top{{display:flex;align-items:baseline;gap:16px;margin-bottom:2px}}
  h1{{font-size:19px;margin:0;font-weight:500}}
  .top span{{font-size:11.5px;color:#6a6a8a}}
  .meta{{color:#6a6a8a;font-size:11px;margin-bottom:8px}}
  .list{{flex:1;display:flex;flex-direction:column;gap:6px;min-height:0;
    overflow-y:auto}}
  /* a real minimum height per row: the point of this page is that you can
     take in one shape at a glance, and 50px of squeezed row does not do that */
  .r{{flex:1 0 auto;min-height:62px;display:flex;align-items:center;gap:16px;
    padding:0 14px 0 10px;border-radius:7px;background:#20203a;
    border:1px solid #2a2a4a;border-left:4px solid #5060a0}}
  .r.push{{background:#2a2334;border-color:#3a3040;border-left-color:#e0b060}}
  .rk{{width:26px;font-size:15px;color:#6a6a8a;font-variant-numeric:tabular-nums;
    text-align:right;font-weight:600}}
  .rn{{width:200px;font-size:17px;color:#fff;font-weight:600;line-height:1.15;
    letter-spacing:-.01em}}
  .rn em{{display:block;font-style:normal;font-family:ui-monospace,Menlo,monospace;
    font-size:11px;color:#7a7a9a;margin-top:3px;letter-spacing:0}}
  .rbar{{flex:1;min-width:0}}
  .rp{{width:60px;text-align:right;font-size:26px;font-weight:700;color:#7da3e8;
    font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
  .r.push .rp{{color:#e0b060}}
  .rp span{{font-size:11px;color:#5a5a7a;margin-left:1px;font-weight:500}}
  .rs{{width:168px;font-size:12.5px;color:#9a9ab8;text-align:right;line-height:1.3}}
  .rb{{position:relative;height:36px;background:#14142a;border-radius:4px;
    box-shadow:inset 0 1px 3px rgba(0,0,0,.35)}}
  .rb u{{position:absolute;top:0;bottom:0;width:1px;background:#2b2b4a}}
  .rb u.bar{{background:#50507c}}
  .rb i{{position:absolute;top:4px;bottom:4px;border-radius:3px}}
  .rb i.s0{{background:#5060a0}} .rb i.s1{{background:#2a6a52}}
  .rb i.s2{{background:#8a5a2a}} .rb i.s3{{background:#6a4a80}}
  .rb i.off{{box-shadow:inset 0 0 0 2px #e0b060}}
  .foot{{font-size:10.5px;color:#5a5a7a;margin-top:8px;flex:0 0 auto}}
  .foot b{{color:#8a8ab0;font-weight:600}}
</style></head><body><div class="wrap">
  <div class="top"><h1>The thirteen</h1>
    <span>four bars &middot; {cov:.0%} of every phrase in guitar50, guitar100
      and the Beatles</span></div>
  <p class="meta">Counted as the phrase is written &mdash;
    | C | C | Em | Em | is four bars, not two chords. Gold means the change
    arrives early, off the beat.</p>
  <div class="list">{rows}</div>
  <p class="foot"><b>Read a row as four bars.</b> Heavy ticks are bar lines,
    light ticks beats. Each block is one chord, sized to how long it lasts.
    The other 24 shapes in the corpus share the remaining {1-cov:.0%}.</p>
</div></body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{a.n} shapes, {cov:.1%} coverage -> {a.out}')


if __name__ == '__main__':
    main()
