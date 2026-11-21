#!/usr/bin/env python3
"""
What does a chorus melody do differently from its own verse?

    python3 melody_verse_chorus.py

Paired within each song: the FIRST verse against the FIRST chorus (the user's
rule -- the first instance is the one entered carefully), notes sliced on the
phrase (corpus.section_phrase), no intros/outros/solos. Three readings:

  REGISTER   mean, highest and lowest pitch in scale steps; chorus minus verse.
  ROLE       every note's job over the chord sounding at its onset, by scale-
             step distance from the chord root: R, 3, 5, or a colour/passing
             note (2, 4, 6, 7). Time-weighted, and separately for LANDINGS
             (notes >= 1.5 beats). Chromatic notes and chromatic chords
             (applied / borrowed) are left out of the role count.
  SAME CHORDS  the Friday case: pairs whose verse and chorus open on the same
             four bars of chords, where the melody is the ONLY thing that can
             make the chorus new.
"""
import collections, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of

ROLE = {0: 'R', 2: '3', 4: '5', 1: '2', 3: '4', 5: '6', 6: '7'}


def pitch(n):
    sd = str(n.get('sd', ''))
    return None if not sd.isdigit() else (n.get('octave', 0) * 7 + int(sd) - 1)


def chord_at(chords, b):
    for c in chords:
        if c['beat'] <= b < c['beat'] + c.get('duration', 0):
            return c
    return None


def first_sections(d):
    out = {}
    for name, b0, b1 in corpus.sections(d):
        r = role_of(name)
        r = 'pre-chorus' if r == 'prechorus' else r
        if r in ('verse', 'chorus') and r not in out:
            out[r] = (b0, b1)
    return out


def read(d, b0, b1, chords):
    notes, _, _ = corpus.section_phrase([n for n in d.get('notes') or [] if not n.get('isRest')], b0, b1)
    ps = [(pitch(n), n) for n in notes]
    ps = [(p, n) for p, n in ps if p is not None]
    if len(ps) < 8: return None
    time, land = collections.Counter(), collections.Counter()
    for p, n in ps:
        c = chord_at(chords, n['beat'])
        if not c or c.get('applied') or c.get('borrowed'): continue
        r = ROLE[(p - (c['root'] - 1)) % 7]
        time[r] += n.get('duration', 0)
        if n.get('duration', 0) >= 1.5: land[r] += 1
    w = [n.get('duration', 0) or .25 for _, n in ps]
    mean = sum(p * x for (p, _), x in zip(ps, w)) / sum(w)
    first4 = tuple((corpus.identity(c), x) for c, _, x in corpus.merged(
        [c for c in chords if b0 <= c['beat'] < b0 + 16]))
    span = max(n['beat'] + n.get('duration', 0) for _, n in ps) - ps[0][1]['beat']
    pc = collections.Counter()
    for (p, n), x in zip(ps, w): pc[p] += x
    return dict(dens=len(ps) / max(span / 4, 1), recite=pc.most_common(1)[0][1] / sum(w),
                rng=max(p for p, _ in ps) - min(p for p, _ in ps),
                held=sum(x for x in w if x >= 1.5) / sum(w),
                rep=sum(1 for a, b in zip(ps, ps[1:]) if a[0] == b[0]) / (len(ps) - 1),
                mean=mean, hi=max(p for p, _ in ps), lo=min(p for p, _ in ps),
                time=time, land=land, first4=first4)


def share(cnt):
    t = sum(cnt.values()) or 1
    return {k: cnt[k] / t for k in 'R35'} | {'off': sum(cnt[k] for k in '2467') / t}


