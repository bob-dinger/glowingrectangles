"""Cross-reference Beatles key changes across three sources:
  1. Pollack  — raw HTML "Key:" header (multi-tonic / arrow) + "modulat" prose
  2. Hookpad  — distinct (tonic, scale) in the song's keys array (Supabase)
  3. UG tabs  — per-section inferred tonic disagreement (parse_ug)

Writes ~/Desktop/beatles_key_changes.xlsx, one row per song, flagging which
sources report a change and distinguishing true modulation (tonic change) from
mode/parallel shifts (same tonic).
"""
import os, re, glob, json, html, psycopg2
from collections import defaultdict
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from parse_ug import parse_tab, infer_key
from bennett_key_changes import BENNETT

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
POL = os.path.expanduser('~/Desktop/music/pollack_beatles_notes')
UG = os.path.expanduser('~/Desktop/music/ug_tabs')

# --- David Bennett video (authoritative TYPE source) ---
def bennett():
    return {norm(t): {'title': t, 'type': v[0], 'detail': v[1]} for t, v in BENNETT.items()}

# --- Pollack PROSE: pull the sentences that actually discuss the modulation ---
_KEYWORDS = re.compile(r'\b(modulat|key change|key of|new key|home key|tonic(?:iz|is)|pivot|'
                       r'raised.*(?:key|tonic)|shift(?:s|ed)?\s+(?:up|down|to|the key)|relative (?:major|minor))', re.I)
def pollack_prose(slug):
    doc = html.unescape(open(os.path.join(POL, slug + '.html'), encoding='utf-8', errors='replace').read())
    txt = re.sub(r'<[^>]+>', ' ', doc).replace('&nbsp;', ' ')
    txt = re.sub(r'\s+', ' ', txt)
    sents = re.split(r'(?<=[.!?])\s+', txt)
    hits = [s.strip() for s in sents if 'modulat' in s.lower() or ('key' in s.lower() and _KEYWORDS.search(s))]
    # de-noise: keep sentences that name a key change, drop generic 'key of X' one-offs
    hits = [s for s in hits if len(s) > 25]
    return hits[:4]

# ---------- 1. Pollack ----------
def pollack():
    idx = json.load(open(POL + '/_index.json'))
    out = {}
    for slug, v in idx.items():
        doc = html.unescape(open(os.path.join(POL, slug + '.html'), encoding='utf-8', errors='replace').read()).replace('&nbsp;', ' ')
        m = re.search(r'Key:\s*([^\n<]+)', doc)
        keyline = m.group(1).strip() if m else ''
        main = re.sub(r'\([^)]*\)', '', keyline)              # drop parentheticals (mode notes / mono-stereo)
        tonics = re.findall(r'\b([A-G][b#-]*(?:flat|sharp)?)\s*(?:Major|minor)', main)
        tonics = [re.sub(r'[-\s]', '', t).lower() for t in tonics]
        arrow = '»' in keyline or '->' in keyline or '&gt;' in keyline
        header_change = arrow or len(set(tonics)) > 1
        prose = len(re.findall(r'\bmodulat', re.sub(r'<[^>]+>', ' ', doc), re.I))
        if header_change or prose >= 3:
            out[norm(v['title'])] = {'title': v['title'], 'key': keyline,
                                     'strong': header_change, 'prose': prose,
                                     'notes': ' / '.join(pollack_prose(slug))}
    return out

# ---------- 2. Hookpad ----------
def hookpad():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("""select distinct on (lower(regexp_replace(title,'[^a-zA-Z0-9]','','g'))) title, hookpad_json->'keys'
        from parcels.songs where slug like 'beatles_%' and hookpad_json is not null
        order by lower(regexp_replace(title,'[^a-zA-Z0-9]','','g'))""")
    out = {}
    for title, keys in cur.fetchall():
        if not keys: continue
        tonics = set(k.get('tonic') for k in keys)
        pairs = set((k.get('tonic'), k.get('scale')) for k in keys)
        if len(pairs) > 1:
            seq = [f"{k.get('tonic')} {k.get('scale')}" for k in keys]
            comp = ' -> '.join(x for i, x in enumerate(seq) if i == 0 or x != seq[i-1])
            out[norm(title)] = {'title': title, 'seq': comp,
                                'modulation': len(tonics) > 1}   # true tonic change vs mode-only
    return out

# ---------- 3. UG (per-section inferred tonic) ----------
_NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
_FLAT = {'Db':1,'Eb':3,'Gb':6,'Ab':8,'Bb':10}
_MAJ = [0,2,4,5,7,9,11]
def _pc(note):
    if note in _NOTES: return _NOTES.index(note)
    return _FLAT.get(note)
def _keyset(tonic_pc):
    return set((tonic_pc + i) % 12 for i in _MAJ)   # major-scale pcs (relative minor shares them)

