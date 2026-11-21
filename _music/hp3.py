"""Hookpad 3 songs -> the Hookpad 2 shape every script here reads.

Hookpad 3 (released 2026-11-18) saves a song as a NEW song with the same name
(flagged madeInHookpad3 in the song list) in a new format, version 3.x:

    {ppqn: 480, version: '3.1.0', score: {sections: [...], arrangement: [...], ...}}

Each section holds its own notes / chords / keys / tempos / meters / swings /
lyrics, timed in ticks from the section's start; `arrangement` lists the
sections in song order (a section can appear more than once). Notes carry a
voice 1-4 (Hookpad 2's four melody layers).

to_hp2(d) lays the arrangement end to end and gives back a Hookpad 2-shaped
dict: notes / chords on beats (1-based), keys / tempos / meters only where they
change, sections [{beat, name}], breaks at section starts, lyrics with values +
sectionLyrics, inactiveNotes for the four voices, endBeat. Hookpad 3 splits a
note that crosses a section boundary in two, the second half with an `n_` id;
those are joined back (same pitch, the first ending exactly where the second
starts, at a boundary), which is what the Hookpad 2 original had. Applied chords
are stored the other way round (Hookpad 3: root = target, applied = function;
Hookpad 2: V/IV is root 5, applied 4) and are swapped back. The result carries `hp3: True` so a reader can tell.

save(parsed, fname) is the one call the downloaders use: a Hookpad 3 song is
written converted to fname, and the raw file kept in hookpad_songs_hp3/. It
returns what it wrote. newest_per_name(list) keeps one list entry per name, the
newest, so the Hookpad 3 copy stands in for its song.

Writing back: from_hp2(edited, live) puts an edited Hookpad 2-shaped song back
into the live Hookpad 3 song (instruments, mixer and tabs kept); payload_for()
gives the jsonData to PATCH. hookpad_upload_variants.call does this by itself for
any PATCH of a Hookpad 3 song, and lyrics_run reads and writes through it, so the
writers work on songs from either Hookpad.

    hp3.py <file.json>      # convert one file, print a summary
"""
import json, os, sys

RAW_DIR = os.path.expanduser('~/Desktop/music/hookpad_songs_hp3')


def is_hp3(d):
    return isinstance(d, dict) and isinstance(d.get('score'), dict) and 'sections' in d['score']


def _num(x):
    x = round(x, 6)
    return int(x) if x == int(x) else x


def _meter(m):
    # Hookpad 2 counts the beat unit in quarter notes (4/4 = numBeats 4, beatUnit 1)
    bu = m.get('beatUnit') or 4
    return {'numBeats': m.get('numBeats', 4), 'beatUnit': _num(4 / bu)}


CHORD_KEYS = ['root', 'type', 'inversion', 'applied', 'adds', 'omits', 'alterations',
              'suspensions', 'substitutions', 'pedal', 'alternate', 'borrowed', 'isRest']


