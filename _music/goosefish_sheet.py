"""A PRINTABLE sheet of the 24 orderings of C / F / G / Am, with song examples.

The text version of this was unreadable on paper -- the user: "this format is
absolutely terrible... you need to keep in mind printing margins, but also colors
and chord names, which are more human friendly."  So:

  - CHORD NAMES are the primary label (C, F, G, Am), big. Roman numerals are
    secondary, small, underneath.
  - Colour by PITCH CLASS of the root in C, full-opacity hex from
    music_chord_color_pitchclass: C red, F green, G blue, Am purple.
    `print-color-adjust: exact` or browsers drop the fills.
  - Real @page margins, and `break-inside: avoid` on every block so no ordering is
    ever split across a page boundary (the pool-sheet rule: fits the page, never
    truncates).
  - Examples are capped at 6 with an explicit "+N more", so nothing vanishes silently.

    themap_venv/python goosefish_sheet.py
"""
import os, sys, itertools, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goosefish_hunt import scan_opens, NAMED

OUT = os.path.expanduser('~/Desktop/goosefish_24.html')
CH = {'1': 'C', '4': 'F', '5': 'G', '6': 'Am'}
RN = {'1': 'I', '4': 'IV', '5': 'V', '6': 'vi'}
COL = {'1': '#E84545', '4': '#50C878', '5': '#5090F0', '6': '#7040B0'}  # pitch class
MAXEX = 6

def canon(f):
    d = f.split('-'); return min(''.join(d[i:]+d[:i]) for i in range(4))

def esc(s):
    return (str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))

def title(s):
    """turn `bryan adams_summer of 69` into `Bryan Adams - Summer Of 69`"""
    s = str(s)
    art, _, song = s.partition('_')
    nice = lambda x: ' '.join(w if w.isupper() else w.capitalize() for w in x.split())
    return f"{nice(art)} &ndash; {nice(song)}" if song else nice(s)

