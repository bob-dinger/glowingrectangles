#!/usr/bin/env python3
"""One tile per song: chord palette as colour, melody rhythm as marks, tempo as size.

A clock face for the song's main section. The ring is one bar. Coloured arcs
are the chords in their degree colours (music_chord_colors); dots on the rim are
melody onsets in sixteenths; the tile's ring weight follows tempo, so fast songs
read tight and slow ones open.
"""
import sys, os, json, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

DEG = {'C':'#E84545','Dm':'#F0A040','Em':'#E8C828','F':'#50C878','G':'#5090F0',
       'Am':'#7040B0','Bdim':'#888'}
rows = json.load(open(os.path.expanduser('~/Desktop/melody_map.json')))
want = {}
for r in rows:                       # one section per song: prefer the chorus
    k = r['file']
    if k not in want or (r['role'] == 'chorus' and want[k]['role'] != 'chorus'):
        want[k] = r

tiles = []
for name, d, nb in corpus.songs():
    m = want.get(name)
    if not m or nb != 4: continue
    st = None
    for sec, s0, s1 in corpus.sections(d):
        if sec == m['section']: st, en = s0, s1; break
    if st is None: continue
    runs = corpus.merged([c for c in d['chords'] if st <= c['beat'] < en])
    if not runs: continue
    # THE UNIT IS TWO BARS. Drawing a whole 8-16 bar section put sixteen arcs
    # on a ring and every song came out the same confetti. A part is a 2-bar
    # cell repeated; 4-bar cells are mostly that cell doubled. So find the
    # 2-bar window the section spends most of its time in and draw only that.
    W = nb * 2
    span_all = max(b + dur for _, b, dur in runs) - st
    cells = collections.Counter()
    for w in range(max(1, int(span_all // W))):
        w0 = st + w * W
        cell = tuple((round((b - w0) * 2), round(dur * 2),
                      corpus.chord_name(c, corpus.mode_at(d, b)).rstrip('*'))
                     for c, b, dur in runs if -1e-6 <= b - w0 < W)
        if cell: cells[cell] += 1
    if not cells: continue
    cell = cells.most_common(1)[0][0]
    bars = 2
    arcs = [{'a': o / (W * 2), 'w': min(dd, W * 2 - o) / (W * 2),
             'c': DEG.get(nm, '#555')} for o, dd, nm in cell]
    w0 = st
    for w in range(max(1, int(span_all // W))):
        t = st + w * W
        c2 = tuple((round((b - t) * 2), round(dur * 2),
                    corpus.chord_name(c, corpus.mode_at(d, b)).rstrip('*'))
                   for c, b, dur in runs if -1e-6 <= b - t < W)
        if c2 == cell: w0 = t; break
    notes = [x for x in (d.get('notes') or [])
             if w0 <= x['beat'] < w0 + W and not x.get('isRest')]
    onsets = sorted({round((x['beat'] - w0) / W * 32) for x in notes})
    tiles.append({'song': m['song'], 'artist': m['artist'], 'bpm': m['bpm'],
                  'role': m['role'], 'bars': bars, 'arcs': arcs,
                  'onsets': onsets, 'group': m['group']})

tiles.sort(key=lambda t: (t['bpm'], t['artist']))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sigils.html'), 'w').write(
"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Song Sigils</title>
<style>
body{margin:0;background:#101018;color:#e8e8f0;font:12px/1.4 -apple-system,BlinkMacSystemFont,sans-serif}
header{padding:14px 20px 6px}
h1{font-size:16px;margin:0 0 3px}.sub{color:#7b7b90;font-size:12px;margin:0}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:4px;padding:10px 16px 24px}
.t{text-align:center;padding:5px 2px;border-radius:7px}
.t:hover{background:#1b1b26}
.nm{font-size:10px;color:#c8c8d8;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ar{font-size:9px;color:#6a6a80;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bp{font-size:9px;color:#FF3D9A}
</style></head><body>
<header><h1>Song Sigils</h1><p class="sub">One ring per song &mdash; arcs are the chords in degree
colour, dots are melody onsets, ring weight follows tempo. One 2-BAR CELL per song. Sorted slow to fast.</p></header>
<div id="grid"></div><script>
const T = """ + json.dumps(tiles) + """;
const g = document.getElementById('grid');
T.forEach(t=>{
  const S=96, R=34, cx=S/2, cy=S/2;
  const w = 5 + Math.max(0, Math.min(9, (180-t.bpm)/12));   // slow = thick ring
  let s=`<svg width="${S}" height="${S}">`;
  t.arcs.forEach(a=>{
    const a0=a.a*2*Math.PI-Math.PI/2, a1=(a.a+a.w)*2*Math.PI-Math.PI/2;
    const x0=cx+R*Math.cos(a0), y0=cy+R*Math.sin(a0);
    const x1=cx+R*Math.cos(a1), y1=cy+R*Math.sin(a1);
    const big=a.w>0.5?1:0;
    s+=`<path d="M${x0} ${y0} A${R} ${R} 0 ${big} 1 ${x1} ${y1}" stroke="${a.c}"
        stroke-width="${w}" fill="none" stroke-linecap="butt" opacity=".9"/>`;
  });
  t.onsets.forEach(o=>{
    const an=o/32*2*Math.PI-Math.PI/2, rr=R-w/2-4;
    s+=`<circle cx="${cx+rr*Math.cos(an)}" cy="${cy+rr*Math.sin(an)}" r="1.7" fill="#fff" opacity=".85"/>`;
  });
  s+='</svg>';
  const d=document.createElement('div'); d.className='t';
  d.innerHTML=s+`<div class="nm">${t.song}</div><div class="ar">${t.artist}</div>
                 <div class="bp">${t.bpm}</div>`;
  d.title=`${t.artist} — ${t.song}\\n${t.role}, ${t.bars} bars, ${t.bpm}bpm, ${t.group}`;
  g.appendChild(d);
});
</script></body></html>""")
print(f"  {len(tiles)} sigils -> _music/sigils.html")
