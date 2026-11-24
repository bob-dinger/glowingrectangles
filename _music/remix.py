"""Remix one song section: same section, one thing changed at a time.

    remix.py --song "muse_starlight" --section Verse            # build locally, list the sections
    remix.py --song "muse_starlight" --section Verse --upload   # dated, onto the second account
    remix.py ... --tempos 70,90,110,130,150 --no-loops --no-strums

Every section of the output is the source section with ONE thing swapped, so you
hear what that one thing does. The melody is always the original notes.
  as written   the section exactly, its own tempo, its own chords and strums
  tempo N      the same section at N bpm (default 70 90 110 130 150, skipping any
               within 8 bpm of the original)
  loop X       its chord rhythm (the merged chord changes, pushes and all) under
               another of the 12 commonest four-chord loops, plain triads
  strum X      its own progression and chord changes, re-struck with a pattern
               from strum_library.json (every chord change is still struck where
               it falls, so pushes survive)

The user's workflow (2026-11-23): sections, not whole songs; mix tempos, swap the
progression under a chord rhythm, re-strum a progression. Saved on the second
Hookpad account (~/.hookpad_token_alt) as M-D-YY-<song>-<section>-remix, the
user's own date style; dated names are corpus scratch.
"""
import argparse, copy, json, os, time
import corpus, strum, template_8 as T
from rhythm_combos import LOOPS, RN


def source(song, section):
    d = json.load(open(f'{T.D}/{song}.json'))
    d['notes'] = corpus.dedupe_notes(d.get('notes') or [])
    secs = [(n, b, e) for n, b, e in corpus.sections(d) if n.strip().lower() == section.lower()]
    if not secs:
        raise SystemExit(f'no section {section!r}: ' + ', '.join(n for n, _, _ in corpus.sections(d)))
    _, st, en = secs[0]
    en = min(en, d.get('endBeat') or en)
    raw = [dict(c, beat=c['beat'] - st) for c in d['chords'] if st <= c['beat'] < en]
    merged = [(c, b - st, du) for c, b, du in corpus.merged(d['chords']) if st <= b < en]
    notes = [dict(n, beat=n['beat'] - st) for n in d['notes'] if st <= n['beat'] < en and not n.get('isRest')]
    bpm = [t for t in d.get('tempos') or [{}] if t.get('beat', 1) <= st][-1:] or [{'bpm': 100}]
    key = [k for k in d.get('keys') or [] if k['beat'] <= st][-1:] or (d.get('keys') or [{'scale': 'major', 'tonic': 'C'}])[:1]
    return dict(raw=raw, merged=merged, notes=notes, length=en - st, bpm=round(bpm[0].get('bpm') or 100),
                key=key[0], nb=(d.get('meters') or [{}])[0].get('numBeats') or 4)


def restrum(merged, length, pattern, nb):
    """the progression re-struck: a strike at every pattern onset and every chord change"""
    hits = {round(b, 4) for b, _ in [(bar * nb + o, s) for bar in range(int(length // nb))
                                     for o, s in strum.pattern_onsets(pattern)] if b < length}
    hits |= {round(b, 4) for _, b, _ in merged}
    hits = sorted(hits)
    out = []
    for i, b in enumerate(hits):
        c = [c for c, cb, _ in merged if cb <= b + 1e-6][-1]
        end = hits[i + 1] if i + 1 < len(hits) else length
        out.append(dict(copy.deepcopy(c), beat=b, duration=end - b))
    return out


def plain(root, beat, du, tmpl):
    c = copy.deepcopy(tmpl)
    c.update(root=root, beat=beat, duration=du, type=5, inversion=0, applied=0, adds=[], omits=[],
             alterations=[], suspensions=[], substitutions=[], pedal=None, borrowed='')
    return c


def build(a):
    from tempo_variant_pastes import full_json
    s = source(a.song, a.section)
    L, own = s['length'], s['bpm']
    plan = [('as written', own, s['raw'])]
    for t in a.tempos:
        if abs(t - own) > 8:
            plan.append((f'tempo {t}', t, s['raw']))
    m = s['merged']
    if not a.no_loops:
        roots = tuple(c.get('root') for c, _, _ in m[:4])
        for loop in LOOPS:
            if loop == roots: continue
            ch = [plain(loop[i % 4], b, (m[i + 1][1] if i + 1 < len(m) else L) - b, m[0][0])
                  for i, (_, b, _) in enumerate(m)]
            plan.append((f"loop {' '.join(RN[r] for r in loop)}", own, ch))
    if not a.no_strums:
        for name, pat in strum.load_lib().items():
            plan.append((f'strum {name}', own, restrum(m, L, pat, s['nb'])))
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    chords, notes, secs, tempos, beat = [], [], [], [], 1
    for label, bpm, ch in plan:
        secs.append({'beat': beat, 'name': label})
        tempos.append({'beat': beat, 'bpm': bpm, 'swingFactor': 0, 'swingBeat': 0.5})
        chords += [dict(copy.deepcopy(c), beat=beat + c['beat'], duration=min(c['duration'], L - c['beat'])) for c in ch]
        notes += [dict(copy.deepcopy(n), beat=beat + n['beat'], duration=min(n['duration'], L - n['beat'])) for n in s['notes']]
        beat += L
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat, tempos=tempos,
             breaks=[{'beat': x['beat']} for x in secs[1:]],
             keys=[dict(s['key'], beat=1)],
             meters=[{'beat': 1, 'numBeats': s['nb'], 'beatUnit': 1}])
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': x['name'], 'lyrics': ['', '', '', '']} for x in secs]
    return o


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--song', required=True, help='file name in hookpad_songs_full, no .json')
    ap.add_argument('--section', required=True)
    ap.add_argument('--tempos', default='70,90,110,130,150', type=lambda x: [int(t) for t in x.split(',') if t])
    ap.add_argument('--no-loops', action='store_true')
    ap.add_argument('--no-strums', action='store_true')
    ap.add_argument('--name')
    ap.add_argument('--main', action='store_true', help='upload to the main account instead of the second')
    ap.add_argument('--upload', action='store_true')
    a = ap.parse_args()
    t = time.localtime()
    title = a.song.split('_', 1)[-1]
    a.name = a.name or f'{t.tm_mon}-{t.tm_mday}-{t.tm_year % 100}-{title}-{a.section.lower()}-remix'
    o = build(a)
    out = os.path.expanduser(f'~/Desktop/music/{a.name}.json')
    json.dump(o, open(out, 'w'), indent=1)
    print(' | '.join(f"{x['name']}" for x in o['sections']))
    print(f'{len(o["sections"])} sections, {len(o["chords"])} chords, {len(o["notes"])} notes -> {out}')
    if a.upload:
        from hookpad_upload_variants import upload
        tok = open(os.path.expanduser('~/.hookpad_token' if a.main else '~/.hookpad_token_alt')).read().strip()
        r, err = upload(tok, a.name, o, hp3_base=True)
        print(err or r)
