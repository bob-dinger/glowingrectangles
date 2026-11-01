#!/usr/bin/env python3
"""
The long notes of every melody, section by section -> _music/hold-patterns.html

    themap_venv/python hold_patterns.py

A melody reads by its holds: quick notes landing on a long one. Straight
Tequila Night's verse lines land on 1.5, 2.5, then 4 beats -- the holds grow.
The user: "I can easily see now this is a .5, 1.5, 4 song in the verse (or
actually 1.5, 2.5, 4)".

A note's length here is how long it SOUNDS: until the next note starts
(legato), except across a rest longer than a bar (an instrumental stretch),
where it stops at the next half bar after it was sung -- the same rule as
audio_to_hookpad.legato.

For the first verse, chorus, pre-chorus and bridge of each song (4/4 songs,
copies collapsed by same_progressions.same, the copy with the most melody
kept), the first 8 bars are read as four 2-bar lines and each line gives one
number: its longest note. Straight Tequila Night's verse: 1.5 4.5 2 4. The four
numbers get a shape:

    even            all four within half a beat
    call & answer   lines 2 and 4 land at least a beat longer than 1 and 3
    answer & call   the mirror (1 and 3 longer)
    growing         each line's hold at least as long as the last, the 4th a beat longer
    shrinking       the mirror
    long landing    the 4th line's hold a beat longer than any before it
    long start      the 1st line's a beat longer than any after it
    mixed           anything else
"""
import json, math, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from same_progressions import same, title_case, HASH

HERE = os.path.dirname(os.path.abspath(__file__))
HOLD = 1.5
KINDS = ['verse', 'chorus', 'pre-chorus', 'bridge']


def kind(name):
    s = re.sub(r'\(.*?\)|\d+|\b[ivx]+\b', ' ', str(name).lower()).replace('_', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    if re.search(r'pre[\s-]?chorus|prechorus|lift|build', s): return 'pre-chorus'
    if re.search(r'chorus|refrain|hook', s): return 'chorus'
    if re.search(r'verse', s): return 'verse'
    if re.search(r'bridge|middle', s): return 'bridge'
    return None


def sounding(notes, max_rest=4):
    """[(beat, sung duration)] -> [(beat, sounding duration, rest after)]"""
    out = []
    for (b, d), nxt in zip(notes, notes[1:] + [None]):
        if nxt is None:
            out.append((b, d, 0)); continue
        end = b + d
        if nxt[0] - end <= max_rest:
            out.append((b, nxt[0] - b, 0))
        else:
            stop = math.ceil((end - 1) / 2) * 2 + 1
            out.append((b, stop - b, nxt[0] - stop))
    return out


def step(n):
    """a note's height in scale steps, as Hookpad draws it: degree + 7 an octave, a sharp/flat half a step"""
    m = re.match(r'([b#]?)(\d)', str(n['sd']))
    return int(m.group(2)) - 1 + 7 * (n.get('octave') or 0) + {'#': 0.5, 'b': -0.5}.get(m.group(1), 0)


def shape(h):
    """h = the longest note of each 2-bar line (4 lines)"""
    if max(h) - min(h) <= 0.5: return 'even'
    if len(h) == 4 and min(h[1], h[3]) >= max(h[0], h[2]) + 1: return 'call & answer'
    if len(h) == 4 and min(h[0], h[2]) >= max(h[1], h[3]) + 1: return 'answer & call'
    if all(b >= a - 0.25 for a, b in zip(h, h[1:])) and h[-1] >= h[0] + 1: return 'growing'
    if all(b <= a + 0.25 for a, b in zip(h, h[1:])) and h[0] >= h[-1] + 1: return 'shrinking'
    if h[-1] >= max(h[:-1]) + 1: return 'long landing'
    if h[0] >= max(h[1:]) + 1: return 'long start'
    return 'mixed'


def main():
    ids = {}
    for s in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json'))):
        ids.setdefault(s['song'].replace('/', '_').lower(), s['ID'])
    best = {}
    for name, d, nb in C.songs(need_chords=False):
        if nb != 4: continue
        notes = [n for n in d.get('notes') or [] if not n.get('isRest') and n.get('sd')]
        if len(notes) < 16: continue
        k = same(name)
        rank = (len(notes), name.lower() == k)             # a melody page: the copy with the most melody
        if k not in best or rank > best[k][0]:
            best[k] = (rank, name, d)
    songs, secs = [], []
    for _, name, d in sorted(best.values(), key=lambda b: b[1].lower()):
        ns = sorted((float(n['beat']), float(n['duration']), step(n), n['sd']) for n in d['notes'] if not n.get('isRest') and n.get('sd'))
        snd = sounding([(b, du) for b, du, _, _ in ns])
        pitch = {b: (p, str(n)) for b, _, p, n in ns}
        seen, mine = set(), []
        for sec, b0, end in C.sections(d):
            kd = kind(sec)
            if not kd or kd in seen: continue
            inside = [(b, du, r) for b, du, r in snd if b0 - 1 <= b < end]       # a pickup half a bar early counts
            if len(inside) < 6: continue
            # one value per 2-bar line over the first 8 bars: the longest note that starts in it
            holds = []
            for ln in range(4):
                lo, hi = b0 + 8 * ln, min(end, b0 + 8 * ln + 8)
                if lo >= end: break
                ds = [min(du, hi - b) for b, du, r in inside if lo - (1 if ln == 0 else 0) <= b < hi]
                holds.append(round(max(ds) * 2) / 2 if ds else 0)
            if sum(1 for x in holds if x) < 3: continue
            seen.add(kd)
            t0 = inside[0][0]
            roll = [[round((b - b0) * 4) / 4, round(min(du, end - b, b0 + 32 - b) * 4) / 4, *pitch[b]]   # piano roll of the first 8 bars
                    for b, du, r in inside if b < b0 + 32]
            mine.append([kd, str(sec), int((end - b0) // 4), holds, shape(holds), roll])
        if not mine: continue
        base = same(name)
        artist, title = base.split('_', 1) if '_' in base else ('', base)
        si = len(songs)
        songs.append(dict(t=title_case(title), a=title_case(artist),
                          bpm=((d.get('tempos') or [{}])[0] or {}).get('bpm'),
                          u=HASH.encode(ids[name.lower()]) if name.lower() in ids else ''))
        for m in mine: secs.append([si] + m)
    data = dict(songs=songs, secs=secs, kinds=KINDS)
    tpl = open(os.path.join(HERE, 'hold_patterns_template.html')).read()
    open(os.path.join(HERE, 'hold-patterns.html'), 'w').write(
        tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    print(f'{len(songs)} songs, {len(secs)} sections')
    for kd in KINDS:
        c = Counter(s[5] for s in secs if s[1] == kd)
        print(f'  {kd:11} {sum(c.values()):4}  ' + ', '.join(f'{k} {v}' for k, v in c.most_common()))
    for s in secs:
        if songs[s[0]]['t'].startswith('Straight Tequila') and s[1] == 'verse':
            print('  Straight Tequila Night verse:', s[4], s[5])


if __name__ == '__main__':
    main()
