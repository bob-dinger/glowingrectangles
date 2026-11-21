"""template_8-full: every template_8 section with a real melody and tempo.

    template_8_full.py                   # writes ~/Desktop/music/template_8-full.json, prints the picks
    template_8_full.py --upload          # also creates it in Hookpad (private), as a Hookpad 3 song
    template_8_full.py --upload --id 101374993   # overwrite the Hookpad 3 one (2026-11-21)

Same 31 sections and chords as template_8. For each one, the melody comes from a
library section with the same chord rhythm (8 bars of 4/4, major, chord onsets
on the same eighth slots). The section is named after its source and plays at
that song's tempo, so the melody sounds the way it was written.

Very few library sections use the template's own chords, so each note is moved
onto them chord by chord: a note keeps its place relative to the chord under it
(the 3rd of the chord stays the 3rd), shifted by the smallest step (-3..+3
degrees) that takes the source chord's root to the template chord's root. The
rhythm is untouched. When no library section has the exact chord rhythm, the
closest one is used (most onsets shared), and the name says "near". Intros, outros and solos are
skipped, a song is used once, and an original beats its -70 / -hooktab copies.
"""
import collections, copy, json, os, sys
import corpus, template_8 as T
from same_progressions import same, SKIP_SEC

OUT = os.path.expanduser('~/Desktop/music/template_8-full.json')
NAME = 'template_8-full'


def letters(seq):
    m = {}
    return ''.join(m.setdefault(x, chr(65 + len(m))) for x in seq)


