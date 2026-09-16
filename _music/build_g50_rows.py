#!/usr/bin/env python3
"""
One row per section: song, part, and the whole thing in bars. Printable.

No boxes, no chips — the chord is coloured text, coloured by its scale degree
in the song's key, so red is always the I whatever key you are in. Bars are
grouped by phrase length with | between groups, which is why John Deere
Green's sixteen-bar verse reads as four fours rather than sixteen things.

    python3 build_g50_rows.py
    python3 build_g50_rows.py --pools G50,G100 --out ~/Desktop/g100-rows.html
"""
import argparse, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import chord_key as ck
import pao_pools as pp

HERE = os.path.dirname(os.path.abspath(__file__))
DEG_HEX = {1:'#d02828', 2:'#d07800', 3:'#9a8c00', 4:'#1f8a4c',
           5:'#1663c7', 6:'#8038c0', 7:'#c02080'}   # darkened for print on white
NORM_DEG = {'C':1, 'Dm':2, 'Em':3, 'F':4, 'G':5, 'Am':6, 'A#':7, 'D':2, 'E':3}
# An applied dominant is stored as `@<semitone above tonic>`, which misses
# NORM_DEG entirely and printed grey. V/I is spelled `@7` and sounds exactly
# like the V chord, so Found Out About You had one chorus in colour and two in
# grey — the same eight bars. Colour by PITCH CLASS, which is the convention
# used everywhere else in the project: V/V lands on the ii colour, not V's.
PITCH_DEG = {0:1, 2:2, 4:3, 5:4, 7:5, 9:6, 11:7}


def deg_of(tok):
    t = tok.split('~')[0]
    if t.startswith('@'):
        try: return PITCH_DEG.get(int(t[1:]) % 12)
        except ValueError: return None
    return NORM_DEG.get(t)
