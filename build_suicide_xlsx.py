#!/usr/bin/env python3
"""
CDC suicide series -> one formatted workbook.

Source: Health, United States Table 9 (data.cdc.gov 9j2v-jamp), 1950-2018,
plus the user's own 1932-2023 age/sex pull as a separate sheet.

The one thing this file must not let you do is compare a crude rate to an
age-adjusted one. The source mixes both in a single column, distinguished
only by UNIT_NUM, and every sheet here is therefore ONE rate type, named in
the sheet title. Age-specific rates exist only as crude, which is correct —
an age-specific rate has nothing left to adjust for.

    python3 build_suicide_xlsx.py
    python3 build_suicide_xlsx.py --src /path/to/rows.csv --out ~/Desktop/x.xlsx
"""
import argparse, collections, csv, os, sys

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

URL = ('https://data.cdc.gov/National-Center-for-Health-Statistics/'
       'Death-rates-for-suicide-by-sex-race-Hispanic-origi/9j2v-jamp')
USER_CSV = os.path.expanduser('~/Desktop/us_suicide_rates_selected_1932_2023.csv')

HEAD = PatternFill('solid', fgColor='1F2430')
HF   = Font(color='FFFFFF', bold=True, size=10)
SUBF = Font(color='FFFFFF', bold=False, size=9, italic=True)
THIN = Side(style='thin', color='D9D9D9')
BOX  = Border(bottom=THIN)
NUM  = '0.0'


def load(path):
    rows = [r for r in csv.DictReader(open(path)) if r['ESTIMATE']]
    for r in rows:
        r['year'] = int(r['YEAR'])
        r['val']  = float(r['ESTIMATE'])
        r['adj']  = (r['UNIT_NUM'] == '1')
    return rows


def parse_label(lab):
    """'Male: Black or African American: 45-64 years' -> parts"""
    parts = [p.strip() for p in lab.split(':')]
    sex = parts[0] if parts[0] in ('Male', 'Female') else ''
    age = parts[-1] if parts[-1].endswith(('years', 'over')) else ''
    mid = [p for p in parts[1:] if p != age]
    hisp = ''
    if mid and mid[0].startswith('Hispanic'):     hisp, mid = 'Hispanic', mid[1:]
    elif mid and mid[0].startswith('Not Hispanic'): hisp, mid = 'Not Hispanic', mid[1:]
    race = mid[0] if mid else ''
    if race == 'All races': race = 'All races'
    return sex, race, hisp, (age or 'All ages')


SHORT = {'American Indian or Alaska Native': 'AI/AN',
         'Asian or Pacific Islander': 'Asian/PI',
         'Black or African American': 'Black', 'White': 'White',
         'All races': 'All races'}


