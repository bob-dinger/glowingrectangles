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
import argparse, collections, difflib, glob, html, json, os, re, sys

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
    if c.get('applied'):
        # Hookpad writes an applied dominant as <applied>/<root>: `applied` is
        # the NUMERAL and `root` is the TARGET. So root 6 + applied 5 is V/vi,
        # which in C major sounds as E. This was emitting VI/V — backwards —
        # and to_nine then resolved it to the wrong pitch.
        tgt = (ROMAN_UP if QUAL.get(scale, QUAL['major'])[deg-1] in ('M','a')
               else ROMAN_LO)[deg - 1]
        return f'{ROMAN_UP[c["applied"] - 1]}/{tgt}'
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

def quality(c, scale='major'):
    """What to print after the letter: 7, maj7, sus4, add9 and so on.

    8.8% of chords in the pools carry something past a plain triad — 324
    sevenths and 308 suspensions — and the sheet was throwing all of it away,
    so a Dsus4 read as D. Hookpad's `type: 7` means a diatonic seventh, whose
    quality follows the degree: I and IV take a major 7th, V a dominant, the
    minor degrees a minor 7th (already implied by the m in the name).
    """
    bits = []
    root = str(c.get('root', ''))
    rs = root.lstrip('b#')
    deg = int(rs) if rs.isdigit() else 0
    if c.get('type') in (7, '7'):
        if c.get('applied'): bits.append('7')          # applied = dominant
        elif deg in (1, 4): bits.append('maj7')
        elif deg == 7: bits.append('7')                # bVII7
        else: bits.append('7')                         # m7 via the name's m
    elif c.get('type') in (11, '11'): bits.append('11')
    sus = tuple(c.get('suspensions') or ())
    if sus == (2,): bits.append('sus2')
    elif sus == (4,): bits.append('sus4')
    elif sus: bits.append('sus' + ''.join(str(x) for x in sus))
    for x in (c.get('adds') or []): bits.append(f'add{x}')
    for x in (c.get('alterations') or []): bits.append(str(x))
    return ''.join(bits)


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
# an applied dominant is a fifth above its target and always major. Some of
# those land outside the nine white-note chords (V/iii is B major), so they
# carry their own tokens which chord_key.actual() resolves against the key.
APPLIED = {'V/I':'@7', 'V/ii':'@9', 'V/II':'@9', 'V/iii':'@11', 'V/III':'@11',
           'V/IV':'@0', 'V/V':'@2', 'V/vi':'@4', 'V/VI':'@4', 'V/vii':'@6',
           'V/bVII':'@5'}


def to_nine(lbl, scale='major'):
    L = re.sub(r'7|°|sus\d*|add\d*', '', lbl)
    if L in APPLIED: return APPLIED[L]
    if scale == 'minor' and '/' not in L and L in MINOR_NINE:
        return MINOR_NINE[L]
    if '/' in L:                      # an applied form we have no token for
        return None
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


# An applied dominant normalises to `@<semitone above tonic>`, which is not
# one of the nine images. It is always a MAJOR chord, so read it by pitch
# class: @7 is the V chord, @2 is V/V and lands on D. The five semitones with
# no white-note chord have no image and stay unknown.
APPLIED_NINE = {0: 'C', 2: 'D', 4: 'E', 5: 'F', 7: 'G', 9: 'Am', 10: 'A#'}


def nine_of(tok):
    """Any chord token -> one of the nine PAO keys, or None."""
    t = (tok or '').split('~')[0]
    if t in PAO: return t
    if t.startswith('@'):
        try: return APPLIED_NINE.get(int(t[1:]) % 12)
        except ValueError: return None
    return None


def scene(chords):
    """4 chords -> one sentence. More than 4 -> consecutive scenes."""
    out = []
    for i in range(0, len(chords), 4):
        grp = chords[i:i+4]
        parts = []
        for slot, ch in enumerate(grp):
            if ch is None:
                parts.append('???'); continue
            k = nine_of(ch)
            if not k:
                parts.append('???'); continue
            p, a, o, pl = PAO[k]
            parts.append([f'A {p.lower()}', a, o, f'in {pl}'][slot])
        out.append(' '.join(parts))
    return ' … then '.join(out)


