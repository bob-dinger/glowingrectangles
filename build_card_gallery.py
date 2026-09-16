#!/usr/bin/env python3
"""
One page for every card, so the collection is visible as it grows.

Two card families live in different folders and know nothing about each
other: the perception cards (what people think vs what is true) and the rate
cards (measured against measured). This indexes both, reads the real caption
out of the JSON rather than guessing from the filename, and writes a gallery
to the Desktop so the relative image paths work on a double-click.

    python3 build_card_gallery.py
"""
import html, json, os, glob, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DESK = os.path.expanduser('~/Desktop')
OUT  = os.path.join(DESK, 'cards.html')

SETS = [
    dict(key='perception', name='Perception gap',
         blurb='What people think, against what is true.',
         dirs=['9-11-26/sprite-cards'], src='perception-items.json'),
    dict(key='rates', name='Rates',
         blurb='Two measured facts, side by side.',
         dirs=['rate-cards'], src='suicide-items.json'),
]


def captions(path):
    """id -> a one-line description, taken from whatever the file actually has."""
    out = {}
    if not os.path.exists(path): return out
    d = json.load(open(path))
    for it in d.get('items', []):
        t = it.get('ask') or it.get('claim') or ''
        note = it.get('point') or it.get('note') or ''
        out[it['id']] = (t, note)
    return out


def main():
    cards = []
    for s in SETS:
        caps = captions(os.path.join(HERE, s['src']))
        for dd in s['dirs']:
            for p in sorted(glob.glob(os.path.join(DESK, dd, '*.png'))):
                stem = os.path.splitext(os.path.basename(p))[0]
                cid = stem.split('__')[0]
                ask, note = caps.get(cid, ('', ''))
                cards.append(dict(set=s['key'], rel=os.path.relpath(p, DESK),
                                  id=cid, ask=ask, note=note,
                                  mtime=os.path.getmtime(p)))
    cards.sort(key=lambda c: -c['mtime'])

    def esc(x): return html.escape(str(x))
    tabs = ''.join(
        f'<button data-s="{s["key"]}">{esc(s["name"])} '
        f'<i>{sum(1 for c in cards if c["set"]==s["key"])}</i></button>' for s in SETS)

    items = []
    for c in cards:
        cap = c['ask'] or c['id'].replace('-', ' ')
        sub = c['note'][:150] + ('…' if len(c['note']) > 150 else '')
        items.append(
            f'<figure data-s="{c["set"]}" data-q="{esc((cap+" "+c["id"]).lower())}">'
            f'<a href="{esc(c["rel"])}" target="_blank">'
            f'<img loading="lazy" src="{esc(c["rel"])}" alt="{esc(cap)}"></a>'
            f'<figcaption><b>{esc(cap)}</b>'
            + (f'<span>{esc(sub)}</span>' if sub else '') +
            f'</figcaption></figure>')

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cards</title><style>
*{{box-sizing:border-box}} html,body{{margin:0;background:#0b0b0d;color:#e8e8e8;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
header{{position:sticky;top:0;z-index:5;background:#0b0b0dee;backdrop-filter:blur(9px);
border-bottom:1px solid #1c1c22;padding:16px 26px 12px}}
h1{{margin:0 0 9px;font-family:Georgia,serif;font-size:21px;font-weight:normal;color:#fff}}
.bar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
button{{background:#15151a;border:1px solid #26262e;color:#a8a8b0;padding:5px 12px;
border-radius:20px;font-size:12px;cursor:pointer}}
button.on{{background:#e8e8e8;color:#111;border-color:#e8e8e8}}
button i{{font-style:normal;opacity:.55;font-size:11px;margin-left:3px}}
input{{flex:1;min-width:160px;max-width:280px;background:#15151a;border:1px solid #26262e;
color:#e8e8e8;padding:6px 11px;border-radius:20px;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
gap:20px;padding:22px 26px 60px}}
figure{{margin:0;background:#111116;border:1px solid #1c1c22;border-radius:10px;
overflow:hidden}}
figure img{{width:100%;display:block;background:#8fbc63}}
figcaption{{padding:10px 12px 12px;font-size:12px;line-height:1.45}}
figcaption b{{color:#fff;font-weight:600;display:block;margin-bottom:3px}}
figcaption span{{color:#80808a;font-size:11px;line-height:1.5}}
.none{{padding:40px 26px;color:#6a6a72;font-size:13px}}
</style></head><body>
<header>
  <h1>Cards &mdash; {len(cards)} of them</h1>
  <div class="bar">
    <button class="on" data-s="all">All <i>{len(cards)}</i></button>
    {tabs}
    <input id="q" placeholder="filter…">
  </div>
</header>
<div class="grid" id="g">{''.join(items)}</div>
<div class="none" id="none" hidden>nothing matches.</div>
<script>
const figs=[...document.querySelectorAll('figure')];
let set='all', q='';
function apply(){{
  let n=0;
  figs.forEach(f=>{{
    const ok=(set==='all'||f.dataset.s===set)&&(!q||f.dataset.q.includes(q));
    f.hidden=!ok; if(ok)n++;
  }});
  document.getElementById('none').hidden=n>0;
}}
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
  document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); set=b.dataset.s; apply();
}});
document.getElementById('q').oninput=e=>{{q=e.target.value.toLowerCase().trim();apply();}};
</script></body></html>"""
    open(OUT, 'w').write(doc)
    print(f'{len(cards)} cards -> {OUT}')
    for s in SETS:
        print(f"   {s['name']:<18} {sum(1 for c in cards if c['set']==s['key'])}")


if __name__ == '__main__':
    main()
