#!/usr/bin/env python3
"""
one-percent-data.js -> ~/Desktop/one-percent/  (25 PNGs, ready for Substack)

Square 1200x1200 PNGs. Substack strips SVG out of the email version, so the
raster is the publishable artefact; the interactive page is the web version.

    python3 make_one_percent.py
    python3 make_one_percent.py --dark --size 1456
"""
import argparse, json, os, re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'one-percent-data.js')
AVENIR = '/System/Library/Fonts/Avenir Next.ttc'
BOLD, DEMI, MEDIUM = 0, 2, 5

THEME = {
    'light': dict(bg=(255,255,255), off=(230,230,234), on=(224,72,58),
                  ink=(22,22,26),   cap=(111,111,120)),
    'dark':  dict(bg=(20,20,26),    off=(38,38,46),    on=(255,91,74),
                  ink=(242,240,238), cap=(138,136,148)),
}


def load():
    txt = open(DATA).read()
    return json.loads(re.search(r'=\s*(\[.*\])\s*;', txt, re.S).group(1))


def font(px, index=BOLD):
    try:    return ImageFont.truetype(AVENIR, px, index=index)
    except Exception: return ImageFont.load_default()


def wrap(d, text, fnt, max_px):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=fnt) <= max_px: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines or ['']


def card(item, S, t):
    """S = pixel size of the square. All geometry is a fraction of it, so any
    output size stays proportional."""
    img = Image.new('RGB', (S, S), t['bg'])
    d = ImageDraw.Draw(img)
    u = S / 600.0                       # the original design was 600x600

    # Vertical budget, top to bottom: title / grid / caption / headline.
    # Everything is measured before anything is drawn, so nothing collides
    # and no text is ever chopped to make room.
    pad = round(52*u)

    # title — shrink until it fits two lines
    for pt in range(round(34*u), round(17*u), -1):
        f_t = font(pt, BOLD)
        t_lines = wrap(d, item['title'], f_t, S - pad*2)
        if len(t_lines) <= 2: break
    t_line_h = round(pt*1.18)
    t_block  = len(t_lines) * t_line_h

    # caption — the FULL note, never split on a full stop (that was cutting
    # "1.01 to the 365th" down to "1.")
    # real-world items carry a longer note, so give them more room
    max_c = 4 if item.get('source') else 2
    f_c = font(round(15.5*u), MEDIUM)
    c_lines  = wrap(d, item['note'], f_c, S - pad*2)[:max_c]
    c_line_h = round(19*u)
    c_block  = len(c_lines) * c_line_h

    f_h = font(round(23*u), BOLD)
    h_block = round(30*u)

    # a sourced item gets its citation on the card, so the image can travel
    # without losing its provenance
    f_s = font(round(11*u), MEDIUM)
    s_block = round(20*u) if item.get('source') else 0

    # whatever is left over is the grid
    avail = S - pad*2 - t_block - c_block - h_block - s_block - round(34*u)
    box   = min(round(430*u), avail)
    gap   = max(2.0, 6*u * box / (430*u))
    cell  = (box - gap*9) / 10

    y = pad
    for ln in t_lines:
        d.text((S/2, y), ln, font=f_t, fill=t['ink'], anchor='ma')
        y += t_line_h

    y += round(22*u)
    x0 = (S - box) / 2
    for i in range(100):
        r, c = divmod(i, 10)
        d.rounded_rectangle([x0 + c*(cell+gap), y + r*(cell+gap),
                             x0 + c*(cell+gap) + cell, y + r*(cell+gap) + cell],
                            radius=4*u, fill=t['on'] if i < item['lit'] else t['off'])
    y += 10*(cell+gap) + round(18*u)

    for ln in c_lines:
        d.text((S/2, y), ln, font=f_c, fill=t['cap'], anchor='ma')
        y += c_line_h

    y += round(8*u)
    d.text((S/2, y), item['headline'], font=f_h, fill=t['on'], anchor='ma')

    if item.get('source'):
        d.text((S/2, S - round(34*u)), item['source'], font=f_s,
               fill=t['cap'], anchor='ma')
    return img


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/one-percent'))
    ap.add_argument('--size', type=int, default=1200)
    ap.add_argument('--dark', action='store_true')
    a = ap.parse_args()

    items = load()
    t = THEME['dark' if a.dark else 'light']
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.endswith('.png'): os.remove(os.path.join(a.out, f))

    caps = []
    for i, it in enumerate(items, 1):
        name = f"{i:02d}-{slug(it['title'])}.png"
        card(it, a.size, t).save(os.path.join(a.out, name))
        caps.append(f"=== {name}\n{it['title']}  ->  {it['headline']}\n{it['note']}\n")

    open(os.path.join(a.out, '_captions.txt'), 'w').write('\n'.join(caps))
    print(f"wrote {len(items)} PNGs to {a.out}   {a.size} x {a.size}")


if __name__ == '__main__':
    main()
