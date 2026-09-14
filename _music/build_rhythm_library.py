#!/usr/bin/env python3
"""
_music/rhythm-library.html — every four-measure rhythm shape in the corpus.

Chords and rhythm are separate axes: V-IV-iii-ii appears both as 2-2-2-2 and
as the pushed 1.5-2-2-2.5. This is the second axis on its own — how long each
chord lasts across four bars, ignoring which chords they are.

    python3 build_rhythm_library.py
"""
import argparse, collections, html, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_pools as pp
import chord_key as ck

HERE = os.path.dirname(os.path.abspath(__file__))
RN = {1:'I', 2:'ii', 3:'iii', 4:'IV', 5:'V', 6:'vi', 7:'bVII'}


def slugs_for(pools):
    """Pool names, plus two keywords: BEATLES pulls beatles_proj.json (141
    songs, none of which are in the guitar pools) and ALL takes every guitar
    pool. The guitar-50 corpus is one man's shortlist; the wider set is a
    better test of whether a rhythm shape is common or just common to it."""
    pm = json.load(open(pp.POOLS))
    out = set()
    if 'ALL' in pools:
        out |= set(pm)
    else:
        out |= {k for k, v in pm.items() if v in pools}
    if 'BEATLES' in pools or 'ALL' in pools:
        bp = os.path.join(HERE, 'beatles_proj.json')
        if os.path.exists(bp): out |= set(json.load(open(bp)))
    return sorted(out)


