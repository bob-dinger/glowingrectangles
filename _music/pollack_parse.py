"""Parse Alan W. Pollack's "Notes on..." Beatles analyses into structured
per-measure chord data.

Pollack's chord figures live in <pre> blocks and look like:

       -------------- 2x ---------------
    m.1/3
      |E       g#  g   |f#      B7      |
   E:  I                ii      V

Notation decoded:
  - `|cell |cell |`  : each cell between bars = ONE measure
  - space-separated tokens in a cell = chords within that measure (subdivisions)
  - CASE encodes quality:  E = E major,  e = E minor,  g# = G# minor,  B7 = B dom7
  - `-`                : chord held / continues from previous measure
  - `E:` / `f#:`       : the key the roman-numeral line below is analyzed in
  - `m.1/3`, `mm.9-12` : measure-number label for the figure
  - `2x` / `2X`        : the labeled unit repeats (m.1/3 means "at m1 AND m3")
  - `[Figure 32.2]`    : figure id tag

Usage:
    from pollack_parse import parse_song
    figs = parse_song('dywtkas')          # -> list of Figure dicts
"""
import re, os, html as _html

POLDIR = os.path.expanduser('~/Desktop/music/pollack_beatles_notes')

# ---- entity / whitespace cleanup -------------------------------------------

def _clean(pre):
    s = pre.replace('&nbsp;', ' ').replace('&raquo;', '>').replace('&flat;', 'b')
    s = _html.unescape(s)
    return s

def _pre_blocks(fname):
    path = os.path.join(POLDIR, fname if fname.endswith('.html') else fname + '.html')
    doc = open(path, encoding='utf-8', errors='replace').read()
    return [_clean(p) for p in re.findall(r'<pre>(.*?)</pre>', doc, re.S)]

# ---- chord-token parsing ----------------------------------------------------

_TOK = re.compile(r'^[A-Ga-g][#b]?')

def token_to_chord_name(tok):
    """Pollack token -> GP-style chord name (case-encoded quality).
    'g#' -> 'G#m'  |  'B7' -> 'B7'  |  'E' -> 'E'  |  '-' -> None (held)
    Returns (gp_name, is_hold, raw)."""
    tok = tok.strip()
    if not tok or tok in ('-', '|'):
        return None, True, tok
    m = _TOK.match(tok)
    if not m:
        return None, False, tok            # unparseable (e.g. 'C-augmented', '??')
    head = m.group(0)
    suffix = tok[len(head):]
    root = head[0].upper()
    acc = head[1:] if len(head) > 1 else ''
    is_minor = head[0].islower()
    # normalize a couple of spelled-out suffixes
    suffix = suffix.replace('augmented', 'aug').replace('dim', 'dim')
    gp = root + acc + ('m' if is_minor else '') + suffix
    return gp, False, tok

def _split_measures(chord_line):
    """'|E g# g |f# B7 |' -> [[('E',col),...], [('f#',col),('B7',col)]]
    One list per measure; each token carries its start column in the raw line."""
    measures = []
    cur = None            # None until first '|' seen
    i = 0
    n = len(chord_line)
    while i < n:
        ch = chord_line[i]
        if ch == '|':
            measures.append([]); cur = measures[-1]; i += 1; continue
        if ch.isspace():
            i += 1; continue
        # read a token (non-space run)
        j = i
        while j < n and not chord_line[j].isspace() and chord_line[j] != '|':
            j += 1
        tok = chord_line[i:j]
        if cur is not None:
            cur.append((tok, i))
        i = j
    # drop trailing empty cell produced by the closing '|'
    return [m for m in measures if m]

# roman-numeral token on an analysis line (I, ii, IV, V, vi, flat-II, bIII ...)
_ROMAN = re.compile(r'(?<![A-Za-z])(?:flat-|sharp-|[b#])?[ivIV]+(?![A-Za-z:])')

def _roman_cols(line):
    """Column indices where roman-numeral tokens start (skips the 'E:' key prefix)."""
    line = re.sub(r'^\s*[a-gA-G][#b]?:', lambda m: ' ' * len(m.group(0)), line)
    return [m.start() for m in _ROMAN.finditer(line)]

# ---- line classification ----------------------------------------------------

_KEYLINE = re.compile(r'^\s*([a-gA-G][#b]?):\s')          # 'E:  I  ii  V'
_MLABEL  = re.compile(r'^\s*mm?\.\s*[\d]')                # 'm.1/3' , 'mm. 9 - 12'
_BARENUM = re.compile(r'^\s*\d+\s*$')                     # bare '5'
_REPEAT  = re.compile(r'(\d+)\s*[xX]')                    # '2x'
def _is_chordline(l):
    return '|' in l and re.search(r'[A-Ga-g]', l.replace('flat', ''))

def parse_figure(block):
    """Parse one <pre> figure block -> dict with ordered 'measures'.
    Each measure: {'chords':[gp|None], 'raw':[...], 'holds':[...],
                   'structural':[bool,...], 'label':str|None, 'repeat':int}.
    'structural' marks tokens that carry a roman numeral (vs. passing chords)."""
    lines = block.split('\n')
    fig = {'measures': [], 'keys': [], 'figure_id': None}
    cur_label = None
    cur_repeat = 1
    n = len(lines)
    for idx, l in enumerate(lines):
        fid = re.search(r'\[Figure\s+([\d.]+)\]', l)
        if fid:
            fig['figure_id'] = fid.group(1)
        km = _KEYLINE.match(l)
        if km and not _is_chordline(l):
            fig['keys'].append(km.group(1))
            continue
        if _MLABEL.match(l) or _BARENUM.match(l):
            cur_label = l.strip()
            continue
        rp = _REPEAT.search(l)
        if rp and '|' not in l and '-----' in l:
            cur_repeat = int(rp.group(1))
            continue
        if _is_chordline(l):
            # gather roman-numeral columns from the following analysis line(s)
            rcols = []
            j = idx + 1
            while j < n and not _is_chordline(lines[j]) and (
                    _KEYLINE.match(lines[j]) or _ROMAN.search(lines[j])):
                rcols += _roman_cols(lines[j]); j += 1
            for meas in _split_measures(l):
                names, holds, raws, struct = [], [], [], []
                for tok, col in meas:
                    gp, hold, raw = token_to_chord_name(tok)
                    names.append(gp); holds.append(hold); raws.append(raw)
                    struct.append(any(abs(col - rc) <= 3 for rc in rcols))
                fig['measures'].append({
                    'chords': names, 'raw': raws, 'holds': holds,
                    'structural': struct, 'label': cur_label, 'repeat': cur_repeat,
                })
            cur_label = None
            cur_repeat = 1
    return fig

def parse_song(slug):
    """Return the list of figure dicts (skips header + revision-history blocks)."""
    figs = []
    for blk in _pre_blocks(slug):
        if 'Key:' in blk and 'Form:' in blk:      # header block
            continue
        if 'Revision History' in blk:
            continue
        f = parse_figure(blk)
        if f['measures']:
            figs.append(f)
    return figs

if __name__ == '__main__':
    import sys, json
    slug = sys.argv[1] if len(sys.argv) > 1 else 'dywtkas'
    for i, f in enumerate(parse_song(slug)):
        print(f"--- Figure {f.get('figure_id') or i}  keys={f['keys']} ---")
        for m in f['measures']:
            r = ' '.join(m['raw'])
            c = ' '.join(x or '·' for x in m['chords'])
            lab = f"[{m['label']}]" if m['label'] else ''
            rep = f" x{m['repeat']}" if m['repeat'] > 1 else ''
            print(f"    {lab:12s} {r:20s} -> {c}{rep}")
