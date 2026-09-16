#!/usr/bin/env python3
"""
Read a section as BARS and 4-bar chunks, not as a chord list.

A chord list throws away the thing that makes a progression learnable: where
the bar lines are and which four-bar phrase repeats. This groups chords into
bars using beat+duration, chunks the bars into fours, and labels repeated
chunks A/B/C so the section reads as a form.

    python3 bars.py "nashville blues"
    python3 bars.py "maggie may" --section chorus
"""
import argparse, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_pools as pp

EXPORT = os.path.expanduser('~/Desktop/music/hookpad_songs_full')


def beats_per_bar(d):
    m = (d.get('meters') or [{}])[0]
    num = m.get('numBeats') or m.get('num') or m.get('numerator') or 4
    return float(num or 4)


def bars_for(path, with_beats=False, with_quality=False):
    """-> (tonic, scale, bpb, [(section_name, [bar, ...]), ...])

    with_beats=True yields (name, bars, start_beat) instead. Callers that need
    the key in effect at a section must have the beat: matching sections by
    NAME is wrong whenever a name repeats, and it silently gave both of
    Heaven's pre-choruses the first one's key.
    each bar is a tuple of chord labels sounding in it, in order."""
    d = json.load(open(path))
    k = (d.get('keys') or [{}])[0]
    scale = k.get('scale', 'major')
    bpb = beats_per_bar(d)
    chords = sorted((d.get('chords') or []), key=lambda c: c.get('beat', 0))
    secs = sorted((d.get('sections') or []), key=lambda s: s.get('beat', 0)) \
           or [{'name': 'whole song', 'beat': 1}]

    out = []
    for i, s in enumerate(secs):
        lo = s.get('beat', 1)
        hi = secs[i+1].get('beat', 10**9) if i+1 < len(secs) else 10**9
        inside = [c for c in chords
                  if lo <= c.get('beat', 0) < hi and not pp.is_rest(c)]
        if not inside: continue
        bars = {}
        for c in inside:
            lbl = pp.to_nine(pp.chord_label(c, scale), scale) or '?'
            if with_quality:
                q = pp.quality(c, scale)
                if q: lbl = f'{lbl}~{q}'      # chord_key.actual splits on ~
            b = int((c.get('beat', 1) - lo) // bpb) + 1     # bar within section
            bars.setdefault(b, [])
            if not bars[b] or bars[b][-1] != lbl:           # same chord held = once
                bars[b].append(lbl)
        n = max(bars) if bars else 0
        bl = [tuple(bars.get(j, ['·'])) for j in range(1, n + 1)]
        # An empty bar at either edge is silence, not a pickup. Leaving it in
        # gave In My Place's outro a phantom "(·)" pickup and shifted the
        # phase of every phrase after it.
        while bl and bl[0] == ('·',): bl.pop(0)
        while bl and bl[-1] == ('·',): bl.pop()
        if bl: out.append((s.get('name', '?'), bl, s.get('beat', 1)))
    if not with_beats:
        out = [(nm, bl) for nm, bl, _ in out]
    return k.get('tonic', '?'), scale, bpb, out


def chunk(bars, n):
    return [tuple(bars[i:i+n]) for i in range(0, len(bars), n)]


def cell_of(seq):
    """Shortest repeating cell, allowing an incomplete final pass.

    -> (cell, full_repeats, tail)

    Two things the old collapse_loop got wrong. It only found EXACT whole-
    length periods, so C-G-F-C-G-F-C (a cell twice, then the landing) stayed
    seven chords. And it ran on chords AFTER adjacent duplicates had been
    squashed, which is fatal: |C|C|F|C| twice is 8 bars, but squashing the
    held C first gives C-F-C-F-C, and nothing about that looks periodic any
    more. Period-finding must happen on BARS, before any collapsing.
    """
    n = len(seq)
    best = None
    for p in range(1, n // 2 + 1):
        k = 1
        while (k + 1) * p <= n and all(seq[i] == seq[i % p]
                                       for i in range(k * p, (k + 1) * p)):
            k += 1
        if k < 2: continue
        # the tail is whatever is left and may be NEW material, not just a
        # prefix of the cell: |C|F| |C|F| |G| is the cell twice then an
        # ending, and demanding a prefix there leaves it as five chords.
        cover = k * p
        # A cell has to cover most of the phrase to be worth calling a cell.
        # |C|C| repeating twice inside |C|C|F|C|C|C|F|G| is technically a
        # period and tells you nothing — that phrase is A A', not "C x2 then
        # five more chords".
        if cover * 2 < n: continue
        if best is None or (cover, -p) > (best[0], -best[1]):
            best = (cover, p, k)
    if not best: return list(seq), 1, []
    _, p, k = best
    return list(seq[:p]), k, list(seq[p * k:])


def phrase_chords(chunk):
    """A chunk of bars -> (chord changes to encode, repeats, tail).

    Reduce to the cell first, then read chord changes inside it: a chord held
    over a bar line is one chord, not one per bar.
    """
    cell, reps, tail = cell_of(list(chunk))
    flat = []
    for bar in cell:
        for lbl in bar:
            if lbl in ('\u00b7', '?'): continue
            if not flat or flat[-1] != lbl: flat.append(lbl)
    tflat = []
    for bar in tail:
        for lbl in bar:
            if lbl in ('\u00b7', '?'): continue
            if not tflat or tflat[-1] != lbl: tflat.append(lbl)
    return flat, reps, tflat


def forms(bars):
    """The section read at every plausible phrase length.

    Chunk size must NOT be hardcoded: a phrase may be 1, 2, 4 or 8 bars, and
    a 4-bar chunker silently pairs up 2-bar phrases and loses the form. The
    same section is a real form at several scales (the user's point about this
    being fractal), so report them all and let the eye choose.
    """
    out = []
    # 3 and 6 matter: a phrase like |Am|G|C| is three bars, and a chunker that
    # only tries powers of two cannot see AABA in it at all.
    for n in (2, 4, 3, 8, 6, 1):
        if n > len(bars): continue
        # ...and the phrase need not start at bar 1. In My Place's outro is a
        # pickup bar then |C|Am|Em|G| six times; chunking from bar 1 sees the
        # cell ROTATED (|G|C|Am|Em|) and reports A B B B B B instead of A x6.
        # So search the offset too, preferring 0 when it ties.
        for off in range(n):
            body = bars[off:]
            full = len(body) // n
            if full < 2: continue
            ch = chunk(body[:full * n], n)
            labs, uniq = letters(ch)
            widest = max((len(phrase_chords(c)[0]) for c in ch), default=0)
            nbase = len({l.rstrip("'") for l in labs})
            out.append(dict(n=n, off=off, head=bars[:off], tail=body[full * n:],
                            chunks=ch, labs=labs, uniq=uniq, widest=widest,
                            nbase=nbase, shape=shape(labs),
                            ratio=nbase / len(ch)))
    # Order: readings that actually repeat first, then by convention, and only
    # then by how much they repeat. Sorting on the ratio first always elects
    # 1-bar chunks (their alphabet is tiny) and always reads as noise.
    PREF = {4: 0, 2: 1, 3: 2, 8: 3, 6: 4, 1: 5}
    # A phrase also has to be DRAWABLE: a scene holds four slots, so a reading
    # whose phrase carries seven chord changes loses to a shorter one that
    # repeats less but fits. Texas Time Travelin' is AAAA over |C G|Am F|C G|F|
    # — perfect repetition, seven changes, impossible to picture.
    # Leftover bars are ranked BEFORE the ratio, or the offset search quietly
    # cheats: ABAC (4 phrases, nothing left over) loses to AAA plus a
    # four-bar "tail", which scores better only because the departing final
    # phrase has been swept out of the count. Leftover material is real music
    # — an ending — and hiding it fakes a lower picture count.
    # Being a SAYABLE form outranks being drawable. Roll With The Changes'
    # chorus is A B A C over 4-bar phrases, one of which carries five chord
    # changes; penalising that first demoted it below a 1-bar reading with
    # eight letters, which is not a form at all. Order: repeats, few enough
    # letters to say, fits a scene, conventional length, nothing left over.
    out.sort(key=lambda d: (d['ratio'] >= 1, d['nbase'] > 4, d['widest'] > 4,
                            PREF[d['n']], len(d['head']) + len(d['tail']),
                            round(d['ratio'], 3), d['off'] != 0))
    return out


def variant(a, b):
    """Is b the same phrase as a with a different ending?

    Only the LAST bar may differ. That difference is the cadence, and swapping
    it is how songs answer a phrase — |C|F|G|G| then |C|F|G|C| is A then A',
    the commonest 16-bar move there is. Exact matching calls those A and B and
    so turns AABA into ABAB, hiding the form completely.

    A difference EARLIER in the phrase is a genuinely different phrase, not a
    variant, which is why this is not a general similarity score.
    """
    # len>=2 is essential: for one-bar chunks a[:-1] == b[:-1] compares two
    # empty lists, so EVERY bar becomes a prime of A and a section reads as
    # AAAAAAAA with A''''' cells that share nothing. A single bar has no body
    # to hold constant, so it cannot be a variant of anything.
    return (len(a) == len(b) >= 2 and a[:-1] == b[:-1] and a[-1] != b[-1])


def reduced_key(ch):
    """What a chunk amounts to musically: its cell, its repeats, its tail.

    Two chunks can differ bar-for-bar and still be the same thing to learn.
    |G Dm|Am| and |G Dm|Dm Am| are both G-Dm-Am — one merely re-strikes the
    Dm across the bar line. Labelling those A and A' invents a distinction
    you would never hear, so equality is tested on the reduction.
    """
    core, reps, tail = phrase_chords(ch)
    return (tuple(core), reps, tuple(tail))


def letters(chunks, fuzzy=True):
    """A/B/C labels, with A' for 'A but ending elsewhere'.

    A prime costs no extra picture — you learn A and the note 'end on C' —
    so primes are tracked separately from base letters.
    """
    keys = [reduced_key(c) for c in chunks]
    bases, prim, out = [], {}, []
    for ch, k in zip(chunks, keys):
        lab = next((L for L, _, bk in bases if bk == k), None)
        if lab is None and fuzzy:
            for L, b, bk in bases:
                if variant(b, ch) and bk != k:
                    vs = prim.setdefault(L, [])
                    if k not in vs: vs.append(k)
                    lab = L + "'" * (vs.index(k) + 1)
                    break
        if lab is None:
            lab = chr(ord('A') + len(bases))
            bases.append((lab, ch, k))
        out.append(lab)
    uniq = {L: c for L, c, _ in bases}
    for L, c, _ in bases:
        for i, _k in enumerate(prim.get(L, [])):
            uniq[L + "'" * (i + 1)] = next(
                ch for ch, kk in zip(chunks, keys) if kk == _k)
    return out, uniq


def sayable(f):
    """Is this reading a form you could say aloud, or just a chord list?

    'Any 1-bar reading is noise' was too absolute. It holds when each bar
    carries one chord — then 1-bar letters are the chord list relabelled. But
    Mainstreet's chorus is |Am D|Am D|A# C|Am D|, two chords to the bar, and
    that is a genuine AABA. So allow a 1-bar reading when it stays within
    three letters, and reject any reading needing more than four.
    """
    if f['nbase'] > 4: return False
    if f['n'] == 1 and f['nbase'] > 3: return False
    return True


def shape(labs):
    """The form with primes collapsed: A A B A' -> AABA."""
    return ''.join(l.rstrip("'") for l in labs)


def render_bar(b):
    return ' '.join(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--section', default=None)
    ap.add_argument('--all-scales', action='store_true',
                    help='show the form at 1, 2, 4 and 8-bar phrase lengths')
    a = ap.parse_args()

    hits = [p for p in glob.glob(os.path.join(EXPORT, '*.json'))
            if pp.norm(a.query) in
               pp.norm(os.path.basename(p)[:-5])]
    if not hits: sys.exit(f'no file matching {a.query!r}')
    path = sorted(hits, key=len)[0]

    tonic, scale, bpb, secs = bars_for(path)
    print(f'\n{os.path.basename(path)[:-5]}   key {tonic} {scale}   {bpb:g} beats/bar')

    for name, bars in secs:
        if a.section and a.section.lower() not in str(name).lower(): continue
        fs = forms(bars)
        if not fs: continue
        print(f'\n  {name}   {len(bars)} bars')
        keep = fs if a.all_scales else [f for f in fs if f['n'] in (2, 3, 4)][:2]
        for f in keep:
            print(f'     {f["n"]}-bar phrases -> {" ".join(f["labs"])}')
            for lab, ch in sorted({l: c for l, c in zip(f['labs'], f['chunks'])}.items()):
                cells = ' | '.join(render_bar(b) for b in ch)
                print(f'        {lab} = | {cells} |')


if __name__ == '__main__':
    main()
