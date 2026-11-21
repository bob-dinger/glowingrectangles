"""Find real songs using each of the 24 orderings of the GOOSEFISH palette.

GOOSEFISH (chord_words.json) = C F G Am = I IV V vi. Bennett names only 9 of its 24
orderings; this looks for the other 15 in the user's own library.

Only verse / chorus / pre-chorus / bridge / refrain count. The user: "I don't like to
count outros, they're usually just a part of the song repeated and I don't like running
analysis on it." First instance per role only, and variant files (-hooktab, -C, -right)
collapse to the base song, so one song cannot supply the same progression twice.

How a section qualifies: take its chords in order, collapse consecutive repeats (a
repeated chord is harmonic rhythm, not a different progression -- Bennett's own point),
and keep it if the result is a clean repeating 4-cycle drawn from exactly {I, IV, V, vi}.
The ordering recorded is the one the SECTION STARTS ON, because that is what separates
Axis from Angels from Other axis.

Labels come from chord_label, which references the RELATIVE MAJOR in both modes -- so a
minor-key song playing Am F C G still reads vi IV I V and still counts. Extensions are
stripped (Imaj7 counts as I) but qualities are not: a major III or a minor v is a
different chord and disqualifies the section.

    themap_venv/python goosefish_hunt.py
    themap_venv/python goosefish_hunt.py --missing     # only the unnamed orderings
    themap_venv/python goosefish_hunt.py --order 1-4-5-6
"""
import os, sys, re, argparse, itertools, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of, base_of, richest_first

EXT = re.compile(r'(sus\d*|add\d+|maj\d*|dim|aug|no5|\(no5\)|\d+|[#b]\d+|\+|\-)+')
WANT = {'I': '1', 'IV': '4', 'V': '5', 'vi': '6'}
NAMED = {  # from named_progressions.xlsx / his videos
 '1-5-6-4': 'Axis', '4-1-5-6': 'Another axis', '5-6-4-1': 'Angels', '6-4-1-5': 'Other axis',
 '1-6-4-5': 'Doo-wop / 50s', '4-5-1-6': 'Viva la Vida', '1-4-6-5': 'Mr. Brightside',
 '6-1-5-4': 'Polly', '1-6-5-4': 'Purple Rain'}

def bare(lab):
    out = []
    for p in lab.split('/'):
        prev = None
        while p != prev: prev = p; p = EXT.sub('', p)
        out.append(p or prev)
    return '/'.join(out)

def cycle_of(seq):
    """If seq is a repeating 4-cycle of the four wanted degrees, return it as a figure."""
    if len(seq) < 4: return None
    if any(s not in WANT for s in seq): return None
    head = seq[:4]
    if len(set(head)) != 4: return None
    if any(seq[i] != head[i % 4] for i in range(len(seq))): return None
    return '-'.join(WANT[s] for s in head)

