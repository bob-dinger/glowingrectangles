"""An xlsx worklist of every lyric-annotated section, graded, for cleaning up.

One row per annotated section. The point is triage: `off` rows are where the value
is (most are boundary spill, not bad annotation), and `exact` rows with a rhyme
scheme are ready to build on.

Columns: what it is, how far off, and what markers it already carries.

    themap_venv/python lyrics_worklist.py        # -> ~/Desktop/lyrics_worklist.xlsx
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from parse_lyrics import parse_song, grade
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

OUT = os.path.expanduser('~/Desktop/lyrics_worklist.xlsx')
HEAD = ['song', 'section', 'idx', 'syllables', 'notes', 'diff', 'off by %', 'band',
        'why', 'suggested fix', 'lines', 'rhyme scheme', 'rhymes', 'melisma',
        'notation', 'song grade', 'song flags', 'first line']
BAND_FILL = {'exact': 'C6E7C6', '<=5%': 'DDEEDD', '<=10%': 'FFF3CC',
             '<=25%': 'FFE0B2', 'off': 'F4CCCC'}

def band(s, n):
    if s == n: return 'exact'
    e = abs(s - n) / max(n, 1)
    return '<=5%' if e <= .05 else '<=10%' if e <= .10 else '<=25%' if e <= .25 else 'off'

def spill_moves(rows):
    """{live-list position: (text, gain)} for every move that provably reduces error.
    Keyed by position, not name, because section names repeat ("verse", "verse")."""
    live = [r for r in rows if r['notes']]
    found = {}
    for i in range(len(live) - 1):
        a, b = live[i], live[i+1]
        base = abs(a['syllables']-a['notes']) + abs(b['syllables']-b['notes'])
        if len(b['lines']) > 1:
            k = len(b['lines'][0]['syllables'])
            after = abs(a['syllables']+k-a['notes']) + abs(b['syllables']-k-b['notes'])
            if after < base:
                txt = ' '.join(b['lines'][0]['syllables'])[:44]
                found[i]   = (f'pull up from next: "{txt}"', base-after)
                found[i+1] = (f'push its 1st line up: "{txt}"', base-after)
                continue
        if len(a['lines']) > 1:
            k = len(a['lines'][-1]['syllables'])
            after = abs(a['syllables']-k-a['notes']) + abs(b['syllables']+k-b['notes'])
            if after < base:
                txt = ' '.join(a['lines'][-1]['syllables'])[:44]
                found[i]   = (f'push its last line down: "{txt}"', base-after)
                found[i+1] = (f'pull down from previous: "{txt}"', base-after)
    return found

def why(r, s, n, spillable):
    """Why this section does not line up — the category that tells you the work."""
    if abs(s-n)/max(n, 1) <= .25: return ''
    if r['index'] is None:        return 'unsectioned blob'
    if len(r['lines']) == 1:      return 'only one line typed'
    if spillable:                 return 'boundary spill'
    if s < n*0.5:                 return 'covers under half the notes'
    if s > n*1.25:                return 'more syllables than notes'
    return 'short, but not by a whole line'

def rows():
    for name, d, nb in corpus.songs(need_chords=False):
        sec_rows, flags = parse_song(d)
        if not sec_rows: continue
        g = grade(sec_rows, flags)
        moves = spill_moves(sec_rows)
        live_pos = {id(r): i for i, r in enumerate([x for x in sec_rows if x['notes']])}
        for r in sec_rows:
            if not r['notes']: continue
            s, n = r['syllables'], r['notes']
            pos = live_pos[id(r)]
            fix = moves.get(pos)
            nr = sum(1 for l in r['lines'] if l['rhyme'])
            nm = sum(len(l.get('melisma') or []) for l in r['lines'])
            nota = next((l['notation'] for l in r['lines'] if l['notation']), '')
            first = ' '.join(r['lines'][0]['syllables'])[:70] if r['lines'] else ''
            yield [name, r['name'], r['index'], s, n, s - n,
                   round(100*abs(s-n)/max(n,1), 1), band(s, n),
                   why(r, s, n, fix is not None), fix[0] if fix else '',
                   len(r['lines']), r['scheme'], nr, nm, nota or '', g,
                   ' '.join(flags), first]

def main():
    data = list(rows())
    order = {'exact': 0, '<=5%': 1, '<=10%': 2, '<=25%': 3, 'off': 4}
    # ready-to-use first, then near misses; inside "off", the mechanical fixes first
    fixfirst = {'boundary spill': 0, 'unsectioned blob': 1,
                'short, but not by a whole line': 2, 'more syllables than notes': 3,
                'covers under half the notes': 4, 'only one line typed': 5, '': 0}
    data.sort(key=lambda r: (order[r[7]], fixfirst.get(r[8], 9), -r[12], r[0]))

    wb = Workbook(); ws = wb.active; ws.title = 'sections'
    ws.append(HEAD)
    for c in ws[1]:
        c.font = Font(bold=True); c.alignment = Alignment(vertical='top')
    for r in data:
        ws.append(r)
        ws.cell(ws.max_row, 8).fill = PatternFill('solid', fgColor=BAND_FILL[r[7]])
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}{ws.max_row}"
    for i, w in enumerate([34, 14, 5, 10, 7, 6, 9, 8, 26, 46, 6, 16, 8, 8,
                           10, 11, 14, 52], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws2 = wb.create_sheet('summary')
    cnt = collections.Counter(r[7] for r in data)
    ws2.append(['band', 'sections', 'share']); ws2['A1'].font = Font(bold=True)
    for k in ('exact', '<=5%', '<=10%', '<=25%', 'off'):
        ws2.append([k, cnt[k], round(100*cnt[k]/len(data), 1)])
    ws2.append([])
    ws2.append(['sections with a rhyme scheme', sum(1 for r in data if r[12])])
    ws2.append(['sections with melisma marks', sum(1 for r in data if r[13])])
    ws2.append(['GOLD: within 5% and rhymed',
                sum(1 for r in data if r[7] in ('exact', '<=5%') and r[12])])
    ws2.append(['songs represented', len({r[0] for r in data})])
    ws2.append([])
    ws2.append(['why the off rows are off', 'sections'])
    ws2[f'A{ws2.max_row}'].font = Font(bold=True)
    for k, c in collections.Counter(r[8] for r in data if r[8]).most_common():
        ws2.append([k, c])
    for i, w in enumerate([30, 10, 8], 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    wb.save(OUT)
    print(f"  {len(data)} sections, {len({r[0] for r in data})} songs -> {OUT}")
    for k in ('exact', '<=5%', '<=10%', '<=25%', 'off'):
        print(f"    {k:6} {cnt[k]:5}")

if __name__ == '__main__':
    main()
