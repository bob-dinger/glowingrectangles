#!/usr/bin/env python3
"""
_music/how-few.html — three chords over eight bars, possible vs actual.

Generated, not written, so the counts cannot drift from the corpus.

    python3 build_how_few_page.py
"""
import argparse, collections, html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp

HERE = os.path.dirname(os.path.abspath(__file__))


def letter_patterns(pools):
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    pat = collections.Counter(); ex = collections.defaultdict(list)
    n = 0
    for s in sorted(k for k, v in pm.items() if v in pools):
        path = pp.find(s, idx)
        if not path: continue
        try: _, _, _, ss = B.bars_for(path)
        except Exception: continue
        seen = set()
        for name, bb in ss:
            k = (name, tuple(bb))
            if k in seen: continue
            seen.add(k)
            if len(bb) != 8: continue
            if any(len(b) != 1 or b[0] in ('·', '?') for b in bb): continue
            ch = [b[0] for b in bb]
            if len(set(ch)) != 3: continue
            n += 1
            lab, out = {}, []
            for c in ch:
                if c not in lab: lab[c] = chr(65 + len(lab))
                out.append(lab[c])
            p = ''.join(out); pat[p] += 1
            art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')
            ex[p].append((ttl.replace('-', ' ').title(), name, '-'.join(dict.fromkeys(ch))))
    return n, pat, ex


