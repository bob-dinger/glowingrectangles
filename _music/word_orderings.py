"""The 24 orderings of ANY four-chord word, with song examples, as a printable sheet.

Generalises goosefish_hunt.py + goosefish_sheet.py to the 44 four-chord words in
chord_words.json. A section counts when its FIRST FOUR chord changes are the word's four
chords in a given order -- whatever it does afterwards. Repeated chords collapsed (a
repeat is harmonic rhythm, not a different progression); verse/chorus/pre-chorus/bridge/
refrain only, first instance per role, one song per variant group.

Colour is by PITCH CLASS of the root in C (music_chord_color_pitchclass), full opacity so
it survives printing; chromatic roots get diagonal stripes of their two diatonic
neighbours. Chord names are the primary label, Roman numerals secondary.

    themap_venv/python word_orderings.py --word CATFISH
    themap_venv/python word_orderings.py --word GOOSEFISH --open
    themap_venv/python word_orderings.py --list
"""
import os, sys, json, argparse, itertools, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of, base_of, richest_first
from goosefish_hunt import bare

WORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chord_words.json')
# chord name in C -> (roman label, full-opacity colour) ; 'stripe' = chromatic
DIA = {'C':('I','#E84545'), 'Dm':('ii','#F0A040'), 'D':('II','#F0A040'),
       'Em':('iii','#E8C828'), 'E':('III','#E8C828'), 'F':('IV','#50C878'),
       'Fm':('iv','#50C878'), 'G':('V','#5090F0'), 'Gm':('v','#5090F0'),
       'Am':('vi','#7040B0'), 'A':('VI','#7040B0'), 'Bdim':('vii','#E070B0'),
       'B':('VII','#E070B0')}
STRIPE = {'A#':('bVII','#7040B0','#E070B0'), 'Bb':('bVII','#7040B0','#E070B0'),
          'G#':('bVI','#5090F0','#7040B0'), 'Ab':('bVI','#5090F0','#7040B0'),
          'D#':('bIII','#F0A040','#E8C828'), 'Eb':('bIII','#F0A040','#E8C828'),
          'C#':('bII','#E84545','#F0A040'), 'Db':('bII','#E84545','#F0A040'),
          'F#':('#IV','#50C878','#5090F0')}

def fill(ch):
    if ch in STRIPE:
        _, a, b = STRIPE[ch]
        return (f"background:repeating-linear-gradient(45deg,{a} 0 1.6mm,{b} 1.6mm 3.2mm)")
    return f"background:{DIA[ch][1]}"

def label_of(ch):
    return DIA[ch][0] if ch in DIA else STRIPE[ch][0]

