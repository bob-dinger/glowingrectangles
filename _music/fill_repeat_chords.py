#!/usr/bin/env python3
"""
Fill chordless repeat sections in Hookpad songs, in place, by copying the
chords of the earlier section with the same name.

    themap_venv/python fill_repeat_chords.py --survey            # local files only, no API
    themap_venv/python fill_repeat_chords.py --run [--only name ...] [--throttle 4]

A section is filled only when all of these hold:
  - it has no chords and has melody notes
  - an earlier section has the same name (trailing numbers ignored: "Verse 2" = "Verse")
    and chords, and is exactly the same length
  - the note-onset rhythm matches that section by >= 60% (half-beat grid)
  - the mode in force is the same at both (degrees are key-relative, so a
    key change up a step still copies correctly)
Generic "Section" names and the user's own songs (mine_/perms_/music_) are skipped,
as are variants (-80, -hooktab, -filled...).

--run pulls each song fresh, saves it to ~/Desktop/hookpad_fill_backups/<name>.json,
PATCHes the filled jsonData over it, reads it back and checks the chord count.
Ledger: ~/Desktop/hookpad_fill_backups/_done.json (re-running skips what's done).
"""
import argparse, glob, json, os, re, sys, time
import hp3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
BK = os.path.expanduser('~/Desktop/hookpad_fill_backups')
LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
SKIP = re.compile(r'^(mine|perms|music_|chord-riffs|6-30)', re.I)
VARIANT = re.compile(r'-(\d{2,3}|hooktab|simple|double|C|right|wrong|mixolydian|filled)$|-\d{2,3}-\d{2,3}$|\d{2,3}$')


def norm(n): return re.sub(r'[\s\d]+$', '', (n or '').strip().lower())
def inside(xs, a, b): return [x for x in xs if not x.get('isRest') and a <= x['beat'] < b]
def ons(ns, a): return {round((n['beat'] - a) * 2) / 2 for n in ns}
def sim(A, B): return len(A & B) / max(len(A | B), 1)


def mode_at(keys, b):
    k = [k for k in sorted(keys or [], key=lambda k: k['beat']) if k['beat'] <= b] or keys or [{}]
    return k[-1].get('scale')


def fill(j):
    """add copied chords to j in place; return a log line per filled section"""
    S = sorted(j.get('sections') or [], key=lambda s: s['beat'])
    end = j.get('endBeat') or 0
    sp = [(s['name'], s['beat'], S[i + 1]['beat'] if i + 1 < len(S) else end) for i, s in enumerate(S)]
    ch, nt, added, log = j.get('chords') or [], j.get('notes') or [], [], []
    for i, (n, a, b) in enumerate(sp):
        if b <= a or inside(ch, a, b) or norm(n) in ('', 'section'): continue
        tn = inside(nt, a, b)
        c = [(n2, a2, b2) for n2, a2, b2 in sp[:i] if norm(n2) == norm(n) and inside(ch, a2, b2) and b2 - a2 == b - a]
        if not tn or not c: continue
        n2, a2, b2 = max(c, key=lambda c: sim(ons(tn, a), ons(inside(nt, c[1], c[2]), c[1])))
        s = sim(ons(tn, a), ons(inside(nt, a2, b2), a2))
        if s < .6 or mode_at(j.get('keys'), a) != mode_at(j.get('keys'), a2): continue
        new = [{**x, 'beat': x['beat'] - a2 + a, 'recordingEndBeat': None} for x in inside(ch, a2, b2)]
        added += new
        log.append(f'{n.strip()}@bar{(a - 1) // 4 + 1} <- {n2.strip()}@bar{(a2 - 1) // 4 + 1} ({len(new)} chords, rhythm {s:.0%})')
    j['chords'] = sorted(ch + added, key=lambda c: c['beat'])
    return log