def to_hp2(d):
    if not is_hp3(d):
        return d
    ppqn = d.get('ppqn') or 480
    sc = d['score']
    secs = {s['id']: s for s in sc['sections']}
    order = [secs[c['sectionId']] for c in sc.get('arrangement') or [] if c.get('sectionId') in secs]
    if not order:
        order = sc['sections']

    voices = {1: [], 2: [], 3: [], 4: []}
    chords, keys, tempos, meters, sections, lyr = [], [], [], [], [], []
    bounds = set()
    off = 0                                     # ticks
    beat = lambda t: _num((off + t) / ppqn + 1)
    for s in order:
        start = beat(0)
        sections.append({'beat': start, 'name': s.get('name') or ''})
        if off:
            bounds.add(start)
        for n in sorted(s.get('notes') or [], key=lambda n: n.get('startTick', 0)):
            voices.setdefault(n.get('voice') or 1, []).append({
                'sd': n.get('sd'), 'octave': n.get('octave', 0),
                'beat': beat(n.get('startTick', 0)), 'duration': _num(n.get('durationTicks', 0) / ppqn),
                'isRest': bool(n.get('isRest')), 'recordingEndBeat': None, '_id': n.get('id') or ''})
        for c in sorted(s.get('chords') or [], key=lambda c: c.get('startTick', 0)):
            o = {k: c.get(k) for k in CHORD_KEYS if k in c}
            o.setdefault('alternate', '')
            if o.get('applied'):                # Hookpad 3: root = target, applied = function (V/IV is root 4, applied 5)
                o['root'], o['applied'] = o['applied'], o['root']
            o['beat'] = beat(c.get('startTick', 0))
            o['duration'] = _num(c.get('durationTicks', 0) / ppqn)
            o['recordingEndBeat'] = None
            chords.append(o)
        sw = {w.get('startTick', 0): w for w in s.get('swings') or []}
        for k in s.get('keys') or []:
            keys.append({'beat': beat(k.get('startTick', 0)), 'scale': k.get('scale'), 'tonic': k.get('tonic')})
        for t in s.get('tempos') or []:
            w = sw.get(t.get('startTick', 0)) or (s.get('swings') or [{}])[0]
            tempos.append({'beat': beat(t.get('startTick', 0)), 'bpm': t.get('bpm'),
                           'swingBeat': w.get('swingBeat', 0.5), 'swingFactor': w.get('swingFactor', 0)})
        for m in s.get('meters') or []:
            meters.append({'beat': beat(m.get('startTick', 0)), **_meter(m)})
        ly = next((x.get('lyrics') for x in s.get('lyrics') or [] if x.get('lyrics') is not None), None)
        lyr.append({'lyrics': list(ly or ['', '', '', '']), 'sectionName': s.get('name') or ''})
        off += s.get('endTick') or 0

    def changes(xs, fields):
        out = []
        for x in xs:
            if out and all(out[-1].get(f) == x.get(f) for f in fields):
                continue
            out.append(x)
        return out

    def join(ns):
        out = []
        for n in ns:
            # look back a few notes: a doubled note (two copies on one onset) splits twice
            p = next((q for q in reversed(out[-8:]) if _num(q['beat'] + q['duration']) == n['beat']
                      and q['sd'] == n['sd'] and q['octave'] == n['octave']), None)
            if (p and n['beat'] in bounds and n['_id'].startswith('n_') and not n['isRest'] and not p['isRest']
                    and p['sd'] == n['sd'] and p['octave'] == n['octave']
                    and _num(p['beat'] + p['duration']) == n['beat']):
                p['duration'] = _num(p['duration'] + n['duration'])
                continue
            out.append(dict(n))
        for n in out:
            n.pop('_id', None)
        return out

    layers = [join(voices.get(v, [])) for v in (1, 2, 3, 4)]
    values = ['\n'.join(x['lyrics'][i] for x in lyr if i < len(x['lyrics']) and (x['lyrics'][i] or '').strip())
              for i in range(4)]
    return {
        'version': 1, 'hp3': True, 'hp3Version': d.get('version'),
        'notes': layers[0], 'chords': chords,
        'keys': changes(keys, ('scale', 'tonic')),
        'tempos': changes(tempos, ('bpm', 'swingBeat', 'swingFactor')),
        'meters': changes(meters, ('numBeats', 'beatUnit')),
        'sections': sections,
        'breaks': [{'beat': s['beat']} for s in sections[1:]],
        'lyrics': {'isOpen': False, 'values': values, 'sectionLyrics': lyr},
        'inactiveNotes': layers, 'activeMelodyIndex': 0, 'visibleMelodies': [0, 1, 2, 3],
        'keyFrames': sc.get('keyFrames') or [], 'youtube': sc.get('youtube'),
        'pickup': False, 'endBeat': _num(off / ppqn + 1),
    }


