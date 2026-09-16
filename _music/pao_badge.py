#!/usr/bin/env python3
"""
Stamp a short structural note onto an existing card — "x3", "last 2 home",
whatever the repeat scheme is.

Works on already-composited cards, so nothing has to be regenerated. The badge
sits in a corner of the ARTWORK (not the caption band), because there is no way
to know where in the frame a given object ended up.

    pao_badge.py nashville-blues__verse.png --badge "x3 + last two"
    pao_badge.py maggie-may__chorus.png --badge "x3, then home" --corner tl
"""
import argparse, os, sys
from PIL import Image, ImageDraw, ImageFont

AVENIR = '/System/Library/Fonts/Avenir Next.ttc'
DEMI, BOLD = 2, 0
CARDS = os.path.expanduser('~/Desktop/pao-cards')


def font(px, idx=DEMI):
    try: return ImageFont.truetype(AVENIR, px, index=idx)
    except Exception: return ImageFont.load_default()


def stamp(path, text, corner='tr', out=None):
    im = Image.open(path).convert('RGB')
    W = im.width
    # the artwork is square; anything below that is the caption band
    art_h = min(W, im.height)

    f = font(round(W * 0.042), BOLD)
    pad_x, pad_y = round(W * 0.026), round(W * 0.016)
    d0 = ImageDraw.Draw(im)
    tw = d0.textlength(text, font=f)
    bw, bh = tw + pad_x * 2, round(W * 0.042) + pad_y * 2
    m = round(W * 0.030)

    x = m if corner in ('tl', 'bl') else W - bw - m
    y = m if corner in ('tl', 'tr') else art_h - bh - m

    chip = Image.new('RGBA', (int(bw), int(bh)), (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle(
        [0, 0, bw - 1, bh - 1], radius=bh / 2, fill=(28, 26, 22, 224))
    im.paste(chip, (int(x), int(y)), chip)
    ImageDraw.Draw(im).text((x + pad_x, y + pad_y - round(W * 0.004)),
                            text, font=f, fill=(247, 244, 236))

    im.save(out or path)
    return out or path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('card')
    ap.add_argument('--badge', required=True)
    ap.add_argument('--corner', default='tr', choices=['tl', 'tr', 'bl', 'br'])
    ap.add_argument('--inplace', action='store_true')
    a = ap.parse_args()

    p = a.card if os.path.exists(a.card) else os.path.join(CARDS, a.card)
    if not os.path.exists(p):
        sys.exit(f'no such card: {a.card}')
    out = None if a.inplace else p.replace('.png', '.badged.png')
    print('->', stamp(p, a.badge, a.corner, out))


if __name__ == '__main__':
    main()
