#!/usr/bin/env python3
"""
Songs that share the exact same progression -> _music/same-progressions.html

    themap_venv/python same_progressions.py

A progression here is a section's LOOP: the shortest run of chords that the
section plays at least twice in a row from its first chord. Two loops are the
same when the chords match in order AND their lengths stand in the same RATIO.
Speed is not part of it: | I | V | vi | IV | and | I V | vi IV | are both
I V vi IV at 1:1:1:1, one chord a bar against two. The user: "ratios are the
most important thing." Speed (beats per chord, bpm) rides along per song.

Rotations are kept apart and linked: vi IV I V and I V vi IV are the same
circle entered from a different chord (front vs back runner, runners-map).

Rules from corpus.py: re-strikes merged, scratch songs out, meter per song,
mode per section (roman() reads minor through the relative major). Variants
(-simple, -80, -hooktab...) are left out when the plain song is also there,
so one song is never counted twice; a variant that is the ONLY copy (140
songs exist only as -hooktab imports) stands in for it.
"""
import collections, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from hashids import Hashids

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = re.compile(r'(-(\d{2,3}|hooktab|simple|double|C|right|wrong|mixolydian|filled|3way)|_o_c_ly_?|_o_)$', re.I)
HASH = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
               alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
SKIP_SEC = re.compile(r'intro|outro|coda|ending|instrumental|solo', re.I)


def title_case(s):
    return ' '.join(w[:1].upper() + w[1:] for w in s.replace('_', ' ').split())


