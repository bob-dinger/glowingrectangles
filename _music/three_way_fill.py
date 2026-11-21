#!/usr/bin/env python3
"""
Fill the chordless sections of an unfinished Hookpad song from its MIDI, checked
against the UG tab. Three sources, one vote each:

  Hookpad  hand-entered, trusted; melody runs the whole song, chords stop early
  MIDI     the whole song, beat-exact, but chords have to be read out of the notes
  UG       chord names + section labels for the whole song, loose timing

    themap_venv/python three_way_fill.py "monkees_im a believer"            # report only
    themap_venv/python three_way_fill.py "monkees_im a believer" --upload   # + a "-3way" copy in Hookpad

1. Line the MIDI up with Hookpad on the MELODY: best track, transposition, time
   scale (1, 2, 1/2) and offset, then re-fit the offset per section (fan MIDIs
   drop or add bars). A section whose melody doesn't line up is left alone.
2. UG names the chords, the MIDI times them: each section's UG progression is
   laid over the MIDI in half-bar slots (stay or step to the next chord, cycling),
   picking the timing that best explains the notes. "Fit" = how much of the music
   those chords explain vs the best free chord in every slot.
3. Calibrate: run the same thing on the sections you already did and score it
   against your chords (root per beat). That is how far to trust it on this song.
4. Which UG section: same role ("Verse", "Chorus"...; the k-th verse when the
   tab numbers them), best fit wins. The tab's key is found the same way.
5. Fill a section when the fit is >= 80%, its melody lines up >= 40%, and the
   calibration (when there are >= 32 beats to judge) is >= 70%.
   --strict (the in-place tier): fit >= 90%, melody >= 60%, and calibration
   >= 90% on >= 64 beats of your own chords. Held-out test on finished songs:
   95% of beats agree with the user's chords (vs 66% for the default tier).
"""
import argparse, collections, difflib, glob, json, os, re, sys
import hp3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mido
from v2_chord_extract import segment
from parse_ug import parse_tab, parse_chord_name as ug_chord
import synthv_song as SV
import song_render as SR
from pollack_fill import make_chord, role as _role


def role(name):
    n = name.strip().lower()
    return 'prechorus' if re.match(r'^pre\b|^pre[- ]', n) else _role(name)

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
UG = os.path.expanduser('~/Desktop/music/ug_tabs')
PAIRS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'midi_hookpad_pairs.json')
NAMES = 'C C# D Eb E F F# G Ab A Bb B'.split()
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def nrm(s): return re.sub(r'[^a-z0-9]', '', s.lower())
def snap(x, g=2): return round(x / g) * g


def load(name):
    d = json.load(open(os.path.join(D, name + '.json'))); j = d.get('jsonData', d)
    return json.loads(j) if isinstance(j, str) else j


def find_midi(name):
    mf = json.load(open(PAIRS))[name]
    return next(glob.iglob(os.path.expanduser('~/Desktop/**/' + mf), recursive=True))


def find_ug(name):
    tabs = {nrm(os.path.basename(f)[:-4]): f for f in glob.glob(UG + '/*.txt')}
    return tabs.get(nrm(name)) or tabs.get(nrm(name.split('_', 1)[-1]))


def midi_tracks(path):
    mid = mido.MidiFile(path, clip=True); tpb = mid.ticks_per_beat; out = []
    for tr in mid.tracks:
        t, on, ns = 0, {}, []
        for m in tr:
            t += m.time
            if m.type not in ('note_on', 'note_off') or m.channel == 9: continue
            k = (m.channel, m.note)
            if m.type == 'note_on' and m.velocity > 0: on.setdefault(k, []).append(t)
            elif on.get(k):
                s = on[k].pop(0)
                if t > s: ns.append((m.note, s / tpb, t / tpb))
        if ns: out.append((tr.name, sorted(ns, key=lambda n: n[1])))
    return out


def sections(j):
    S = sorted(j.get('sections') or [], key=lambda s: s['beat']); end = j.get('endBeat') or 0
    return [(s['name'], s['beat'], S[i + 1]['beat'] if i + 1 < len(S) else end) for i, s in enumerate(S)]