def save(parsed, fname):
    """Write a downloaded song: Hookpad 3 converted (raw kept in RAW_DIR), else as is."""
    if is_hp3(parsed):
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(os.path.join(RAW_DIR, os.path.basename(fname)), 'w', encoding='utf-8') as fh:
            json.dump(parsed, fh, ensure_ascii=False)
        parsed = to_hp2(parsed)
    with open(fname, 'w', encoding='utf-8') as fh:
        json.dump(parsed, fh, ensure_ascii=False)
    return parsed


def newest_per_name(songs, key=lambda s: s['song']):
    """List entries -> one per song name, the most recently modified (a Hookpad 3
    save is a new song with the same name; it is the newer version)."""
    best = {}
    for s in songs:
        k = key(s)
        if k not in best or (s.get('dateModified') or '') > (best[k].get('dateModified') or ''):
            best[k] = s
    return list(best.values())


# --- writing: Hookpad 2 shape back into a Hookpad 3 song ---------------------

def _rid(prefix=''):
    import random, string
    return prefix + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(15))


def _at(xs, b):
    """The entry in effect at beat b (xs sorted by beat)."""
    cur = xs[0] if xs else None
    for x in xs:
        if x['beat'] <= b + 1e-9:
            cur = x
    return cur


def _resize(sec, end_tick, ppqn):
    """A section's instrument regions follow its length; drum markers are one per bar."""
    for t in sec.get('instrumentTracks') or []:
        for r in t.get('regions') or []:
            r['startTick'] = 0
            r['endTick'] = end_tick
            if r.get('markers'):
                bar = (sec.get('meters') or [{}])[0]
                bar_ticks = (bar.get('numBeats', 4) * 4 / (bar.get('beatUnit') or 4)) * ppqn
                n = max(1, int(round(end_tick / bar_ticks)))
                old = r['markers']
                r['markers'] = [{**old[i % len(old)], 'bar': i} for i in range(n)]
        t['regions'] = (t.get('regions') or [])[:1]