def main():
    found = scan_opens()
    orders = ['-'.join(p) for p in itertools.permutations('1456')]
    cls = collections.defaultdict(list)
    for o in orders: cls[canon(o)].append(o)
    used = sum(1 for o in orders if found.get(o))
    nsec = sum(len(v) for v in found.values())

    H = []
    H.append(f"""<!doctype html><meta charset="utf-8">
<title>24 orderings of C F G Am</title>
<style>
  @page {{ size: letter; margin: 14mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0 auto; max-width: 196mm; padding: 10mm 8mm;
         font: 10.5pt/1.35 "Helvetica Neue", Helvetica, Arial, sans-serif;
         color: #1a1a1a; background: #fff;
         -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  h1 {{ font-size: 16pt; margin: 0 0 2mm; letter-spacing: -.2pt; }}
  .lede {{ font-size: 9pt; color: #555; margin: 0 0 6mm; max-width: 150mm; }}
  .lede b {{ color: #1a1a1a; }}
  .cycle {{ break-inside: avoid; margin: 0 0 7mm; }}
  .chead {{ display: flex; align-items: baseline; gap: 4mm;
            border-bottom: 1.5pt solid #1a1a1a; padding-bottom: 1.2mm; margin-bottom: 2.5mm; }}
  .chead .map {{ font-size: 11.5pt; font-weight: 700; }}
  .chead .n {{ font-size: 8.5pt; color: #666; margin-left: auto; }}
  .row {{ display: flex; align-items: center; gap: 4mm; padding: 1.6mm 0;
          border-bottom: .4pt solid #e2e2e2; break-inside: avoid; }}
  .row:last-child {{ border-bottom: 0; }}
  .chips {{ display: flex; gap: 1.2mm; flex: 0 0 46mm; }}
  .chip {{ flex: 1; text-align: center; border-radius: 1.4mm; padding: 1.4mm .5mm 1mm;
           color: #fff; }}
  .chip b {{ display: block; font-size: 12pt; line-height: 1; letter-spacing: -.3pt; }}
  .chip i {{ display: block; font-size: 6.5pt; font-style: normal; opacity: .82;
             margin-top: .5mm; }}
  .meta {{ flex: 0 0 34mm; }}
  .meta .name {{ font-weight: 700; font-size: 9.5pt; }}
  .meta .un {{ color: #999; font-weight: 400; font-style: italic; }}
  .meta .cnt {{ font-size: 8pt; color: #666; }}
  .ex {{ flex: 1; font-size: 8.5pt; color: #333; }}
  .ex span {{ white-space: nowrap; }}
  .ex .sec {{ color: #777; }}
  .ex .more {{ color: #999; font-style: italic; }}
  .none {{ flex: 1; font-size: 9pt; color: #b00; font-weight: 600; }}
  .foot {{ margin-top: 6mm; font-size: 8pt; color: #666; border-top: .4pt solid #ccc;
           padding-top: 2mm; }}
  @media print {{ body {{ padding: 0; max-width: none; }} }}
</style>
<h1>The 24 orderings of C &middot; F &middot; G &middot; Am</h1>
<p class="lede">A section counts when its <b>first four chord changes</b> are these four
chords in this order &mdash; whatever it does next. Repeated chords collapsed;
verse / chorus / pre-chorus / bridge only; one song per variant.
<b>{used} of 24</b> orderings open at least one section, across <b>{nsec}</b> sections.
All 24 occur as chord <i>runs</i>, since a loop contains all four of its rotations at
once &mdash; what differs is where a section begins.</p>""")

    for k in sorted(cls, key=lambda k: -sum(len(found.get(o, [])) for o in cls[k])):
        tot = sum(len(found.get(o, [])) for o in cls[k])
        arrows = ' &rarr; '.join(RN[c] for c in k) + ' &rarr; ' + RN[k[0]]
        H.append(f'<div class="cycle"><div class="chead">'
                 f'<span class="map">{arrows}</span>'
                 f'<span class="n">{tot} sections</span></div>')
        for o in cls[k]:
            hits = sorted(found.get(o, []), key=lambda h: -h[3])
            chips = ''.join(
                f'<div class="chip" style="background:{COL[c]}">'
                f'<b>{CH[c]}</b><i>{RN[c]}</i></div>' for c in o.split('-'))
            nm = NAMED.get(o)
            label = (f'<div class="name">{esc(nm)}</div>' if nm
                     else '<div class="name un">unnamed</div>')
            if hits:
                ex = ' &nbsp;&middot;&nbsp; '.join(
                    f'<span>{title(n)} <span class="sec">{esc(s)}</span></span>'
                    for n, s, role, bars, full in hits[:MAXEX])
                if len(hits) > MAXEX:
                    ex += f' <span class="more">+{len(hits)-MAXEX} more</span>'
                body = f'<div class="ex">{ex}</div>'
            else:
                body = '<div class="none">no section in the library opens here</div>'
            H.append(f'<div class="row"><div class="chips">{chips}</div>'
                     f'<div class="meta">{label}'
                     f'<div class="cnt">{len(hits)} section{"" if len(hits)==1 else "s"}'
                     f'</div></div>{body}</div>')
        H.append('</div>')
    H.append('<p class="foot">Colour by pitch class of the root in C: '
             '<b style="color:#E84545">C&thinsp;=&thinsp;I</b>, '
             '<b style="color:#50C878">F&thinsp;=&thinsp;IV</b>, '
             '<b style="color:#5090F0">G&thinsp;=&thinsp;V</b>, '
             '<b style="color:#7040B0">Am&thinsp;=&thinsp;vi</b>. '
             'Generated by _music/goosefish_sheet.py</p>')
    open(OUT, 'w').write('\n'.join(H))
    print(f"  {used} of 24 orderings used, {nsec} sections, {len(cls)} cycles")
    print(f"  -> {OUT}")

if __name__ == '__main__':
    main()
