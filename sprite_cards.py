#!/usr/bin/env python3
"""
perception-items.json -> tweetable pixel-art cards.

Left panel = what people picture. Right = what's actually there.
100 villagers per panel; the lit ones are the count.

Design rule: the SPRITES are pixel art (drawn at 1x, blown up with
nearest-neighbour so every pixel stays square). Everything else - type,
background, shadows, panels - is drawn at full resolution and antialiased.

The crowd is varied: four body types crossed with skin, hair, tunic and hat
palettes. Assignment is deterministic per item id, so a given card always
renders identically, but no two cards look like the same hundred people.

    python3 sprite_cards.py                    # every eligible item
    python3 sprite_cards.py --id trans
    python3 sprite_cards.py --scale 5 --out ~/Desktop/cards
"""
import argparse, json, os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, 'perception-items.json')

AVENIR = '/System/Library/Fonts/Avenir Next.ttc'
BOLD, DEMI, MEDIUM = 0, 2, 5

# ---------------------------------------------------------------- bodies
# 12 wide x 16 tall. H hair, S skin, N neck, E eye, T tunic, L legs,
# B boots, K hat; lowercase = the shaded variant of the same material.
BODIES = [
    [   # short hair
        '....HHHH....', '...HHHHHHh..', '..HHHHHHHHh.', '..HSSSSSSh..',
        '..HSESSESh..', '..HSSSSSSh..', '...SSSSSs...', '....NNNs....',
        '..TTTTTTtt..', '.STTTTTTTtS.', '.STTTTTTTtS.', '.sTTTTTTTts.',
        '..TTTTTTtt..', '..LLL..LLl..', '..LLL..LLl..', '..BBB..BBb..',
    ],
    [   # long hair
        '....HHHH....', '...HHHHHHh..', '..HHHHHHHHh.', '..HSSSSSSHh.',
        '..HSESSESHh.', '..HSSSSSSHh.', '..HHSSSSHHh.', '....NNNs....',
        '..TTTTTTtt..', '.STTTTTTTtS.', '.STTTTTTTtS.', '.sTTTTTTTts.',
        '..TTTTTTtt..', '..LLL..LLl..', '..LLL..LLl..', '..BBB..BBb..',
    ],
    [   # hat
        '...KKKKKK...', '..KKKKKKKK..', '.KKKKKKKKKK.', '..HSSSSSSh..',
        '..HSESSESh..', '..HSSSSSSh..', '...SSSSSs...', '....NNNs....',
        '..TTTTTTtt..', '.STTTTTTTtS.', '.STTTTTTTtS.', '.sTTTTTTTts.',
        '..TTTTTTtt..', '..LLL..LLl..', '..LLL..LLl..', '..BBB..BBb..',
    ],
    [   # stockier, shorter legs
        '....HHHH....', '...HHHHHHh..', '..HHHHHHHHh.', '..HSSSSSSh..',
        '..HSESSESh..', '..HSSSSSSh..', '...SSSSSs...', '....NNNs....',
        '.TTTTTTTTtt.', 'STTTTTTTTTtS', 'STTTTTTTTTtS', 'sTTTTTTTTTts',
        '.TTTTTTTTtt.', '..LLL..LLl..', '..BBB..BBb..', '..BBB..BBb..',
    ],
]
BW, BH = 12, 16
TW, TH = BW + 2, BH + 2          # room for the outline

SKINS  = [(240,195,145),(226,171,120),(198,140,95),(163,110,72),(126,82,52),(247,214,178)]
HAIRS  = [(74,47,22),(38,28,20),(122,80,36),(168,128,64),(96,96,102),(140,52,38)]
TUNICS = [(178,58,46),(52,96,148),(58,124,74),(150,104,40),(112,72,140),
          (196,132,52),(64,112,124),(158,72,112),(88,104,52),(190,96,72)]
HATS   = [(122,82,38),(92,62,112),(58,102,72),(150,60,50)]
LEGS   = [(74,53,36),(58,60,74),(88,72,50)]
BOOT   = (36,26,18)
OUTLINE= (23,16,10)