def wide(ws, rows, colkey, title, sub, adj):
    """years down the side, one column per series."""
    sel = [r for r in rows if r['adj'] == adj]
    keys, data = [], collections.defaultdict(dict)
    for r in sel:
        k = colkey(r)
        if k is None: continue
        if k not in keys: keys.append(k)
        data[r['year']][k] = r['val']
    if not keys: return False
    ws['A1'] = title; ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = sub;   ws['A2'].font = Font(size=9, color='777777')
    hr = 4
    ws.cell(hr, 1, 'year').fill = HEAD; ws.cell(hr, 1).font = HF
    for i, k in enumerate(keys, 2):
        c = ws.cell(hr, i, k); c.fill = HEAD; c.font = HF
        c.alignment = Alignment(horizontal='center', wrap_text=True)
    for j, y in enumerate(sorted(data), hr+1):
        ws.cell(j, 1, y).font = Font(bold=True)
        for i, k in enumerate(keys, 2):
            c = ws.cell(j, i, data[y].get(k))
            c.number_format = NUM
            c.border = BOX
    ws.freeze_panes = ws.cell(hr+1, 2)
    ws.column_dimensions['A'].width = 7
    for i in range(2, len(keys)+2):
        ws.column_dimensions[get_column_letter(i)].width = max(9, min(16, len(keys[i-2])+2))
    ws.row_dimensions[hr].height = 30
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='suic_race.csv')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/us_suicide_1950_2023.xlsx'))
    a = ap.parse_args()
    if not os.path.exists(a.src): sys.exit(f'no source csv at {a.src}')

    rows = load(a.src)
    for r in rows:
        r['sex'], r['race'], r['hisp'], r['age'] = parse_label(r['STUB_LABEL'])
        r['race_s'] = SHORT.get(r['race'], r['race'])

    wb = Workbook()

    # ---------------------------------------------------------------- README
    ws = wb.active; ws.title = 'README'
    L = [('US suicide rates — CDC series', 15, True),
         ('', 10, False),
         ('SHEETS', 11, True),
         ('by sex (adj)        all-ages rates, AGE-ADJUSTED. The only sheet safe for', 10, False),
         ('                    comparing across long spans, because the population aged.', 10, False),
         ('by race (adj)       all-ages by race and sex, AGE-ADJUSTED, 1950-2018.', 10, False),
         ('by age              age-specific, CRUDE (an age-specific rate has nothing', 10, False),
         ('                    left to adjust for). Male and female.', 10, False),
         ('by age + race       the richest cut: sex x race x age band, CRUDE.', 10, False),
         ('tidy                everything, one row per observation, filterable.', 10, False),
         ('1932-2023 (mine)    the original pull: age and sex, incl. Depression-era 1932', 10, False),
         ('                    and detailed 2022-23 counts. Mixed rate types — see below.', 10, False),
         ('', 10, False),
         ('THE ONE TRAP', 11, True),
         ('Never compare a CRUDE rate to an AGE-ADJUSTED one. The source file carries', 10, False),
         ('both in a single ESTIMATE column, separated only by a UNIT flag. It is how', 10, False),
         ('1932 (17.4 crude) comes to look worse than 2018 (14.2 age-adjusted) when in', 10, False),
         ('fact they are not the same measurement. Every sheet here is one rate type.', 10, False),
         ('', 10, False),
         ('OTHER CAVEATS', 11, True),
         ('Race categories changed in 1999 (ICD-9 to ICD-10) and again in 2018', 10, False),
         ('(single-race reporting), so series do not join cleanly at those seams.', 10, False),
         ('Black suicides are misclassified as "undetermined" at about 2.4x the White', 10, False),
         ('rate, and CDC states AI/AN deaths are undercounted by roughly a third. Every', 10, False),
         ('non-White figure here is therefore a floor, by an unknown and probably', 10, False),
         ('shrinking amount.', 10, False),
         ('', 10, False),
         ('SOURCE', 11, True),
         ('Health, United States Table 9 — Death rates for suicide, by sex, race,', 10, False),
         ('Hispanic origin, and age. National Vital Statistics System.', 10, False),
         (URL, 9, False)]
    for i, (t, sz, b) in enumerate(L, 1):
        c = ws.cell(i, 1, t); c.font = Font(size=sz, bold=b)
    ws.column_dimensions['A'].width = 92

    # ---------------------------------------------------------------- sheets
    allages = [r for r in rows if r['age'] == 'All ages']

    wide(wb.create_sheet('by sex (adj)'),
         [r for r in allages if r['STUB_NAME'] in ('Sex', 'Total')],
         lambda r: r['STUB_LABEL'],
         'Suicide rate by sex, all ages',
         'Deaths per 100,000 — AGE-ADJUSTED to the 2000 US standard population', True)

    wide(wb.create_sheet('by race (adj)'),
         [r for r in allages if r['STUB_NAME'] == 'Sex and race'],
         lambda r: f"{r['sex']} · {r['race_s']}",
         'Suicide rate by sex and race, all ages',
         'Deaths per 100,000 — AGE-ADJUSTED. Race categories change in 1999 and 2018.', True)

    wide(wb.create_sheet('by race+hisp (adj)'),
         [r for r in allages if r['STUB_NAME'] == 'Sex and race and Hispanic origin'],
         lambda r: f"{r['sex']} · {r['hisp'] or '-'} {r['race_s']}",
         'Suicide rate by sex, race and Hispanic origin, all ages',
         'Deaths per 100,000 — AGE-ADJUSTED. Hispanic origin reported from 1985.', True)

    for sex in ('Male', 'Female'):
        wide(wb.create_sheet(f'by age — {sex.lower()}'),
             [r for r in rows if r['STUB_NAME'] == 'Sex and age' and r['sex'] == sex],
             lambda r: r['age'],
             f'{sex} suicide rate by age group',
             'Deaths per 100,000 — CRUDE. Age-specific rates are never age-adjusted.', False)

    for sex in ('Male', 'Female'):
        wide(wb.create_sheet(f'age+race — {sex.lower()}'),
             [r for r in rows if r['STUB_NAME'] == 'Sex, age and race' and r['sex'] == sex],
             lambda r: f"{r['race_s']} · {r['age'].replace(' years','')}",
             f'{sex} suicide rate by race and age group',
             'Deaths per 100,000 — CRUDE. The richest cut in the CDC file.', False)

    # ---------------------------------------------------------------- tidy
    ws = wb.create_sheet('tidy')
    cols = [('year',7),('sex',9),('race',11),('hispanic_origin',15),('age',15),
            ('rate_per_100k',13),('rate_type',13),('cross_tab',34),('source_url',30)]
    ws.append([c[0] for c in cols])
    for i,(n,w) in enumerate(cols,1):
        ws.column_dimensions[get_column_letter(i)].width = w
        c = ws.cell(1,i); c.fill = HEAD; c.font = HF
    for r in sorted(rows, key=lambda r:(r['year'], r['STUB_NAME'], r['STUB_LABEL'], r['adj'])):
        ws.append([r['year'], r['sex'], r['race_s'], r['hisp'], r['age'], r['val'],
                   'age-adjusted' if r['adj'] else 'crude', r['STUB_NAME'], URL])
    for row in range(2, ws.max_row+1):
        ws.cell(row,6).number_format = NUM
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(cols))}{ws.max_row}'

    # ---------------------------------------------------------- the user's csv
    if os.path.exists(USER_CSV):
        ws = wb.create_sheet('1932-2023 (mine)')
        src = list(csv.reader(open(USER_CSV)))
        for i, row in enumerate(src, 1):
            ws.append(row)
            if i == 1:
                for j in range(1, len(row)+1):
                    c = ws.cell(1, j); c.fill = HEAD; c.font = HF
        for j, w in enumerate([7,12,12,13,9,13,42,30,46], 1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = f'A1:I{ws.max_row}'

    wb.save(a.out)
    print(f'{len(wb.sheetnames)} sheets, {len(rows)} CDC observations')
    for s in wb.sheetnames: print('   ', s)
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
