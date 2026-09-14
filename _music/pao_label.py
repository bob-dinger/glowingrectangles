#!/usr/bin/env python3
"""
Add a caption band under each generated PAO image.

Done AFTER generation, not in the prompt: image models render text as garbled
pseudo-letters, and a card whose caption is nonsense is worse than no caption.
Composited with PIL it is perfectly crisp.

Originals are left untouched; labelled copies go to <out>/labelled/.

    python3 pao_label.py
    python3 pao_label.py --no-progression      # hide the answer, flashcard style
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_images as pi
from PIL import Image, ImageDraw, ImageFont

AVENIR = '/System/Library/Fonts/Avenir Next.ttc'
MENLO  = '/System/Library/Fonts/Menlo.ttc'
BOLD, DEMI, MEDIUM = 0, 2, 5

INK, MUTED, ACCENT = (34, 32, 28), (132, 128, 118), (176, 74, 44)
BAND = (243, 240, 232)


def font(path, px, idx=0):
    try: return ImageFont.truetype(path, px, index=idx)
    except Exception: return ImageFont.load_default()


def wrap(d, text, f, maxw):
    out, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out or ['']


def label(src, dst, song, part, scene, prog, show_prog=True, context=None,
          picture=None):
    im = Image.open(src).convert('RGB')
    W = im.width
    pad = round(W * 0.045)

    f_hd = font(AVENIR, round(W * 0.026), DEMI)     # song — part
    f_sc = font(AVENIR, round(W * 0.040), BOLD)     # the scene
    f_pg = font(MENLO,  round(W * 0.030))           # the phrase in the picture
    f_cx = font(MENLO,  round(W * 0.021))           # the whole section, for context

    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines = wrap(probe, scene, f_sc, W - pad * 2)
    # the full section can be sixteen bars, so it has to wrap rather than run
    # off the edge — it is context, not the headline
    ctx = wrap(probe, context, f_cx, W - pad * 2) if context else []
    # the normalised names the PICTURE encodes, kept small: the scene was
    # built from degrees, so without this line a reader cannot check that
    # "a judge" really is the D they are being told to play
    pic = wrap(probe, picture, f_cx, W - pad*2) if picture else []
    h = pad + round(W*0.030) + round(W*0.014)
    h += len(lines) * round(W*0.050)
    if show_prog: h += round(W*0.046)
    h += (len(ctx) + len(pic)) * round(W*0.030)
    h += pad

    out = Image.new('RGB', (W, im.height + h), BAND)
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.line([(0, im.height), (W, im.height)], fill=(214, 208, 195), width=2)

    y = im.height + pad
    d.text((pad, y), f'{song}  ·  {part}'.upper(), font=f_hd, fill=MUTED)
    y += round(W*0.030) + round(W*0.014)
    for ln in lines:
        d.text((pad, y), ln, font=f_sc, fill=INK)
        y += round(W*0.050)
    if show_prog:
        d.text((pad, y), prog, font=f_pg, fill=ACCENT)
        y += round(W*0.046)
    for ln in ctx:
        d.text((pad, y), ln, font=f_cx, fill=(150, 144, 132))
        y += round(W*0.030)
    for ln in pic:
        d.text((pad, y), ln, font=f_cx, fill=(186, 180, 168))
        y += round(W*0.030)
    out.save(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.expanduser('~/Desktop/pao-images'))
    ap.add_argument('--pools', default='G50')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--no-progression', action='store_true')
    a = ap.parse_args()

    # same seed reproduces the same scenes, so captions match the pictures
    rows = {r['name']: r for r in pi.collect(set(a.pools.split(',')), a.seed)}
    outdir = os.path.join(a.dir, 'labelled')
    os.makedirs(outdir, exist_ok=True)

    n = 0
    for name in sorted(os.listdir(a.dir)):
        if not name.endswith('.png'): continue
        r = rows.get(name)
        if not r:
            print(f'  no caption data for {name} (seed mismatch?)'); continue
        label(os.path.join(a.dir, name), os.path.join(outdir, name),
              r['song'], r['part'], r['scene'], r['prog'],
              show_prog=not a.no_progression)
        n += 1
    print(f'labelled {n} -> {outdir}')


if __name__ == '__main__':
    main()