def match(H, idx, s, tr, off):
    """fraction of Hookpad melody notes H [(beat, pc)] with a MIDI onset at the mapped
    time (+-0.26 beat) and the transposed pitch class. idx: pc -> sorted onsets."""
    import bisect
    hit = 0
    for b, pc in H:
        x, arr = s * (b - 1) + off, idx[(pc + tr) % 12]
        i = bisect.bisect_left(arr, x - .26)
        hit += i < len(arr) and arr[i] <= x + .26
    return hit / max(len(H), 1)


def align(j, tracks):
    keys = j.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    H = [(n['beat'], SV.midi_pitch(n, keys) % 12) for n in j.get('notes') or [] if not n.get('isRest')]
    best = None
    for ti, (tname, ns) in enumerate(tracks):
        if len(ns) < 30: continue
        idx = collections.defaultdict(list)
        for p, a, _ in ns: idx[p % 12].append(a)
        for v in idx.values(): v.sort()
        hc = collections.Counter(pc for _, pc in H); mc = collections.Counter(p % 12 for p, _, _ in ns)
        trs = sorted(range(12), key=lambda t: -sum(hc[k] * mc[(k + t) % 12] for k in range(12)))[:2]
        sample = H[::max(1, len(H) // 200)]
        for s in (1, 2, .5):
            for tr in trs:
                votes = collections.Counter()
                for b, pc in sample:
                    for a in idx[(pc + tr) % 12]: votes[round((a - s * (b - 1)) * 4) / 4] += 1
                for off, _ in votes.most_common(5):
                    sc = match(H, idx, s, tr, off)
                    if not best or sc > best[0]: best = (sc, ti, s, tr, off, idx)
    return best, H


def section_offset(H, idx, s, tr, off, a, b):
    Hs = [h for h in H if a <= h[0] < b]
    if not Hs: return None, 0
    cands = [off + k * .5 for k in range(-32, 33)]
    o = max(cands, key=lambda o: (match(Hs, idx, s, tr, o), -abs(o - off)))
    return o, match(Hs, idx, s, tr, o)


def midi_chords(tracks, s, tr, off, a, b):
    """chords read from the MIDI for Hookpad beats [a, b): [(beat, dur, root_pc, qual)] in Hookpad's key frame"""
    L, ns = b - a, []
    for _, t in tracks:
        for p, x, y in t:
            hx, hy = (x - off) / s + 1 - a, (y - off) / s + 1 - a
            if hy <= 0 or hx >= L: continue
            ns.append((p, max(hx, 0), min(hy, L)))
    if not ns: return []
    _, segs = segment(ns, int(L), .5, .6)
    out = []
    for i, n, (r, q) in segs:
        st, en = snap(i), snap(i + n)
        if en <= st or (out and out[-1][0] + out[-1][1] > st): continue
        rp = (r - tr) % 12
        if out and out[-1][2:] == (rp, q) and out[-1][0] + out[-1][1] == st:
            out[-1] = (out[-1][0], out[-1][1] + en - st, rp, q); continue
        out.append((st, en - st, rp, q))
    return [(a + st, d, rp, q) for st, d, rp, q in out]


def hookpad_roots(j, a, b):
    keys = j.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    beat = {}
    for c in j.get('chords') or []:
        if c.get('isRest') or c['beat'] + c['duration'] <= a or c['beat'] >= b: continue
        try: r, iv = SR.chord_pcs(c, keys)
        except Exception: continue
        for x in range(int(max(c['beat'], a)), int(min(c['beat'] + c['duration'], b))): beat[x] = r
    return beat


def collapse(xs):
    out = []
    for x in xs:
        if not out or out[-1] != x: out.append(x)
    return out


def ug_sections(path):
    meta, secs = parse_tab(open(path).read())
    out = []
    for s in secs:
        seq = []
        for kind, payload in s['events']:
            if kind != 'chord_line': continue
            for cname, _ in payload:
                c = ug_chord(cname)
                if not c: continue
                pc = (NOTE[c['note'][0].upper()] + c['note'][1:].count('#') - c['note'][1:].count('b')) % 12
                seq.append(pc)
        if seq: out.append((s['name'], collapse(seq)))
    return out


def seq_sim(a, b):
    if not a or not b: return 0
    reps = max(1, round(len(a) / len(b)))
    return difflib.SequenceMatcher(None, a, (b * (reps + 1))[:max(len(a), len(b))]).ratio()


def slot_chroma(tracks, skip, s, off, a, b, g=2):
    """per half-bar slot of Hookpad beats [a, b): (chroma[12], bass[12]) from the MIDI, melody track left out"""
    n = max(1, int((b - a) // g)); ch = [[0.0] * 12 for _ in range(n)]; bs = [[0.0] * 12 for _ in range(n)]
    for ti, (_, t) in enumerate(tracks):
        if ti == skip: continue
        for p, x, y in t:
            hx, hy = (x - off) / s + 1 - a, (y - off) / s + 1 - a
            for k in range(max(0, int(hx // g)), min(n, int(hy // g) + 1)):
                ov = min(hy, (k + 1) * g) - max(hx, k * g)
                if ov > 0:
                    ch[k][p % 12] += ov
                    if p < 52: bs[k][p % 12] += ov
    return ch, bs


def chord_score(c, b, r, q):
    tot = sum(c) or 1; bt = sum(b) or 1
    tones = {r, (r + (3 if q == 'min' else 4)) % 12, (r + 7) % 12}
    on = sum(c[t] for t in tones) / tot
    return on - .5 * (1 - on) + .5 * b[r] / bt


ALL = [(r, q) for r in range(12) for q in ('maj', 'min')]


def fit_seq(ch, bs, U):
    """lay UG chords U [(pc, q)] over the slots in order (stay or step to the next, cycling),
    starting anywhere. -> (fit 0..1 vs the best free chord per slot, [chord index per slot])"""
    n, m = len(ch), len(U)
    if not n or not m: return 0, []
    sc = [[chord_score(ch[i], bs[i], *U[k]) for k in range(m)] for i in range(n)]
    free = sum(max(chord_score(ch[i], bs[i], *c) for c in ALL) for i in range(n) if sum(ch[i]))
    dp = [sc[0][k] - (.05 if k else 0) for k in range(m)]; bk = []
    for i in range(1, n):
        prev = dp; dp = []; bk.append([])
        for k in range(m):
            stay, step = prev[k], prev[(k - 1) % m]
            bk[-1].append(k if stay >= step else (k - 1) % m)
            dp.append(max(stay, step) + sc[i][k])
    k = max(range(m), key=lambda k: dp[k]); path = [k]
    for row in reversed(bk): k = row[k]; path.append(k)
    path.reverse()
    silent = sum(1 for i in range(n) if not sum(ch[i]))
    got = sum(sc[i][path[i]] for i in range(n) if sum(ch[i]))
    return (got / free if free > 0 and silent < n else 0), path


def ug_sections2(path):
    meta, secs = parse_tab(open(path).read()); out = []
    for s_ in secs:
        seq = []
        for kind, payload in s_['events']:
            if kind != 'chord_line': continue
            for cname, _ in payload:
                c = ug_chord(cname)
                if not c: continue
                pc = (NOTE[c['note'][0].upper()] + c['note'][1:].count('#') - c['note'][1:].count('b')) % 12
                q = 'min' if str(c.get('quality', '')).startswith('m') and not str(c.get('quality', '')).startswith('maj') else 'maj'
                if not seq or seq[-1] != (pc, q): seq.append((pc, q))
        if seq: out.append((s_['name'], seq))
    return out


STRICT = False   # --strict: only the obvious ones (see the docstring)


def run(name, verbose=True, j=None):
    j = j if j is not None else load(name)
    try: tracks = midi_tracks(find_midi(name))
    except Exception as e: raise SystemExit(f'{name}: MIDI unreadable ({e})')
    al = align(j, tracks)
    if not al or not al[0]: raise SystemExit(f'{name}: no MIDI track with enough notes to line up')
    (sc, ti, s, tr, off, idx), H = al
    say = print if verbose else (lambda *x, **k: None)
    say(f'{name}\n  MIDI melody track {ti} "{tracks[ti][0]}", melody match {sc:.0%} '
        f'(time x{s:g}, transpose {tr:+d}, offset {off:g} beats)')
    if sc < .4: raise SystemExit(f'  the MIDI melody matches yours only {sc:.0%}: not this MIDI')
    # leave the melody out of the harmony unless it is all the MIDI has
    skip = ti if sum(len(t) for i, (_, t) in enumerate(tracks) if i != ti) >= 200 else None
    keys = j.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    ugp = find_ug(name)
    if not ugp: raise SystemExit('  no UG tab')
    ug0 = ug_sections2(ugp)
    per = []
    for n, a, b in sections(j):
        o, m = section_offset(H, idx, s, tr, off, a, b)
        ch, bs = slot_chroma(tracks, skip, s, o if o is not None else off, a, b)
        per.append(dict(name=n, a=a, b=b, mel=m, ch=ch, bs=bs, hp=hookpad_roots(j, a, b)))
    # UG key -> MIDI key: the transposition under which the tab explains the MIDI best
    def total(t):
        U = [(un, [((pc + t) % 12, q) for pc, q in u]) for un, u in ug0]
        return sum(max((fit_seq(p['ch'], p['bs'], u)[0] for _, u in U), default=0) for p in per[::2])
    ug_t = max(range(12), key=total)
    ug = [(un, [((pc + ug_t) % 12, q) for pc, q in u]) for un, u in ug0]
    say(f'  UG: {os.path.basename(ugp)}, {len(ug)} sections, shifted {ug_t:+d} semitones onto the MIDI')
    seen = collections.Counter()
    for p in per:
        r = role(p['name']); seen[r] += 1
        same = [u for u in ug if role(u[0]) == r]
        kth = [u for u in same if re.search(rf'\b({seen[r]}|{"I" * seen[r]})\b', u[0])]
        best = None
        for un, u in (kth or same):
            f, path = fit_seq(p['ch'], p['bs'], u)
            if not best or f > best[0]: best = (f, un, u, path)
        p['fit'] = best
        if best:   # chords in Hookpad's frame, merged
            out = []
            for i, k in enumerate(best[3]):
                pc, q = best[2][k]; c = ((pc - tr) % 12, q)
                if out and out[-1][2:] == c: out[-1][1] += 2
                else: out.append([p['a'] + 2 * i, 2, *c])
            p['chords'] = out
    # calibration: the same method on the sections you already did
    agree = tot = 0
    for p in per:
        if not p['hp'] or not p.get('chords') or p['mel'] < .6: continue   # only where the MIDI is lined up
        for st, d, pc, q in p['chords']:
            for x in range(int(st), int(st + d)):
                if x in p['hp']: tot += 1; agree += p['hp'][x] == pc
    cal = agree / tot if tot >= (64 if STRICT else 32) else None
    say('  calibration on your chords: ' + (f'{cal:.0%} of {tot} beats' if cal is not None else f'only {tot} beats, not used'))
    fills, rows = [], []
    for p in per:
        if p['hp']: continue
        f = p['fit']
        if STRICT: ok = bool(f) and f[0] >= .9 and p['mel'] >= .6 and cal is not None and cal >= .9
        else: ok = bool(f) and f[0] >= .8 and p['mel'] >= .4 and (cal is None or cal >= .7)
        txt = ' '.join(NAMES[c[2]] + ('m' if c[3] == 'min' else '') for c in p.get('chords', [])[:12])
        why = f'melody {p["mel"]:.0%}, ' + (f'UG "{f[1]}" fit {f[0]:.0%}' if f else 'no UG section of that kind')
        rows.append((p['name'], (p['a'] - 1) // 4 + 1, (p['b'] - p['a']) // 4, why, ok, txt))
        if ok: fills.append(p)
    for n, bar, L, why, ok, txt in rows:
        say(f'    {n.strip():14} bar {bar:>3} ({L:>2} bars)  {why:42} {"FILL" if ok else "skip"}  {txt}')
    added = []
    for p in fills:
        for st, d, pc, q in p['chords']:
            k = SV.key_at(keys, st)
            mode = 'minor' if (k.get('scale') or 'major') in ('minor', 'dorian', 'phrygian', 'harmonicMinor', 'locrian') else 'major'
            added.append(make_chord(NAMES[pc] + ('m' if q == 'min' else ''), st, d, SV.PC[k['tonic']], mode))
    j['chords'] = sorted((j.get('chords') or []) + added, key=lambda c: c['beat'])
    say(f'  filled {len(fills)} of {len(rows)} empty sections, {len(added)} chords')
    return j, dict(cal=cal, melody=sc, filled=len(fills), empty=len(rows),
                   sections=[(p['name'], p['a'], p['b'], p['fit'][0] if p['fit'] else None, p['mel'], p.get('chords', [])) for p in per])


def push(names, throttle=6):
    """--push: strict fill IN PLACE on the main account. Each song is pulled fresh,
    backed up to ~/Desktop/hookpad_fill_backups/three_way/<name>.json, filled,
    PATCHed, read back. Ledger _done.json there; a rerun skips what's done."""
    import time, hookpad_upload_variants as U, fill_repeat_chords as F
    global STRICT; STRICT = True
    bk = os.path.join(F.BK, 'three_way'); os.makedirs(bk, exist_ok=True)
    tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
    ids = {}
    for x in hp3.newest_per_name(json.load(open(F.LIST))): ids[x['song']] = ids[x['song'].lower()] = x['ID']   # the Hookpad 3 copy, if one exists
    ledger = os.path.join(bk, '_done.json')
    done = json.load(open(ledger)) if os.path.exists(ledger) else {}
    for i, name in enumerate(names, 1):
        if name in done: continue
        if name not in ids: print(f'[{i}] {name}: not in catalog list'); continue
        slug = U.HASH.encode(ids[name])
        g = U.call('GET', f'{U.API}/songs/{slug}?fields=ID,song,jsonData', tok)
        if g.status_code == 401: sys.exit('token rejected (401): paste a fresh main bearer and re-run; done songs are skipped')
        if g.status_code >= 300: print(f'[{i}] {name}: GET {g.status_code}'); continue
        rec = g.json()
        json.dump(rec, open(os.path.join(bk, re.sub(r'[/:]', '_', name) + '.json'), 'w'))
        j = hp3.to_hp2(json.loads(rec['jsonData'])); j.pop('fp', None)
        before = len(j.get('chords') or [])
        try: j, info = run(name, False, j)
        except SystemExit as e: print(f'[{i}] {name}: {e}'); continue
        if not info['filled']: done[name] = {'filled': 0}; print(f'[{i}] {name}: nothing obvious on the fresh copy'); continue
        time.sleep(1)
        p = U.call('PATCH', f'{U.API}/songs/{ids[name]}', tok, json={'jsonData': U.json_data(j), 'cloudBackupsEnabled': True})
        if p.status_code == 401: sys.exit('token rejected (401) mid-song: nothing was saved for ' + name)
        time.sleep(1)
        v = U.call('GET', f'{U.API}/songs/{slug}?fields=ID,jsonData', tok)
        got = len(hp3.to_hp2(json.loads(v.json()['jsonData'])).get('chords') or []) if v.status_code < 300 else -1
        ok = p.status_code < 300 and got == len(j['chords'])
        secs = [n.strip() for n, a, b, f, m, c in info['sections'] if c and f and f >= .9 and m >= .6]
        done[name] = {'ID': ids[name], 'before': before, 'after': got, 'ok': ok, 'cal': info['cal'],
                      'filled': info['filled'], 'url': f'https://hookpad.hooktheory.com/?idOfUserSong={slug}'}
        json.dump(done, open(ledger, 'w'), indent=1)
        print(f'[{i}/{len(names)}] {name}: {before} -> {got} chords {"ok" if ok else "CHECK"} (cal {info["cal"]:.0%}, {info["filled"]} sections)', flush=True)
        time.sleep(throttle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song', nargs='*'); ap.add_argument('--upload', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--push', action='store_true', help='strict fill in place on the main account (song names, or none = the survey list)')
    ap.add_argument('--survey', help='json of {name: ...} to push when no names are given')
    a = ap.parse_args()
    if a.push: return push(a.song or list(json.load(open(a.survey))))
    global STRICT; STRICT = a.strict
    j, info = run(a.song[0])
    if a.upload:
        import hookpad_upload_variants as U
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        j.pop('fp', None)
        rec, err = U.upload(tok, a.song[0] + '-3way', j)
        print(rec['url'] if rec else err)


if __name__ == '__main__':
    main()
