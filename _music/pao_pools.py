#!/usr/bin/env python3
"""
Turn every section of every song in a guitar pool into a PAO scene.

Progressions are stored as scale degrees, so the scenes are key-independent:
the same picture works whether the song is in E or A flat.

    python3 pao_pools.py                     # G50 + G100
    python3 pao_pools.py --pools G50
    python3 pao_pools.py --out ~/Desktop/pao.html

Writes an HTML sheet grouped by song, and prints coverage stats.
"""
import argparse, collections, glob, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
POOLS = os.path.join(HERE, 'pool_map.json')

ROMAN_UP = ['I','II','III','IV','V','VI','VII']
ROMAN_LO = ['i','ii','iii','iv','v','vi','vii']
QUAL = {'major': ['M','m','m','M','M','m','d'],
        'minor': ['m','d','M','m','m','M','M']}


def chord_label(c, scale='major'):
    """Lifted from build_section_curation_xlsx.py so the labels match the
    rest of the project. applied>0 is always major."""
    root = str(c.get('root', ''))
    acc, rs = '', root
    while rs and rs[0] in 'b#':
        acc += rs[0]; rs = rs[1:]
    if not rs.isdigit(): return '?'
    deg = int(rs)
    if deg == 0: return '?'                  # root 0 is a rest; see is_rest()
    # A root-7 POWER chord has no third, so it CANNOT be diminished. In
    # practice it is bVII entered without the borrowed flag — the same trap
    # that made vii-dim look twice as common as bVII corpus-wide. Ditto any
    # root-7 borrowed from minor or mixolydian, where bVII is diatonic.
    if deg == 7 and not c.get('applied') and (
            c.get('type') in (5, '5') or
            c.get('borrowed') in ('minor', 'mixolydian', 'dorian', 'phrygian')):
        return 'bVII'
    if c.get('applied'): q = 'M'
    elif c.get('type') in ('m', 'min'): q = 'm'
    else: q = QUAL.get(scale, QUAL['major'])[deg - 1]
    r = (ROMAN_UP if q in ('M', 'a') else ROMAN_LO)[deg - 1]
    lbl = acc + r
    if c.get('type') in (7, '7'): lbl += '7'
    if q == 'd': lbl += '°'
    if c.get('applied'): lbl += f'/{ROMAN_UP[c["applied"] - 1]}'
    return lbl


# ------------------------------------------------------------------ the nine
# C is 29% of all chords, so three quarters of scenes contain one. Its four
# images therefore have to be the most vivid in the grid AND share no register
# with each other — King / crown / canyon were all epic-medieval and smeared
# together. Animal / loud action / spiky plant / neon building do not.
PAO = {
  'C':  ('Gorilla',   'kicking',   'a cactus',  'a casino'),
  'Dm': ('Diver',     'dancing',   'a drum',    'a tunnel'),
  'Em': ('Mermaid',   'mowing',    'a magnet',  'a mine'),
  'F':  ('Pharaoh',   'frying',    'a fork',    'a volcano'),
  'G':  ('Jockey',    'juggling',  'a gem',     'a jungle'),
  'Am': ('Samurai',   'sawing',    'a sponge',  'a swamp'),
  'A#': ('Ballerina', 'boxing',    'a piano',   'a bridge'),
  'D':  ('Wizard',    'welding',   'a wheel',   'a waterfall'),
  'E':  ('Robot',     'rowing',    'a rocket',  'a roof'),
}

def is_rest(c):
    """Hookpad stores a rest as root 0 with isRest true. Nothing here checked
    it, so silence was being labelled vii-dim and then rendered '?' — and a
    single '?' in a bar destroys the whole section's form."""
    return bool(c.get('isRest')) or c.get('root') in (0, '0')


# In a minor key the same roman numerals mean different chords, so the nine
# are reached through the RELATIVE MAJOR (minor -> Am), matching the
# convention used elsewhere in the project. V in minor is a major III (E).
MINOR_NINE = {'i': 'Am', 'III': 'C', 'iv': 'Dm', 'v': 'Em', 'VI': 'F',
              'VII': 'G', 'bVII': 'G', 'V': 'E', 'IV': 'D', 'i7': 'Am'}

# roman label -> one of the nine.  Sevenths and inversions collapse to the
# plain chord: the mnemonic carries the progression, not the voicing.
def to_nine(lbl, scale='major'):
    L = re.sub(r'7|°|sus\d*|add\d*', '', lbl)
    if scale == 'minor' and '/' not in L and L in MINOR_NINE:
        return MINOR_NINE[L]
    if '/' in L:                      # applied dominant
        tgt = L.split('/')[1]
        return {'V':'D', 'VI':'E', 'IV':'C', 'II':'A#'}.get(tgt)
    return {'I':'C', 'ii':'Dm', 'iii':'Em', 'IV':'F', 'V':'G', 'vi':'Am',
            'bVII':'A#', 'VII':'A#', 'vii':'G',
            'II':'D', 'III':'E',
            'bIII':'Em', 'bVI':'Am', 'iv':'F', 'v':'G'}.get(L)


