#!/usr/bin/env python3
"""
Every progression in a guitar pool on one or two printable sheets.

The point is to stop switching between fifty browser tabs. One line per
section: the chords you actually play, grouped into phrases with | between
them, coloured by scale degree so the normalised C-major version is not
needed on the page.

    python3 build_g50_sheet.py                  # G50
    python3 build_g50_sheet.py --pools G50,G100 --out ~/Desktop/g100.html
"""
import argparse, html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import chord_key as ck
import pao_pools as pp

HERE = os.path.dirname(os.path.abspath(__file__))
# chord_viz.py's palette, so this page and the visualisers agree
DEG_HEX = {1:'#e84545', 2:'#f0a040', 3:'#e8c828', 4:'#50c878',
           5:'#5090f0', 6:'#b870f0', 7:'#e070b0'}
NORM_DEG = {'C':1, 'Dm':2, 'Em':3, 'F':4, 'G':5, 'Am':6, 'A#':7, 'D':2, 'E':3}
SKIP = {'intro', 'outro', 'section', 'pickup', 'interlude', 'solo', 'riff1', 'riff'}


def phrases(bb, f):
    """-> [[chord,...], ...] one list per distinct phrase, in form order"""
    out, seen = [], {}
    for lab, ch in zip(f['labs'], f['chunks']):
        base = lab.rstrip("'")
        core, reps, tail = B.phrase_chords(ch)
        seq = core + tail
        if not seq: continue
        key = tuple(seq)
        if key in seen: continue
        seen[key] = 1
        out.append(seq)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/g50-sheet.html'))
    ap.add_argument('--all-sections', action='store_true',
                    help='include intros, outros and solos too')
    a = ap.parse_args()
    want = set(a.pools.split(','))
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    def esc(s): return html.escape(str(s))

    songs, done = [], set()
    for slug in sorted(s for s, p in pm.items() if p in want):
        path = pp.find(slug, idx)
        if not path or path in done: continue    # two slugs can hit one file
        done.add(path)
        try: tonic, scale, _, secs = B.bars_for(path)
        except Exception: continue
        art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')
        rows, seen = [], set()
        for name, bb in secs:
            nm = str(name).strip()
            if not a.all_sections and nm.lower() in SKIP: continue
            # Read from the top of the section, not from the best offset.
            # forms() searches the phase to find repeating cells, which is
            # right for counting shapes but wrong here: it can enter a phrase
            # mid-way, so Wonderwall's verse came out "D Am | Em G" instead of
            # "Em G | D Am". On a sheet you play from, playing order wins.
            fs = B.forms(bb) or []
            f = next((x for x in fs if x['off'] == 0), fs[0] if fs else None)
            if not f: continue
            ph = phrases(bb, f)
            if not ph: continue
            sig = (nm.lower(), tuple(tuple(p) for p in ph))
            if sig in seen: continue
            seen.add(sig)
            rows.append((nm, ph))
        if rows:
            songs.append(dict(title=ttl.replace('-', ' ').title(),
                              artist=art.replace('-', ' ').title(),
                              key=tonic, scale=scale, rows=rows))

    def chip(norm, tonic, scale):
        d = NORM_DEG.get(norm)
        nm = ck.actual(tonic, scale, norm)
        col = DEG_HEX.get(d, '#9a9a9a')
        return f'<b style="background:{col}">{esc(nm)}</b>'

    cards = []
    for s in songs:
        lines = ''
        for nm, ph in s['rows']:
            groups = ' <u>|</u> '.join(
                ' '.join(chip(c, s['key'], s['scale']) for c in p) for p in ph)
            lines += (f'<div class="sec"><i>{esc(nm)}</i>'
                      f'<span>{groups}</span></div>')
        cards.append(f'<div class="song"><h3>{esc(s["title"])}'
                     f'<em>{esc(s["artist"])}</em>'
                     f'<u>{esc(s["key"])}{"m" if s["scale"]!="major" else ""}</u></h3>'
                     f'{lines}</div>')

    legend = ''.join(
        f'<span><b style="background:{DEG_HEX[d]}">{r}</b></span>'
        for d, r in ((1,'I'),(2,'ii'),(3,'iii'),(4,'IV'),(5,'V'),(6,'vi'),(7,'bVII')))

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{esc(a.pools)} on a sheet</title><style>
  @page{{margin:.4in;size:letter portrait}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:9pt;
    color:#111;background:#fff;padding:.3in .25in}}
  header{{display:flex;align-items:baseline;gap:12px;border-bottom:1.5px solid #111;
    padding-bottom:5px;margin-bottom:8px}}
  h1{{font-size:14pt;font-weight:700;letter-spacing:-.01em}}
  header .n{{font-size:8.5pt;color:#888}}
  .leg{{margin-left:auto;display:flex;gap:3px;align-items:center}}
  .leg span b{{display:inline-block;padding:1px 4px;border-radius:3px;color:#fff;
    font-size:7pt;font-weight:700}}
  .grid{{columns:2;column-gap:16px}}
  .song{{break-inside:avoid;margin-bottom:6px;padding-bottom:4px;
    border-bottom:1px solid #eee}}
  .song h3{{font-size:9.5pt;font-weight:700;display:flex;align-items:baseline;
    gap:5px;margin-bottom:1px}}
  .song h3 em{{font-style:normal;font-weight:400;font-size:7.5pt;color:#999}}
  .song h3 u{{text-decoration:none;margin-left:auto;font-size:7.5pt;color:#555;
    font-weight:600}}
  .sec{{display:flex;gap:5px;align-items:baseline;line-height:1.5}}
  .sec i{{font-style:normal;font-size:6.8pt;text-transform:uppercase;
    letter-spacing:.04em;color:#999;width:52px;flex:0 0 52px;text-align:right;
    padding-top:1px}}
  .sec span b{{display:inline-block;min-width:18px;padding:0 3px;margin-right:3px;
    border-radius:3px;color:#fff;font-weight:700;font-size:8pt;text-align:center}}
  .sec span u{{text-decoration:none;color:#bbb;margin:0 3px 0 1px;font-weight:700}}
  @media print{{body{{padding:0}}}}
</style></head><body>
<header><h1>{esc(a.pools)}</h1>
  <span class="n">{len(songs)} songs &middot; {sum(len(s['rows']) for s in songs)} parts
    &middot; chords as played, coloured by degree</span>
  <span class="leg">{legend}</span></header>
<div class="grid">{''.join(cards)}</div>
</body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{len(songs)} songs, {sum(len(s["rows"]) for s in songs)} parts -> {a.out}')


if __name__ == '__main__':
    main()
