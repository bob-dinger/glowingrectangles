"""Write the real sections behind a measure-alphabet word out as a Hookpad paste.

`melody_bar_words.py` says an eight-bar melody is a four-bar word said twice, and
that when the restatement changes it changes in bar 8.  This is the hearing test:
pick a word, get every section in the corpus that reads that word, laid out one
after another with their chords so they can be compared side by side.

Each section is labelled with its word, and the letters are spelled out bar by bar
in the section name so the word can be read against the notes on screen.

    themap_venv/python melody_word_paste.py --word MMMHMMMH
    themap_venv/python melody_word_paste.py --word MMMHMMMH --word MMMMMMMH --max 4
    themap_venv/python melody_word_paste.py --list 6          # words with 6+ songs
"""
import os, sys, json, argparse, collections
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import (role_of, place_at, key_entries, tempo_entries,
                           base_of, num)
from melody_bar_words import letter, HOLD, QUIET

OUT = os.path.expanduser('~/Desktop/shared_figures')

# One bar of air between sections. The longest pickup in the corpus is 2 beats
# (552 sections carry one; 2 beats is both the max and the 99th percentile), so a
# single bar holds every one of them. Two bars left 10+ beats of dead space and
# made each section look like it started late.
GAP = 0

def scan():
    """(word, song, section, role, notes, chords) per eight-bar role section."""
    rows = []
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if not notes: continue
        chords = sorted(d.get('chords') or [], key=lambda c: c['beat'])
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, d.get('endBeat') or 10**9)
            if int((end-b0)//4) != 8: continue
            # STRICT: marker to section end, no anacrusis (the layout the user
            # approved 2026-10-03). This also fixes the bar grid -- st == b0 now, so
            # bar masks below are counted from the notated barline.
            end = b0 + 8*4      # the slot, which can be SHORTER than the
                                 # marker-to-marker span; clipping to the
                                 # latter let a chord cross the next marker
            inn = [n for n in notes if b0 <= n['beat'] < end]
            st, sp = b0, end
            if len(inn) < 6: continue
            used.add(role)
            # counted from the notated barline; see melody_bar_words.scan
            w = ''.join(letter([n for n in inn if b0+m*4 <= n['beat'] < b0+m*4+4])
                        for m in range(8))
            ch = [c for c in chords if st <= c['beat'] < sp and c.get('root')]
            rows.append((w, name, sec, role, inn, ch, b0, end, d))
    return rows

def build(pick, bpm):
    """One paste from a list of picked sections."""
    notes, chords, secs, keys, tempos, at = [], [], [], [], [], 1
    for w, name, sec, role, inn, ch, b0, end, d in pick:
        shift, lead = place_at(inn, at, b0)
        keys   += key_entries(d, b0, end, shift)
        tempos += tempo_entries(d, b0, end, shift, bpm)
        secs.append({'beat': num(at),
                     'name': f"{' '.join(w)}  {name[:24]} {sec[:9]}"[:62]})
        for n in inn:
            notes.append({'sd': str(n['sd']), 'octave': int(n.get('octave', 0)),
                          'beat': num(n['beat']+shift),
                          'duration': num(min(n['duration'], end-n['beat'])),
                          'isRest': False, 'recordingEndBeat': None})
        for c in ch:
            chords.append({'root': c['root'], 'beat': num(c['beat']+shift),
                           'duration': num(min(c.get('duration', 4), end-c['beat'])),
                           'type': int(c.get('type', 5)), 'inversion': 0,
                           'applied': c.get('applied', 0), 'adds': c.get('adds', []),
                           'omits': c.get('omits', []), 'alterations': c.get('alterations', []),
                           'suspensions': c.get('suspensions', []), 'substitutions': [],
                           'pedal': None, 'alternate': '',
                           'borrowed': c.get('borrowed') or '',
                           'isRest': False, 'recordingEndBeat': None})
        at += (lead+8+GAP)*4
    return {'version': 1, 'chords': chords, 'notes': notes,
            'keys': keys, 'tempos': tempos,
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': secs, 'endBeat': num(at), 'audioTracks': []}

def choose(rows, w, cap):
    """Sections reading word `w`: chords first, then one per ARTIST so a word is not
    illustrated by six songs from one band."""
    hits = sorted([r for r in rows if r[0] == w], key=lambda r: (not r[5], r[1]))
    seen, artists, pick = set(), set(), []
    for r in hits:
        b = base_of(r[1]); art = b.split('_')[0]
        if b in seen or art in artists: continue
        seen.add(b); artists.add(art); pick.append(r)
        if len(pick) >= cap: break
    return pick

def fname(w):
    """`.` is the air letter; `_` stands in for it in filenames."""
    return 'word_' + w.replace('.', '_') + '.txt'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--word', action='append', default=[])
    ap.add_argument('--top', type=int, help="the N commonest words, one FILE each")
    ap.add_argument('--max', type=int, default=6, help="sections per word")
    ap.add_argument('--bpm', type=int)
    ap.add_argument('--list', type=int, metavar='MINSONGS',
                    help="just list the words carried by this many distinct songs")
    a = ap.parse_args()
    rows = scan()
    tot = len(rows)

    if a.list:
        by = collections.defaultdict(set)
        for w, name, *_ in rows: by[w].add(name)
        rank = sorted(((len(s), w) for w, s in by.items()), reverse=True)
        print(f"\n  words in {a.list}+ distinct songs\n")
        for n, w in rank:
            if n < a.list: break
            dd = sum(x != y for x, y in zip(w[:4], w[4:]))
            tag = ('period-4' if dd == 0 else
                   'differs in bar ' + str(next(i+1 for i in range(4) if w[i] != w[i+4]))
                   if dd == 1 else '')
            print(f"    {w}  {n:3} songs   {tag}")
        return

    words = a.word
    if a.top:
        words = [w for w, _ in collections.Counter(r[0] for r in rows).most_common(a.top)]
    if not words:
        ap.error("give --word W (repeatable), --top N, or --list N")

    os.makedirs(OUT, exist_ok=True)
    share = collections.Counter(r[0] for r in rows)
    print(f"\n  {tot} eight-bar role sections; one file per word\n")
    for w in words:
        pick = choose(rows, w, a.max)
        if not pick:
            print(f"  {w}: no sections"); continue
        obj = build(pick, a.bpm)
        p = os.path.join(OUT, fname(w))
        open(p, 'w').write(hp3.clipboard(obj))
        modes = collections.Counter(k['scale'] for k in obj['keys'])
        bpms = [t['bpm'] for t in obj['tempos']]
        print(f"  {w}  {share[w]:3} sections in the corpus ({100*share[w]/tot:.1f}%)"
              f"  -> {len(pick)} in the file, {int((obj['endBeat']-1)/4)} bars, "
              f"{min(bpms)}-{max(bpms)}bpm, {dict(modes)}")
        for r in pick:
            print(f"        {r[1][:34]:34} {r[2][:12]:12} {len(r[4]):3} notes {len(r[5]):2} chords")
        print(f"        -> {p}")

if __name__ == '__main__':
    main()