def scan():
    found = collections.defaultdict(list)
    seen = set()
    # base files FIRST, so a variant never blocks the real one from claiming its slot
    allsongs = richest_first(corpus.songs(need_chords=True))
    for name, d, nb in allsongs:
        chords = sorted([c for c in (d.get('chords') or []) if c.get('root')],
                        key=lambda c: c['beat'])
        if not chords: continue
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue   # no intros/outros/solos
            used.add(role)
            if (base_of(name), role) in seen: continue  # one per song, not per variant
            seen.add((base_of(name), role))
            end = min(b1, d.get('endBeat') or 10**9)
            inn = [c for c in chords if b0 <= c['beat'] < end]
            if len(inn) < 4: continue
            seq, prev = [], None
            for c in inn:
                lab = bare(corpus.roman(c, corpus.mode_at(d, c['beat'])))
                if lab != prev: seq.append(lab); prev = lab
            fig = cycle_of(seq)
            if fig:
                found[fig].append((name, sec, int((end-b0)//4), len(seq)//4))
    return found

def scan_opens():
    """Sections whose FIRST FOUR chord changes are the four goosefish chords in some
    order -- regardless of what the section does afterwards.

    This is the looser and more honest test. Requiring the WHOLE section to be a clean
    4-cycle threw away real cases: Teenage Dirtbag's chorus opens C F G Am then adds a
    iii, and Taylor Swift's Trouble bridge opens C G F Am then continues IV V. Under the
    strict rule 19 of 24 orderings were used; under this one, 22.
    """
    out = collections.defaultdict(list)
    seen = set()
    allsongs = richest_first(corpus.songs(need_chords=True))
    for name, d, nb in allsongs:
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
            if any(x not in WANT for x in head) or len(set(head)) != 4: continue
            out['-'.join(WANT[x] for x in head)].append(
                (name, sec, role, int((end-b0)//4), ' '.join(seq[:12])))
    return out


def write_text(path):
    """The whole picture as a plain text file, grouped by cycle."""
    found = scan_opens()
    CH = {'1': 'C', '4': 'F', '5': 'G', '6': 'Am'}
    RN = {'1': 'I', '4': 'IV', '5': 'V', '6': 'vi'}
    orders = ['-'.join(p) for p in itertools.permutations('1456')]
    def canon(f):
        d = f.split('-'); return min(''.join(d[i:]+d[:i]) for i in range(4))
    cls = collections.defaultdict(list)
    for o in orders: cls[canon(o)].append(o)
    n_used = sum(1 for o in orders if found.get(o))
    L = []
    L.append("THE 24 ORDERINGS OF C / F / G / Am   (GOOSEFISH = I IV V vi)")
    L.append("=" * 74)
    L.append("")
    L.append("A section counts here when its FIRST FOUR chord changes are these four")
    L.append("chords in this order -- whatever it does afterwards. Consecutive repeats")
    L.append("are collapsed, since a repeated chord is harmonic rhythm, not a different")
    L.append("progression. verse/chorus/pre-chorus/bridge/refrain only, first instance")
    L.append("per role, one song per variant group.")
    L.append("")
    L.append(f"{n_used} of the 24 orderings open at least one section.")
    L.append("All 24 occur as chord RUNS, because a looping cycle contains all four of")
    L.append("its rotations at once -- what differs is where a section begins.")
    L.append("")
    for k in sorted(cls, key=lambda k: -sum(len(found.get(o, [])) for o in cls[k])):
        tot = sum(len(found.get(o, [])) for o in cls[k])
        L.append("")
        L.append("-" * 74)
        L.append(f"CYCLE {k}    " + "  ".join(
            f"{RN[a]}->{RN[b]}" for a, b in zip(k, k[1:]+k[0])) + f"    {tot} sections")
        L.append("-" * 74)
        for o in cls[k]:
            hits = sorted(found.get(o, []), key=lambda h: -h[3])
            nm = NAMED.get(o, '')
            L.append("")
            L.append(f"  {o}   {' '.join(CH[c] for c in o.split('-')):11}"
                     f"{'-'.join(RN[c] for c in o.split('-')):13}"
                     f"{len(hits):3} sections   {nm or '(unnamed)'}")
            if not hits:
                L.append("        no section in the library opens on this")
                continue
            for name, sec, role, bars, full in hits[:12]:
                L.append(f"        {name[:38]:38} {sec[:13]:13} {bars:3}b  {full[:40]}")
            if len(hits) > 12:
                L.append(f"        ... and {len(hits)-12} more")
    L.append("")
    open(path, 'w').write("\n".join(L) + "\n")
    return path, n_used, sum(len(v) for v in found.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--missing', action='store_true', help="only the unnamed orderings")
    ap.add_argument('--order'); ap.add_argument('--max', type=int, default=6)
    ap.add_argument('--text', nargs='?', const=os.path.expanduser(
        '~/Desktop/goosefish_24_orderings.txt'),
        help="write the whole picture to a text file (opens-on rule)")
    a = ap.parse_args()
    if a.text:
        path, used, n = write_text(a.text)
        print(f"\n  {n} sections, {used} of 24 orderings used as an opening")
        print(f"  -> {path}\n")
        return
    found = scan()
    orders = ['-'.join(p) for p in itertools.permutations('1456')]
    CH = {'1': 'C', '4': 'F', '5': 'G', '6': 'Am'}
    RN = {'1': 'I', '4': 'IV', '5': 'V', '6': 'vi'}
    if a.order: orders = [a.order]
    elif a.missing: orders = [o for o in orders if o not in NAMED]
    orders.sort(key=lambda o: -len(found.get(o, [])))
    tot = sum(len(v) for v in found.values())
    print(f"\n  {tot} sections in the library are a clean 4-cycle of C/F/G/Am\n")
    for o in orders:
        hits = found.get(o, [])
        tag = NAMED.get(o, '-- UNNAMED --')
        print(f"  {o}   {' '.join(CH[c] for c in o.split('-')):10} "
              f"{'-'.join(RN[c] for c in o.split('-')):12} {len(hits):4} sections   {tag}")
        for name, sec, bars, loops in sorted(hits, key=lambda h: -h[3])[:a.max]:
            print(f"        {name[:40]:40} {sec[:14]:14} {bars:3} bars, loops x{loops}")
        if not hits: print(f"        none")
    print()

if __name__ == '__main__':
    main()