def shade(c, f=0.74):
    return tuple(round(v*f) for v in c)


def palette(skin, hair, tunic, hat, leg):
    return {
        'H':hair,  'h':shade(hair),
        'S':skin,  's':shade(skin, 0.86),  'N':shade(skin, 0.88),
        'E':(26,16,8),
        'T':tunic, 't':shade(tunic),
        'K':hat,   'k':shade(hat),
        'L':leg,   'l':shade(leg),
        'B':BOOT,  'b':shade(BOOT),
        'O':OUTLINE,
    }


_cache = {}

def sprite(combo, lit, ground, size):
    """One villager as RGBA with an auto 1px outline, upscaled and cached."""
    key = (combo, lit, size)
    if key in _cache:
        return _cache[key]

    bi, si, hi, ti, ki, li = combo
    body = BODIES[bi]
    pal  = palette(SKINS[si], HAIRS[hi], TUNICS[ti], HATS[ki], LEGS[li])

    img = Image.new('RGBA', (TW, TH), (0,0,0,0))
    px  = img.load()
    filled = {(c+1, r+1): ch for r, row in enumerate(body)
              for c, ch in enumerate(row) if ch != '.'}

    for (x, y) in list(filled):                      # outline first
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (x+dx, y+dy)
            if n not in filled and 0 <= n[0] < TW and 0 <= n[1] < TH:
                px[n] = pal['O'] + (255,)
    for (x, y), ch in filled.items():
        px[x, y] = pal[ch] + (255,)

    if not lit:
        # fade into the panel rather than lowering alpha, so unlit figures
        # read as scenery instead of ghosts
        for y in range(TH):
            for x in range(TW):
                r, g, b, aa = px[x, y]
                if aa:
                    px[x, y] = tuple(round(c*0.10 + gc*0.90)
                                     for c, gc in zip((r,g,b), ground)) + (255,)

    out = img.resize(size, Image.NEAREST)
    _cache[key] = out
    return out


def crowd(seed_text, n=200):
    """A deterministic, repeatable cast of characters for one card."""
    s = abs(hash(seed_text)) % 4294967296
    def nxt(m):
        nonlocal s
        s = (s*1664525 + 1013904223) % 4294967296
        return (s >> 8) % m
    return [(nxt(len(BODIES)), nxt(len(SKINS)), nxt(len(HAIRS)),
             nxt(len(TUNICS)), nxt(len(HATS)), nxt(len(LEGS)))
            for _ in range(n)]


