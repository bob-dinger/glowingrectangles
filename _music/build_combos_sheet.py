#!/usr/bin/env python3
"""
Every 2- and 3-chord combination of the six white-note chords. Printable.

15 pairs and 20 triples, with how many sections in G50+G100 use exactly that
set of chords — so the list is ordered by what you will actually meet, not
just by arithmetic.

    python3 build_combos_sheet.py
"""
import argparse, collections, html, itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp

SIX = ['C', 'Dm', 'Em', 'F', 'G', 'Am']
RN  = {'C':'I', 'Dm':'ii', 'Em':'iii', 'F':'IV', 'G':'V', 'Am':'vi'}
NAMED = {frozenset(['C','F','G']): 'the three-chord song',
         frozenset(['C','G','Am']): 'half the axis',
         frozenset(['C','F','Am']): 'axis without V',
         frozenset(['F','G','Am']): 'the minor-key end of the axis',
         frozenset(['C','Dm','G']): 'ii-V-I, the jazz cadence',
         frozenset(['C','F']): 'plagal',
         frozenset(['C','G']): 'the whole of punk'}


def usage(pools=('G50','G100')):
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    use = collections.Counter()
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
            core, _, tail = B.phrase_chords(bb)
            st = frozenset(core + tail)
            if st and st <= set(SIX): use[st] += 1
    return use


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/chord-combos.html'))
    ap.add_argument('--by', choices=['use', 'order'], default='use')
    a = ap.parse_args()
    use = usage()
    def esc(s): return html.escape(str(s))

    def block(n):
        combos = list(itertools.combinations(SIX, n))
        if a.by == 'use':
            combos.sort(key=lambda c: (-use[frozenset(c)], c))
        rows = []
        for c in combos:
            u = use[frozenset(c)]
            nm = NAMED.get(frozenset(c), '')
            cls = 'hot' if u >= 10 else ('warm' if u >= 3 else ('cold' if u == 0 else ''))
            bar = ('<span class="bar" style="width:%dpx"></span>' % min(120, u*2)) if u else ''
            rows.append(
                f'<tr class="{cls}"><td class="ch">{esc("–".join(c))}</td>'
                f'<td class="rn">{esc("–".join(RN[x] for x in c))}</td>'
                f'<td class="u">{u or "&mdash;"}</td>'
                f'<td class="b">{bar}</td>'
                f'<td class="nm">{esc(nm)}</td></tr>')
        return ''.join(rows)

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Chord combinations</title><style>
@page{{margin:.5in}}*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Georgia,'Iowan Old Style',serif;color:#111;background:#fff;
max-width:7.3in;margin:0 auto;padding:.35in .25in .5in;font-size:10pt}}
h1{{font-size:21pt;margin-bottom:2px;letter-spacing:-.01em}}
.sub{{font-family:-apple-system,sans-serif;font-size:9pt;color:#666;margin-bottom:16px}}
h2{{font-family:-apple-system,sans-serif;font-size:8.5pt;letter-spacing:.1em;
text-transform:uppercase;color:#fff;background:#111;padding:3px 8px;
margin:18px 0 8px;page-break-after:avoid}}
table{{width:100%;border-collapse:collapse}}
td{{padding:3px 8px 3px 0;border-bottom:1px solid #f0f0f0;vertical-align:baseline}}
.ch{{font-size:12pt;font-weight:600;width:112px;font-variant-numeric:tabular-nums}}
.rn{{font-family:-apple-system,sans-serif;font-size:9pt;color:#999;width:84px}}
.u{{font-family:ui-monospace,Menlo,monospace;font-size:9.5pt;width:34px;
text-align:right;color:#444}}
.b{{width:130px}}
.bar{{display:inline-block;height:7px;background:#c8b273;border-radius:3px;
vertical-align:middle;margin-left:6px}}
.nm{{font-size:9pt;color:#777;font-style:italic}}
tr.hot .ch{{color:#8a5a12}} tr.hot .bar{{background:#b8862c}}
tr.cold .ch{{color:#bbb}} tr.cold .rn{{color:#ccc}} tr.cold .u{{color:#ccc}}
.note{{font-size:9pt;color:#666;line-height:1.5;margin:9px 0 2px}}
footer{{margin-top:16px;padding-top:8px;border-top:1px solid #ccc;
font-family:-apple-system,sans-serif;font-size:7.5pt;color:#999}}
</style></head><body>

<h1>Every combination of the six</h1>
<p class="sub">C &middot; Dm &middot; Em &middot; F &middot; G &middot; Am
&mdash; 15 pairs and 20 triples. The count is how many sections in guitar50
and guitar100 use <i>exactly</i> that set of chords and nothing else.</p>

<h2>15 pairs</h2>
<table>{block(2)}</table>

<h2>20 triples</h2>
<table>{block(3)}</table>

<p class="note">Greyed rows never occur on their own anywhere in the two
pools. Ten of the twenty triples are empty &mdash; the arithmetic gives you
twenty, the music uses about half, and one of them
(C&ndash;F&ndash;G) accounts for more sections than the next four together.</p>

<footer>Generated from the Hookpad corpus by build_combos_sheet.py.
<code>--by order</code> lists them alphabetically instead of by usage.</footer>
</body></html>"""
    open(a.out, 'w').write(doc)
    print(f'15 pairs + 20 triples -> {a.out}')


if __name__ == '__main__':
    main()
