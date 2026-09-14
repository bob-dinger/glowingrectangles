#!/usr/bin/env python3
"""
The six white-note chords, grouped three ways. Printable.

C Dm Em F G Am is not a list of six things to memorise. It is three majors
and three minors, and those pair off as relatives sharing two notes each —
so it is really three pairs. Sounds come from pao_options so the sheet cannot
drift from the code.

    python3 build_six_sheet.py
"""
import argparse, html, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_options as po

MAJ = [('C','I','C E G'), ('F','IV','F A C'), ('G','V','G B D')]
# the other way to cut the six: by what a chord DOES, not what it is built
# from. Home / away / tension is the grammar every progression is written in.
FUNC = [('home',   'rest, arrival, the chord you can stop on',
         [('C','I','C E G','maj'), ('Am','vi','A C E','min'), ('Em','iii','E G B','min')]),
        ('away',   'departure, the middle of the phrase',
         [('F','IV','F A C','maj'), ('Dm','ii','D F A','min')]),
        ('tension','wants to resolve, almost always back to C',
         [('G','V','G B D','maj')])]
MIN = [('Am','vi','A C E'), ('Dm','ii','D F A'), ('Em','iii','E G B')]
PAIRS = [('C','Am','C and E'), ('F','Dm','F and A'), ('G','Em','G and B')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/the-six.html'))
    a = ap.parse_args()
    def esc(s): return html.escape(str(s))

    def card(ch, rn, notes, cls):
        return (f'<div class="c {cls}"><div class="ch">{esc(ch)}</div>'
                f'<div class="rn">{esc(rn)}</div>'
                f'<div class="nt">{esc(notes)}</div>'
                f'<div class="sd">{esc(po.SOUNDS[ch])}</div></div>')

    majrow = ''.join(card(c,r,n,'maj') for c,r,n in MAJ)
    minrow = ''.join(card(c,r,n,'min') for c,r,n in MIN)
    funcs = ''.join(
        f'<div class="fn"><div class="fh"><b>{esc(nm)}</b><span>{esc(desc)}</span></div>'
        + '<div class="row">' + ''.join(card(c,r,n,cl) for c,r,n,cl in members)
        + '</div></div>' for nm, desc, members in FUNC)

    pairs = ''.join(
        f'<div class="pair">'
        + card(a_, dict((x[0],x[1]) for x in MAJ)[a_], dict((x[0],x[2]) for x in MAJ)[a_], 'maj')
        + f'<div class="lnk"><span>shares</span><b>{esc(sh)}</b></div>'
        + card(b_, dict((x[0],x[1]) for x in MIN)[b_], dict((x[0],x[2]) for x in MIN)[b_], 'min')
        + '</div>' for a_, b_, sh in PAIRS)

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>The six</title><style>
@page{{margin:.55in}}*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Georgia,'Iowan Old Style',serif;color:#111;background:#fff;
max-width:7.3in;margin:0 auto;padding:.4in .25in .6in;font-size:10pt}}
h1{{font-size:22pt;margin-bottom:2px;letter-spacing:-.01em}}
.sub{{font-family:-apple-system,sans-serif;font-size:9pt;color:#666;margin-bottom:18px}}
h2{{font-family:-apple-system,sans-serif;font-size:8.5pt;letter-spacing:.1em;
text-transform:uppercase;color:#fff;background:#111;padding:3px 8px;
margin:20px 0 12px;page-break-after:avoid}}
.row{{display:flex;gap:12px;margin-bottom:4px}}
.c{{flex:1;border:1.5px solid #ddd;border-radius:8px;padding:10px 12px;
text-align:center;page-break-inside:avoid}}
.c.maj{{background:#fdf9ee;border-color:#e6d9b4}}
.c.min{{background:#f3f6fa;border-color:#c9d6e4}}
.ch{{font-size:23pt;font-weight:bold;line-height:1}}
.rn{{font-family:-apple-system,sans-serif;font-size:9pt;color:#8a8a8a;margin-top:1px}}
.nt{{font-family:ui-monospace,Menlo,monospace;font-size:9pt;color:#555;margin-top:5px}}
.sd{{font-family:ui-monospace,Menlo,monospace;font-size:8.5pt;color:#999;margin-top:3px}}
.lbl{{font-family:-apple-system,sans-serif;font-size:8pt;color:#999;
text-transform:uppercase;letter-spacing:.08em;margin:10px 0 4px}}
.pair{{display:flex;align-items:center;gap:10px;margin-bottom:9px}}
.pair .c{{flex:1}}
.lnk{{flex:0 0 78px;text-align:center;font-family:-apple-system,sans-serif}}
.lnk span{{display:block;font-size:7pt;color:#aaa;text-transform:uppercase;
letter-spacing:.08em}}
.lnk b{{font-family:ui-monospace,Menlo,monospace;font-size:11pt;color:#333}}
.fn{{margin-bottom:11px;page-break-inside:avoid}}
.fh{{display:flex;align-items:baseline;gap:9px;margin-bottom:5px}}
.fh b{{font-family:-apple-system,sans-serif;font-size:10pt;text-transform:uppercase;
letter-spacing:.07em}}
.fh span{{font-family:-apple-system,sans-serif;font-size:8.5pt;color:#999}}
.fn .row{{gap:12px}}
.rule{{background:#f7f5f0;border:1px solid #e4e0d5;padding:10px 13px;margin:12px 0;
font-size:9.5pt;line-height:1.55}}
footer{{margin-top:18px;padding-top:8px;border-top:1px solid #ccc;
font-family:-apple-system,sans-serif;font-size:7.5pt;color:#999}}
</style></head><body>

<h1>The six</h1>
<p class="sub">Everything on the white notes. Not six things to learn &mdash;
three, twice over.</p>

<h2>Six</h2>
<div class="row">{majrow}</div>
<div class="row">{minrow}</div>

<h2>Three and three</h2>
<div class="lbl">the majors &mdash; I, IV, V</div>
<div class="row">{majrow}</div>
<div class="lbl">the minors &mdash; vi, ii, iii</div>
<div class="row">{minrow}</div>
<div class="rule">
Every major has a minor a third below it holding two of its three notes.
That is why swapping one for the other barely changes the sound &mdash; and
why so many progressions are the same shape with one chord flipped.
</div>

<h2>Three groups &mdash; by what they do</h2>
{funcs}
<div class="rule">
<b>Home &rarr; away &rarr; tension &rarr; home.</b> Nearly every progression
you know is a walk through those three. C&ndash;F&ndash;G&ndash;C is one of
each. C&ndash;G&ndash;Am&ndash;F is home, tension, home, away &mdash; and the
reason it never quite settles is that it ends on <i>away</i>.
</div>

<h2>Three pairs</h2>
{pairs}
<div class="rule">
<b>C&ndash;Am, F&ndash;Dm, G&ndash;Em.</b> Learn three pairs and you have all
six. The axis progression (C&ndash;G&ndash;Am&ndash;F) is just both halves of
two of these pairs.
</div>

<footer>Sounds generated from pao_options.py &mdash; re-run build_six_sheet.py
if the map changes.</footer>
</body></html>"""
    open(a.out, 'w').write(doc)
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
