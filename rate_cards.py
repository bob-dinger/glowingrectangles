#!/usr/bin/env python3
"""
suicide-items.json -> pixel-art rate cards.

Same villagers as sprite_cards.py, a different and incompatible arithmetic.

THE WHOLE POINT: the perception cards light N of 100 villagers because their
numbers are PERCENTAGES — 21 of 100 people. These numbers are per 100,000 per
year. Lighting 13 of 100 villagers for a rate of 13 per 100,000 would read as
13%, wrong by a factor of a thousand. So here the figures are a COUNT — this
many died out of a hundred thousand alive — and there is deliberately no
100-slot frame behind them to imply a denominator. Both panels share a row
count so the two crowds are to the same scale.

    python3 rate_cards.py
    python3 rate_cards.py --id gradient-1932 --scale 5
"""
import argparse, json, math, os

from PIL import Image, ImageDraw

import sprite_cards as sc

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, 'suicide-items.json')
PER_ROW = 10


def card(item, scale):
    lv, rv = item['left']['value'], item['right']['value']
    ln, rn = max(1, round(lv)), max(1, round(rv))
    share = bool(item.get('share'))
    # A SHARE is a percentage, so the denominator is the crowd itself and the
    # unlit figures are the rest of the hundred. A RATE must never get this
    # frame: 13 lit of 100 would read as 13%, not 13 per 100,000.
    rows = 10 if share else max(1, math.ceil(max(ln, rn) / PER_ROW))

    sw, sh = sc.TW*scale, sc.TH*scale
    gap = max(4, scale)
    cell_w, cell_h = sw+gap, sh+gap
    grid_w, grid_h = PER_ROW*cell_w, rows*cell_h

    margin, mid_gap = 74, 96
    W = margin*2 + grid_w*2 + mid_gap

    f_lbl = sc.font(round(scale*6.2), sc.DEMI)
    f_num = sc.font(round(scale*17), sc.BOLD)
    f_ft  = sc.font(round(scale*5.2), sc.MEDIUM)
    f_pt  = sc.font(round(scale*6.8), sc.DEMI)

    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for pt in range(round(scale*11), round(scale*5), -1):
        f_q = sc.font(pt, sc.BOLD)
        lines = sc.wrap_to(item['ask'], f_q, W - margin*2, probe)
        if len(lines) <= 2: break
    line_h = round(pt*1.18)

    title_y = 62
    label_y = title_y + (len(lines)-1)*line_h + round(scale*13)
    num_y   = label_y + round(scale*12)
    head    = num_y + round(scale*11)
    # the unit line and the point both live in the footer, so it is taller
    # than the perception cards': a rate is meaningless without its
    # denominator printed next to it
    foot    = 150
    H = head + grid_h + foot

    img = Image.new('RGB', (W, H), sc.BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y/H
        d.line([(0,y),(W,y)],
               fill=tuple(round(a+(b-a)*t) for a,b in zip(sc.BG_TOP, sc.BG_BOT)))

    s = abs(hash('grass'+item['id'])) % 4294967296
    for _ in range(190):
        s = (s*1664525 + 1013904223) % 4294967296; gx = (s >> 8) % (W//scale)
        s = (s*1664525 + 1013904223) % 4294967296; gy = (s >> 8) % (H//scale)
        px_, py_ = gx*scale, gy*scale
        for dx, dy in ((0,1),(1,0),(2,1),(1,1)):
            d.rectangle([px_+dx*scale, py_+dy*scale,
                         px_+(dx+1)*scale-1, py_+(dy+1)*scale-1], fill=sc.TUFT)

    for i, ln_ in enumerate(lines):
        sc.centre(d, (W//2, title_y + i*line_h), ln_, f_q, sc.INK)

    cast   = sc.crowd(item['id'])
    shadow = sc.shadow_tile(round(sw*0.72))
    # match the decimals across both panels: 22 beside 21.2 reads as a
    # rounder, less careful number than its neighbour
    dp = 1 if (lv % 1 or rv % 1) else 0
    fmt = lambda v: f'{v:.{dp}f}'
    # Colour by MAGNITUDE, not by position. Red on the right was fine while
    # every card ran small-then-big, but on a card where the later number is
    # the smaller one — old white men, 55.8 in 1950 down to 36.2 — red on the
    # right reads as "this is the alarming one" and inverts the meaning.
    panels = [(item['left']['label'],  lv, ln, sc.RED if lv >= rv else sc.NAVY),
              (item['right']['label'], rv, rn, sc.RED if rv > lv else sc.NAVY)]
    xs = (margin, margin+grid_w+mid_gap)

    for p, ((label, value, n, colour), x0) in enumerate(zip(panels, xs)):
        cx = x0 + grid_w//2
        d.rounded_rectangle([x0-22, head-30, x0+grid_w+22, head+grid_h+18],
                            radius=18, fill=sc.PANEL_L)
        sc.centre(d, (cx, label_y), label, f_lbl, sc.MUTED)
        num_with_unit(d, img, cx, num_y, value, dp,
                      item.get('suffix', 'per 100k'), f_num, f_ft,
                      colour, sc.MUTED)
        # bottom-up, so both crowds sit on the same ground line and the
        # taller one reads as taller rather than as a differently-filled grid
        for i in range(100 if share else n):
            r, c = divmod(i, PER_ROW)
            x = x0 + c*cell_w + gap//2
            y = head + ((r if share else rows-1-r))*cell_h + gap//2
            on = (i < n) if share else True
            if on:
                img.paste(shadow, (x+(sw-shadow.width)//2,
                                   y+sh-shadow.height//2), shadow)
            sp = sc.sprite(cast[p*100+i], on, sc.PANEL_L, (sw, sh))
            img.paste(sp, (x, y), sp)

    d.line([(W//2, head-40), (W//2, head+grid_h)], fill=(92,138,54), width=2)

    fy = head + grid_h + 40
    sc.centre(d, (W//2, fy), item['unit'], f_pt, sc.INK)
    for i, ln_ in enumerate(sc.wrap_to(item['point'], f_ft, W-margin*2, probe)[:2]):
        sc.centre(d, (W//2, fy + 30 + i*round(scale*6.4)), ln_, f_ft, sc.MUTED)
    yr = f" {item['year']}" if item.get('year') else ''
    kind = 'share of the total' if item.get('share') else f"{item['rate_type']} rate"
    sc.centre(d, (W//2, H-28), f'CDC/NCHS{yr}   {kind}', f_ft, sc.MUTED)
    return img


def num_with_unit(d, img, cx, y, value, dp, suffix, f_num, f_suf, colour, muted):
    """Draw the figure with its unit WELDED to it, centred as one object.

    The card previously printed bare numerals with the denominator up in the
    row title. A reader takes the unit from the first number they decode and
    carries it to the next one — so a row of percentages above a row of
    per-100,000 rates got read as percentages throughout, out by a factor of
    a thousand. The unit has to travel with the numeral.
    """
    n = f'{value:.{dp}f}'
    # '%' closes up against the figure; a worded unit needs its space
    suffix = suffix if suffix == '%' else ' ' + suffix
    wn = d.textlength(n, font=f_num)
    ws = d.textlength(suffix, font=f_suf)
    x = cx - (wn + ws) / 2
    d.text((x, y), n, font=f_num, fill=colour, anchor='lm')
    d.text((x + wn, y + round(f_num.size * 0.10)), suffix,
           font=f_suf, fill=muted, anchor='lm')


def flip_card(item, scale):
    """A card with TWO rows, each row its own measure and its own denominator.

    This exists because the interesting comparison is across measures that
    cannot share an axis: suicide ATTEMPTS are a percentage of high school
    students, suicide DEATHS are per 100,000 men. Plot them together on one
    scale and the picture is a lie. Stack them as separate rows, each with its
    denominator printed, and the honest finding shows up on its own — the
    trying is nearly level, the dying is not.
    """
    rows = item['rows']
    per_row = PER_ROW
    sw, sh = sc.TW*scale, sc.TH*scale
    gap = max(4, scale)
    cell_w, cell_h = sw+gap, sh+gap

    # every row gets the same number of sprite-rows so no row is visually
    # compressed relative to another
    counts = [[max(1, round(v)) for _, v in r['values']] for r in rows]
    # Each row is sized to ITS OWN largest count, not to a shared maximum.
    # A shared vertical scale would invite reading row heights against each
    # other, and the rows have different denominators — percent of students
    # against deaths per 100,000 — so that comparison is meaningless. The
    # printed denominator is what makes each row legible, not its height.
    hr = [max(1, math.ceil(max(c) / per_row)) for c in counts]
    # When every row carries the SAME denominator — three causes of death all
    # per 100,000 — a shared scale is not just allowed, it is the point: the
    # eye is supposed to compare row against row. Per-row sizing is for the
    # opposite case, rows whose units cannot be compared.
    if item.get('shared_scale'):
        hr = [max(hr)] * len(hr)
    grid_w = per_row*cell_w

    margin, mid_gap = 74, 96
    W = margin*2 + grid_w*2 + mid_gap

    f_lbl = sc.font(round(scale*6.2), sc.DEMI)
    f_num = sc.font(round(scale*14), sc.BOLD)
    f_ft  = sc.font(round(scale*5.2), sc.MEDIUM)
    f_row = sc.font(round(scale*8), sc.BOLD)
    f_den = sc.font(round(scale*5.4), sc.MEDIUM)

    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for pt in range(round(scale*11), round(scale*5), -1):
        f_q = sc.font(pt, sc.BOLD)
        lines = sc.wrap_to(item['ask'], f_q, W - margin*2, probe)
        if len(lines) <= 2: break
    line_h = round(pt*1.18)

    title_y = 58
    top = title_y + (len(lines)-1)*line_h + round(scale*15)
    blocks = [round(scale*10) + round(scale*13) + round(scale*9) + h*cell_h
              + round(scale*13) for h in hr]
    H = top + sum(blocks) + 108

    img = Image.new('RGB', (W, H), sc.BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y/H
        d.line([(0,y),(W,y)],
               fill=tuple(round(a+(b-a)*t) for a,b in zip(sc.BG_TOP, sc.BG_BOT)))
    s_ = abs(hash('grass'+item['id'])) % 4294967296
    for _ in range(230):
        s_ = (s_*1664525 + 1013904223) % 4294967296; gx = (s_ >> 8) % (W//scale)
        s_ = (s_*1664525 + 1013904223) % 4294967296; gy = (s_ >> 8) % (H//scale)
        for dx, dy in ((0,1),(1,0),(2,1),(1,1)):
            d.rectangle([gx*scale+dx*scale, gy*scale+dy*scale,
                         gx*scale+(dx+1)*scale-1, gy*scale+(dy+1)*scale-1], fill=sc.TUFT)
    for i, ln_ in enumerate(lines):
        sc.centre(d, (W//2, title_y + i*line_h), ln_, f_q, sc.INK)

    # four panels, not two, so the default 200-combo cast runs out
    cast   = sc.crowd(item['id'], 100*2*len(rows))
    shadow = sc.shadow_tile(round(sw*0.72))
    xs = (margin, margin+grid_w+mid_gap)
    y = top
    for ri, row in enumerate(rows):
        hrows, grid_h = hr[ri], hr[ri]*cell_h
        # match decimals within the row, as the single cards do
        vals = [v for _, v in row['values']]
        dp = 1 if any(v % 1 for v in vals) else 0
        sc.centre(d, (W//2, y), row['title'].upper(), f_row, sc.INK)
        sc.centre(d, (W//2, y + round(scale*9)), row['unit'], f_den, sc.MUTED)
        lab_y = y + round(scale*20)
        head  = lab_y + round(scale*12)
        for p, ((label, value), x0) in enumerate(zip(row['values'], xs)):
            cx = x0 + grid_w//2
            d.rounded_rectangle([x0-22, head-24, x0+grid_w+22, head+grid_h+16],
                                radius=18, fill=sc.PANEL_L)
            sc.centre(d, (cx, lab_y), label, f_lbl, sc.MUTED)
            colour = sc.RED if value >= max(vals) else sc.NAVY
            num_with_unit(d, img, cx, head-4, value, dp,
                          row.get('suffix', 'per 100k'), f_num, f_den,
                          colour, sc.MUTED)
            n = counts[ri][p]
            for i in range(n):
                r, c = divmod(i, per_row)
                x = x0 + c*cell_w + gap//2
                yy = head + round(scale*9) + (hrows-1-r)*cell_h + gap//2
                img.paste(shadow, (x+(sw-shadow.width)//2,
                                   yy+sh-shadow.height//2), shadow)
                sp = sc.sprite(cast[(ri*2+p)*100 + i], True, sc.PANEL_L, (sw, sh))
                img.paste(sp, (x, yy), sp)
        y += blocks[ri]

    for i, ln_ in enumerate(sc.wrap_to(item['point'], f_ft, W-margin*2, probe)[:3]):
        sc.centre(d, (W//2, H-88 + i*round(scale*6.6)), ln_, f_ft, sc.MUTED)
    sc.centre(d, (W//2, H-26), item['cite'], f_ft, sc.MUTED)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/rate-cards'))
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--id', default=None)
    a = ap.parse_args()

    items = json.load(open(SRC))['items']
    if a.id: items = [i for i in items if a.id in i['id']]
    unver = [i['id'] for i in items if not i.get('verified')]
    if unver:
        items = [i for i in items if i.get('verified')]
        print('skipped unverified:', ', '.join(unver))

    os.makedirs(a.out, exist_ok=True)
    for it in items:
        img = flip_card(it, a.scale) if it.get('rows') else card(it, a.scale)
        p = os.path.join(a.out, it['id'] + '.png')
        img.save(p)
        if it.get('rows'):
            print(f"  {it['id']:<24} {img.width}x{img.height}  "
                  + ' | '.join(f"{r['title']}: " +
                    ' vs '.join(f'{round(v)}' for _, v in r['values'])
                    for r in it['rows']))
        else:
            print(f"  {it['id']:<24} {img.width}x{img.height}  "
                  f"{round(it['left']['value'])} vs {round(it['right']['value'])} figures")
    print(f'\n-> {a.out}')


if __name__ == '__main__':
    main()
