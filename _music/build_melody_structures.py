"""Build _music/melody-structures.html from ~/Desktop/melodies_curated.xlsx.

Run after editing the xlsx to refresh the page.
"""
import os, json, re
from collections import defaultdict
from openpyxl import load_workbook

XLSX = os.path.expanduser('~/Desktop/melodies_curated.xlsx')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'melody-structures.html')


def parse_phrases(coarse, letter):
    """Return list of (width_in_bars, letter) tuples for the outer phrase blocks."""
    coarse = (coarse or '').strip()
    letter = (letter or '').strip()
    # widths from coarse_shape
    if '+' in coarse:
        widths = [int(re.match(r'\d+', s).group(0)) for s in coarse.split('+') if re.match(r'\d+', s)]
    elif coarse.isdigit():
        widths = [int(d) for d in coarse]
    else:
        # e.g. "224" — single string of digits
        m = re.match(r'(\d+)', coarse)
        if m: widths = [int(d) for d in m.group(1)]
        else: widths = []
    letters = list(re.sub(r"[^A-Za-z']", '', letter)) if letter else []
    # Pair them; if letters too short, blank-pad
    while len(letters) < len(widths): letters.append('')
    return list(zip(widths, letters))


def build():
    wb = load_workbook(XLSX)
    ws = wb['melodies']
    headers = [c.value for c in ws[1]]
    rows = [dict(zip(headers, r)) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    print(f"loaded {len(rows)} curated melody rows")

    # Group by (bars, coarse_shape, letter_shape)
    grouped = defaultdict(list)
    for r in rows:
        key = (r.get('bars') or 0, (r.get('coarse_shape') or '').strip(), (r.get('letter_shape') or '').strip())
        grouped[key].append(r)

    # Sort group keys: by bars asc, then by phrase-count asc, then by letter
    def sort_key(k):
        bars, coarse, letter = k
        phrases = len(parse_phrases(coarse, letter))
        return (bars, phrases, coarse, letter)
    keys_sorted = sorted(grouped.keys(), key=sort_key)

    sections_html = []
    for k in keys_sorted:
        bars, coarse, letter = k
        items = grouped[k]
        phrases = parse_phrases(coarse, letter)
        # heading text
        label_bits = []
        if bars: label_bits.append(f"{bars} bars")
        if coarse: label_bits.append(coarse)
        if letter: label_bits.append(letter)
        head = ' · '.join(label_bits)

        cards = []
        for r in items:
            phr = parse_phrases(r.get('coarse_shape'), r.get('letter_shape'))
            total = sum(w for w, _ in phr) or (r.get('bars') or 8)
            blocks_html = []
            for w, lt in phr:
                lt_norm = re.sub(r"['′]", '', (lt or '').upper())[:1] or '?'
                cls = f'ph-{lt_norm}' if lt_norm in ('A','B','C','D','E','F') else 'ph-X'
                # inner subdivisions if present
                inner_split = (r.get('inner_split') or '').strip()
                inner_letter = (r.get('inner_letter') or '').strip()
                inner_blocks = ''
                if inner_split and inner_split.isdigit():
                    sub_widths = [int(d) for d in inner_split]
                    sub_total = sum(sub_widths)
                    if sub_total > 0 and sub_total == w:
                        sub_letters = list(re.sub(r"[^A-Za-z']", '', inner_letter))
                        while len(sub_letters) < len(sub_widths): sub_letters.append('')
                        inner_html = []
                        for sw, sl in zip(sub_widths, sub_letters):
                            sl_show = sl if sl else ''
                            inner_html.append(f'<div class="sub" style="flex:{sw}">{sl_show}</div>')
                        inner_blocks = ''.join(inner_html)
                blocks_html.append(
                    f'<div class="ph {cls}" style="flex:{w}">'
                    f'<span class="lt">{lt or ""}</span>'
                    f'{inner_blocks}'
                    f'</div>'
                )
            blocks_str = ''.join(blocks_html)
            notes = r.get('notes') or ''
            chord = r.get('chord_shape') or ''
            hp = r.get('hookpad_url') or ''
            link_open = f'<a class="hp" href="{hp}" target="_blank" rel="noopener">HP↗</a>' if hp else ''
            extra = []
            if chord: extra.append(f'<span class="chord">{chord}</span>')
            if notes: extra.append(f'<span class="notes">{notes}</span>')
            extras_html = ' · '.join(extra)
            cards.append(
                f'<div class="card">'
                f'  <div class="meta">'
                f'    <span class="title">{r["title"]}</span>'
                f'    <span class="artist">{r["artist"]}</span>'
                f'    <span class="section">[{r["section"]}]</span>'
                f'    {link_open}'
                f'  </div>'
                f'  <div class="blocks">{blocks_str}</div>'
                f'  {f"<div class=\"sub-meta\">{extras_html}</div>" if extras_html else ""}'
                f'</div>'
            )
        cards_html = '\n'.join(cards)
        sections_html.append(
            f'<section class="group">'
            f'<h2>{head} <span class="count">{len(items)}</span></h2>'
            f'<div class="cards">{cards_html}</div>'
            f'</section>'
        )

    body = '\n'.join(sections_html)

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Melody Structures — Curated</title>
<style>
  body {{ margin:0; background:#1a1a2e; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; padding:16px 22px; }}
  a.back {{ color:#6a6a8a; text-decoration:none; font-size:13px; }}
  a.back:hover {{ color:#e0e0e0; }}
  h1 {{ font-size:18px; margin:0 0 4px; }}
  .sub {{ font-size:12px; color:#8a8ab0; margin-bottom:18px; }}
  .group {{ margin-bottom:24px; }}
  .group h2 {{ font-size:13px; color:#a5a8fc; text-transform:uppercase; letter-spacing:1.2px; margin:0 0 10px; font-weight:700; display:flex; align-items:center; gap:8px; padding:6px 12px; background:#22223e; border-left:3px solid #6366f1; border-radius:4px; }}
  .group h2 .count {{ font-size:11px; color:#a5a8fc; background:rgba(99,102,241,0.2); padding:1px 8px; border-radius:10px; font-weight:600; }}
  .cards {{ display:flex; flex-direction:column; gap:10px; }}
  .card {{ background:#16162a; border:1px solid #2a2a4a; border-radius:6px; padding:10px 14px; }}
  .meta {{ display:flex; align-items:baseline; gap:10px; margin-bottom:8px; font-size:13px; flex-wrap:wrap; }}
  .meta .title {{ font-weight:700; color:#e0e0e0; }}
  .meta .artist {{ color:#8a8ab0; font-size:12px; }}
  .meta .section {{ color:#6a6a8a; font-size:11px; }}
  .meta .hp {{ color:#a5b4fc; text-decoration:none; font-size:11px; font-weight:700; margin-left:auto; padding:2px 8px; background:rgba(99,102,241,0.15); border-radius:4px; }}
  .meta .hp:hover {{ background:rgba(99,102,241,0.3); }}
  .blocks {{ display:flex; gap:3px; height:44px; }}
  .ph {{ position:relative; display:flex; align-items:stretch; border-radius:4px; overflow:hidden; min-width:30px; }}
  .ph .lt {{ position:absolute; top:3px; left:6px; font-weight:700; font-size:13px; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,0.5); z-index:2; }}
  .ph-A {{ background:rgba(60, 120, 220, 0.85); }}
  .ph-B {{ background:rgba(220, 90, 80, 0.85); }}
  .ph-C {{ background:rgba(50, 180, 80, 0.85); }}
  .ph-D {{ background:rgba(230, 170, 40, 0.85); }}
  .ph-E {{ background:rgba(160, 80, 220, 0.85); }}
  .ph-F {{ background:rgba(220, 70, 200, 0.85); }}
  .ph-X {{ background:#3a3a5a; }}
  .sub {{ flex:1; border-left:1px dashed rgba(255,255,255,0.35); display:flex; align-items:flex-end; justify-content:center; font-size:10px; color:rgba(255,255,255,0.8); font-weight:600; padding-bottom:3px; }}
  .sub:first-child {{ border-left:none; }}
  .sub-meta {{ font-size:11px; color:#8a8ab0; margin-top:8px; display:flex; gap:14px; flex-wrap:wrap; }}
  .sub-meta .chord {{ color:#fbbf24; font-weight:600; }}
  .sub-meta .notes {{ color:#8a8ab0; font-style:italic; }}
</style>
</head>
<body>
<a href="index.html" class="back">&larr; Music</a>
<h1>Melody Structures (curated)</h1>
<div class="sub">{len(rows)} hand-picked sections grouped by bar count + phrase shape. Source: <code>~/Desktop/melodies_curated.xlsx</code></div>
{body}
</body>
</html>
'''
    with open(OUT, 'w') as f: f.write(html)
    print(f"wrote {OUT}")


if __name__ == '__main__':
    build()
