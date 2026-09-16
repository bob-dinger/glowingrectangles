"""Build beatles_by_project.html — 12 recording-project sections with UG-linked songs.

Reads ~/Desktop/beatles_by_project.csv (made by scraping icce.rug.nl + UG lookup).
"""
import csv, os, html

CSV_IN  = '/Users/robert/Desktop/beatles_by_project.csv'
OUT     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beatles_by_project.html')

rows = list(csv.DictReader(open(CSV_IN)))

# Group by project
projects = {}
for r in rows:
    key = (int(r['project_num']), r['project_name'], r['project_period'])
    projects.setdefault(key, []).append(r)

n_total = len(rows)
n_official = sum(1 for r in rows if r.get('ug_kind') == 'official')
n_any = sum(1 for r in rows if r.get('ug_url'))


def badge(kind):
    colors = {'official':'#25a838', 'chords':'#3a9c9c', 'tabs':'#b35610', 'guitar-pro':'#6e16a5', 'other':'#44446a'}
    if not kind: return ''
    return f'<span class="kind kind-{kind}" style="background:{colors.get(kind,"#44446a")}">{kind}</span>'


def song_row(r):
    title_html = html.escape(r['title'])
    if r.get('ug_url'):
        title_html = f'<a href="{html.escape(r["ug_url"])}" target="_blank">{title_html}</a>'
    cover_cls = ' cover' if r.get('is_cover') == 'True' else ''
    return f'''<tr class="song{cover_cls}">
        <td class="code">{html.escape(r["code"])}</td>
        <td class="date">{html.escape(r["date"])}</td>
        <td class="title">{title_html}</td>
        <td class="kind-cell">{badge(r.get("ug_kind"))}</td>
    </tr>'''


sidebar_items = ''.join(
    f'<a class="proj-link" href="#proj-{n}"><span class="pn">{n}</span> {html.escape(name)}</a>'
    for (n, name, _) in projects.keys()
)

project_sections = ''
for (n, name, period), songs in projects.items():
    n_off = sum(1 for s in songs if s.get('ug_kind') == 'official')
    project_sections += f'''<div class="project" id="proj-{n}">
        <div class="proj-header">
            <span class="proj-num">{n}</span>
            <span class="proj-name">{html.escape(name)}</span>
            <span class="proj-period">{html.escape(period)}</span>
            <span class="proj-count">{len(songs)} songs · {n_off} UG official</span>
        </div>
        <table class="songs">
            <thead><tr><th>code</th><th>date</th><th>title</th><th>UG</th></tr></thead>
            <tbody>{"".join(song_row(s) for s in songs)}</tbody>
        </table>
    </div>'''

HTML = f'''<!doctype html>
<html><head><meta charset="utf-8">
<title>Beatles by Recording Project</title>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }}
.layout {{ display: flex; min-height: 100vh; }}

.sidebar {{
  width: 220px; min-width: 220px; background: #0f0f1f;
  border-right: 1px solid #2a2a4a; padding: 14px;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}}
.sidebar h2 {{ font-size: 11px; color: #6a6a8a; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 10px; }}
.sidebar .stats {{ font-size: 11px; color: #8a8ab0; margin-bottom: 14px; line-height: 1.6; }}
.sidebar .stats b {{ color: #e0e0e0; }}
.proj-link {{
  display: block; padding: 5px 8px; color: #b0b0cc; text-decoration: none; font-size: 12px;
  border-left: 3px solid transparent; border-radius: 0 3px 3px 0; margin-bottom: 2px;
}}
.proj-link:hover {{ background: #1e1e3a; color: #e0e0e0; border-left-color: #6366f1; }}
.proj-link .pn {{
  display: inline-block; width: 22px; height: 18px; background: #2a2a4a; color: #e0e0e0;
  border-radius: 3px; text-align: center; font-weight: 700; font-size: 11px; margin-right: 6px;
}}

.main {{ flex: 1; padding: 14px 22px; }}
.main h1 {{ font-size: 20px; margin: 0 0 4px; }}
.main .subtitle {{ font-size: 12px; color: #8a8ab0; margin-bottom: 18px; }}

.project {{ margin-bottom: 28px; }}
.proj-header {{
  display: flex; align-items: baseline; gap: 12px; padding: 8px 14px;
  background: #16162a; border-radius: 5px 5px 0 0; border: 1px solid #2a2a4a; border-bottom: none;
}}
.proj-header .proj-num {{
  background: #6366f1; color: white; padding: 2px 10px; border-radius: 11px;
  font-weight: 700; font-size: 12px;
}}
.proj-header .proj-name {{ font-weight: 700; font-size: 15px; color: #e0e0e0; }}
.proj-header .proj-period {{ font-size: 11px; color: #8a8ab0; }}
.proj-header .proj-count {{ margin-left: auto; font-size: 11px; color: #b0b0cc; }}

table.songs {{
  width: 100%; border-collapse: collapse; background: #20203a;
  border: 1px solid #2a2a4a; border-radius: 0 0 5px 5px;
}}
table.songs th {{
  text-align: left; padding: 6px 10px; background: #1e1e3a; color: #6a6a8a;
  font-size: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;
  border-bottom: 1px solid #2a2a4a;
}}
table.songs td {{ padding: 6px 10px; border-bottom: 1px solid rgba(42,42,74,0.4); font-size: 13px; }}
table.songs tr:last-child td {{ border-bottom: none; }}
table.songs tr.song:hover {{ background: #1e1e3a; }}
table.songs tr.cover .title {{ color: #8a8ab0; font-style: italic; }}
table.songs td.code {{ color: #6a6a8a; font-family: monospace; font-size: 11px; width: 50px; }}
table.songs td.date {{ color: #8a8ab0; font-family: monospace; font-size: 11px; width: 80px; }}
table.songs td.title a {{ color: #e0e0e0; text-decoration: none; font-weight: 500; }}
table.songs td.title a:hover {{ color: #6366f1; text-decoration: underline; }}
table.songs td.kind-cell {{ width: 80px; }}

.kind {{
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 10px; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.5px;
}}
</style>
</head><body>
<div class="layout">
  <aside class="sidebar">
    <div class="stats">
      <b>{n_total}</b> songs total<br>
      <b>{n_official}</b> with UG official<br>
      <b>{n_any}</b> with any UG link
    </div>
    <h2>projects</h2>
    {sidebar_items}
  </aside>
  <main class="main">
    <h1>The Beatles · by Recording Project</h1>
    <div class="subtitle">All 224 officially recorded songs, grouped by Tuomas Eerola's 12-project chronology. Click a title to open its Ultimate Guitar tab.</div>
    {project_sections}
  </main>
</div>
</body></html>'''

open(OUT, 'w').write(HTML)
print(f'wrote {OUT}')
print(f'  {n_total} songs, {n_official} official UG, {n_any} any UG')