def scan(labels):
    """labels: the four Roman labels, e.g. ['I','ii','IV','V'] -> {ordering: [hits]}"""
    want = {l: str(i) for i, l in enumerate(labels, 1)}
    out = collections.defaultdict(list); seen = set()
    songs = richest_first(corpus.songs(need_chords=True))
    for name, d, nb in songs:
        chords = sorted([c for c in (d.get('chords') or []) if c.get('root')],
                        key=lambda c: c['beat'])
        if not chords: continue
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            used.add(role)
            if (base_of(name), role) in seen: continue
            seen.add((base_of(name), role))
            end = min(b1, d.get('endBeat') or 10**9)
            seq, prev = [], None
            for c in chords:
                if not (b0 <= c['beat'] < end): continue
                lab = bare(corpus.roman(c, corpus.mode_at(d, c['beat'])))
                if lab != prev: seq.append(lab); prev = lab
            if len(seq) < 4: continue
            head = seq[:4]
            if any(x not in want for x in head) or len(set(head)) != 4: continue
            out['-'.join(want[x] for x in head)].append(
                (name, sec, role, int((end-b0)//4), ' '.join(seq[:12])))
    return out

def title(s):
    art, _, song = str(s).partition('_')
    nice = lambda x: ' '.join(w if w.isupper() else w.capitalize() for w in x.split())
    return f"{nice(art)} &ndash; {nice(song)}" if song else nice(s)

CSS = """@page{size:letter;margin:14mm 12mm}*{box-sizing:border-box}
body{margin:0 auto;max-width:196mm;padding:10mm 8mm;font:10.5pt/1.35 "Helvetica Neue",Helvetica,Arial,sans-serif;color:#1a1a1a;background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1{font-size:16pt;margin:0 0 2mm;letter-spacing:-.2pt}
h1 em{font-style:normal;color:#666;font-weight:400}
.lede{font-size:9pt;color:#555;margin:0 0 6mm;max-width:150mm}.lede b{color:#1a1a1a}
.cycle{break-inside:avoid;margin:0 0 7mm}
.chead{display:flex;align-items:baseline;gap:4mm;border-bottom:1.5pt solid #1a1a1a;padding-bottom:1.2mm;margin-bottom:2.5mm}
.chead .map{font-size:11.5pt;font-weight:700}.chead .n{font-size:8.5pt;color:#666;margin-left:auto}
.row{display:flex;align-items:center;gap:4mm;padding:1.6mm 0;border-bottom:.4pt solid #e2e2e2;break-inside:avoid}
.row:last-child{border-bottom:0}
.chips{display:flex;gap:1.2mm;flex:0 0 48mm}
.chip{flex:1;text-align:center;border-radius:1.4mm;padding:1.4mm .5mm 1mm;color:#fff;text-shadow:0 0 1.2mm rgba(0,0,0,.45)}
.chip b{display:block;font-size:12pt;line-height:1;letter-spacing:-.3pt}
.chip i{display:block;font-size:6.5pt;font-style:normal;opacity:.88;margin-top:.5mm}
.meta{flex:0 0 32mm}.meta .name{font-weight:700;font-size:9.5pt}
.meta .un{color:#999;font-weight:400;font-style:italic}.meta .cnt{font-size:8pt;color:#666}
.ex{flex:1;font-size:8.5pt;color:#333}.ex span{white-space:nowrap}.ex .sec{color:#777}
.ex .more{color:#999;font-style:italic}
.none{flex:1;font-size:9pt;color:#b00;font-weight:600}
.foot{margin-top:6mm;font-size:8pt;color:#666;border-top:.4pt solid #ccc;padding-top:2mm}
@media print{body{padding:0;max-width:none}}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--word', default='GOOSEFISH')
    ap.add_argument('--max', type=int, default=6, help="examples shown per ordering")
    ap.add_argument('--list', action='store_true'); ap.add_argument('--open', action='store_true')
    a = ap.parse_args()
    words = json.load(open(WORDS))
    if a.list:
        for k, v in sorted(words.items()):
            if len(v) == 4: print(f"  {k:14} {' '.join(v)}")
        return
    w = a.word.upper()
    if w not in words: sys.exit(f"no chord word {w!r} (try --list)")
    chs = words[w]
    if len(chs) != 4: sys.exit(f"{w} has {len(chs)} chords, this sheet wants 4")
    labels = [label_of(c) for c in chs]
    found = scan(labels)
    NAME = {str(i): c for i, c in enumerate(chs, 1)}
    LAB = {str(i): l for i, l in enumerate(labels, 1)}
    orders = ['-'.join(p) for p in itertools.permutations('1234')]
    canon = lambda f: min(''.join((d := f.split('-'))[i:] + d[:i]) for i in range(4))
    cls = collections.defaultdict(list)
    for o in orders: cls[canon(o)].append(o)
    used = sum(1 for o in orders if found.get(o)); nsec = sum(len(v) for v in found.values())

    H = [f'<!doctype html><meta charset="utf-8"><title>{w}: 24 orderings</title>',
         f'<style>{CSS}</style>',
         f'<h1>{w} &nbsp;<em>{" &middot; ".join(chs)}</em></h1>',
         f'<p class="lede">The 24 orderings of these four chords. A section counts when '
         f'its <b>first four chord changes</b> are them in this order &mdash; whatever it '
         f'does next. Repeats collapsed; verse / chorus / pre-chorus / bridge only; one '
         f'song per variant. <b>{used} of 24</b> orderings open at least one section, '
         f'across <b>{nsec}</b> sections. All 24 occur as chord <i>runs</i>, since a loop '
         f'holds all four of its rotations at once &mdash; what differs is where a section '
         f'begins.</p>']
    for k in sorted(cls, key=lambda k: -sum(len(found.get(o, [])) for o in cls[k])):
        tot = sum(len(found.get(o, [])) for o in cls[k])
        arrows = ' &rarr; '.join(LAB[c] for c in k) + ' &rarr; ' + LAB[k[0]]
        H.append(f'<div class="cycle"><div class="chead"><span class="map">{arrows}</span>'
                 f'<span class="n">{tot} sections</span></div>')
        for o in cls[k]:
            hits = sorted(found.get(o, []), key=lambda h: -h[3])
            chips = ''.join(f'<div class="chip" style="{fill(NAME[c])}">'
                            f'<b>{NAME[c]}</b><i>{LAB[c]}</i></div>' for c in o.split('-'))
            if hits:
                ex = ' &nbsp;&middot;&nbsp; '.join(
                    f'<span>{title(n)} <span class="sec">{s}</span></span>'
                    for n, s, role, bars, full in hits[:a.max])
                if len(hits) > a.max: ex += f' <span class="more">+{len(hits)-a.max} more</span>'
                body = f'<div class="ex">{ex}</div>'
            else:
                body = '<div class="none">no section in the library opens here</div>'
            H.append(f'<div class="row"><div class="chips">{chips}</div><div class="meta">'
                     f'<div class="name un">&nbsp;</div><div class="cnt">{len(hits)} '
                     f'section{"" if len(hits)==1 else "s"}</div></div>{body}</div>')
        H.append('</div>')
    H.append(f'<p class="foot">Colour by pitch class of the root in C. '
             + ' &nbsp; '.join(f'<b>{c}</b> = {l}' for c, l in zip(chs, labels))
             + '. Generated by _music/word_orderings.py</p>')
    out = os.path.expanduser(f'~/Desktop/{w.lower()}_24.html')
    open(out, 'w').write('\n'.join(H))
    print(f"\n  {w}  {' '.join(chs)}  =  {' '.join(labels)}")
    print(f"  {used} of 24 orderings open a section, {nsec} sections, {len(cls)} cycles")
    for k in sorted(cls, key=lambda k: -sum(len(found.get(o, [])) for o in cls[k])):
        tot = sum(len(found.get(o, [])) for o in cls[k])
        print(f"    cycle {'-'.join(LAB[c] for c in k):18} {tot:4} sections   "
              + '  '.join(f"{'-'.join(NAME[c] for c in o.split('-'))}={len(found.get(o,[]))}"
                          for o in cls[k]))
    print(f"  -> {out}")
    if a.open: os.system(f'open "{out}"')

if __name__ == '__main__':
    main()