def collect(pools, collapse=False):
    idx = pp.build_index()
    pat = collections.Counter(); ex = collections.defaultdict(list)
    tot = 0
    for s in slugs_for(pools):
        path = pp.find(s, idx)
        if not path: continue
        d = json.load(open(path))
        m = (d.get('meters') or [{}])[0]
        if float(m.get('numBeats') or m.get('num') or 4) != 4: continue
        ch = sorted((c for c in (d.get('chords') or []) if not pp.is_rest(c)),
                    key=lambda c: c.get('beat', 0))
        if not ch: continue
        art, _, ttl = pp.strip_tags(os.path.splitext(os.path.basename(path))[0]).partition('_')
        song = ttl.replace('-', ' ').title()
        secs = (sorted((d.get('sections') or []), key=lambda x: x.get('beat', 0))
                or [{'beat': 1}])
        last = max(c['beat'] + c.get('duration', 0) for c in ch)
        for si, sec in enumerate(secs):
            lo = sec.get('beat', 1)
            hi = secs[si+1].get('beat', 10**9) if si+1 < len(secs) else 10**9
            end = min(hi, last)
            # WALK the section in four-bar windows. Taking only the first
            # window threw most of the corpus away: an 8-bar section holds two
            # phrases and a 16-bar section four. I Won't Back Down's verse
            # contains its shape twice and was counted once.
            w0 = lo
            while w0 + 16 <= end + 0.01:
                w = [c for c in ch if w0 <= c['beat'] < w0 + 16]
                w0 += 16
                if not w: continue
                if collapse:
                    col = []
                    for c in w:
                        r = c['root']
                        if col and col[-1][0] == r: col[-1][1] += c.get('duration', 0)
                        else: col.append([r, c.get('duration', 0)])
                else:
                    col = [[c['root'], c.get('duration', 0)] for c in w]
                durs = [round(x*2)/2 for _, x in col]
                if abs(sum(durs) - 16) > .01: continue
                tot += 1
                k = '-'.join(f'{x:g}' for x in durs)
                pat[k] += 1
                kk = (d.get('keys') or [{}])[0]
                tonic, scale = kk.get('tonic', 'C'), kk.get('scale', 'major')
                NINE = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'A#'}
                played = [ck.actual(tonic, scale, NINE.get(r, '?')) for r, _ in col]
                ex[k].append((song, sec.get('name', '?'),
                              '-'.join(RN.get(r, '?') for r, _ in col),
                              played, tonic))
    # Count DISTINCT song-sections, not every replay. A song whose chorus
    # comes round eight times contributed eight windows of the same shape,
    # which made Katy Perry's Birthday look like 41 instances when it is one
    # song and three parts. What you learn is the part, not the repeat.
    ded = collections.Counter()
    for k, rows in ex.items():
        ded[k] = len({(r[0], r[1]) for r in rows})
    return sum(ded.values()), ded, ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100,BEATLES')
    ap.add_argument('--out', default=os.path.join(HERE, 'rhythm-library.html'))
    a = ap.parse_args()
    tot, pat, ex = collect(set(a.pools.split(',')))
    def esc(s): return html.escape(str(s))

    ranked = pat.most_common()
    cum, need = 0, 0
    for i, (_, v) in enumerate(ranked, 1):
        cum += v
        if cum / tot >= .84 and not need: need = i

    def bar(k, played=None):
        durs = [float(x) for x in k.split('-')]
        segs, at = [], 0.0
        for i, d in enumerate(durs):
            off = ' off' if abs(at % 2) > .01 else ''
            # the chord goes INSIDE its block, so the shape and the harmony are
            # one object rather than a bar and a separate string to align by eye
            nm = (played[i] if played and i < len(played) else '')
            lab = f'<b>{html.escape(nm)}</b>' if nm and d >= 1 else ''
            segs.append(f'<i class="s{i%4}{off}" style="left:{at/16*100:.4f}%;'
                        f'width:{d/16*100:.4f}%">{lab}</i>')
            at += d
        ticks = ''.join(
            f'<u style="left:{b/16*100:.4f}%"'
            f'{" class=bar" if b % 4 == 0 else ""}></u>' for b in range(1, 16))
        return f'<div class="rb">{ticks}{"".join(segs)}</div>'

    rows = []
    for i, (k, v) in enumerate(ranked, 1):
        if i == need + 1:
            rows.append(f'<tr class="cut"><td colspan="5">'
                        f'the first {need} shapes cover 84% of all sections '
                        f'&mdash; everything below is the tail</td></tr>')
        pushed = any(abs(sum(float(x) for x in k.split('-')[:j]) % 2) > .01
                     for j in range(1, len(k.split('-'))))
        s, sec, deg, played, tonic = ex[k][0]
        nsongs = len({r[0] for r in ex[k]})
        # name up to three songs: one example is not enough to tell whether a
        # shape is widespread or one band's habit
        others = []
        for r in ex[k]:
            if r[0] != s and r[0] not in others: others.append(r[0])
            if len(others) >= 2: break
        more = (' &middot; ' + ' &middot; '.join(esc(o) for o in others)) if others else ''
        extra = f' +{nsongs-1-len(others)}' if nsongs-1-len(others) > 0 else ''
        rows.append(
            f'<tr class="{"push" if pushed else ""}"><td class="n">{v}</td>'
            f'<td class="pc">{nsongs}<span> songs</span></td>'
            f'<td class="rbw">{bar(k, played)}</td>'
            f'<td class="dur">{esc(k)}</td>'
            f'<td class="sng"><b>{esc(s)}</b> <i>{esc(sec)}</i>'
            f'<br><em>key of {esc(tonic)} &middot; {esc(deg)}</em>'
            f'<br><u>{more.lstrip(" &middot;") or "&mdash;"}{extra}</u></td></tr>')

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rhythm library</title><style>
  *{{box-sizing:border-box}}
  html,body{{height:100%;margin:0;background:#1a1a2e;color:#e0e0e0;
    font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden}}
  .wrap{{height:100vh;display:flex;flex-direction:column;padding:14px 20px 10px}}
  h1{{font-size:17px;margin:0 0 3px;font-weight:500}}
  .meta{{color:#6a6a8a;font-size:11.5px;line-height:1.45;margin-bottom:9px;max-width:720px}}
  .big{{display:flex;align-items:center;gap:28px;padding:9px 0;margin-bottom:9px;
    border-top:1px solid #2a2a4a;border-bottom:1px solid #2a2a4a}}
  .hero{{display:flex;align-items:baseline;gap:11px}}
  .hero b{{font-size:64px;line-height:.82;font-weight:700;color:#7da3e8;letter-spacing:-.04em}}
  .hero span{{font-size:11.5px;color:#8a8ab0;text-transform:uppercase;
    letter-spacing:.1em;line-height:1.5}}
  .b{{display:flex;flex-direction:column}}
  .b b{{font-size:20px;font-weight:600;color:#fff;line-height:1}}
  .b span{{font-size:10px;color:#6a6a8a;text-transform:uppercase;
    letter-spacing:.09em;margin-top:3px}}
  .legend{{margin-left:auto;font-size:10.5px;color:#6a6a8a}}
  .legend i{{display:inline-block;width:9px;height:9px;border-radius:2px;
    background:#5060a0;margin-right:4px;vertical-align:-1px}}
  .legend i.o{{background:#22223c;box-shadow:inset 0 0 0 1px #e0b060}}
  .sc{{flex:1;overflow-y:auto;min-height:0}}
  table{{width:100%;border-collapse:collapse;font-size:12px}}
  td{{padding:9px 10px 9px 0;border-bottom:1px solid #23233c;vertical-align:middle}}
  td.n{{color:#e0e0e0;width:40px;text-align:right;font-variant-numeric:tabular-nums;
    font-weight:700;font-size:15px}}
  td.pc{{color:#9a9ab8;width:58px;font-size:14px;font-weight:600;
    font-variant-numeric:tabular-nums}}
  td.pc span{{color:#5a5a7a;font-size:9.5px;font-weight:400;display:block;
    margin-top:-1px}}
  td.rbw{{width:430px;padding-right:18px}}
  td.dur{{width:190px;font-family:ui-monospace,Menlo,monospace;color:#9a9ab8;font-size:10.5px}}
  td.sng{{color:#c8c8dc;font-size:13px;line-height:1.38;width:300px}}
  td.sng i{{color:#6a6a8a;font-style:normal}}
  td.sng b{{color:#fff;font-weight:600}}
  td.sng em{{font-style:normal;font-family:ui-monospace,Menlo,monospace;
    font-size:10.5px;color:#7a7a9a}}
  td.sng u{{text-decoration:none;font-size:10.5px;color:#61617f;display:block;
    margin-top:1px}}
  tr.push td.n{{color:#e0b060}}
  tr.cut td{{padding:9px 0 7px;border-bottom:none;color:#5a5a7a;font-size:10px;
    text-transform:uppercase;letter-spacing:.11em;
    border-top:1px solid #3a3a5e}}
  .rb{{position:relative;height:38px;background:#14142a;border-radius:4px;
    box-shadow:inset 0 1px 3px rgba(0,0,0,.35)}}
  .rb u{{position:absolute;top:0;bottom:0;width:1px;background:#2b2b4a}}
  .rb u.bar{{background:#4e4e78}}
  .rb i{{position:absolute;top:4px;bottom:4px;border-radius:3px;
    display:flex;align-items:center;justify-content:center;overflow:hidden}}
  .rb i b{{font-size:12px;font-weight:600;color:#fff;opacity:.94;
    letter-spacing:-.01em;white-space:nowrap}}
  .rb i.s0{{background:#5060a0}} .rb i.s1{{background:#2a6a52}}
  .rb i.s2{{background:#8a5a2a}} .rb i.s3{{background:#6a4a80}}
  .rb i.off{{box-shadow:inset 0 0 0 1px #e0b060}}
</style></head><body><div class="wrap">
  <h1>Rhythm library</h1>
  <p class="meta">Every four-measure rhythm shape in guitar50, guitar100 and the
    Beatles &mdash; how long each chord lasts, ignoring which chords they are.
    Counted once per song-section, so a chorus that comes round sixteen times
    counts once. Bar lines are the heavy ticks; a gold outline means the change
    lands off the two-beat grid.</p>
  <div class="big">
    <div class="hero"><b>{len(pat)}</b><span>shapes<br>in the whole corpus</span></div>
    <div class="b"><b>{tot}</b><span>song sections</span></div>
    <div class="b"><b>{need}</b><span>shapes = 84%</span></div>
    <div class="b"><b>{ranked[0][1]/tot:.0%}</b><span>is just 4-4-4-4</span></div>
    <div class="legend"><i></i>on the grid &nbsp; <i class="o"></i>pushed</div>
  </div>
  <div class="sc"><table>{''.join(rows)}</table></div>
</div></body></html>"""
    open(a.out, 'w').write(doc)
    print(f'{len(pat)} shapes over {tot} phrases -> {a.out}')


if __name__ == '__main__':
    main()
