#!/usr/bin/env python3
"""
Build a browsable page of every PAO card, grouped by pool, showing which
sections still have no card.

Lives on the Desktop beside the image folders so the relative paths work by
double-click — no server needed.

    python3 gen_pao_gallery.py
    python3 gen_pao_gallery.py --pools G50,G100,G150
"""
import argparse, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_pools as pp

DESK = os.path.expanduser('~/Desktop')
DIRS = ['pao-cards', 'pao-images/labelled']


def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def have_cards():
    """{normalised 'bandsong': [(part, relative path), ...]}"""
    out = {}
    for d in DIRS:
        full = os.path.join(DESK, d)
        if not os.path.isdir(full): continue
        for f in sorted(os.listdir(full)):
            if not f.endswith('.png') or f.endswith('.badged.png'): continue
            bits = f[:-4].split('__')
            # two filename shapes in play: pao_images writes
            # band__song__part, pao_card writes title__part
            if len(bits) >= 3:
                keys = [norm(bits[0] + bits[1]), norm(bits[1])]
                part = bits[2]
            elif len(bits) == 2:
                keys, part = [norm(bits[0])], bits[1]
            else:
                keys, part = [norm(bits[0])], ''
            for k in keys:
                out.setdefault(k, [])
                entry = (part.replace('-', ' '), f'{d}/{f}')
                if entry not in out[k]: out[k].append(entry)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--out', default=os.path.join(DESK, 'pao-gallery.html'))
    a = ap.parse_args()

    want = a.pools.split(',')
    pm = json.load(open(pp.POOLS))
    idx = pp.build_index()
    cards = have_cards()

    songs = []          # (pool, band, title, [sections], [cards])
    for slug in sorted(s for s, p in pm.items() if p in want):
        path = pp.find(slug, idx)
        band, _, title = pp.strip_tags(slug).partition('_')
        band, title = band.replace('-', ' ').title(), title.replace('-', ' ').title()
        secs = []
        if path:
            _, _, sl = pp.sections_of(path)
            seen = set()
            for name, seq in sl:
                prog = '-'.join(x or '?' for x in seq)
                if (name, prog) in seen: continue
                seen.add((name, prog)); secs.append((name, prog))
        got = cards.get(norm(band + title)) or cards.get(norm(title)) or []
        songs.append((pm[slug], band, title, secs, got))

    # dedupe songs that appear under several slugs
    uniq, seen = [], set()
    for row in songs:
        k = (row[1], row[2])
        if k in seen: continue
        seen.add(k); uniq.append(row)
    songs = uniq

    tot_sec = sum(len(s[3]) for s in songs)
    tot_card = sum(len(s[4]) for s in songs)

    E = html.escape
    P = [f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PAO cards — guitar pools</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#12121a;color:#e9e7e4}}
header{{position:sticky;top:0;z-index:10;background:#12121aee;backdrop-filter:blur(8px);
padding:16px 26px 12px;border-bottom:1px solid #26262f;display:flex;gap:14px;
align-items:baseline;flex-wrap:wrap}}
h1{{font-size:17px;font-weight:600}}
.stat{{font-size:12px;color:#6f6e7a;font-family:ui-monospace,Menlo,monospace}}
.tabs{{margin-left:auto;display:flex;gap:6px}}
.tabs button{{background:#1c1c24;border:1px solid #2e2e39;color:#b9b7c4;font:inherit;
font-size:12px;padding:6px 12px;border-radius:5px;cursor:pointer}}
.tabs button.on{{background:#5eead4;border-color:#5eead4;color:#062e29;font-weight:600}}
main{{padding:20px 26px 60px}}
.song{{margin-bottom:26px}}
.song h2{{font-size:14.5px;font-weight:600;display:inline}}
.song .band{{font-size:12px;color:#75737f;margin-left:8px}}
.song .pool{{font-size:10px;color:#5eead4;border:1px solid #2c5c52;border-radius:3px;
padding:1px 5px;margin-left:8px;vertical-align:1px}}
.grid{{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px}}
figure{{width:188px}}
figure img{{width:100%;border-radius:6px;display:block;background:#1a1a22;cursor:zoom-in}}
figcaption{{font-size:11px;color:#8b8996;margin-top:5px;line-height:1.35}}
.none{{font-size:11.5px;color:#55555f;margin-top:8px}}
.none b{{color:#7f7d8a;font-weight:500;font-family:ui-monospace,Menlo,monospace}}
dialog{{border:0;background:transparent;max-width:94vw;max-height:94vh}}
dialog img{{max-width:94vw;max-height:94vh;border-radius:8px}}
dialog::backdrop{{background:#000000dd}}
</style></head><body>
<header><h1>PAO cards</h1>
<span class="stat">{tot_card} cards &middot; {tot_sec} sections &middot; {len(songs)} songs</span>
<div class="tabs" id="tabs"></div></header><main id="main">"""]

    for pool, band, title, secs, got in songs:
        cls = 'has' if got else 'gap'
        P.append(f'<div class="song {cls}" data-pool="{E(pool)}">'
                 f'<h2>{E(title)}</h2><span class="band">{E(band)}</span>'
                 f'<span class="pool">{E(pool)}</span>')
        if got:
            P.append('<div class="grid">')
            for part, rel in got:
                P.append(f'<figure><img src="{E(rel)}" loading="lazy" alt="{E(part)}">'
                         f'<figcaption>{E(part)}</figcaption></figure>')
            P.append('</div>')
        if secs:
            missing = [f'{n} <b>{p}</b>' for n, p in secs
                       if not any(norm(n) == norm(pt) for pt, _ in got)]
            if missing:
                P.append('<div class="none">no card: ' + ' &nbsp;·&nbsp; '.join(missing) + '</div>')
        elif not got:
            P.append('<div class="none">no hookpad file</div>')
        P.append('</div>')

    P.append("""</main>
<dialog id="lb"><img id="lbimg" alt=""></dialog>
<script>
const pools = [...new Set([...document.querySelectorAll('.song')].map(s=>s.dataset.pool))];
const tabs = document.getElementById('tabs');
function show(mode){
  document.querySelectorAll('.song').forEach(s=>{
    const ok = mode==='all' ? true
             : mode==='gaps' ? s.classList.contains('gap')
             : mode==='cards' ? s.classList.contains('has')
             : s.dataset.pool===mode;
    s.style.display = ok ? '' : 'none';
  });
  [...tabs.children].forEach(b=>b.classList.toggle('on', b.dataset.m===mode));
}
[['all','All'],['cards','With cards'],['gaps','Missing'],...pools.map(p=>[p,p])]
  .forEach(([m,label])=>{
    const b=document.createElement('button'); b.textContent=label; b.dataset.m=m;
    b.onclick=()=>show(m); tabs.appendChild(b);
  });
const lb=document.getElementById('lb'), lbimg=document.getElementById('lbimg');
document.addEventListener('click',e=>{
  if(e.target.tagName==='IMG' && e.target.closest('figure')){
    lbimg.src=e.target.src; lb.showModal();
  } else if(e.target===lb || e.target===lbimg){ lb.close(); }
});
show('all');
</script></body></html>""")

    open(a.out, 'w').write('\n'.join(P))
    print(f'{tot_card} cards across {len(songs)} songs ({tot_sec} sections known)')
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