def shadow_tile(w):
    s = Image.new('RGBA', (w, max(6, w//3)), (0,0,0,0))
    ImageDraw.Draw(s).ellipse([0,0,w-1,s.height-1], fill=(90,62,20,70))
    return s.filter(ImageFilter.GaussianBlur(w/9))


# ---------------------------------------------------------------- type
def font(size, index=0):
    try:    return ImageFont.truetype(AVENIR, size, index=index)
    except Exception: return ImageFont.load_default()

def centre(d, xy, text, fnt, fill):
    d.text(xy, text, font=fnt, fill=fill, anchor='mm')

def wrap_to(text, fnt, max_px, d):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=fnt) <= max_px: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines or ['']


# ---------------------------------------------------------------- card
COLS = ROWS = 10
# Zelda overworld grass. Deliberately not sand — a desert palette reads as
# "Middle East" and colours the reading of items that have nothing to do
# with it.
BG_TOP, BG_BOT = (138,186,86), (104,152,62)
PANEL_L  = (156,199,102)          # the mown lawn the crowd stands on
TUFT     = (118,166,70)
INK      = (28,46,20)
MUTED    = (72,104,44)
RED      = (176,44,36)            # perceived
NAVY     = (26,66,104)            # actual — green would vanish into the grass
GREEN    = NAVY                   # keep the old name working


def count_for(v):
    if v is None or v <= 0: return 0
    return max(1, int(round(v)))


def card(item, scale, only=None):
    """only=None draws both panels; only=0 or 1 draws just that side."""
    sw, sh = TW*scale, TH*scale
    gap = max(4, scale)
    cell_w, cell_h = sw+gap, sh+gap
    grid_w, grid_h = COLS*cell_w, ROWS*cell_h

    margin, mid_gap = 74, 96
    panels_n = 1 if only is not None else 2
    W = margin*2 + grid_w*panels_n + (mid_gap if panels_n == 2 else 0)

    f_q   = font(round(scale*11), BOLD)
    f_lbl = font(round(scale*6.2), DEMI)
    f_num = font(round(scale*17), BOLD)
    f_ft  = font(round(scale*5.2), MEDIUM)

    # Measure the title first — a two-line question used to run straight into
    # the panel labels, because the header height was hard-coded for one line.
    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    # Shrink the title until the WHOLE question fits — never truncate. A long
    # question on a half-width card would otherwise lose its last words, which
    # is the one thing a card like this cannot survive.
    max_lines = 2 if only is None else 3
    for pt in range(round(scale*11), round(scale*5), -1):
        f_q   = font(pt, BOLD)
        lines = wrap_to(item['ask'], f_q, W - margin*2, probe)
        if len(lines) <= max_lines:
            break
    line_h = round(pt*1.18)
    title_y = 62
    label_y = title_y + (len(lines)-1)*line_h + round(scale*13)
    num_y   = label_y + round(scale*12)
    head    = num_y + round(scale*11)
    foot    = 96
    H = head + grid_h + foot

    img = Image.new('RGB', (W, H), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y/H
        d.line([(0,y),(W,y)],
               fill=tuple(round(a+(b-a)*t) for a,b in zip(BG_TOP,BG_BOT)))

    # grass tufts, on the pixel grid so they belong to the sprites
    s = abs(hash('grass'+item['id'])) % 4294967296
    for _ in range(190):
        s = (s*1664525 + 1013904223) % 4294967296; gx = (s >> 8) % (W//scale)
        s = (s*1664525 + 1013904223) % 4294967296; gy = (s >> 8) % (H//scale)
        px_, py_ = gx*scale, gy*scale
        for dx, dy in ((0,1),(1,0),(2,1),(1,1)):
            d.rectangle([px_+dx*scale, py_+dy*scale,
                         px_+(dx+1)*scale-1, py_+(dy+1)*scale-1], fill=TUFT)

    for i, ln in enumerate(lines):
        centre(d, (W//2, title_y + i*line_h), ln, f_q, INK)

    cast   = crowd(item['id'])
    shadow = shadow_tile(round(sw*0.72))
    all_panels = [('WHAT PEOPLE PICTURE', item['perceived'], RED),
                  ("WHAT'S ACTUALLY THERE", item['actual'],  NAVY)]
    if only is None:
        panels, xs, idx = all_panels, (margin, margin+grid_w+mid_gap), (0, 1)
    else:
        # keep the same cast slice as the combined card, so the two halves
        # show the same hundred people they would have side by side
        panels, xs, idx = [all_panels[only]], (margin,), (only,)

    for slot, ((label, value, colour), x0) in enumerate(zip(panels, xs)):
        p = idx[slot]
        cx = x0 + grid_w//2
        d.rounded_rectangle([x0-22, head-30, x0+grid_w+22, head+grid_h+18],
                            radius=18, fill=PANEL_L)
        centre(d, (cx, label_y), label, f_lbl, MUTED)
        centre(d, (cx, num_y), f"{value:g}%", f_num, colour)

        lit = count_for(value)
        for i in range(COLS*ROWS):
            r, c = divmod(i, COLS)
            x = x0 + c*cell_w + gap//2
            y = head + r*cell_h + gap//2
            on = i < lit
            if on:                       # only lit figures cast a shadow
                img.paste(shadow, (x+(sw-shadow.width)//2,
                                   y+sh-shadow.height//2), shadow)
            s = sprite(cast[p*100+i], on, PANEL_L, (sw, sh))
            img.paste(s, (x, y), s)

    if only is None:
        d.line([(W//2, head-40), (W//2, head+grid_h)], fill=(92,138,54), width=2)
    centre(d, (W//2, H-52), short_cite(item), f_ft, MUTED)
    return img


def short_cite(item):
    who  = item.get('_cite', item['source']).split(',')[0].strip()
    line = f"{who} {item['year']}" if item.get('year') else who
    if item.get('n'): line += f"   n = {item['n']:,}"
    return line


def tweet_text(item):
    p, a, ratio = item['perceived'], item['actual'], item.get('ratio')
    out = f"{item['ask']}\n\nGuessed: {p:g}%\nActual: {a:g}%"
    if ratio and ratio >= 2:
        out += f"\n\nOff by {ratio:g}x."
    elif ratio and 0 < ratio < 1:
        out += f"\n\nReality is {round(1/ratio,1):g}x bigger than people think."
    return out


def citation_block(item):
    lines = [f"SOURCE : {item['_cite']}"]
    if item.get('_fielded'): lines.append(f"FIELDED: {item['_fielded']}")
    if item.get('n'):        lines.append(f"N      : {item['n']:,}")
    if item.get('_url'):     lines.append(f"URL    : {item['_url']}")
    if item.get('note'):     lines.append(f"NOTE   : {item['note']}")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/sprite-cards'))
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--id', default=None)
    ap.add_argument('--kinds', default='size,meta')
    ap.add_argument('--include-unverified', action='store_true',
                    help='render cards for items not traceable to a primary source')
    ap.add_argument('--no-sides', action='store_true',
                    help='skip the per-panel images in sides/')
    a = ap.parse_args()

    raw, kinds = json.load(open(SRC)), set(a.kinds.split(','))
    srcs = raw['sources']

    items = [i for i in raw['items'] if i['kind'] in kinds
             and isinstance(i.get('perceived'), (int,float))
             and isinstance(i.get('actual'), (int,float))]

    # never render a card for an item whose number is not traceable to a
    # primary source — a card is publishable by definition once it exists
    unverified = [i['id'] for i in items if not i.get('verified')]
    if unverified and not a.include_unverified:
        items = [i for i in items if i.get('verified')]
        print(f"skipped {len(unverified)} unverified: {', '.join(unverified)}")

    if a.id: items = [i for i in items if i['id'] == a.id]

    sides_dir = os.path.join(a.out, 'sides')
    os.makedirs(a.out, exist_ok=True)
    if not a.no_sides: os.makedirs(sides_dir, exist_ok=True)
    if not a.id:
        for folder in (a.out, sides_dir):
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    if f.endswith('.png'): os.remove(os.path.join(folder, f))

    caps, size, side_size = [], None, None
    for it in items:
        s = srcs.get(it['source'], {})
        it['_cite'], it['_url'], it['_fielded'] = \
            s.get('cite', it['source']), s.get('url'), s.get('fielded')
        stem = f"{it['id']}__{it['source']}"
        im = card(it, a.scale); im.save(os.path.join(a.out, stem + '.png'))
        size = (im.width, im.height)

        if not a.no_sides:
            for i, tag in ((0, 'picture'), (1, 'reality')):
                half = card(it, a.scale, only=i)
                half.save(os.path.join(sides_dir, f"{stem}__{tag}.png"))
                side_size = (half.width, half.height)

        caps.append(f"{'='*72}\n{stem}.png\n{'='*72}\n"
                    f"{tweet_text(it)}\n\n{citation_block(it)}\n")

    if not a.id and caps:
        open(os.path.join(a.out,'_captions.txt'),'w').write('\n'.join(caps))
    if size:
        print(f"wrote {len(items)} cards to {a.out}   {size[0]} x {size[1]}")
    if side_size:
        print(f"      {len(items)*2} half-cards in sides/   "
              f"{side_size[0]} x {side_size[1]}")


if __name__ == '__main__':
    main()
