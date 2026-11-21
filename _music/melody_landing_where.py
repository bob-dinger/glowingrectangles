#!/usr/bin/env python3
"""
Where is the landing note?

    python3 melody_landing_where.py

First verse and first chorus per song, eight bars of 4/4, sliced strictly on the
barline (b0 .. b0+32). Each half's LANDING is the note in its last two bars that is
followed by the longest silence (its end to the next onset anywhere in the song) --
the note the phrase stops on. A note on the 'and' of 4 is an anticipation and counts
as the NEXT bar's (bar 3's last eighth can be bar 4's landing; bar 4's cannot). For each landing: where it starts (bar + beat), how
long it is, its scale degree, its job over the chord, whether it is the section's
home note (commonest pitch by time) and whether it sits on a chord change.
"""
import collections, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_verse_chorus import pitch, chord_at, first_sections, ROLE


def landing(notes, allnotes, lo, hi):
    cand = [n for n in notes if lo <= n['beat'] < hi and pitch(n) is not None]
    if not cand: return None
    def gap(n):
        end = n['beat'] + n.get('duration', 0)
        nxt = [m['beat'] for m in allnotes if m['beat'] > n['beat']]
        return (min(nxt) if nxt else end + 8) - end
    best = max(cand, key=lambda n: (round(gap(n), 3), n['beat']))
    return best, gap(best)


def main():
    rows = []
    for name, d, nb in corpus.songs():
        if nb != 4 or not d.get('notes'): continue
        alln = sorted((n for n in d['notes'] if not n.get('isRest')), key=lambda n: n['beat'])
        chords = sorted((c for c in d['chords'] if not c.get('isRest')), key=lambda c: c['beat'])
        starts = {c['beat'] for c in chords}
        for role, (b0, b1) in first_sections(d).items():
            if b1 - b0 < 32: continue
            sec = [n for n in alln if b0 - .5 <= n['beat'] < b0 + 31.5 and pitch(n) is not None]
            if len(sec) < 8: continue
            pc = collections.Counter()
            for n in sec: pc[pitch(n) % 7] += n.get('duration', 0)
            home = pc.most_common(1)[0][0]
            for half, lo in ((1, b0 + 8), (2, b0 + 24)):
                r = landing(sec, alln, lo - .5, lo + 7.5)     # the 'and' of 4 belongs to the next bar
                if not r: continue
                n, g = r
                p = pitch(n)
                c = chord_at(chords, n['beat'])
                job = None if not c or c.get('applied') or c.get('borrowed') else ROLE[(p - (c['root'] - 1)) % 7]
                rel = n['beat'] - (lo + 4)              # 0 = downbeat of bar 4 / bar 8
                halfnotes = [m for m in sec if lo - 8 <= m['beat'] < lo + 8]
                rows.append(dict(name=name, role=role, half=half, rel=rel, dur=n.get('duration', 0),
                                 gap=g, deg=p % 7 + 1, job=job, home=(p % 7 == home),
                                 longest=n.get('duration', 0) >= max(m.get('duration', 0) for m in halfnotes),
                                 onchange=n['beat'] in starts, p=p))
    print(f"{len(rows)} landings from {len({r['name'] for r in rows})} songs\n")
    pct = lambda xs: f'{len(xs) / len(rows):5.1%}'
    for half in (1, 2):
        R = [r for r in rows if r['half'] == half]
        bar = 4 * half
        print(f'=== BAR {bar} ({len(R)})')
        pos = collections.Counter()
        for r in R:
            b = bar - 1 if r['rel'] < 0 else bar
            beat = (r['rel'] % 4) + 1
            pos[f'bar {b} beat {beat:g}'] += 1
        print('  starts at:   ' + '   '.join(f'{k} {v / len(R):.0%}' for k, v in pos.most_common(8)))
        print(f"  before bar {bar}'s downbeat: {sum(r['rel'] < 0 for r in R) / len(R):.0%}   "
              f"on it: {sum(r['rel'] == 0 for r in R) / len(R):.0%}   after: {sum(r['rel'] > 0 for r in R) / len(R):.0%}")
        print(f"  length: median {st.median(r['dur'] for r in R):g} beats   "
              f">=2 beats {sum(r['dur'] >= 2 for r in R) / len(R):.0%}   silence after: median {st.median(r['gap'] for r in R):g} beats")
        dg = collections.Counter(r['deg'] for r in R)
        print('  degree:      ' + '   '.join(f'{k} {v / len(R):.0%}' for k, v in dg.most_common(7)))
        J = [r for r in R if r['job']]
        jb = collections.Counter(r['job'] for r in J)
        print('  over chord:  ' + '   '.join(f'{k} {jb[k] / len(J):.0%}' for k in 'R35') +
              f"   off {sum(jb[k] for k in '2467') / len(J):.0%}")
        print(f"  is the home note {sum(r['home'] for r in R) / len(R):.0%}   longest note of the half "
              f"{sum(r['longest'] for r in R) / len(R):.0%}   starts on a chord change {sum(r['onchange'] for r in R) / len(R):.0%}")
        for role in ('verse', 'chorus'):
            Q = [r for r in R if r['role'] == role]
            q = collections.Counter(r['deg'] for r in Q)
            print(f'    {role:6} degree: ' + '  '.join(f'{k} {v / len(Q):.0%}' for k, v in q.most_common(4)))
        print()
    pair = collections.defaultdict(dict)
    for r in rows: pair[(r['name'], r['role'])][r['half']] = r
    both = [v for v in pair.values() if len(v) == 2]
    same = sum(v[1]['deg'] == v[2]['deg'] for v in both)
    lower = sum(v[2]['p'] < v[1]['p'] for v in both); higher = sum(v[2]['p'] > v[1]['p'] for v in both)
    print(f'BAR 4 vs BAR 8 ({len(both)} sections): same degree {same / len(both):.0%}   '
          f'bar 8 lower {lower / len(both):.0%}  higher {higher / len(both):.0%}')
    mv = collections.Counter((v[1]['deg'], v[2]['deg']) for v in both)
    print('  ' + '   '.join(f'{a}->{b} {n / len(both):.0%}' for (a, b), n in mv.most_common(8)))


if __name__ == '__main__':
    main()