# ------------------------------------------------------------------ matching
TAGS = ('_o', '_c', '_ly', '_j', '_z', '_')

# A `-tag` suffix marks a VARIANT that lives beside the song, not a newer copy
# of it: `-hooktab` is somebody else's chords, `-simple` a reduction, `-150` a
# tempo re-frame, `-C` a transposition. They are their own songs, so a variant
# must never be returned for a bare slug -- preferring the newest file outright
# handed the G50 sheet 100+ hooktab imports in place of the user's own charts.
VARIANT = re.compile(
    r'-(?:hooktab|hooktabs|hookpad|theorytab|ug|simple\d*|simplified|right|wrong'
    r'|double|half|mixolydian|dorian|lydian|phrygian|aeolian|alt\d*|v\d+'
    r'|\d{2,3}|[A-Ga-g][b#]?)$')


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


def split_variant(stem):
    """('bob dylan_tangled up in blue', 'hooktab') -- base name + variant tag."""
    s = strip_tags(stem)
    m = VARIANT.search(s)
    return (s[:m.start()], s[m.start() + 1:]) if m else (s, '')


def build_index():
    """base key -> [(path, variant_tag), ...]"""
    idx = {}
    for p in glob.glob(os.path.join(EXPORT, '*.json')):
        base, tag = split_variant(os.path.splitext(os.path.basename(p))[0])
        idx.setdefault(norm(base), []).append((p, tag))
    return idx


def _tokens(s):
    # Apostrophes have to go BEFORE splitting, or "won't" tokenises as
    # {won, t}. A pool slug spells the same apostrophe as a hyphen -- `won-t`
    # -- which survives that, so one-letter tokens are dropped as contraction
    # debris. "I" and "A" go too, which is what we want: the retitle from
    # "Won't Back Down" to "I Won't Back Down" should still match.
    s = strip_tags(s).lower().replace("'", '').replace('\u2019', '')
    return set(t for t in re.split(r'[^a-z0-9]+', s) if len(t) > 1)


def find(slug, idx):
    """Resolve a pool slug to a file.

    Three traps, all of which silently served the wrong chords:

    1. The export accumulates duplicates -- a rename in Hookpad writes a new
       file beside the old one -- so among equals the newest wins.
    2. `-hooktab` and friends are variants, not updates (see VARIANT); a bare
       slug must resolve to the base song even when a variant is newer.
    3. A retitle can add or drop a word ("Won't Back Down" -> "I Won't Back
       Down"), which no substring test catches. Fall back to token overlap.
    """
    want_base, want_tag = split_variant(strip_tags(slug))
    k = norm(want_base)
    cands = list(idx.get(k) or [])

    if not cands:                                   # substring, then tokens
        cands = [c for kk, cs in idx.items()
                 if k and (k in kk or kk in k) for c in cs]
    if not cands:
        # Token overlap alone says "Won't Back Down" and "I Won't Back Down"
        # are 0.8 alike -- but so are plenty of genuinely different titles, so
        # the squashed strings have to be close too.
        wt, ws = _tokens(slug), norm(strip_tags(slug).replace("'", ''))
        best, score = [], 0.0
        for kk, cs in idx.items():
            for p, tag in cs:
                st = os.path.splitext(os.path.basename(p))[0]
                ft, fs = _tokens(st), norm(strip_tags(st).replace("'", ''))
                if not wt or not ft: continue
                ov = len(wt & ft) / max(len(wt), len(ft))
                sim = difflib.SequenceMatcher(None, ws, fs).ratio()
                # A perfect token match with a poor string ratio means the
                # slug has artist and title the other way round
                # ('celebrity-skin_hole'), which is still the same song.
                if ov < 1.0 and (ov < 0.7 or sim < 0.85): continue
                s = ov * sim
                if s > score: best, score = [(p, tag)], s
                elif s == score and score: best.append((p, tag))
        cands = best
    if not cands: return None

    exact = [c for c in cands if c[1] == want_tag]
    base  = [c for c in cands if not c[1]]
    pick  = exact or base or cands
    return max(pick, key=lambda c: os.path.getmtime(c[0]))[0]


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
