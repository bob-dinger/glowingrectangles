"""Build _music/templates.html — visual home for section templates.

Reads the same archetype lists (CHORUSES, VERSES, BRIDGES) that
build_template_pastes.py uses, so adding an archetype there shows up here.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_pastes import CHORUSES, VERSES, BRIDGES, LETTERS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'templates.html')

# Same diatonic color palette as song_viewer.js
DEG_COLORS = {
    1: '#a01e1e',  # I red
    2: '#b35610',  # ii orange
    3: '#957e0c',  # iii mustard
    4: '#25a838',  # IV green
    5: '#3050d0',  # V blue
    6: '#6e16a5',  # vi purple
    7: '#a01b6b',  # vii pink
}
ROMAN = ['I','ii','iii','IV','V','vi','vii°']


def letters_to_letters_at_level(pattern, chunk):
    """Group per-chord-event letters into chunks; assign new letter per unique chunk."""
    seq = pattern.replace(' ','')
    n = len(seq)
    if n < chunk or n % chunk: return ''
    out, seen = [], {}
    for i in range(0, n, chunk):
        c = seq[i:i+chunk]
        if c not in seen: seen[c] = chr(ord('A')+len(seen))
        out.append(seen[c])
    return ''.join(out)


def measure_boxes_html(pattern, beats_per_chord=4):
    """Render a row of colored boxes — one per measure (4 beats).
    If chord duration < 1 measure (sub-measure harmony), pack them into one box."""
    bpm = 4  # 4 beats per measure assumed
    seq = pattern.replace(' ','')
    if beats_per_chord == bpm:
        items = [(L,) for L in seq]
    else:
        chords_per_measure = bpm // beats_per_chord
        items = [tuple(seq[i:i+chords_per_measure]) for i in range(0, len(seq), chords_per_measure)]

    html = ['<div class="measures">']
    for measure_idx, chords_in_measure in enumerate(items):
        if len(chords_in_measure) == 1:
            L = chords_in_measure[0]
            deg = LETTERS[L]
            html.append(f'<div class="m" style="background:{DEG_COLORS[deg]}">'
                        f'<span class="rn">{ROMAN[deg-1]}</span></div>')
        else:
            # Sub-divided measure
            inner = ''.join(
                f'<div class="sub" style="background:{DEG_COLORS[LETTERS[L]]}">'
                f'<span class="rn-sm">{ROMAN[LETTERS[L]-1]}</span></div>'
                for L in chords_in_measure
            )
            html.append(f'<div class="m m-split">{inner}</div>')
    html.append('</div>')
    return ''.join(html)


def phrase_letters_summary(pattern, beats_per_chord=4):
    """Compute letters at 4/2/1-bar levels based on per-chord-event letters,
    treating per-chord letters as if they were per-measure."""
    bpm = 4
    chords_per_measure = bpm // beats_per_chord if beats_per_chord <= bpm else 1
    seq = pattern.replace(' ','')
    # Convert per-chord seq into per-measure seq (each measure = chunk of chords)
    if chords_per_measure > 1:
        per_measure = []
        seen = {}
        for i in range(0, len(seq), chords_per_measure):
            chunk = seq[i:i+chords_per_measure]
            if chunk not in seen: seen[chunk] = chr(ord('A')+len(seen))
            per_measure.append(seen[chunk])
        per_measure = ''.join(per_measure)
    else:
        per_measure = seq
    out = {}
    for cs in (4, 2, 1):
        n = len(per_measure)
        if n < cs or n % cs: continue
        if n // cs < 2: continue
        out[cs] = letters_to_letters_at_level(per_measure, cs)
    return out


def card_html(label, pattern_meta):
    """pattern_meta is either (label, pattern) or (label, pattern, beats_per_chord)."""
    pattern = pattern_meta[1]
    bpc = pattern_meta[2] if len(pattern_meta) > 2 else 4
    measures_html = measure_boxes_html(pattern, bpc)
    summary = phrase_letters_summary(pattern, bpc)
    summary_lines = ''.join(
        f'<div class="lvl"><span class="lvl-name">{cs}-bar</span><span class="lvl-letters">{letters}</span></div>'
        for cs, letters in summary.items()
    )
    return f'''
    <div class="card">
      <div class="card-label">{label}</div>
      {measures_html}
      <div class="summary">{summary_lines}</div>
    </div>
    '''


def section_html(title, archetypes):
    cards = ''.join(card_html(a[0], a) for a in archetypes)
    return f'''
    <section class="section">
      <h2>{title}</h2>
      <div class="cards">{cards}</div>
    </section>
    '''


HTML = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Section Templates — Glowing Gardens</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#1a1a2e; color:#e0e0e0; margin:0; padding:0; }
  .back-link { position:fixed; top:18px; left:20px; color:#6a6a8a; text-decoration:none; font-size:13px; }
  .back-link:hover { color:#e0e0e0; }
  header { padding:36px 24px 18px; text-align:center; }
  header h1 { font-size:24px; font-weight:700; margin:0 0 4px; }
  header p { font-size:13px; color:#8a8ab0; margin:0; }
  main { padding:8px 24px 48px; max-width:1400px; margin:0 auto; }
  .section { margin-bottom:36px; }
  .section h2 { font-size:14px; color:#a5a8fc; text-transform:uppercase; letter-spacing:1.5px; margin:18px 0 14px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:14px; }
  .card { background:#16162a; border:1px solid #2a2a4a; border-radius:8px; padding:14px; }
  .card-label { font-weight:700; color:#e0e0e0; margin-bottom:10px; font-size:14px; }
  .measures { display:grid; grid-template-columns:repeat(8,1fr); gap:2px; margin-bottom:10px; }
  .m { height:36px; border-radius:3px; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:11px; text-shadow:0 1px 0 rgba(0,0,0,0.6); }
  .m-split { display:flex; gap:1px; padding:0; background:transparent !important; }
  .sub { flex:1; height:36px; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:9px; }
  .sub:first-child { border-radius:3px 0 0 3px; }
  .sub:last-child { border-radius:0 3px 3px 0; }
  .summary { display:flex; flex-direction:column; gap:3px; font-size:11px; color:#8a8ab0; font-family: ui-monospace, Menlo, monospace; }
  .lvl { display:flex; gap:8px; }
  .lvl-name { width:50px; color:#6a6a8a; }
  .lvl-letters { color:#a5b4fc; font-weight:600; }
</style>
</head>
<body>
<a href="index.html" class="back-link">&larr; Music</a>
<header>
  <h1>Section Templates</h1>
  <p>Curated chorus / verse / bridge archetypes — same shapes Hookpad paste files demo</p>
</header>
<main>
__CHORUSES__
__VERSES__
__BRIDGES__
</main>
</body>
</html>
'''


def main():
    html = (HTML
            .replace('__CHORUSES__', section_html('Choruses', CHORUSES))
            .replace('__VERSES__',   section_html('Verses',   VERSES))
            .replace('__BRIDGES__',  section_html('Bridges',  BRIDGES)))
    open(OUT, 'w').write(html)
    n = len(CHORUSES) + len(VERSES) + len(BRIDGES)
    print(f"wrote {OUT}  ({n} archetypes: {len(CHORUSES)} choruses, {len(VERSES)} verses, {len(BRIDGES)} bridges)")


if __name__ == '__main__':
    main()