def fill_loose(j):
    """second pass (--loose): the earlier same-named section may differ in length.
    Its chords are laid in from its start, tiled when the target is longer, cut at
    the target's end. A later start (whole bars) is used only if it matches the
    rhythm 0.15 better than starting at the top. Thresholds: rhythm >= 0.4 for a
    same-length section, >= 0.5 otherwise. Same mode required."""
    S = sorted(j.get('sections') or [], key=lambda s: s['beat'])
    end = j.get('endBeat') or 0
    sp = [(s['name'], s['beat'], S[i + 1]['beat'] if i + 1 < len(S) else end) for i, s in enumerate(S)]
    ch, nt, added, log = j.get('chords') or [], j.get('notes') or [], [], []

    def lay(a2, b2, off, L):
        src, cs, so, t = inside(ch, a2, b2), [], set(), -off
        while t < L:
            for x in src:
                r = x['beat'] - a2 + t
                if 0 <= r < L: cs.append((r, x))
            so |= {o + t for o in ons(inside(nt, a2, b2), a2) if 0 <= o + t < L}
            t += b2 - a2
        return cs, so

    for i, (n, a, b) in enumerate(sp):
        if b <= a or inside(ch, a, b) or norm(n) in ('', 'section'): continue
        tn = inside(nt, a, b)
        if not tn: continue
        L, T, best = b - a, ons(tn, a), None
        for n2, a2, b2 in sp[:i]:
            if norm(n2) != norm(n) or not inside(ch, a2, b2) or b2 <= a2: continue
            if mode_at(j.get('keys'), a) != mode_at(j.get('keys'), a2): continue
            top = None
            for off in range(0, b2 - a2, 4):
                cs, so = lay(a2, b2, off, L)
                if not cs: continue
                s = sim(T, so)
                if off == 0: top = (s, n2, a2, b2, off, cs)
                cand = (s, n2, a2, b2, off, cs) if off == 0 or (top and s >= top[0] + .15) else None
                if cand and (not best or cand[0] > best[0]): best = cand
        if not best: continue
        s, n2, a2, b2, off, cs = best
        if s < (.4 if b2 - a2 == L and off == 0 else .5): continue
        new = [{**x, 'beat': a + r, 'duration': min(x['duration'], L - r), 'recordingEndBeat': None} for r, x in cs]
        added += new
        log.append(f'{n.strip()}@bar{(a - 1) // 4 + 1} ({L // 4} bars) <- {n2.strip()}@bar{(a2 - 1) // 4 + 1} '
                   f'({(b2 - a2) // 4} bars{f", from bar +{off // 4}" if off else ""}) ({len(new)} chords, rhythm {s:.0%})')
    j['chords'] = sorted(ch + added, key=lambda c: c['beat'])
    return log


FILL = fill


def load(f):
    d = json.load(open(f)); j = d.get('jsonData', d)
    return json.loads(j) if isinstance(j, str) else j


def candidates():
    out = []
    for f in sorted(glob.glob(D + '/*.json')):
        base = os.path.basename(f)[:-5]
        if SKIP.match(base) or VARIANT.search(base): continue
        try: j = load(f)
        except Exception: continue
        if j.get('chords') and FILL(j): out.append(base)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--survey', action='store_true'); ap.add_argument('--run', action='store_true')
    ap.add_argument('--loose', action='store_true', help='second pass: fill_loose, own ledger + backups')
    ap.add_argument('--only', nargs='*'); ap.add_argument('--throttle', type=float, default=4)
    a = ap.parse_args()
    global FILL, BK
    if a.loose: FILL, BK = fill_loose, os.path.join(BK, 'loose')
    names = a.only or candidates()
    print(len(names), 'songs with fillable sections')
    if a.survey or not a.run:
        for n in names: print(' ', n)
        return
    import hookpad_upload_variants as U
    tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
    ids = {}
    for s in hp3.newest_per_name(json.load(open(LIST))): ids[s['song']] = ids[s['song'].lower()] = s['ID']   # the Hookpad 3 copy, if one exists
    key = lambda n: n if n in ids else re.sub(r'(_(o|ly|c))+_?$', '', n.lower()).strip()
    os.makedirs(BK, exist_ok=True)
    ledger = os.path.join(BK, '_done.json')
    done = json.load(open(ledger)) if os.path.exists(ledger) else {}
    for i, name in enumerate(names, 1):
        if name in done: continue
        name = key(name)
        if name in done: continue
        if name not in ids: print(f'[{i}] {name}: not in catalog list'); continue
        slug = U.HASH.encode(ids[name])
        g = U.call('GET', f'{U.API}/songs/{slug}?fields=ID,song,jsonData', tok)
        if g.status_code == 401: sys.exit('token rejected (401): paste a fresh main bearer and re-run; done songs are skipped')
        if g.status_code >= 300: print(f'[{i}] {name}: GET {g.status_code}'); continue
        s = g.json()
        json.dump(s, open(os.path.join(BK, re.sub(r'[/:]', '_', name) + '.json'), 'w'))
        j = hp3.to_hp2(json.loads(s['jsonData'])); j.pop('fp', None)
        before = len(j.get('chords') or [])
        log = FILL(j)
        if not log: done[name] = {'filled': 0}; print(f'[{i}] {name}: nothing to fill on fresh copy'); continue
        time.sleep(1)
        p = U.call('PATCH', f'{U.API}/songs/{ids[name]}', tok, json={'jsonData': U.json_data(j), 'cloudBackupsEnabled': True})
        if p.status_code == 401: sys.exit('token rejected (401) mid-song: nothing was saved for ' + name)
        time.sleep(1)
        v = U.call('GET', f'{U.API}/songs/{slug}?fields=ID,jsonData', tok)
        got = len(hp3.to_hp2(json.loads(v.json()['jsonData'])).get('chords') or []) if v.status_code < 300 else -1
        ok = p.status_code < 300 and got == len(j['chords'])
        done[name] = {'ID': ids[name], 'before': before, 'after': got, 'ok': ok, 'log': log,
                      'url': f'https://hookpad.hooktheory.com/?idOfUserSong={slug}'}
        json.dump(done, open(ledger, 'w'), indent=1)
        print(f'[{i}/{len(names)}] {name}: {before} -> {got} chords {"ok" if ok else "CHECK"}  ' + '; '.join(log), flush=True)
        time.sleep(a.throttle)


if __name__ == '__main__':
    main()