def library():
    """Every major 8-bar 4/4 section whose chords start on eighth slots:
    (song, section, start, bpm, onsets, merged chords, notes)"""
    out = []
    for song, d, nb in corpus.songs():
        if nb != 4 or len({m.get('numBeats') for m in d.get('meters') or []}) > 1:
            continue
        ch = corpus.merged(d.get('chords') or [])
        notes = [n for n in d.get('notes') or [] if not n.get('isRest')]
        tempos = d.get('tempos') or [{}]
        for sec, st, en in corpus.sections(d):
            if SKIP_SEC.search(sec) or en - st != 32 or corpus.mode_at(d, st) != 'major' or corpus.mode_at(d, en - 0.01) != 'major':
                continue
            cs = [(c, b, du) for c, b, du in ch if st <= b < en]
            if not cs or abs(cs[0][1] - st) > 1e-6:
                continue
            ons = tuple(round((b - st) * 2) for _, b, _ in cs)
            if any(abs((b - st) * 2 - o) > 1e-6 for (_, b, _), o in zip(cs, ons)):
                continue
            ns = [n for n in notes if st <= n['beat'] < en]
            bars = {int((n['beat'] - st) // 4) for n in ns}
            if len(ns) < 8 or len(bars) < 6:          # a real melody, not a fragment
                continue
            bpm = [t for t in tempos if t['beat'] <= st][-1:] or tempos[:1]
            out.append(dict(song=song, sec=sec, st=st, bpm=round(bpm[0].get('bpm') or 100),
                            ons=ons, chords=[(c.get('root'), b - st) for c, b, _ in cs],
                            ids=letters([corpus.identity(c) for c, _, _ in cs]),
                            plain=all(not c.get('borrowed') and not c.get('applied') for c, _, _ in cs),
                            notes=[dict(n, beat=n['beat'] - st) for n in ns]))
    return out


def pick(tons, tlet, troots, lib, used):
    """The best source for one template section: exact onsets first, then same
    letter pattern, then same roots; among those an unused song with a typical
    note count. No exact onsets: the most shared onsets."""
    exact = [s for s in lib if s['ons'] == tons]
    near = not exact
    if near:
        best = max(len(set(s['ons']) & set(tons)) - len(set(s['ons']) ^ set(tons)) for s in lib)
        exact = [s for s in lib if len(set(s['ons']) & set(tons)) - len(set(s['ons']) ^ set(tons)) == best]
    med = sorted(len(s['notes']) for s in exact)[len(exact) // 2]
    key = lambda s: (same(s['song']) in used, same(s['song']) != s['song'].lower(),
                     not (s['plain'] and tuple(r for r, _ in s['chords']) == troots),
                     s['ids'] != tlet,
                     abs(len(s['notes']) - med), s['song'])
    return min(exact, key=key), near, len([s for s in lib if s['ons'] == tons])


def root_at(chords, t):
    r = chords[0][0]
    for root, b in chords:
        if b <= t + 1e-6: r = root
    return r


def move(notes, src, dst):
    """Each note onto the template chord under it, same place relative to its chord."""
    out = []
    for n in notes:
        delta = (root_at(dst, n['beat']) - root_at(src, n['beat'])) % 7
        if delta > 3: delta -= 7
        sd = str(n['sd']); acc = sd.rstrip('1234567'); deg = int(sd[len(acc):])
        step = (n.get('octave') or 0) * 7 + deg - 1 + delta
        out.append(dict(n, sd=acc + str(step % 7 + 1), octave=step // 7))
    return out


def build():
    from tempo_variant_pastes import full_json
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    tmpl_c, tmpl_n = base['chords'][0], base['notes'][0]
    lib = library()
    chords, notes, secs, tempos, picks, used, beat = [], [], [], [], [], set(), 1
    for name, windows, *fix in T.SECTIONS:
        fix = fix[0] if fix else {}
        if isinstance(fix, list): fix = dict(enumerate(fix))
        sc = T.section_chords(windows, fix)
        tons, troots = tuple(x for x, _, _ in sc), tuple(r for *_, r in sc)
        src, near, n_exact = pick(tons, letters(troots), troots, lib, used)
        used.add(same(src['song']))
        dst = [(r, x / 2) for x, _, r in sc]
        for x, du, root in sc:
            c = copy.deepcopy(tmpl_c); c.update(root=root, beat=beat + x / 2, duration=du)
            chords.append(c)
        for n in move(src['notes'], src['chords'], dst):
            m = copy.deepcopy(tmpl_n)
            m.update(sd=n['sd'], octave=n['octave'], beat=beat + n['beat'],
                     duration=min(n['duration'], 32 - n['beat']))
            notes.append(m)
        song = same(src['song']).split('_', 1)[-1].title()
        secs.append({'beat': beat, 'name': f"{name.split(' [')[0]} / {'near ' if near else ''}{song} {src['sec']}"})
        tempos.append({'beat': beat, 'bpm': src['bpm'], 'swingFactor': 0, 'swingBeat': 0.5})
        picks.append((name, src, near, n_exact))
        beat += 32
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat, tempos=tempos,
             breaks=[{'beat': s['beat']} for s in secs[1:]],
             keys=[{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
             meters=[{'beat': 1, 'numBeats': 4, 'beatUnit': 1}])
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': s['name'], 'lyrics': ['', '', '', '']} for s in secs]
    return o, picks


if __name__ == '__main__':
    o, picks = build()
    json.dump(o, open(OUT, 'w'), indent=1)
    for name, s, near, n in picks:
        print(f"{'near ' if near else '     '}{n:3d} {s['bpm']:4d}bpm {len(s['notes']):3d} notes  {name[:44]:44s} <- {s['song']} / {s['sec']}")
    print(f'{len(o["sections"])} sections, {len(o["notes"])} notes -> {OUT}')
    if '--upload' in sys.argv:
        from hookpad_upload_variants import upload, call, json_data, API
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        if '--id' in sys.argv:
            sid = sys.argv[sys.argv.index('--id') + 1]
            r = call('PATCH', f'{API}/songs/{sid}', tok, json={'jsonData': json_data(o), 'song': NAME})
            print('PATCH', r.status_code, r.text[:120])
        else:
            r, err = upload(tok, NAME, o, hp3_base=True)
            print(err or r)