# Skip only what is genuinely noise. The first version dropped intros,
# outros, solos and RIFFS, which is exactly backwards — a riff is the part you
# most want on a practice sheet. Shake Me Down's riff1 vanished because of it.
SKIP = {'section', 'pickup', 'half-intro'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/g50-rows.html'))
    ap.add_argument('--all-sections', action='store_true')
    ap.add_argument('--keep-outros', action='store_true')
    ap.add_argument('--no-merge', action='store_true',
                    help='keep sections separate even when the bars match')
    ap.add_argument('--cols', type=int, default=2)
    a = ap.parse_args()
    pm = json.load(open(pp.POOLS)); idx = pp.build_index()
    def esc(s): return html.escape(str(s))

    rows, done = [], set()
    for slug in sorted(s for s, p in pm.items() if p in set(a.pools.split(','))):
        path = pp.find(slug, idx)
        if not path or path in done: continue
        done.add(path)
        try: tonic, scale, _, secs = B.bars_for(path, with_beats=True,
                                                with_quality=True)
        except Exception: continue
        keys = (json.load(open(path)).get('keys') or [])
        allb = sorted(x.get('beat', 1) for x in
                      (json.load(open(path)).get('sections') or []))
        art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')
        # str.title() capitalises after an apostrophe, giving "Won'T Back Down"
        title = re.sub(r"[A-Za-z']+",
                       lambda m: m.group(0)[0].upper() + m.group(0)[1:],
                       ttl.replace('-', ' ').lower())
        # Merge on the BARS, not the name. Most songs list a section three or
        # four times, and plenty have two parts with identical chords — the
        # chorus of Louisiana Saturday Night is its verse, Teen Spirit's intro
        # is its chorus. Showing those once and naming both is shorter AND
        # more informative than printing them twice.
        groups = {}
        for name, bb, beat in secs:
            nm = str(name).strip()
            if not a.all_sections and nm.lower() in SKIP: continue
            if not a.keep_outros and 'outro' in nm.lower(): continue
            key = (nm.lower(), tuple(bb)) if a.no_merge else tuple(bb)
            if key in groups:
                if nm not in groups[key][0]: groups[key][0].append(nm)
                continue
            groups[key] = ([nm], bb, beat)
        for names, bb, beat in groups.values():
            nm = ' = '.join(names)
            # the key in effect where THIS section starts, by its own beat
            stonic, sscale = ck.key_at(keys, beat) if keys else (tonic, scale)
            nxt = next((b for b in allb if b > beat), 10**9)
            mods = ck.changes_within(keys, beat, nxt)
            fs = B.forms(bb) or []
            # read from the top, not from the best offset — this is a sheet
            # you play from, so playing order beats shape-finding
            f = next((x for x in fs if x['off'] == 0), fs[0] if fs else None)
            n = f['n'] if f else 4
            # THE PIPE MARKS THE MEASURE whenever a measure holds more than
            # one chord — "G Am | D | G Am | D" tells you where the bar lines
            # are, which is the thing you need when playing. Only when every
            # bar holds a single chord does piping each one become noise
            # ("G | G | C | G |" x16), and then the phrase reading groups them.
            #
            # This replaced four rounds of trying to pick a phrase length by
            # repetition, primes and density. Each attempt fixed one song and
            # broke another; the measure is simply what the reader wants.
            if any(len(b) > 1 for b in bb):
                n = 1
            else:
                cand = [x for x in fs if x['off'] == 0 and B.sayable(x)
                        and 1 < x['n'] <= 4]
                if cand:
                    cand.sort(key=lambda x: (any("'" in l for l in x['labs']),
                                             round(x['ratio'], 3), -x['n']))
                    n = cand[0]['n']
            # A chord that lasts two bars only appears in the bar it STARTS,
            # so the next bar came out empty and printed as a dash: Somewhere
            # Only We Know read "A – Amaj7 –" when it is A | A | Amaj7 | Amaj7.
            # Carry the sounding chord into its continuation bars.
            filled, last = [], None
            for bar in bb:
                real = tuple(c for c in bar if c not in ('·', '?'))
                if real: last = real[-1]; filled.append(real)
                else: filled.append((last,) if last else ())
            bb = filled

            # Print the SHORTEST repeating unit and a multiplier. Halving
            # twice only caught x2 and x4, so Blue On Black's verse spelled
            # "G | F C" eight times over and had to wrap; it is one two-bar
            # cell played eight times, which is both shorter to print and
            # what the section actually is. This is the same reading as
            # "C-C-F-C. C-C-F-C. that's not 8 chords" — the repeat is the
            # structure, not extra content.
            times = 1
            for p in range(1, len(bb) // 2 + 1):
                if len(bb) % p: continue
                if all(bb[i:i+p] == bb[:p] for i in range(p, len(bb), p)):
                    times = len(bb) // p; bb = bb[:p]; break

            marks = []
            for i, bar in enumerate(bb):
                cell = ' '.join(
                    f'<b style="color:{DEG_HEX.get(deg_of(c), "#888")}">'
                    f'{esc(ck.actual(stonic, sscale, c))}</b>'
                    for c in bar if c not in ('·', '?')) or '<i>&ndash;</i>'
                marks.append(cell)
            # Bars need their own separation or the structure is lost: with
            # chords space-joined inside a bar AND bars space-joined, "C D | Em"
            # and "C | D | Em" both render as "C D Em". Each bar gets its own
            # span with a wider gap, so two chords in one bar sit tight
            # together and the next bar is visibly apart. | still marks the
            # phrase.
            cells = [f'<s>{m}</s>' for m in marks]
            cell = ' <u>|</u> '.join(
                ''.join(cells[i:i+n]) for i in range(0, len(cells), n))
            grouped = cell + (f' <o>&times;{times}</o>' if times > 1 else '')
            # Estimate the rendered width and tighten progressively. About a
            # third of rows overflowed the column and truncated with an
            # ellipsis, which loses the end of the progression — the part you
            # are least likely to remember. Roughly 55 characters fit at 9pt.
            plain = sum(len(' '.join(
                c.split('~')[0] if '~' not in c else
                ck.actual(stonic, sscale, c) for c in bar if c not in ('·','?'))
                or '-') for bar in bb) + len(bb) + (len(bb)//max(n,1))*2
            tight = ('' if plain <= 55 else 't1' if plain <= 72
                     else 't2' if plain <= 92 else 't3')
            rows.append(dict(sort=(title.lower(), len(rows)),
                             song=title, part=nm, key=stonic, tight=tight,
                             minor=(sscale != 'major'), nbars=len(bb) * times,
                             chords=grouped, cell=cell, times=times,
                             moved=(stonic, sscale) != (tonic, scale),
                             mods=mods))

    # A SECOND merge, on the rendered row. The first groups on the raw bars,
    # but the hold-fill and the x2 collapse both run after it, so two sections
    # whose bars differ only in how a held chord was entered still came out
    # identical — Found Out About You printed its chorus twice, the same eight
    # bars both times. Anything that reads the same is one row.
    if not a.no_merge:
        merged = {}
        for r in rows:
            # Merge on the CELL, ignoring how many times it repeats. If It
            # Makes You Happy listed three verses and two instrumental
            # bridges that are all the same droning Dsus4 at different
            # lengths, and Island In The Sun had three rows of Em Am D | G.
            # One row naming every part that plays it is the same reading as
            # "C-C-F-C. C-C-F-C. that's not 8 chords".
            k = (r['song'], r['key'], r['minor'], r['cell'])
            if k in merged:
                m = merged[k]
                have = m['part'].split(' = ')
                for nm in r['part'].split(' = '):
                    if nm not in have:
                        m['part'] += ' = ' + nm; have.append(nm)
                # keep the longest instance, so the bar count is the real one
                if r['nbars'] > m['nbars']:
                    m['nbars'], m['times'], m['chords'] = (
                        r['nbars'], r['times'], r['chords'])
                continue
            merged[k] = r
        rows = list(merged.values())

    # alphabetical by SONG, not by slug — the slug leads with the artist, so
    # Louisiana Saturday Night was filed under Alabama. Sections keep their
    # order within a song.
    rows.sort(key=lambda r: r['sort'])
    body = ''.join(
        f'<div class="r"><span class="s">{esc(r["song"])}</span>'
        f'<span class="p">{"<b>" if " = " in r["part"] else ""}'
        f'{esc(r["part"])}{"</b>" if " = " in r["part"] else ""}</span>'
        f'<span class="k{" mv" if r["moved"] else ""}">{esc(r["key"])}'
        f'{"m" if r["minor"] else ""}'
        f'{"*" if r["mods"] else ""}<em>{r["nbars"]}</em></span>'
        f'<span class="c {r["tight"]}">{r["chords"]}</span></div>' for r in rows)

    legend = ' &nbsp; '.join(
        f'<b style="color:{DEG_HEX[d]}">{r}</b>'
        for d, r in ((1,'I'),(2,'ii'),(3,'iii'),(4,'IV'),(5,'V'),(6,'vi'),(7,'bVII')))

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{esc(a.pools)} — every part</title><style>
  @page{{margin:.35in;size:letter landscape}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#111;
    background:#fff;padding:.1in .2in;font-size:8pt}}
  header{{display:flex;align-items:baseline;gap:14px;border-bottom:1.2px solid #111;
    padding-bottom:3px;margin-bottom:4px}}
  h1{{font-size:13pt;font-weight:700}}
  header .n{{font-size:8pt;color:#888}}
  header .leg{{margin-left:auto;font-size:9pt;font-weight:700}}
  .grid{{columns:{a.cols};column-gap:20px;column-rule:1px solid #eee}}
  /* tightened from 1.62 / .5px: spilling one row onto a third sheet is a
     worse outcome than slightly closer leading, and this buys about nine
     rows of headroom rather than exactly the one needed */
  .r{{break-inside:avoid;display:flex;align-items:baseline;gap:5px;
    line-height:1.36;border-bottom:1px solid #f4f4f4;padding:0}}

  /* The title and part columns get the same treatment as the chords: shrink
     to fit, never truncate. Letting them WRAP instead was worse than the
     ellipsis ever was — a song like "Dont Look Back In Anger" took two lines
     on every one of its rows, and that, not the chords, is what cost a sheet
     of paper. */
  .s{{width:116px;flex:0 0 116px;font-weight:700;font-size:7.6pt;
    white-space:nowrap;overflow:visible;min-width:0}}
  .s.f1{{font-size:7pt}}
  .s.f2{{font-size:6.5pt;letter-spacing:-.01em}}
  .s.f3{{font-size:6pt;letter-spacing:-.02em}}
  .s.f4{{font-size:5.5pt;letter-spacing:-.03em}}
  .s.wrap{{white-space:normal;line-height:1.15}}
  .p{{width:70px;flex:0 0 70px;font-size:6.6pt;color:#999;text-transform:uppercase;
    letter-spacing:.01em;white-space:nowrap;overflow:visible;min-width:0}}
  .p.f1{{font-size:6.1pt;letter-spacing:0}}
  .p.f2{{font-size:5.7pt;letter-spacing:-.01em}}
  .p.f3{{font-size:5.3pt;letter-spacing:-.02em}}
  .p.f4{{font-size:5pt;letter-spacing:-.03em}}
  .p.wrap{{white-space:normal;line-height:1.15}}
  .p b{{color:#c02080;font-weight:600}}   /* two parts, same chords */
  .k{{width:34px;flex:0 0 34px;font-size:7pt;color:#555;font-weight:600}}
  .k.mv{{color:#c02080}}   /* this section is in a different key to the song */
  .k em{{font-style:normal;color:#bbb;font-weight:400;margin-left:2px}}
  /* NO ELLIPSIS, anywhere. Shrinking the type is worth doing — a row that
     fits one line is easier to read than the same row over two — but a
     truncated row loses the end of the progression, which is the part you are
     least likely to remember. So the tiers only tighten; when even the
     tightest will not fit, the row wraps. */
  /* min-width:0 is load-bearing. A flex item defaults to min-width:auto, so
     .c refuses to shrink below its content and overflows the ROW instead of
     wrapping inside its own box — which also makes every width measurement
     read as "fits". The old ellipsis masked this: overflow:hidden happens to
     resolve min-width to 0. */
  .c{{flex:1 1 auto;min-width:0;font-size:9pt;letter-spacing:-.01em;
    white-space:normal;overflow:visible;line-height:1.3}}
  .c.t1{{font-size:8.2pt;letter-spacing:-.02em}}
  .c.t1 s{{margin-right:4.5px}} .c.t1 b{{margin-right:1px}}
  .c.t2{{font-size:7.4pt;letter-spacing:-.025em}}
  .c.t2 s{{margin-right:3.5px}} .c.t2 b{{margin-right:.5px}}
  .c.t2 u{{margin:0}}
  .c.t3{{font-size:7.2pt;letter-spacing:-.025em}}
  .c.t3 s{{margin-right:3px}} .c.t3 b{{margin-right:.5px}} .c.t3 u{{margin:0}}
  .c.t4{{font-size:6.6pt;letter-spacing:-.03em}}
  .c.t4 s{{margin-right:2.5px}} .c.t4 b{{margin-right:.5px}} .c.t4 u{{margin:0}}
  /* used only by the fit pass below, never in the printed output */
  .c.wrap{{white-space:normal}}
  .probe{{white-space:nowrap!important}}
  .c b{{font-weight:700;margin-right:2px}}
  /* a bar is the unit, so it stays whole: the line breaks BETWEEN bars, never
     between two chords that share one */
  .c s{{text-decoration:none;margin-right:7px;
    display:inline-block;white-space:nowrap}}      /* one bar */
  .c s b:last-child{{margin-right:0}}
  .c u{{text-decoration:none;color:#ccc;font-weight:400;margin:0 1px}}
  .c o{{font-size:7.5pt;color:#888;font-weight:700;margin-left:3px}}
  .c i{{font-style:normal;color:#ddd}}
  @media print{{body{{padding:0}}}}
</style></head><body>
<header><h1>{esc(a.pools)}</h1>
  <span class="n">{len({r['song'] for r in rows})} songs &middot; {len(rows)} parts
    &middot; chords as played &middot; | marks the phrase &middot;
    <b style="color:#c02080">pink key</b> = section modulates,
    * = key changes mid-section</span>
  <span class="leg">{legend}</span></header>
<div class="grid">{body}</div>
<script>
/* Pick each row's size by MEASURING it, not by estimating from a character
   count. The estimate had to be conservative, so a dozen rows wrapped that
   would have fitted a size down — and wrapping is what pushed the G50 sheet
   onto a third sheet of paper. Walk the tiers, take the first that fits on
   one line, and only wrap when even the smallest will not. Runs before print,
   so printing straight from the browser gets the same result. */
(function () {{
  var TIERS = ['', 't1', 't2', 't3', 't4'];
  function shrink(base, tiers, sel) {{
    document.querySelectorAll(sel).forEach(function (el) {{
      var fit = null;
      for (var i = 0; i < tiers.length; i++) {{
        el.className = base + ' probe' + (tiers[i] ? ' ' + tiers[i] : '');
        if (el.scrollWidth <= el.clientWidth + 0.5) {{ fit = tiers[i]; break; }}
      }}
      // nothing fits at any size: smallest, and wrap rather than truncate
      el.className = base + (fit === null
        ? ' ' + tiers[tiers.length - 1] + ' wrap'
        : (fit ? ' ' + fit : ''));
    }});
  }}
  shrink('c', TIERS, '.c');
  shrink('s', ['', 'f1', 'f2', 'f3', 'f4'], '.s');
  shrink('p', ['', 'f1', 'f2', 'f3', 'f4'], '.p');
}})();
</script>
</body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{len({r["song"] for r in rows})} songs, {len(rows)} rows -> {a.out}')


if __name__ == '__main__':
    main()
