"""Build _music/favorites.html — a study page of the user's 'favorite parts'.

Each part is a curated (slug, section) from parcels.melodies, shown with its
pattern, palette (degree-coloured), cadence, transforms, lyrics, key + felt tempo.
"""
import os, json, html
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2

# (display song, part label, slug, section)
FAVORITES = [
 ("Maggie May", "112", "rod-stewart_maggie-may", "verse"),
 ("Maggie May", "ABABABCC", "rod-stewart_maggie-may", "chorus"),
 ("Fire Escape", "verse", "fastball_fire-escape", "verse"),
 ("Sunny Came Home", "verse", "shawn-colvin_sunny-came-home", "verse"),
 ("Sunny Came Home", "chorus", "shawn-colvin_sunny-came-home", "chorus"),
 ("1979", "bridge", "smashing-pumpkins_1979", "bridge"),
 ("Margaritaville", "chorus", "jimmy-buffet_margaritaville", "chorus"),
 ("Nothin' but the Taillights", "verse", "clint-black_nothin-but-the-taillights_o", "verse"),
 ("Seashores of Old Mexico", "verse", "merle-haggard_seashores-of-old-mexico", "verse"),
 ("Neon Moon", "chorus", "brooks-and-dunn_neon-moon_o", "chorus"),
 ("Meant to Live", "verse", "switchfoot_meant-to-live_o", "verse"),
 ("Wonder", "chorus", "natalie-merchant_wonder_o_c_ly", "chorus"),
 ("Don't Look Back in Anger", "chorus", "oasis_don-t-look-back-in-anger", "chorus"),
 ("Nineteen", "verse", "old-97s_nineteen", "verse"),
]
COL = {1:'#ef4444',2:'#f97316',3:'#eab308',4:'#22c55e',5:'#3b82f6',6:'#a855f7',7:'#ec4899'}
def deg_chip(sd):
    s=str(sd); base=int(''.join(ch for ch in s if ch.isdigit()) or 0)
    c=COL.get(base,'#6b7280'); txt='#1a1a2e' if base in (2,3,4) else '#fff'
    return f'<span class="deg" style="background:{c};color:{txt}">{html.escape(s)}</span>'

c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432)); cur=c.cursor()
cards=[]
for song,label,slug,section in FAVORITES:
    cur.execute("""select coalesce(m.patterns,m.patterns_auto), m.palette, m.cadence, m.transforms, m.lyrics,
                          s.key_tonic,s.key_scale,s.bpm,s.bpm_canonical
                   from parcels.melodies m join parcels.songs s on s.slug=m.slug
                   where m.slug=%s and m.section=%s limit 1""",(slug,section))
    r=cur.fetchone()
    if not r:
        cards.append(f'<div class="card"><div class="ct"><b>{html.escape(song)}</b> · {html.escape(label)}</div><div class="miss">no data yet</div></div>'); continue
    patt,pal,cad,trans,lyr,kt,ks,bpm,bpmc = r
    key=f"{kt} {ks or ''}".strip()
    felt = bpmc or bpm
    tempo=f"{felt} bpm" if felt else "?"
    if bpm and bpmc and abs(float(bpmc)/float(bpm)-2)<0.2: tempo=f"{bpmc} bpm <span class='half'>(½-time {bpm} in Hookpad)</span>"
    core=' '.join(deg_chip(d) for d in (pal or {}).get('core',[])) if pal else ''
    stretch=(pal or {}).get('stretch','') if pal else ''
    if cad and 'note' in cad:                       # new flat schema: {note, closed, timing, chord_tone}
        cadstr=f"lands on {cad['note']}{'° closed' if cad.get('closed') else '_ open'}"
        for extra in ('timing','chord_tone'):
            if cad.get(extra): cadstr+=f" · {cad[extra]}"
    elif cad:                                        # old per-position schema: {pos:{note,oc}}
        cadstr=' · '.join(f"{k}:{v['note']}{'°' if v.get('oc')=='closed' else '_'}"
                          for k,v in cad.items() if isinstance(v,dict))
    else:
        cadstr=''
    ops='; '.join(f"{t['from']}→{t['to']} {'+'.join(o.split('(')[0] for o in t['ops'])}" for t in (trans or [])) if trans else ''
    lyric = html.escape((lyr or '').strip()).replace('\n','<br>')[:400]
    cards.append(f'''<div class="card">
      <div class="ct"><b>{html.escape(song)}</b> · <span class="lbl">{html.escape(label)}</span>
        <span class="meta">{html.escape(key)} · {tempo}</span></div>
      <div class="row"><span class="k">pattern</span> <code>{html.escape(patt or "—")}</code></div>
      {f'<div class="row"><span class="k">palette</span> {core} <span class="st">{html.escape(stretch)}</span></div>' if core else ''}
      {f'<div class="row"><span class="k">cadence</span> <span class="cad">{cadstr}</span></div>' if cadstr else ''}
      {f'<div class="row"><span class="k">moves</span> <span class="ops">{html.escape(ops)}</span></div>' if ops else ''}
      {f'<div class="lyr">{lyric}</div>' if lyric else ''}
    </div>''')
c.close()

PAGE=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Favorite Parts — Glowing Gardens</title><style>
 *{{box-sizing:border-box;margin:0;padding:0}}
 body{{background:#0f0f1f;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;min-height:100vh}}
 header{{padding:12px 16px;border-bottom:1px solid #2a2a4a;display:flex;align-items:center;gap:14px}}
 header h1{{font-size:16px;margin:0}} a.back{{color:#6a6a8a;text-decoration:none;font-size:13px}} a.back:hover{{color:#fff}}
 header .sub{{color:#8a8ab0;font-size:12px}}
 main{{padding:18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;max-width:1200px;margin:0 auto}}
 .card{{background:#16162a;border:1px solid #2a2a4a;border-radius:10px;padding:14px}}
 .ct{{font-size:15px;margin-bottom:10px}} .ct b{{color:#e8e8f4}} .lbl{{color:#8a8ab0;font-family:ui-monospace,monospace;font-size:13px}}
 .meta{{display:block;color:#7a7a9a;font-size:11px;margin-top:2px}} .half{{color:#f59e0b}}
 .row{{display:flex;gap:8px;align-items:baseline;margin:4px 0;font-size:13px}}
 .k{{color:#6a6a8a;font-size:11px;width:52px;flex-shrink:0;text-transform:uppercase;letter-spacing:.5px}}
 code{{background:#0f0f1f;padding:1px 6px;border-radius:4px;color:#9ab8ff;font-size:12px}}
 .deg{{display:inline-block;width:20px;height:20px;border-radius:5px;text-align:center;line-height:20px;font-weight:800;font-size:11px;font-family:ui-monospace,monospace}}
 .st{{color:#6a6a8a;font-size:11px}} .cad,.ops{{font-family:ui-monospace,monospace;font-size:12px;color:#c0c0d8}}
 .lyr{{margin-top:8px;font-size:12px;color:#8a8ab0;line-height:1.5;border-top:1px solid #22223a;padding-top:8px}}
 .miss{{color:#6a6a8a;font-size:12px}}
</style></head><body>
<header><a class="back" href="index.html">&larr; Music</a><h1>Favorite Parts</h1><span class="sub">{len(cards)} parts to write my take on · ° closed · _ open</span></header>
<main>{''.join(cards)}</main></body></html>'''
open('/Users/robert/Desktop/glowinggardens_claude/_music/favorites.html','w').write(PAGE)
print(f'wrote _music/favorites.html with {len(cards)} favorite parts')