def from_hp2(o, base):
    """An edited Hookpad 2-shaped song -> a Hookpad 3 song, built on `base` (the
    live Hookpad 3 song): its instruments, mixer, view and section tabs are kept;
    notes, chords, keys, tempos, meters and lyrics come from `o`, split by o's
    sections. Sections that keep their length keep their Hookpad 3 section
    (instrument regions and all); a new or resized section copies the base
    section with the same name (else the same place, else the last) and is
    resized. A section shared by several arrangement slots stays shared only if
    every slot got the same content."""
    import copy
    if is_hp3(o):
        return o
    out = copy.deepcopy(base)
    ppqn = out.get('ppqn') or 480
    sc = out['score']
    bsecs = {s['id']: s for s in sc['sections']}
    border = [bsecs[c['sectionId']] for c in sc.get('arrangement') or [] if c.get('sectionId') in bsecs] or sc['sections']
    bstarts, t = [], 0
    for s in border:
        bstarts.append((t, s.get('endTick') or 0)); t += s.get('endTick') or 0

    end_beat = o.get('endBeat') or 1
    secs = sorted(o.get('sections') or [], key=lambda s: s['beat']) or [{'beat': 1, 'name': border[0].get('name', 'Section 1')}]
    if secs[0]['beat'] > 1:
        secs = [{'beat': 1, 'name': border[0].get('name', '')}] + secs
    spans = [(s['beat'], (secs[i + 1]['beat'] if i + 1 < len(secs) else end_beat), s.get('name') or '') for i, s in enumerate(secs)]
    bounds = [b for b, _, _ in spans[1:]]

    # voices: the active layer is `notes`, the rest come from inactiveNotes
    act = o.get('activeMelodyIndex') or 0
    ina = o.get('inactiveNotes') or []
    layers = {v: (o.get('notes') or []) if v - 1 == act else (ina[v - 1] if v - 1 < len(ina) else []) for v in (1, 2, 3, 4)}

    def split(items, bnds):
        """Cut anything that crosses a section boundary; the later piece is marked."""
        res = []
        for x in items:
            b, e = x['beat'], x['beat'] + x['duration']
            pieces, first = [], True
            for cut in bnds:
                if b < cut - 1e-9 < e - 2e-9:
                    pieces.append((b, cut, first)); b, first = cut, False
            pieces.append((b, e, first))
            for pb, pe, f in pieces:
                res.append({**x, 'beat': _num(pb), 'duration': _num(pe - pb), '_cont': not f})
        return res

    keys = sorted(o.get('keys') or [{'beat': 1, 'scale': 'major', 'tonic': 'C'}], key=lambda x: x['beat'])
    tempos = sorted(o.get('tempos') or [{'beat': 1, 'bpm': 120}], key=lambda x: x['beat'])
    meters = sorted(o.get('meters') or [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}], key=lambda x: x['beat'])
    notes = {v: split(sorted(layers[v], key=lambda n: n['beat']), bounds) for v in layers}
    chords = split(sorted(o.get('chords') or [], key=lambda c: c['beat']), bounds)
    sl = (o.get('lyrics') or {}).get('sectionLyrics') or []
    vals = (o.get('lyrics') or {}).get('values') or []
    base_meter = {m.get('numBeats'): m for s in border for m in s.get('meters') or []}

    def content(i, b0, b1):
        tk = lambda b: int(round((b - b0) * ppqn))
        inside = lambda x: b0 - 1e-9 <= x['beat'] < b1 - 1e-9
        ns = []
        for v in (1, 2, 3, 4):
            for n in notes[v]:
                if inside(n):
                    ns.append({'id': _rid('n_' if n['_cont'] else ''), 'sd': n.get('sd'), 'voice': v,
                               'isRest': bool(n.get('isRest')), 'octave': n.get('octave', 0),
                               'startTick': tk(n['beat']), 'durationTicks': tk(n['beat'] + n['duration']) - tk(n['beat'])})
        cs = []
        for c in chords:
            if inside(c):
                x = {k: c.get(k) for k in CHORD_KEYS if k in c and k != 'alternate'}
                if x.get('applied'):
                    x['root'], x['applied'] = x['applied'], x['root']
                x.update(id=_rid(), startTick=tk(c['beat']), durationTicks=tk(c['beat'] + c['duration']) - tk(c['beat']))
                cs.append(x)

        def track(xs, make):
            got = [x for x in xs if b0 + 1e-9 < x['beat'] < b1 - 1e-9]
            return [make(_at(xs, b0), 0)] + [make(x, tk(x['beat'])) for x in got]
        ks = track(keys, lambda k, st: {'id': _rid(), 'scale': k.get('scale'), 'tonic': k.get('tonic'), 'startTick': st})
        ts = track(tempos, lambda x, st: {'id': _rid(), 'bpm': x.get('bpm'), 'startTick': st})
        sw = track(tempos, lambda x, st: {'id': _rid('swing_'), 'startTick': st, 'swingBeat': x.get('swingBeat', 0.5), 'swingFactor': x.get('swingFactor', 0)})
        def meter(m, st):
            bm = base_meter.get(m.get('numBeats'), {})
            return {'id': _rid(), 'beatUnit': int(round(4 / (m.get('beatUnit') or 1))), 'compound': bm.get('compound', 1),
                    'numBeats': m.get('numBeats', 4), 'hp2Legacy': True, 'startTick': st}
        ms = track(meters, meter)
        if i < len(sl) and sl[i].get('lyrics') is not None:
            ly = list(sl[i]['lyrics'])
        elif not sl and i == 0:
            ly = list(vals) + [''] * (4 - len(vals))
        else:
            ly = ['', '', '', '']
        return {'notes': ns, 'chords': cs, 'keys': ks, 'tempos': ts, 'swings': sw, 'meters': ms,
                'lyrics': ly, 'endTick': tk(b1)}

    built = [content(i, b0, b1) for i, (b0, b1, _) in enumerate(spans)]
    same_shape = len(spans) == len(border) and all(
        int(round((b0 - 1) * ppqn)) == bs and built[i]['endTick'] == bl for i, ((b0, _, _), (bs, bl)) in enumerate(zip(spans, bstarts)))

    def norm(c):   # content without the fresh ids, to see if shared slots agree
        strip = lambda xs: [{k: v for k, v in x.items() if k != 'id'} for x in xs]
        return json.dumps({k: (strip(v) if isinstance(v, list) and v and isinstance(v[0], dict) else v) for k, v in c.items()}, sort_keys=True)

    new_secs, arrangement, used = [], [], {}
    for i, ((b0, b1, name), c) in enumerate(zip(spans, built)):
        if same_shape:
            tmpl = border[i]
        else:
            tmpl = (next((s for s in border if (s.get('name') or '').lower() == name.lower()), None)
                    or (border[i] if i < len(border) else border[-1]))
        sid = tmpl['id']
        if sid in used and (not same_shape or used[sid][1] != norm(c)):
            sid = None                      # a slot that now differs gets its own section
        if same_shape and sid in used:
            arrangement.append({'id': _rid('clip_'), 'sectionId': sid}); continue
        sec = copy.deepcopy(tmpl)
        if sid is None or (not same_shape and sid in used):
            sec['id'] = _rid('sec_')
        sec['name'] = name
        for k in ('notes', 'chords', 'keys', 'tempos', 'swings', 'meters', 'endTick'):
            sec[k] = c[k]
        sec['lyrics'] = [{'lyrics': c['lyrics'], 'sectionId': sec['id']}]
        sec['breaks'] = []
        if not same_shape or tmpl.get('endTick') != c['endTick']:
            _resize(sec, c['endTick'], ppqn)
        used.setdefault(sec['id'], (sec, norm(c)))
        new_secs.append(sec)
        arrangement.append({'id': _rid('clip_'), 'sectionId': sec['id']})
    if same_shape:   # keep the base's clip ids where the slot is unchanged
        for a, b in zip(arrangement, sc.get('arrangement') or []):
            if a['sectionId'] == b.get('sectionId'):
                a['id'] = b['id']
    sc['sections'] = new_secs
    sc['arrangement'] = arrangement
    if o.get('keyFrames') is not None:
        sc['keyFrames'] = o['keyFrames']
    return out


