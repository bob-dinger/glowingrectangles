#!/usr/bin/env python3
"""The section-seam data as a coloured workbook on the Desktop.

Chord fills are the project's degree colours (music_chord_colors):
  C red, Dm orange, Em yellow, F green, G blue, Am purple -- with dark text on
  the light three, per chord-groups.html. Section roles get their own muted
  palette so they never compete with a chord colour.
"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

DEG = {'C':'E84545','Dm':'F0A040','Em':'E8C828','F':'50C878','G':'5090F0','Am':'7040B0'}
DARK = {'Dm','Em','F'}                      # light fills want dark text
ROLE = {'verse':'DCE6F1','pre-chorus':'FDE9D9','chorus':'F2DCDB','bridge':'EBF1DE'}

KEEP = ['pre-chorus','chorus','verse','bridge']

def role(s):
    s = s.lower().strip()
    s = re.sub(r'\b(i{1,3}|iv|v|\d+|first|second|third|final|last|half|alt)\b','',s)
    s = s.replace('prechorus','pre-chorus').replace('pre chorus','pre-chorus')
    for k in KEEP:
        if k in s: return k
    return None

def lab(run, d):
    return corpus.chord_name(run[0], corpus.mode_at(d, run[1]))

inst = []
for name, d, nb in corpus.songs():
    secs = [(role(s), corpus.merged([c for c in d['chords'] if st<=c['beat']<en]))
            for s, st, en in corpus.sections(d)]
    for (r1,a),(r2,b) in zip(secs, secs[1:]):
        if not r1 or not r2 or not a or not b: continue
        artist,_,title = name.partition('_')
        inst.append([artist.title(), title.title(), r1, r2, lab(a[-1], d), lab(b[0], d), name])

def paint(ws, cell, val, kind):
    base = val.rstrip('*')
    if kind == 'chord' and base in DEG:
        cell.fill = PatternFill('solid', fgColor=DEG[base])
        cell.font = Font(bold=True, color='1A1A2E' if base in DARK else 'FFFFFF')
    elif kind == 'role' and val in ROLE:
        cell.fill = PatternFill('solid', fgColor=ROLE[val])
    cell.alignment = Alignment(horizontal='center')

wb = Workbook()

# --- 1: summary, one row per seam type + chord move
ws = wb.active; ws.title = 'Seams'
cols = [('From section',14),('To section',14),('From chord',12),('To chord',11),
        ('Songs',8),('Share',8)]
ws.append([c for c,_ in cols])
for i,(_,w) in enumerate(cols,1): ws.column_dimensions[get_column_letter(i)].width = w
for c in ws[1]: c.font = Font(bold=True)
ws.freeze_panes = 'A2'
agg = collections.Counter((r[2],r[3],r[4],r[5]) for r in inst)
tot = sum(agg.values())
for (r1,r2,c1,c2), n in agg.most_common():
    ws.append([r1,r2,c1,c2,n,n/tot])
    row = ws.max_row
    paint(ws, ws.cell(row,1), r1, 'role');  paint(ws, ws.cell(row,2), r2, 'role')
    paint(ws, ws.cell(row,3), c1, 'chord'); paint(ws, ws.cell(row,4), c2, 'chord')
    ws.cell(row,6).number_format = '0.0%'

# --- 2: every instance, with the song
ws2 = wb.create_sheet('By song')
cols = [('Artist',24),('Song',38),('From section',14),('To section',14),
        ('From chord',12),('To chord',11),('Hookpad file',40)]
ws2.append([c for c,_ in cols])
for i,(_,w) in enumerate(cols,1): ws2.column_dimensions[get_column_letter(i)].width = w
for c in ws2[1]: c.font = Font(bold=True)
ws2.freeze_panes = 'A2'
for r in sorted(inst, key=lambda r:(r[0],r[1])):
    ws2.append(r); row = ws2.max_row
    paint(ws2, ws2.cell(row,3), r[2], 'role');  paint(ws2, ws2.cell(row,4), r[3], 'role')
    paint(ws2, ws2.cell(row,5), r[4], 'chord'); paint(ws2, ws2.cell(row,6), r[5], 'chord')

# --- 3: the 30-cell chord matrix
ws3 = wb.create_sheet('Chord moves')
ORDER = ['C','Dm','Em','F','G','Am']
mv = collections.Counter()
for name, d, nb in corpus.songs():
    for s, st, en in corpus.sections(d):
        seq = []
        for c, b, _ in corpus.merged([c for c in d['chords'] if st<=c['beat']<en]):
            n = corpus.chord_name(c, corpus.mode_at(d, b))
            seq.append(None if '*' in n else n)
        for a,b in zip(seq, seq[1:]):
            if a and b and a != b: mv[(a,b)] += 1
# a list reads better than a matrix: you can sort it, and the 30 rows fit on
# one screen with the share and a running cumulative
tot_mv = sum(mv.values())
cols = [('From', 9), ('To', 9), ('Moves', 9), ('Share', 9), ('Cumulative', 12)]
ws3.append([c for c, _ in cols])
for i, (_, w) in enumerate(cols, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w
for c in ws3[1]:
    c.font = Font(bold=True)
ws3.freeze_panes = 'A2'
run = 0
for (a, b), n in mv.most_common():
    run += n
    ws3.append([a, b, n, n / tot_mv, run / tot_mv])
    row = ws3.max_row
    paint(ws3, ws3.cell(row, 1), a, 'chord')
    paint(ws3, ws3.cell(row, 2), b, 'chord')
    ws3.cell(row, 4).number_format = '0.0%'
    ws3.cell(row, 5).number_format = '0.0%'

out = os.path.expanduser('~/Desktop/section_seams.xlsx')
wb.save(out)
print(f"  {len(inst):,} seam instances, {len(agg)} distinct combinations")
print(f"  {out}")