def collapse_loop(seq):
    """A section is usually one loop played N times. F-G-F-G is a two-chord
    loop, not a four-chord progression, and a 16-chord chorus is normally the
    same four bars four times over. Find the shortest period and keep one pass."""
    n = len(seq)
    for p in range(1, n // 2 + 1):
        if n % p == 0 and all(seq[i] == seq[i % p] for i in range(n)):
            return seq[:p]
    return seq


def scene(chords):
    """4 chords -> one sentence. More than 4 -> consecutive scenes."""
    out = []
    for i in range(0, len(chords), 4):
        grp = chords[i:i+4]
        parts = []
        for slot, ch in enumerate(grp):
            if ch is None:
                parts.append('???'); continue
            p, a, o, pl = PAO[ch]
            parts.append([f'A {p.lower()}', a, o, f'in {pl}'][slot])
        out.append(' '.join(parts))
    return ' … then '.join(out)


# ------------------------------------------------------------------ matching
TAGS = ('_o', '_c', '_ly', '_j', '_')
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def strip_tags(stem):
    s, ch = stem.strip('_'), True
    while ch:
        ch = False
        for t in TAGS:
            if s.endswith(t): s, ch = s[:-len(t)], True
        n = re.sub(r'-[0-9a-f]{6}$', '', s)
        if n != s: s, ch = n, True
    return s


def build_index():
    idx = {}
    for p in glob.glob(os.path.join(EXPORT, '*.json')):
        idx.setdefault(norm(strip_tags(os.path.splitext(os.path.basename(p))[0])), []).append(p)
    return idx


def find(slug, idx):
    k = norm(strip_tags(slug))
    if k in idx: return idx[k][0]
    hits = [p for kk, ps in idx.items() if k and (k in kk or kk in k) for p in ps]
    return hits[0] if hits else None


def sections_of(path):
    d = json.load(open(path))
    keys = d.get('keys') or [{}]
    scale = keys[0].get('scale', 'major')
    tonic = keys[0].get('tonic', '?')
    secs = sorted((d.get('sections') or []), key=lambda s: s.get('beat', 0))
    chords = sorted((d.get('chords') or []), key=lambda c: c.get('beat', 0))
    if not secs: secs = [{'name': 'whole song', 'beat': 0}]
    out = []
    for i, s in enumerate(secs):
        lo = s.get('beat', 0)
        hi = secs[i+1].get('beat', 10**9) if i+1 < len(secs) else 10**9
        seq, prev = [], None
        for c in chords:
            b = c.get('beat', 0)
            if lo <= b < hi:
                if is_rest(c): continue
                n = to_nine(chord_label(c, scale), scale)
                if n != prev:                 # collapse consecutive repeats
                    seq.append(n); prev = n
        if seq: out.append((s.get('name', '?'), collapse_loop(seq)))
    return tonic, scale, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50,G100')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/pao-pools.html'))
    a = ap.parse_args()

    want = set(a.pools.split(','))
    pm = json.load(open(POOLS))
    slugs = [s for s, p in pm.items() if p in want]
    idx = build_index()

    rows, missing, unmapped = [], [], collections.Counter()
    for slug in sorted(slugs):
        p = find(slug, idx)
        if not p:
            missing.append(slug); continue
        tonic, scale, secs = sections_of(p)
        keep = []
        for name, seq in secs:
            if any(x is None for x in seq):
                unmapped[sum(1 for x in seq if x is None)] += 1
            keep.append((name, seq))
        rows.append((slug, pm[slug], tonic, scale, keep))

    # ---------- html ----------
    def esc(s): return html.escape(str(s))
    parts = ["""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>PAO — guitar pools</title><style>
@page{margin:.55in}*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Georgia,serif;font-size:9.5pt;line-height:1.38;color:#111;
max-width:7.3in;margin:0 auto;padding:.35in .25in .6in}
h1{font-size:19pt;margin-bottom:2px}
.sub{font-family:-apple-system,sans-serif;font-size:8.5pt;color:#666;margin-bottom:14px}
.song{margin-bottom:11px;page-break-inside:avoid;border-bottom:1px solid #eee;padding-bottom:8px}
.song h2{font-size:11.5pt;display:inline}
.meta{font-family:-apple-system,sans-serif;font-size:7.5pt;color:#999;margin-left:7px}
.sec{display:flex;gap:9px;padding:2px 0}
.sn{font-family:-apple-system,sans-serif;font-size:7.5pt;text-transform:uppercase;
letter-spacing:.05em;color:#999;width:74px;flex:0 0 74px;padding-top:2px}
.pg{font-family:ui-monospace,Menlo,monospace;font-size:8.5pt;color:#555;
width:118px;flex:0 0 118px}
.sc{font-size:10pt}
</style></head><body>
<h1>PAO &mdash; guitar pools</h1>
<p class="sub">Each section as one scene. Degrees, not letters &mdash; the picture
works in any key. Consecutive repeats collapsed.</p>"""]
    for slug, pool, tonic, scale, secs in rows:
        art, _, ttl = strip_tags(slug).partition('_')
        parts.append(f'<div class="song"><h2>{esc(ttl.replace("-"," ").title())}</h2>'
                     f'<span class="meta">{esc(art.replace("-"," ").title())} · '
                     f'{esc(pool)} · {esc(tonic)} {esc(scale)}</span>')
        for name, seq in secs:
            prog = '-'.join(x or '?' for x in seq)
            parts.append(f'<div class="sec"><span class="sn">{esc(name)}</span>'
                         f'<span class="pg">{esc(prog)}</span>'
                         f'<span class="sc">{esc(scene(seq))}</span></div>')
        parts.append('</div>')
    parts.append('</body></html>')
    open(a.out, 'w').write('\n'.join(parts))

    nsec = sum(len(s) for *_, s in rows)
    print(f'songs matched   {len(rows)}/{len(slugs)}')
    print(f'sections        {nsec}')
    print(f'sections with an unmapped chord: {sum(unmapped.values())}')
    if missing:
        print(f'no hookpad file ({len(missing)}):')
        for m in missing[:8]: print('   ', m)
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
