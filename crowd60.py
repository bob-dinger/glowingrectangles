#!/usr/bin/env python3
"""
"Out of every 60 Americans who die..." — one crowd, coloured by cause.

The two-panel rate cards compare two numbers. This one does something the
others cannot: show a whole population divided up, so the scale of each cause
is read against every other at once. Sixty is the right crowd size because it
is the smallest round number where suicide still gets a whole figure.

    python3 crowd60.py
    python3 crowd60.py --scale 6 --out ~/Desktop
"""
import argparse, os, sys

from PIL import Image, ImageDraw

import sprite_cards as sc

PER_ROW, ROWS = 10, 6

# CDC/NCHS monthly provisional counts, United States, 2022 (3,289,236 deaths).
# `n` is the share of 60, already rounded; they sum to exactly 60.
CAUSES = [
    ('Heart disease',      13, 704786, (178, 58, 46)),
    ('Cancer',             11, 609265, (112, 72,140)),
    ('Everything else',    15, 801263, (110,110,118)),
    ('Accidents',           4, 229852, (196,118, 44)),
    ('COVID-19',            3, 186981, ( 58,124,124)),
    ('Stroke',              3, 165726, ( 52, 96,148)),
    ('Lung disease',        3, 147549, ( 96,140,180)),
    ("Alzheimer's",         2, 120156, (150,110,150)),
    ('Diabetes',            2, 101390, (180,150, 60)),
    ('Kidney disease',      1,  58017, (110,130, 80)),
    ('Suicide',             1,  49674, ( 32, 34, 44)),
    ('Flu & pneumonia',     1,  47163, (140,152,164)),
    ('Sepsis',              1,  42349, (122, 92, 62)),
]
HOMICIDE = ('Homicide', 25065)      # 0.46 of 60 — too small to draw one figure
TOTAL = 3289236


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scale', type=int, default=6)
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/rate-cards'))
    a = ap.parse_args()
    scale = a.scale

    assert sum(c[1] for c in CAUSES) == 60, 'shares must sum to 60'

    # The sprite renderer takes indices into TUNICS, so append the cause
    # colours to that palette and use their indices. Cheaper than teaching
    # sprite() about arbitrary colours, and it keeps one code path.
    base = len(sc.TUNICS)
    sc.TUNICS.extend([c[3] for c in CAUSES])

    sw, sh = sc.TW*scale, sc.TH*scale
    gap = max(4, scale)
    cell_w, cell_h = sw+gap, sh+gap
    grid_w, grid_h = PER_ROW*cell_w, ROWS*cell_h
    margin = 74
    W = margin*2 + grid_w

    f_q   = sc.font(round(scale*10), sc.BOLD)
    f_sub = sc.font(round(scale*5.0), sc.MEDIUM)
    f_leg = sc.font(round(scale*4.6), sc.DEMI)
    f_ft  = sc.font(round(scale*4.2), sc.MEDIUM)

    probe = ImageDraw.Draw(Image.new('RGB', (1,1)))
    lines = sc.wrap_to('Out of every 60 Americans who die', f_q, W-margin*2, probe)
    line_h = round(scale*10*1.18)
    title_y = 54
    head = title_y + len(lines)*line_h + round(scale*7)
    leg_rows = (len(CAUSES)+1 + 1)//2
    foot = round(scale*7) + leg_rows*round(scale*7.4) + 96
    H = head + grid_h + foot

    img = Image.new('RGB', (W, H), sc.BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y/H
        d.line([(0,y),(W,y)],
               fill=tuple(round(p+(q-p)*t) for p,q in zip(sc.BG_TOP, sc.BG_BOT)))
    s = abs(hash('grass60')) % 4294967296
    for _ in range(210):
        s = (s*1664525+1013904223) % 4294967296; gx=(s>>8)%(W//scale)
        s = (s*1664525+1013904223) % 4294967296; gy=(s>>8)%(H//scale)
        for dx,dy in ((0,1),(1,0),(2,1),(1,1)):
            d.rectangle([gx*scale+dx*scale, gy*scale+dy*scale,
                         gx*scale+(dx+1)*scale-1, gy*scale+(dy+1)*scale-1], fill=sc.TUFT)

    for i, ln in enumerate(lines):
        sc.centre(d, (W//2, title_y + i*line_h), ln, f_q, sc.INK)
    sc.centre(d, (W//2, title_y + len(lines)*line_h - round(scale*2)),
              f'United States, 2022  ·  {TOTAL:,} deaths', f_sub, sc.MUTED)

    d.rounded_rectangle([margin-22, head-20, margin+grid_w+22, head+grid_h+16],
                        radius=18, fill=sc.PANEL_L)

    cast = sc.crowd('how-americans-die', 80)
    shadow = sc.shadow_tile(round(sw*0.72))
    order = []
    for ci, (_, n, _, _) in enumerate(CAUSES):
        order += [ci]*n

    for i, ci in enumerate(order):
        r, c = divmod(i, PER_ROW)
        x = margin + c*cell_w + gap//2
        y = head + r*cell_h + gap//2
        bi, si, hi, _, ki, li = cast[i]
        combo = (bi, si, hi, base+ci, ki, li)
        img.paste(shadow, (x+(sw-shadow.width)//2, y+sh-shadow.height//2), shadow)
        sp = sc.sprite(combo, True, sc.PANEL_L, (sw, sh))
        img.paste(sp, (x, y), sp)

    # legend, two columns
    ly = head + grid_h + round(scale*10)
    col_w = (W - margin*2)//2
    entries = [(nm, n, v, col) for nm, n, v, col in CAUSES]
    entries.append((HOMICIDE[0], 0, HOMICIDE[1], None))
    for i, (nm, n, v, col) in enumerate(entries):
        cx = margin + (i % 2)*col_w
        cy = ly + (i//2)*round(scale*7.4)
        box = [cx, cy-round(scale*2.0), cx+round(scale*4), cy+round(scale*2.0)]
        if col: d.rounded_rectangle(box, radius=round(scale*0.8), fill=col)
        else:   d.rounded_rectangle(box, radius=round(scale*0.8), outline=sc.MUTED,
                                    width=max(1, round(scale*0.35)))
        cnt = f'{n}' if n else 'under ½'
        d.text((cx+round(scale*6), cy), f'{cnt}   {nm}', font=f_leg,
               fill=sc.INK, anchor='lm')
        d.text((cx+col_w-round(scale*5), cy), f'{v/TOTAL*100:.1f}%', font=f_leg,
               fill=sc.MUTED, anchor='rm')

    sc.centre(d, (W//2, H-58),
              'Each figure is one in sixty. Homicide is under half a figure.', f_ft, sc.MUTED)
    sc.centre(d, (W//2, H-30),
              'CDC/NCHS monthly provisional counts of deaths by select cause',
              f_ft, sc.MUTED)

    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, 'how-americans-die-60.png')
    img.save(p)
    print(f'{img.width}x{img.height} -> {p}')


if __name__ == '__main__':
    main()
