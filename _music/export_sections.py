"""Export all N-bar sections across Hookpad library to xlsx for visual comparison.

Usage:
    export_sections.py            # 8-bar sections (default)
    export_sections.py --bars 4   # 4-bar sections
    export_sections.py --bars 16  # 16-bar sections

One row per section. Each bar gets its own column so you can sort/filter and scan
patterns visually. Same (song, section name, bar pattern) is deduped — if a song
has 3 verses with identical chords, they collapse to one row with Repeats=3.
"""
import os, glob, json, re, argparse
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

HOOKPAD_DIR = '/Users/robert/Desktop/music/hookpad_songs_full'

ROMAN = re.compile(r'^(?P<acc>[b#]*)(?P<deg>VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(?P<suf>.*)$')
NATURAL_MINOR = {'II','III','VI','VII'}
ROMAN_UP = ['','I','II','III','IV','V','VI','VII']

DEG_NUM = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,
           'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7}
DEG_COLOR = {
    1: 'F4A8A8',  # I   red
    2: 'F4C898',  # ii  orange
    3: 'F0E898',  # iii yellow
    4: 'A8E0B0',  # IV  green
    5: 'A8C8F0',  # V   blue
    6: 'D0B0F0',  # vi  purple
    7: 'D0B0F0',  # vii purple
}

def chord_color(tok):
    m = ROMAN.match(tok or '')
    if not m: return None
    return DEG_COLOR.get(DEG_NUM.get(m.group('deg')))

def to_roman(root, type_str):
    rs = str(root or '')
    if not rs: return None
    acc = ''
    while rs and rs[0] in 'b#':
        acc += rs[0]; rs = rs[1:]
    if not rs.isdigit(): return None
    deg = int(rs)
    if not 1 <= deg <= 7: return None
    base = ROMAN_UP[deg]
    ts = str(type_str or '')
    is_minor = ts.lower().startswith('m') and not ts.lower().startswith('maj')
    if is_minor:
        base = base.lower(); suffix = ts[1:]
    else:
        suffix = ts
    return f'{acc}{base}{suffix}'

def normalize(tok, key_is_major):
    m = ROMAN.match(tok)
    if not m: return tok
    acc, deg, suf = m.group('acc'), m.group('deg'), m.group('suf')
    if suf == '5': suf = ''
    if key_is_major and not acc and deg in NATURAL_MINOR and not suf:
        deg = deg.lower()
    return acc + deg + suf

def parse_fname(fname):
    name = os.path.basename(fname).removesuffix('.json')
    name = re.sub(r'-(right|Right|RIGHT)$', '', name)
    parts = name.split('_', 1)
    if len(parts) != 2:
        return None, name
    artist, rest = parts
    toks = rest.split('_')
    while len(toks) > 1 and len(toks[-1]) <= 3:
        toks.pop()
    return artist.strip(), '_'.join(toks).strip()

def song_id(artist, title):
    a = re.sub(r'[^a-z0-9]', '', (artist or '').lower())
    t = re.sub(r'[^a-z0-9]', '', (title or '').lower())
    return (a, t)


CELLS_PER_BAR = 2  # half-bar resolution catches typical 2-beat chord changes