def duration_patterns(pools):
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    pat = collections.Counter(); ex = collections.defaultdict(list)
    tot = push = 0
    for s in sorted(k for k, v in pm.items() if v in pools):
        path = pp.find(s, idx)
        if not path: continue
        d = json.load(open(path))
        m = (d.get('meters') or [{}])[0]
        if float(m.get('numBeats') or m.get('num') or 4) != 4: continue
        ch = sorted((c for c in (d.get('chords') or []) if not pp.is_rest(c)),
                    key=lambda c: c.get('beat', 0))
        if not ch: continue
        art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')
        for sec in (sorted((d.get('sections') or []), key=lambda x: x.get('beat', 0))
                    or [{'beat': 1}]):
            lo = sec.get('beat', 1)
            w = [c for c in ch if lo <= c['beat'] < lo + 8]
            if not w: continue
            durs = tuple(round(c.get('duration', 0)*2)/2 for c in w)
            if abs(sum(durs) - 8) > .01: continue
            tot += 1
            offs = [round((c['beat']-lo)*2)/2 for c in w]
            isp = any(abs(o % 2) > .01 for o in offs)
            if isp: push += 1
            key = ('-'.join(f'{x:g}' for x in durs), isp)
            pat[key] += 1
            ex[key].append((ttl.replace('-', ' ').title(), sec.get('name', '?')))
    return tot, push, pat, ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--out', default=os.path.join(HERE, 'how-few.html'))
    a = ap.parse_args()
    pools = set(a.pools.split(','))
    nsec, lpat, lex = letter_patterns(pools)
    tot, push, dpat, dex = duration_patterns(pools)
    possible = (3**8 - 3*2**8 + 3) // 6

    def esc(s): return html.escape(str(s))

    def chips(p):
        return ''.join(f'<span class="l l{c}">{c}</span>' for c in p)

    lrows = ''.join(
        f'<tr><td class="n">{c}</td><td class="pat">{chips(p)}</td>'
        f'<td class="sng">{esc(lex[p][0][0])} <i>{esc(lex[p][0][1])}</i></td>'
        f'<td class="ch">{esc(lex[p][0][2])}</td></tr>'
        for p, c in lpat.most_common())

    ev = [(k, v) for k, v in dpat.most_common() if not k[1]]
    pu = [(k, v) for k, v in dpat.most_common() if k[1]]
    def rbar(dur_str, pushed):
        """Draw the pattern across eight beats instead of naming it.

        "2-2-2-2" is a number; a row of blocks with the bar line at beat 4 is
        a rhythm. A push then shows up as what it is — segments that do not
        line up with the grid underneath them.
        """
        durs = [float(x) for x in dur_str.split('-')]
        segs, at = [], 0.0
        for i, d in enumerate(durs):
            off = 'off' if abs(at % 2) > .01 else ''
            segs.append(f'<i class="s{i%3} {off}" style="left:{at/8*100:.4f}%;'
                        f'width:{d/8*100:.4f}%"></i>')
            at += d
        ticks = ''.join(f'<u style="left:{b/8*100:.4f}%"'
                        f'{" class=bar" if b == 4 else ""}></u>' for b in range(1, 8))
        return f'<div class="rb{" p" if pushed else ""}">{ticks}{"".join(segs)}</div>'

    def drows(items, lim):
        return ''.join(
            f'<tr><td class="n">{v}</td><td class="rbw">{rbar(k[0], k[1])}</td>'
            f'<td class="dur">{esc(k[0])}</td>'
            f'<td class="sng">{esc(dex[k][0][0])} <i>{esc(dex[k][0][1])}</i></td></tr>'
            for k, v in items[:lim])

    top9 = sum(v for _, v in ev[:5]) + sum(v for _, v in pu[:4])

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>How few</title><style>
  *{{box-sizing:border-box}}
  html,body{{height:100%;margin:0;background:#1a1a2e;color:#e0e0e0;
    font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
  .wrap{{height:100vh;display:flex;flex-direction:column;padding:14px 18px 10px}}
  h1{{font-size:17px;margin:0 0 3px;font-weight:500;letter-spacing:.02em}}
  .meta{{color:#6a6a8a;font-size:11.5px;line-height:1.45;margin-bottom:10px;max-width:760px}}
  .big{{display:flex;align-items:center;gap:30px;margin:0 0 12px;padding:10px 0;
    border-top:1px solid #2a2a4a;border-bottom:1px solid #2a2a4a}}
  .hero{{display:flex;align-items:baseline;gap:12px}}
  .hero b{{font-size:92px;line-height:.82;font-weight:700;color:#7da3e8;
    letter-spacing:-.04em}}
  .hero span{{font-size:12px;color:#8a8ab0;text-transform:uppercase;
    letter-spacing:.11em;line-height:1.5}}
  .bs{{display:flex;gap:26px}}
  .b{{display:flex;flex-direction:column}}
  .b b{{font-size:22px;font-weight:600;color:#fff;line-height:1}}
  .b span{{font-size:10px;color:#6a6a8a;text-transform:uppercase;
    letter-spacing:.1em;margin-top:3px}}
  .b.hi b{{color:#7da3e8}}
  .cols{{flex:1;display:flex;gap:26px;min-height:0}}
  .col{{flex:1;display:flex;flex-direction:column;min-width:0}}
  .col.shapes{{flex:1.45}}
  .col.shapes table{{font-size:15px}}
  .col.shapes td{{padding:5px 8px 5px 0}}
  .col.shapes td.n{{width:34px;font-size:14px}}
  .col.shapes td.pat{{width:210px}}
  .col.shapes td.ch{{width:110px;font-size:13px}}
  .col.shapes .l{{width:22px;height:22px;line-height:22px;font-size:13px;
    margin-right:3px;border-radius:4px}}
  h2{{font-size:11.5px;text-transform:uppercase;letter-spacing:.11em;color:#8a8ab0;
    margin:0 0 6px;font-weight:600}}
  .sc{{overflow-y:auto;min-height:0;flex:1}}
  table{{width:100%;border-collapse:collapse;font-size:11.5px}}
  td{{padding:3px 6px 3px 0;border-bottom:1px solid #23233c;vertical-align:middle}}
  td.n{{color:#7a7a9a;width:26px;text-align:right;font-variant-numeric:tabular-nums}}
  td.pat{{width:150px;white-space:nowrap}}
  td.dur{{width:104px;font-family:ui-monospace,Menlo,monospace;color:#8a8ab0;
    font-size:10px}}
  td.rbw{{width:150px;padding-right:10px}}
  .rb{{position:relative;height:15px;background:#22223c;border-radius:2px}}
  .rb u{{position:absolute;top:0;bottom:0;width:1px;background:#2e2e4e}}
  .rb u.bar{{background:#4a4a70;width:1px}}
  .rb i{{position:absolute;top:2px;bottom:2px;border-radius:2px}}
  .rb i.s0{{background:#5060a0}} .rb i.s1{{background:#2a6a52}}
  .rb i.s2{{background:#8a5a2a}}
  .rb i.off{{box-shadow:inset 0 0 0 1px #e0b060}}
  td.sng{{color:#b8b8cc}} td.sng i{{color:#6a6a8a;font-style:normal}}
  td.ch{{font-family:ui-monospace,Menlo,monospace;color:#8a8ab0;width:86px}}
  .l{{display:inline-block;width:15px;height:15px;line-height:15px;text-align:center;
    border-radius:3px;font-size:9.5px;font-weight:700;margin-right:2px}}
  .lA{{background:#5060a0;color:#fff}} .lB{{background:#2a6a52;color:#fff}}
  .lC{{background:#8a5a2a;color:#fff}}
  .note{{font-size:10.5px;color:#6a6a8a;line-height:1.5;margin-top:8px;
    border-top:1px solid #23233c;padding-top:7px}}
  .note b{{color:#9a9ab8;font-weight:600}}
</style></head><body>
<div class="wrap">
  <h1>Three chords, eight bars</h1>
  <p class="meta">How many ways can three chords fill eight measures? The
    arithmetic says hundreds. Real songs use a dozen, and the distribution is
    brutally top-heavy.</p>

  <div class="big">
    <div class="hero"><b>{len(lpat)}</b><span>shapes<br>actually used</span></div>
    <div class="bs">
      <div class="b"><b>{possible:,}</b><span>possible</span></div>
      <div class="b"><b>{len(lpat)/possible:.1%}</b><span>of the space</span></div>
      <div class="b"><b>{len(dpat)}</b><span>rhythms</span></div>
      <div class="b hi"><b>{top9/tot:.0%}</b><span>in nine of them</span></div>
    </div>
  </div>

  <div class="cols">
    <div class="col shapes">
      <h2>Which shapes &mdash; {nsec} sections, one chord per bar</h2>
      <div class="sc"><table>{lrows}</table></div>
      <p class="note"><b>Eight bars is two four-bar halves.</b> Five of these
        are an exact 4-bar cell played twice. Most of the rest are two halves
        where the second changes only its ending.</p>
    </div>
    <div class="col">
      <h2>Which rhythms &mdash; {tot} two-bar cells in 4/4</h2>
      <h2 style="color:#5a8a72;margin-top:2px">on the grid &mdash; {tot-push}
        cells, and only {len(ev)} patterns</h2>
      <div class="sc" style="flex:0 0 auto"><table>{drows(ev, 6)}</table></div>
      <h2 style="color:#a07a4a;margin-top:9px">pushed &mdash; {push} cells,
        changes landing early</h2>
      <div class="sc"><table>{drows(pu, 9)}</table></div>
      <p class="note"><b>A push is the even grid with the first chord clipped
        and the last one stretched.</b> More Than a Feeling and Teen Spirit
        are the same device in opposite phase &mdash; 1.5&ndash;2.5 against
        2.5&ndash;1.5.</p>
    </div>
  </div>
</div></body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{len(lpat)} shapes, {len(dpat)} rhythms -> {a.out}')


if __name__ == '__main__':
    main()
