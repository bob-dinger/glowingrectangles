#!/usr/bin/env python3
"""
A printable reference for the chord-sound map, GENERATED from pao_options.py.

Two earlier hand-written printouts (chord-peg-system.html,
chord-pao-options.html) still show the superseded mapping with hard-g on C.
That is what happens when the sheet and the code are separate documents, so
this one reads the live tables and cannot drift.

    python3 build_pao_sheet.py
    python3 build_pao_sheet.py --words 10
"""
import argparse, html, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_options as po

ORDER = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'A#', 'D', 'E']
ROMAN = {'C': 'I', 'Dm': 'ii', 'Em': 'iii', 'F': 'IV', 'G': 'V', 'Am': 'vi',
         'A#': 'bVII', 'D': 'II', 'E': 'III'}
# rough share of all chords in the corpus, for deciding how much imagery a
# chord actually needs
WEIGHT = {'C': 'the most common chord in the corpus', 'G': 'very common',
          'F': 'very common', 'Am': 'common', 'Dm': 'common', 'Em': 'less common',
          'A#': 'occasional (bVII)', 'D': 'occasional (II)', 'E': 'rare (III)'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', type=int, default=9, help='examples per role')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/chord-sounds.html'))
    a = ap.parse_args()

    def esc(s): return html.escape(str(s))
    rows = []
    for ch in ORDER:
        w = po.W[ch]
        cells = ''.join(
            f'<tr><td class="role">{r}</td><td class="list">'
            + ' &middot; '.join(f'<b>{esc(x)}</b>' if i == 0 else esc(x)
                                for i, x in enumerate(w[r][:a.words]))
            + '</td></tr>' for r in po.ROLES)
        rows.append(f"""
  <div class="chord">
    <h3>{esc(ch)} <span class="rn">{esc(ROMAN[ch])}</span></h3>
    <span class="snd">{esc(po.SOUNDS[ch])}</span>
    <span class="wt">{esc(WEIGHT[ch])}</span>
    <table>{cells}</table>
  </div>""")

    quick = ''.join(
        f'<tr><td class="q1">{esc(ch)}</td><td class="q2">{esc(ROMAN[ch])}</td>'
        f'<td class="q3">{esc(po.SOUNDS[ch])}</td></tr>' for ch in ORDER)

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Chord sounds</title><style>
@page{{margin:.55in}}*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Georgia,'Iowan Old Style',serif;font-size:10pt;line-height:1.42;
color:#111;background:#fff;max-width:7.3in;margin:0 auto;padding:.35in .25in .6in}}
h1{{font-size:21pt;margin-bottom:2px;letter-spacing:-.01em}}
.sub{{font-family:-apple-system,sans-serif;font-size:9pt;color:#666;margin-bottom:14px}}
h2{{font-family:-apple-system,sans-serif;font-size:8.5pt;letter-spacing:.1em;
text-transform:uppercase;color:#fff;background:#111;padding:3px 8px;
margin:16px 0 10px;page-break-after:avoid}}
table.quick{{width:100%;border-collapse:collapse;margin-bottom:6px}}
table.quick td{{padding:4px 8px;border-bottom:1px solid #eee;vertical-align:baseline}}
.q1{{font-size:14pt;font-weight:bold;width:48px}}
.q2{{font-family:-apple-system,sans-serif;font-size:9pt;color:#888;width:52px}}
.q3{{font-family:ui-monospace,Menlo,monospace;font-size:10.5pt;color:#222}}
.chord{{margin-bottom:11px;page-break-inside:avoid;border-bottom:1px solid #eee;
padding-bottom:7px}}
.chord h3{{font-size:14pt;display:inline-block}}
.chord .rn{{font-family:-apple-system,sans-serif;font-size:8.5pt;color:#999;
font-weight:normal}}
.chord .snd{{font-family:ui-monospace,Menlo,monospace;font-size:9.5pt;color:#666;
margin-left:8px}}
.chord .wt{{font-family:-apple-system,sans-serif;font-size:7.5pt;color:#aaa;
float:right;margin-top:5px}}
.chord table{{width:100%;border-collapse:collapse;margin-top:3px}}
.chord td{{padding:2px 6px 2px 0;vertical-align:top}}
td.role{{font-family:-apple-system,sans-serif;font-size:7pt;text-transform:uppercase;
letter-spacing:.06em;color:#999;width:52px;padding-top:3px}}
td.list{{font-size:9.5pt}} td.list b{{font-weight:700}}
.note{{font-size:9pt;color:#555;line-height:1.5;margin:8px 0}}
.rule{{background:#f7f5f0;border:1px solid #e4e0d5;padding:9px 12px;margin:10px 0;
font-size:9pt;line-height:1.5}}
footer{{margin-top:16px;padding-top:8px;border-top:1px solid #ccc;
font-family:-apple-system,sans-serif;font-size:7.5pt;color:#999}}
</style></head><body>

<h1>Chord sounds</h1>
<p class="sub">Nine chords, four roles. Only the FIRST sound of a word has to
match &mdash; you are seeing a picture, not spelling a word.</p>

<h2>The map</h2>
<table class="quick">{quick}</table>

<div class="rule">
<b>Slot order is Person &rarr; Action &rarr; Object &rarr; Place.</b>
So F&ndash;C&ndash;G&ndash;Am is a <i>pharaoh kicking a gem in a swamp</i>.
A fifth chord starts a second sentence.<br><br>
<b>Every g is G</b>, hard or soft &mdash; gorilla, giant, gem, judge, shoe,
chain. C is the k-sound only. No exception to remember.<br><br>
<b>Repeats need no second word.</b> F&ndash;F&ndash;Am&ndash;C is
F&ndash;Am&ndash;C; you remember the rhythm separately.
</div>

<h2>Words to choose from</h2>
<p class="note">Bold is a suggestion, not a fixture. Pick words that suit the
song &mdash; a picture that fits both the chords and the subject cues twice
over, which is the whole point of not using a fixed grid.</p>
{''.join(rows)}

<footer>
Generated from pao_options.py &mdash; if the code changes, re-run
build_pao_sheet.py rather than editing this page.
Supersedes chord-peg-system.html and chord-pao-options.html, which still show
the old mapping with hard-g on C.
</footer>
</body></html>"""
    open(a.out, 'w').write(doc)
    print(f'9 chords, {a.words} words per role -> {a.out}')


if __name__ == '__main__':
    main()