def main():
    pairs = []
    for name, d, nb in corpus.songs():
        if nb != 4 or not d.get('notes'): continue
        fs = first_sections(d)
        if len(fs) < 2: continue
        chords = sorted((c for c in d['chords'] if not c.get('isRest')), key=lambda c: c['beat'])
        v, c = read(d, *fs['verse'], chords), read(d, *fs['chorus'], chords)
        if v and c: pairs.append((name, v, c))
    n = len(pairs)
    print(f'{n} songs with a first verse and a first chorus, both with melody\n')

    dm = [c['mean'] - v['mean'] for _, v, c in pairs]
    dh = [c['hi'] - v['hi'] for _, v, c in pairs]
    up = lambda xs, t: sum(1 for x in xs if x > t) / n
    dn = lambda xs, t: sum(1 for x in xs if x < -t) / n
    print('REGISTER (scale steps; 7 = an octave)')
    print(f'  mean pitch  chorus - verse: median {st.median(dm):+.2f}   higher {up(dm, .5):.0%}  '
          f'same (within half a step) {1 - up(dm, .5) - dn(dm, .5):.0%}  lower {dn(dm, .5):.0%}')
    print(f'  top note    chorus - verse: median {st.median(dh):+.0f}       higher {up(dh, 0):.0%}  '
          f'same {1 - up(dh, 0) - dn(dh, 0):.0%}  lower {dn(dh, 0):.0%}')
    big = sorted(pairs, key=lambda t: t[2]['mean'] - t[1]['mean'])
    print('  biggest lifts:', ', '.join(f"{p[0]} {p[2]['mean'] - p[1]['mean']:+.1f}" for p in big[-5:][::-1]))
    print('  biggest drops:', ', '.join(f"{p[0]} {p[2]['mean'] - p[1]['mean']:+.1f}" for p in big[:3]))

    print('\nSHAPE (median verse -> chorus; share of songs where the chorus is higher)')
    for k, lab in (('dens', 'notes per bar'), ('held', 'time on notes >= 1.5 beats'),
                   ('rep', 'next note is the same pitch'), ('recite', 'time on the single commonest pitch'),
                   ('rng', 'range, scale steps')):
        a = [v[k] for _, v, c in pairs]; b = [c[k] for _, v, c in pairs]
        hi = sum(y > x for x, y in zip(a, b)) / n; lo = sum(y < x for x, y in zip(a, b)) / n
        print(f'  {lab:36} {st.median(a):6.2f} -> {st.median(b):6.2f}   chorus more {hi:.0%} / less {lo:.0%}')

    for label, key in (('ROLE, share of melody TIME', 'time'), ('ROLE of LANDINGS (notes >= 1.5 beats)', 'land')):
        V = collections.Counter(); C = collections.Counter()
        for _, v, c in pairs: V += v[key]; C += c[key]
        sv, sc = share(V), share(C)
        print(f'\n{label}')
        print('           ' + '  '.join(f'{k:>6}' for k in ('R', '3', '5', 'off')))
        print('  verse    ' + '  '.join(f'{sv[k]:6.1%}' for k in ('R', '3', '5', 'off')))
        print('  chorus   ' + '  '.join(f'{sc[k]:6.1%}' for k in ('R', '3', '5', 'off')))
        print('  off-chord detail (chorus vs verse): ' + '  '.join(
            f"{k} {C[k] / (sum(C.values()) or 1):.1%}/{V[k] / (sum(V.values()) or 1):.1%}" for k in '2467'))

    same = [(nm, v, c) for nm, v, c in pairs if v['first4'] and v['first4'] == c['first4']]
    print(f'\nSAME CHORDS: {len(same)} songs open verse and chorus on the same 4 bars')
    if same:
        d2 = [c['mean'] - v['mean'] for _, v, c in same]
        print(f'  mean pitch chorus - verse: median {st.median(d2):+.2f}   higher {sum(x > .5 for x in d2) / len(same):.0%}'
              f'   (all pairs: {up(dm, .5):.0%})')
        V = collections.Counter(); C = collections.Counter()
        for _, v, c in same: V += v['land']; C += c['land']
        sv, sc = share(V), share(C)
        print('  landings  verse  ' + '  '.join(f'{k} {sv[k]:.0%}' for k in ('R', '3', '5', 'off')))
        print('  landings  chorus ' + '  '.join(f'{k} {sc[k]:.0%}' for k in ('R', '3', '5', 'off')))
        print('  e.g. ' + ', '.join(nm for nm, _, _ in same[:12]))


if __name__ == '__main__':
    main()