def loop_of(ev):
    """Shortest cell (>= 2 chords) the event list plays at least twice in a row
    from the start. ev = [(label, beats)]. Returns (cell, reps) or None.
    A loop whose last chord is also its first (I IV V I) merges across the
    seam and is not found -- those read as a longer cell or none."""
    n = len(ev)
    for p in range(2, n // 2 + 1):
        cell = ev[:p]
        if len({k for k, _ in cell}) < 2:
            continue
        reps = 1
        while (reps + 1) * p <= n and ev[reps * p:(reps + 1) * p] == cell:
            reps += 1
        if reps >= 2:
            return cell, reps
    return None


def ratio(cell):
    """durations -> smallest whole numbers in the same proportion"""
    q = [int(round(d * 4)) for _, d in cell]      # quarter-beat units
    g = 0
    for x in q: g = math.gcd(g, x)
    return tuple(x // g for x in q)


def rotations(key):
    return [key[i:] + key[:i] for i in range(len(key))]


PLAIN = re.compile(r'^[b#]?(?:iii|ii|iv|vii|vi|v|i|III|II|IV|VII|VI|V|I)(?:°|o|dim|\+)?')


def plain(lab):
    """V7/V -> V/V, Imaj7 -> I, IVsus2 -> IV: the triad underneath, for the
    'plain triads' reading. Applied targets stay, they are different chords."""
    out = []
    for part in lab.split('/'):
        m = PLAIN.match(part)
        out.append(m.group(0) if m else part)
    return '/'.join(out)


def progression(ev):
    """(cell, reps): the loop if the section loops, else the section once through"""
    got = loop_of(ev)
    if got:
        return got
    if len({k for k, _ in ev}) >= 2:
        return ev, 1
    return None


# ---- melody over each chord --------------------------------------------------
# Everything is read in the frame the chord labels use: roman() reads a minor
# key through its relative major (A minor's i is vi), every other mode from its
# own tonic with accidentals against major (mixolydian's 7 is b7). Melody sd is
# stored relative to the key's own mode, so it is converted to that frame
# before asking "is this note in the chord?".
MAJ = [0, 2, 4, 5, 7, 9, 11]
SEMI = {'I': 0, 'II': 2, 'III': 4, 'IV': 5, 'V': 7, 'VI': 9, 'VII': 11}
NAME = ['1', 'b2', '2', 'b3', '3', '4', '#4', '5', 'b6', '6', 'b7', '7']
ROM = re.compile(r'^([b#]?)(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)(°|o|dim|\+)?')


def chord_pcs(lab):
    """plain triad of a roman label -> pitch classes in the frame"""
    parts = lab.split('/')
    m = ROM.match(parts[0])
    if not m:
        return None
    up = m.group(2).upper()
    root = SEMI[up] + {'b': -1, '#': 1}.get(m.group(1), 0)
    if len(parts) > 1:
        t = ROM.match(parts[1])
        if not t:
            return None
        root += SEMI[t.group(2).upper()] + {'b': -1, '#': 1}.get(t.group(1), 0)
    minor, dim = m.group(2) != up, m.group(3) not in (None, '+')
    return {root % 12, (root + (3 if minor or dim else 4)) % 12, (root + (6 if dim else 7)) % 12}


def note_pc(sd, mode):
    """Hookpad sd ('b7', '#4', '5') in the key's mode -> pitch class in the frame"""
    sd = str(sd)
    acc = sd.count('#') - sd.count('b')
    n = int(sd.strip('#b'))
    off = C.MODE_OFFSET.get(mode, 0)
    pc = (MAJ[(n - 1 + off) % 7] - MAJ[off] + acc) % 12
    if mode == 'harmonicMinor' and n == 7:
        pc = (pc + 1) % 12
    return (pc + 9) % 12 if mode in ('minor', 'aeolian') else pc


def melody(evs, notes, mode):
    """per chord event: [main note, chord tone?, notes that start inside it].
    The main note is the one sounding longest under the chord, so a note pushed
    in early or held over from the chord before still counts."""
    out = []
    for lab, b, du in evs:
        pcs = chord_pcs(lab)
        w, seq = {}, []
        for n in notes:
            o, e = max(b, n['beat']), min(b + du, n['beat'] + n['duration'])
            if e > o:
                pc = note_pc(n['sd'], mode)
                w[pc] = w.get(pc, 0) + e - o
            if b <= n['beat'] < b + du:
                seq.append(NAME[note_pc(n['sd'], mode)])
        if not w:
            out.append(None)
            continue
        main = max(w, key=w.get)
        out.append([NAME[main], None if pcs is None else int(main in pcs), ' '.join(seq[:10])])
    return out


def main():
    ids = {}
    lst = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
    for s in json.load(open(lst)):
        ids.setdefault(s['song'].replace('/', '_').lower(), s['ID'])
    songs, recs = [], {'exact': [], 'plain': []}
    every = list(C.songs())
    names = {n.lower() for n, _, _ in every}
    taken = set()
    for name, d, nb in every:
        base = VARIANT.sub('', name)
        if base != name and (base.lower() in names or base.lower() in taken):
            continue
        taken.add(base.lower())
        mc = C.merged(d['chords'])
        bpm = ((d.get('tempos') or [{}])[0] or {}).get('bpm')
        tonic = ((d.get('keys') or [{}])[0] or {}).get('tonic') or ''
        artist, title = base.split('_', 1) if '_' in base else ('', base)
        si = len(songs)
        seen = {'exact': set(), 'plain': set()}
        used = False
        for sec, b0, end in C.sections(d):
            if SKIP_SEC.search(str(sec)):
                continue
            mode = C.mode_at(d, b0)
            notes = [n for n in d.get('notes') or [] if not n.get('isRest') and n.get('sd')]
            for how, f in (('exact', lambda x: x), ('plain', plain)):
                ev = []
                for c, b, du in mc:
                    if b0 <= b < end:
                        lab = f(C.roman(c, mode))
                        du = min(du, end - b)
                        if ev and ev[-1][0] == lab: ev[-1][1] += du
                        else: ev.append([lab, du, b])
                ev = [e for e in ev if round(e[1] * 4)]
                starts = [e[2] for e in ev]
                ev = [(k, round(x * 4) / 4) for k, x, _ in ev]
                got = progression(ev)
                if not got:
                    continue
                cell, reps = got
                key = (tuple(k for k, _ in cell), ratio(cell))
                if key in seen[how]:
                    continue            # a song counts once per progression
                seen[how].add(key)
                used = True
                k = len(cell) * min(reps, 2)        # first two passes
                mel = melody([(ev[i][0], starts[i], ev[i][1]) for i in range(min(k, 16))], notes,
                             mode) if notes else []
                recs[how].append([si, list(key[0]), list(key[1]), sum(x for _, x in cell), reps, str(sec), mel])
        if used:
            songs.append(dict(t=title_case(title), a=title_case(artist), nb=nb, bpm=bpm,
                              k=f'{tonic} {C.mode_of(d)}'.strip(),
                              u=HASH.encode(ids[name.lower()]) if name.lower() in ids else ''))
    data = dict(songs=songs, exact=recs['exact'], plain=recs['plain'])
    tpl = open(os.path.join(HERE, 'same_progressions_template.html')).read()
    open(os.path.join(HERE, 'same-progressions.html'), 'w').write(
        tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    for how in ('plain', 'exact'):
        g = collections.defaultdict(set)
        for si, ch, r, *_ in recs[how]:
            g[(tuple(ch), tuple(r))].add(si)
        sh = {k: v for k, v in g.items() if len(v) >= 2}
        print(f"{how}: {len(recs[how])} song-progressions, {len(g)} distinct, {len(sh)} shared by 2+ songs, "
              f"covering {len(set().union(*sh.values()))} of {len(songs)} songs")
        for k, v in sorted(sh.items(), key=lambda kv: -len(kv[1]))[:20]:
            print(f"   {len(v):3d}  {' '.join(f'{c}:{x}' for c, x in zip(*k))}")


if __name__ == '__main__':
    main()
