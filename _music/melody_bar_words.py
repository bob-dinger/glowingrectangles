"""The measure alphabet: an eight-bar section as an eight-letter word.

The user's own description of a section was never a list of eight rhythms — it was
"measure 1 four quarters, 2 the long rest, 3 four quarters, 4 a rest, then two
measures of quarters, then a rest on 8".  That is a word in a tiny alphabet, and the
standing question was whether there is "some math ratio of good melodies".  There is,
and it is at this level: the eight-bar word is a FOUR-BAR WORD SAID TWICE, and when the
restatement changes, it changes in the last bar.

Alphabet — three letters, because the point is that it stays readable at a glance:

    H  hold   a note in the bar runs 1.5 beats or longer.  the bar is a LANDING.
    M  move   no such note, but the bar is sounding.  the bar is movement.
    .  air    one onset or none, or under 2 beats of sound.  the bar is mostly empty.

HOLD IS CHECKED FIRST and that is the whole calibration.  Testing onset-count first
(a bar with 3+ onsets reads as movement) put 83% of bars in M and 43% of sections in
MMMMMMMM, i.e. it measured nothing — because a bar can both run and land, and by the
user's lens the landing is the event while the running notes are flair.

Measured 2026-10-03 over 1,556 eight-bar role sections (first instance per role, no
intros/outros/solos, sliced with corpus.section_phrase so pickups are included):

    bars 1-4 == bars 5-8 exactly    33.7%   vs 14.4% shuffled   2.3x
    differ in exactly one bar       30.8%   vs 19.5%            1.6x
    ------------------------------  -----
    AA or AA' together              64.5%   vs 33.9%            1.9x
    (period 4 among words that are not all one letter: 25.4% vs 3.6% = 7.1x)

    and of the 479 AA' sections, the bar that changes is bar 4/8 in 53.2% of them,
    against ~15.5% for each of the other three positions.  That is the user's
    "ender" (AAAB), measured.  The change is M<->H 56% of the time: the second
    ending either lands where the first one moved, or moves where it landed.

    themap_venv/python melody_bar_words.py               # words + periodicity
    themap_venv/python melody_bar_words.py --bars 4
    themap_venv/python melody_bar_words.py --word MMMHMMMH   # who uses one word
"""
import os, sys, random, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of

HOLD = 1.5          # a note this long makes the bar a landing
QUIET = 2.0         # less sound than this makes the bar air

def letter(bar):
    """One bar -> one letter.  Hold is tested FIRST; see the module docstring."""
    if not bar: return '.'
    if max(n['duration'] for n in bar) >= HOLD: return 'H'
    if len(bar) <= 1 or sum(n['duration'] for n in bar) < QUIET: return '.'
    return 'M'

def scan(nbars=8):
    """(word, song, section, role) for every nbars-long role section."""
    rows = []
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if not notes: continue
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, d.get('endBeat') or 10**9)
            if int((end-b0)//4) != nbars: continue
            # STRICT slice, b0 to b0+nbars*4 -- the same notes the pastes carry, so
            # the words here and in melody_word_paste.py agree. section_phrase trims a
            # trailing pickup out of the last bar and so reads it as air: that alone
            # moved `MMMMMMM.` from 3.2% to 1.2% and `MMMMMMMM` from 6.7% to 8.6%.
            # The headline is unaffected (AA+AA' 61.3% vs 61.6%, 1.9x both ways).
            inn = [n for n in notes if b0 <= n['beat'] < b0 + nbars*4]
            if len(inn) < 6: continue
            used.add(role)
            # bars are counted from the NOTATED BARLINE b0, not from the phrase
            # start: anchoring on the phrase start puts the grid at the pickup's
            # offset and shifts every bar.  32% of sections have a pickup and the
            # word came out different for 20% of them.  Pickup notes fall before
            # bar 1 and are excluded from the word, which is right — a lead-in is
            # not bar 1.  (The AA result holds on either grid: 61.4% vs 64.5%,
            # 1.9x both ways, and the bar-8 ender is STRONGER here, 58% vs 53%.)
            w = ''.join(letter([n for n in inn if b0+m*4 <= n['beat'] < b0+m*4+4])
                        for m in range(nbars))
            rows.append((w, name, sec, role))
    return rows

def halves_distance(w):
    """How many of the four bars the restatement changes.  0 = AA, 1 = AA'."""
    h = len(w)//2
    return sum(a != b for a, b in zip(w[:h], w[h:]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bars', type=int, default=8)
    ap.add_argument('--top', type=int, default=14)
    ap.add_argument('--word', help="list every section with this exact word")
    ap.add_argument('--trials', type=int, default=400)
    a = ap.parse_args()
    rows = scan(a.bars)
    tot = len(rows)
    if a.word:
        hit = [r for r in rows if r[0] == a.word]
        print(f"\n  {len(hit)} sections read {a.word}\n")
        for w, n, s, role in hit:
            print(f"    {n[:38]:38} {s[:14]:14} {role}")
        return
    words = collections.Counter(w for w, *_ in rows)
    ex = collections.defaultdict(list)
    for w, n, s, r in rows: ex[w].append((n, s))
    print(f"\n  {tot:,} {a.bars}-bar role sections -> {len(words)} distinct words\n")
    print(f"  {'word':>10} {'n':>4} {'share':>6}   example")
    for w, n in words.most_common(a.top):
        s0 = ex[w][0]
        print(f"  {w:>10} {n:4} {100*n/tot:5.1f}%   {s0[0][:32]:32} {s0[1][:12]}")

    dd = collections.Counter(halves_distance(w) for w, *_ in rows)
    rnd = random.Random(11); sd = collections.Counter()
    for _ in range(a.trials):
        for w, *_ in rows:
            x = list(w); rnd.shuffle(x); sd[halves_distance(''.join(x))] += 1
    h = a.bars//2
    print(f"\n  how far the second {h} bars are from the first {h}\n")
    print(f"    {'differing bars':<18} {'real':>7} {'shuffled':>9}  {'lift':>5}")
    for k in range(h+1):
        r = 100*dd[k]/tot; s = 100*sd[k]/(tot*a.trials)
        lab = {0: '0  — AA exactly', 1: "1  — AA'"}.get(k, f'{k}' + ('  — unrelated' if k == h else ''))
        print(f"    {lab:<18} {r:6.1f}% {s:8.1f}%  {r/s if s else 0:5.1f}x")
    rr = (dd[0]+dd[1])/tot; ss = (sd[0]+sd[1])/(tot*a.trials)
    print(f"    {'AA or AA’ together':<18} {100*rr:6.1f}% {100*ss:8.1f}%  {rr/ss:5.1f}x")

    one = [w for w, *_ in rows if halves_distance(w) == 1]
    pos = collections.Counter(next(i for i in range(h) if w[i] != w[i+h]) for w in one)
    print(f"\n  of the {len(one)} AA' sections, which bar is the one that changes:")
    for i in range(h):
        print(f"    bar {i+1} / {i+1+h}   {pos[i]:4}  {100*pos[i]/len(one):5.1f}%  "
              f"{'#'*int(56*pos[i]/len(one))}")
    ch = collections.Counter((w[i], w[i+h]) for w in one for i in range(h) if w[i] != w[i+h])
    tc = sum(ch.values())
    print(f"\n  and what the change is (first half -> restatement):")
    for (x, y), n in ch.most_common():
        print(f"    {x} -> {y}   {n:4}  {100*n/tc:5.1f}%")

if __name__ == '__main__':
    main()