def ug():
    """Diatonic-fit modulation detector: a section modulates if its chord roots
    fit some OTHER key's scale clearly better than the whole-song key."""
    from parse_ug import parse_chord_name
    out = {}
    for p in glob.glob(UG + '/beatles_*.txt'):
        meta, secs = parse_tab(open(p, encoding='utf-8', errors='replace').read())
        # whole-song root pcs
        all_pcs = []
        sec_pcs = []
        for s in secs:
            pcs = []
            for kind, pl in s['events']:
                if kind == 'chord_line':
                    for c, _ in pl:
                        pc = _pc((parse_chord_name(c) or {}).get('note', ''))
                        if pc is not None: pcs.append(pc)
            all_pcs += pcs
            if len(pcs) >= 3: sec_pcs.append(pcs)
        if not all_pcs: continue
        # home key = tonic whose scale best covers all roots
        home = max(range(12), key=lambda t: sum(pc in _keyset(t) for pc in all_pcs))
        alts = set()
        for pcs in sec_pcs:
            home_fit = sum(pc in _keyset(home) for pc in pcs) / len(pcs)
            best = max(range(12), key=lambda t: sum(pc in _keyset(t) for pc in pcs))
            best_fit = sum(pc in _keyset(best) for pc in pcs) / len(pcs)
            # loosened: lower fit bar, smaller gap over home, and also catch a
            # section that simply fits home poorly (has a foreign chord or two)
            if best != home and best_fit >= 0.75 and best_fit - home_fit >= 0.15:
                alts.add(_NOTES[best])
        title = re.sub(r'^beatles[-_]', '', os.path.basename(p)[:-4]).replace('-', ' ')
        if alts:
            out[norm(title)] = {'title': title, 'tonics': f'{_NOTES[home]} -> ' + '/'.join(sorted(alts))}
    return out

def main():
    P, H, U, B = pollack(), hookpad(), ug(), bennett()
    all_keys = set(P) | set(H) | set(U) | set(B)
    # fuzzy-fold Bennett titles onto existing keys where norm differs slightly
    rows = []
    for k in all_keys:
        title = (B.get(k) or P.get(k) or H.get(k) or U.get(k))['title']
        p, h, u, b = P.get(k), H.get(k), U.get(k), B.get(k)
        n = sum(bool(x) for x in (p, h, u, b))
        btype = (b['type'] + (f" — {b['detail']}" if b['detail'] else '')) if b else ''
        polcell = ''
        if p:
            polcell = ('★ ' if p['strong'] else '~ ') + p['key']
            if p['notes']: polcell += '  ||  ' + p['notes']
        rows.append({
            'title': title, 'n': n,
            'bennett': btype,
            'pollack': polcell,
            'hookpad': (('★ ' if h['modulation'] else '~ ') + h['seq']) if h else '',
            'ug': (u['tonics']) if u else '',
        })
    rows.sort(key=lambda r: (-r['n'], r['title'].lower()))

    wb = Workbook(); ws = wb.active; ws.title = 'Key changes'
    ws.append(['Song', '# sources', 'Type (Bennett)', 'Pollack (★=header  ||  prose)',
               'Hookpad (★=modulation)', 'UG'])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='305496'); c.alignment = Alignment(horizontal='center')
    fills = {4: '92D050', 3: 'C6EFCE', 2: 'FFEB9C', 1: 'FCE4D6'}
    for r in rows:
        ws.append([r['title'], r['n'], r['bennett'], r['pollack'], r['hookpad'], r['ug']])
        f = fills.get(r['n'])
        if f: ws.cell(ws.max_row, 2).fill = PatternFill('solid', fgColor=f)
        ws.cell(ws.max_row, 4).alignment = Alignment(wrap_text=True, vertical='top')
    for i, w in enumerate([34, 9, 30, 70, 46, 18], 1):
        ws.column_dimensions[chr(64+i)].width = w
    ws.freeze_panes = 'A2'
    out = os.path.expanduser('~/Desktop/beatles_key_changes.xlsx')
    wb.save(out)
    print(f'wrote {out}')
    print(f'  Bennett: {len(B)}   Pollack: {len(P)}   Hookpad: {len(H)}   UG: {len(U)}   union: {len(rows)}')
    for n in (4, 3, 2, 1):
        print(f'  {sum(1 for r in rows if r["n"]==n)} songs flagged by {n} source(s)')
    return rows

if __name__ == '__main__':
    rows = main()
    print('\n=== flagged by ALL 4 sources ===')
    for r in [x for x in rows if x['n'] == 4]:
        print(f"  {r['title']:34} [{r['bennett']}]")
    print('\n=== sample Pollack prose (deeper than the header) ===')
    for r in [x for x in rows if '||' in r['pollack']][:4]:
        print(f"  {r['title']}:")
        print(f"    {r['pollack'].split('||',1)[1].strip()[:240]}")