def build(target_bars):
    sections_data = []
    total_cells = target_bars * CELLS_PER_BAR
    for f in sorted(glob.glob(os.path.join(HOOKPAD_DIR, '*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8-sig'))
        except Exception:
            continue
        sections = d.get('sections') or []
        chords = d.get('chords') or []
        if not sections or not chords: continue
        bpb = (d.get('meters') or [{'numBeats':4}])[0].get('numBeats', 4) or 4
        cell_beats = bpb / CELLS_PER_BAR
        key = (d.get('keys') or [{}])[0]
        key_tonic = key.get('tonic','?')
        key_scale = key.get('scale','?')
        key_is_major = key_scale == 'major'
        bpm = (d.get('tempos') or [{}])[0].get('bpm')
        end_beat = d.get('endBeat') or 999999
        bounds = list(sections) + [{'beat': end_beat, 'name': '<end>'}]
        artist, title = parse_fname(f)

        for i in range(len(bounds)-1):
            s, e = bounds[i], bounds[i+1]
            bars = round((e['beat'] - s['beat']) / bpb)
            if bars != target_bars: continue
            sec_chords = [c for c in chords
                          if not c.get('isRest')
                          and c.get('beat') is not None
                          and s['beat'] <= c['beat'] < e['beat']]
            if not sec_chords: continue

            bar_cells = []
            for cell_idx in range(total_cells):
                cell_start = s['beat'] + cell_idx * cell_beats
                cur = None
                for c in sec_chords:
                    cb = c['beat']; cd = c.get('duration', bpb)
                    if cb <= cell_start < cb + cd:
                        cur = c; break
                if cur is None:
                    prior = [c for c in sec_chords if c['beat'] <= cell_start]
                    cur = prior[-1] if prior else sec_chords[0]
                tok = to_roman(cur.get('root'), cur.get('type',''))
                tok = normalize(tok, key_is_major) if tok else '?'
                bar_cells.append(tok)

            sections_data.append({
                'pattern': ' '.join(bar_cells),
                'unique_chords': len(set(bar_cells)),
                'title': title,
                'artist': artist or '',
                'section': s.get('name','?'),
                'key': f'{key_tonic} {"maj" if key_is_major else key_scale}',
                'bpm': bpm,
                'bars': bar_cells,
                'chord_events': len(sec_chords),
                'song_id': song_id(artist, title),
            })

    # Dedupe: same song + same section name + same bar pattern = same thing
    grouped = defaultdict(list)
    for r in sections_data:
        k = (r['song_id'], r['section'].strip().lower(), r['pattern'])
        grouped[k].append(r)

    rows = []
    for k, group in grouped.items():
        base = group[0]
        base['repeats'] = len(group)
        rows.append(base)

    rows.sort(key=lambda r: (r['pattern'], r['title']))
    return rows, len(sections_data)


def write_xlsx(rows, target_bars, out_path, total_before_dedup):
    wb = Workbook()
    ws = wb.active
    ws.title = f'{target_bars}-bar sections'

    bar_headers = [f'{1 + i/CELLS_PER_BAR:g}' for i in range(target_bars * CELLS_PER_BAR)]
    headers = ['Pattern','Repeats','# chords','Title','Artist','Section','Key','BPM',
               *bar_headers, 'Chord events']
    ws.append(headers)

    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF')
    for cell in ws[1]:
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center')

    bands = ['FFFFFF', 'F2F2F2']
    band_idx = 0
    prev_pattern = None
    bar_col_start = 9  # cols 1..8 are Pattern/Repeats/#chords/Title/Artist/Section/Key/BPM

    for r in rows:
        if r['pattern'] != prev_pattern:
            band_idx = 1 - band_idx
            prev_pattern = r['pattern']
        fill_color = bands[band_idx]
        excel_row = [
            r['pattern'], r['repeats'], r['unique_chords'],
            r['title'], r['artist'], r['section'],
            r['key'], r['bpm'],
            *r['bars'],
            r['chord_events'],
        ]
        ws.append(excel_row)
        for cell in ws[ws.max_row]:
            cell.fill = PatternFill('solid', fgColor=fill_color)
        # Center bar cells + color by chord degree
        for offset, tok in enumerate(r['bars']):
            cell = ws.cell(row=ws.max_row, column=bar_col_start + offset)
            cell.alignment = Alignment(horizontal='center')
            c = chord_color(tok)
            if c:
                cell.fill = PatternFill('solid', fgColor=c)
                cell.font = Font(bold=True, color='000000')

    ws.freeze_panes = ws.cell(row=2, column=bar_col_start).coordinate

    base_widths = {'A':32, 'B':8, 'C':9, 'D':32, 'E':22, 'F':18, 'G':9, 'H':6}
    for col, w in base_widths.items():
        ws.column_dimensions[col].width = w
    total_cells = target_bars * CELLS_PER_BAR
    # Each cell = half a measure, narrow & consistent so the colored cells read as a strip
    HALF_BAR_WIDTH = 4
    for i in range(total_cells):
        col_letter = ws.cell(row=1, column=bar_col_start + i).column_letter
        ws.column_dimensions[col_letter].width = HALF_BAR_WIDTH
    # Slight extra row height makes each colored cell ~square
    for r in range(2, ws.max_row + 1):
        ws.row_dimensions[r].height = 20
    last_col = ws.cell(row=1, column=bar_col_start + total_cells).column_letter
    ws.column_dimensions[last_col].width = 9

    ws.auto_filter.ref = ws.dimensions
    wb.save(out_path)
    return total_before_dedup


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bars', type=int, default=8)
    p.add_argument('--out', default=None)
    args = p.parse_args()

    target = args.bars
    out_path = args.out or f'/Users/robert/Desktop/music/{target}bar_sections.xlsx'

    rows, raw_total = build(target)
    write_xlsx(rows, target, out_path, raw_total)

    unique_songs = len(set(r['song_id'] for r in rows))
    print(f'{target}-bar sections: {raw_total} raw → {len(rows)} after dedup ({raw_total - len(rows)} repeats collapsed)')
    print(f'spanning {unique_songs} unique songs')
    print(f'→ {out_path}')


if __name__ == '__main__':
    main()
