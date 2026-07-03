"""Build _music/strum-library.html — a browsable palette of strum patterns.

Each pattern (from strum_library.json) is drawn as arrows on a beat ruler, with
its notation and a click-to-copy Hookpad paste-JSON (the strum over 2 bars of I,
empty notes + re-struck chords). See strum.py / music_chord_riff_fingerprint.
"""
import os, json, html
import strum

ARROW = {'D': '↓', 'U': '↑', 'x': '×', '.': ''}
CLS   = {'D': 'd', 'U': 'u', 'x': 'm', '.': 'o'}

def draw(pattern):
    beats = []
    for bi, cell in enumerate(pattern.split()):
        slots = ''.join(
            f'<span class="s {CLS[c]}">{ARROW[c]}</span>' for c in cell)
        sub = {1:'', 2:'8th', 3:'trip', 4:'16th'}.get(len(cell), '')
        beats.append(f'<div class="beat"><div class="slots">{slots}</div>'
                     f'<div class="bn">{bi+1}<span class="sub">{sub}</span></div></div>')
    return '<div class="ruler">' + ''.join(beats) + '</div>'

lib = strum.load_lib()
cards = []
for name, pat in lib.items():
    js = strum.paste(strum.encode(pat, [1, 1]))          # 2 bars of I, chord-agnostic strum
    cards.append(f'''<div class="card">
      <div class="nm">{html.escape(name)}</div>
      {draw(pat)}
      <div class="foot"><code>{html.escape(pat)}</code>
        <button class="cp" data-j='{html.escape(js)}'>copy paste-JSON</button></div>
    </div>''')

PAGE = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strum Library — Glowing Gardens</title><style>
 *{{box-sizing:border-box;margin:0;padding:0}}
 body{{background:#0f0f1f;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;min-height:100vh}}
 header{{padding:12px 16px;border-bottom:1px solid #2a2a4a;display:flex;align-items:baseline;gap:14px}}
 header h1{{font-size:16px}} a.back{{color:#6a6a8a;text-decoration:none;font-size:13px}} a.back:hover{{color:#fff}}
 header .sub{{color:#8a8ab0;font-size:12px}}
 header .legend{{margin-left:auto;font-size:12px;color:#8a8ab0;display:flex;gap:12px}}
 .legend b.d{{color:#22c55e}} .legend b.u{{color:#3b82f6}} .legend b.m{{color:#9a9ab0}}
 main{{padding:18px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;max-width:1200px;margin:0 auto}}
 .card{{background:#16162a;border:1px solid #2a2a4a;border-radius:10px;padding:14px}}
 .nm{{font-family:ui-monospace,monospace;font-size:14px;color:#e8e8f4;margin-bottom:12px}}
 .ruler{{display:flex;gap:6px;align-items:stretch}}
 .beat{{flex:1;border-left:1px solid #2a2a4a;padding:0 4px}}
 .beat:first-child{{border-left:none}}
 .slots{{display:flex;justify-content:space-around;height:34px;align-items:center}}
 .s{{font-size:20px;font-weight:800;line-height:1;min-width:8px;text-align:center}}
 .s.d{{color:#22c55e}} .s.u{{color:#3b82f6}} .s.m{{color:#9a9ab0}} .s.o{{color:#2a2a4a}}
 .bn{{text-align:center;color:#6a6a8a;font-size:12px;border-top:1px solid #2a2a4a;padding-top:3px;margin-top:2px}}
 .sub{{display:block;color:#f59e0b;font-size:9px;text-transform:uppercase;letter-spacing:.5px}}
 .foot{{display:flex;align-items:center;gap:8px;margin-top:12px}}
 code{{background:#0f0f1f;padding:2px 7px;border-radius:4px;color:#9ab8ff;font-size:12px;flex:1;font-family:ui-monospace,monospace}}
 .cp{{background:#22224a;border:1px solid #3a3a5a;color:#c0c0e0;font-size:11px;padding:4px 8px;border-radius:5px;cursor:pointer;white-space:nowrap}}
 .cp:hover{{background:#2e2e5a;color:#fff}} .cp.ok{{background:#166534;color:#fff;border-color:#22c55e}}
</style></head><body>
<header><a class="back" href="index.html">&larr; Music</a><h1>Strum Library</h1>
 <span class="sub">{len(cards)} patterns · re-struck chords in Hookpad (empty notes)</span>
 <span class="legend"><span><b class="d">↓</b> down</span><span><b class="u">↑</b> up</span><span><b class="m">×</b> mute</span></span>
</header>
<main>{''.join(cards)}</main>
<script>
document.querySelectorAll('.cp').forEach(b=>b.addEventListener('click',async()=>{{
  await navigator.clipboard.writeText(b.dataset.j);
  const t=b.textContent; b.textContent='copied ✓'; b.classList.add('ok');
  setTimeout(()=>{{b.textContent=t;b.classList.remove('ok')}},1200);
}}));
</script></body></html>'''

out = '/Users/robert/Desktop/glowinggardens_claude/_music/strum-library.html'
open(out, 'w').write(PAGE)
print(f'wrote {out} with {len(cards)} patterns')