def payload_for(live_raw, o):
    """What to PATCH as jsonData: o as is for a Hookpad 2 song, converted onto the
    live song for a Hookpad 3 one (no fp: Hookpad 3 files carry none)."""
    live = json.loads(live_raw) if isinstance(live_raw, str) else live_raw
    if not is_hp3(live):
        return None
    o = {k: v for k, v in o.items() if k != 'fp'}
    return json.dumps(from_hp2(o, live), separators=(',', ':'), ensure_ascii=False)


if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    o = to_hp2(d)
    print(f"hp3={is_hp3(d)}  notes {len(o['notes'])}  chords {len(o['chords'])}  endBeat {o.get('endBeat')}  "
          f"sections {[(s['beat'], s['name']) for s in o.get('sections') or []][:8]}")


# --- clipboard: paste JSON that both Hookpads accept ---------------------------

def _jsnum(o):
    """Numbers as JavaScript's JSON.stringify prints them (2.0 -> 2), so the
    checksum Hookpad recomputes in the browser matches ours."""
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _jsnum(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsnum(v) for v in o]
    return o


def clipboard(obj):
    """A Hookpad 2-shaped paste object (notes, chords, keys, tempos, meters,
    sections, breaks) -> the paste text. No `version` key: Hookpad 3 rejects any
    version but its own ('hooktheory-clipboard-v1'), so the old `version: 1`
    bypass is dead there. Instead the real fp: SHA-1 of the compact JSON without
    fp, the check both Hookpad 2 and Hookpad 3's legacy paste make."""
    import hashlib
    o = _jsnum({k: v for k, v in obj.items() if k not in ('fp', 'version')})
    s = json.dumps(o, separators=(',', ':'), ensure_ascii=False)
    o['fp'] = hashlib.sha1(s.encode('utf-8')).hexdigest()
    return json.dumps(o, separators=(',', ':'), ensure_ascii=False)
