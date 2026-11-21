"""One section's rhythm under the library's common four-chord loops: progression x melody combos.

    rhythm_combos.py                                   # Starlight verse -> ~/Desktop/music/template_starlight-combos.json
    rhythm_combos.py --song "muse_starlight" --section Verse --name template_starlight-combos
    rhythm_combos.py --upload                          # also creates it in Hookpad (private), as a Hookpad 3 song
    rhythm_combos.py --upload --id 101375012           # overwrite the Starlight one (Hookpad 3, 2026-11-21)

Keeps the source section's first 8 bars of rhythm exactly: its chord onsets
(the push and all) and its melody's onsets and lengths, at its tempo. What
changes is the progression, cycled through the chord onsets: the 12 commonest
four-chord loops in the library's 8-bar major sections (2026-11-21 count).

Each loop gets two melodies:
  follows     the melody moved onto the new chords, each note keeping its place
              relative to the chord under it (template_8_full.move)
  same notes  the original scale degrees, unchanged, so the new chords recolour
              the same tune
The source's own loop comes first, played once as written.
"""
import argparse, copy, json, os, sys
import corpus, template_8 as T
from template_8_full import move

LOOPS = [(1, 2, 6, 4), (1, 6, 5, 4), (6, 4, 1, 5), (1, 5, 6, 4), (4, 1, 6, 5), (1, 5, 2, 4),
         (1, 4, 6, 5), (1, 6, 4, 5), (2, 4, 1, 5), (6, 5, 4, 1), (5, 2, 4, 1), (1, 5, 3, 4)]
RN = {1: 'I', 2: 'ii', 3: 'iii', 4: 'IV', 5: 'V', 6: 'vi', 7: 'vii'}


def source(song, section):
    d = json.load(open(f'{T.D}/{song}.json'))
    d['notes'] = corpus.dedupe_notes(d.get('notes') or [])
    st = next(b for name, b, _ in corpus.sections(d) if name.strip().lower() == section.lower())
    ch = [(c.get('root'), b - st) for c, b, _ in corpus.merged(d['chords']) if st <= b < st + 32]
    ns = [dict(n, beat=n['beat'] - st) for n in d['notes'] if st <= n['beat'] < st + 32 and not n.get('isRest')]
    bpm = [t for t in d.get('tempos') or [{}] if t.get('beat', 1) <= st][-1:] or [{'bpm': 100}]
    return ch, ns, round(bpm[0].get('bpm') or 100)


def build(song, section):
    from tempo_variant_pastes import full_json
    ch, ns, bpm = source(song, section)
    own = tuple(r for r, _ in ch[:4])
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    tmpl_c, tmpl_n = base['chords'][0], base['notes'][0]
    chords, notes, secs, beat = [], [], [], 1
    plan = [(own, 'as written', ns)]
    for loop in [own] + [l for l in LOOPS if l != own]:
        dst = [(loop[i % 4], b) for i, (_, b) in enumerate(ch)]
        if loop != own:
            plan.append((loop, 'same notes', ns))
        plan.append((loop, 'follows', move(ns, ch, dst)))
    plan = [plan[0]] + [p for p in plan[1:] if not (p[0] == own and p[1] == 'follows')]
    for loop, how, mel in plan:
        secs.append({'beat': beat, 'name': f"{' '.join(RN[r] for r in loop)} / {how}"})
        for i, (_, b) in enumerate(ch):
            end = ch[i + 1][1] if i + 1 < len(ch) else 32
            c = copy.deepcopy(tmpl_c); c.update(root=loop[i % 4], beat=beat + b, duration=end - b)
            chords.append(c)
        for n in mel:
            m = copy.deepcopy(tmpl_n)
            m.update(sd=str(n['sd']), octave=n.get('octave') or 0, beat=beat + n['beat'],
                     duration=min(n['duration'], 32 - n['beat']))
            notes.append(m)
        beat += 32
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat,
             tempos=[{'beat': 1, 'bpm': bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
             breaks=[{'beat': s['beat']} for s in secs[1:]],
             keys=[{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
             meters=[{'beat': 1, 'numBeats': 4, 'beatUnit': 1}])
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': s['name'], 'lyrics': ['', '', '', '']} for s in secs]
    return o


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--song', default='muse_starlight')
    ap.add_argument('--section', default='Verse')
    ap.add_argument('--name', default='template_starlight-combos')
    ap.add_argument('--upload', action='store_true')
    ap.add_argument('--id')
    a = ap.parse_args()
    o = build(a.song, a.section)
    out = os.path.expanduser(f'~/Desktop/music/{a.name}.json')
    json.dump(o, open(out, 'w'), indent=1)
    print('\n'.join(s['name'] for s in o['sections']))
    print(f'{len(o["sections"])} sections, {len(o["notes"])} notes, {o["tempos"][0]["bpm"]} bpm -> {out}')
    if a.upload:
        from hookpad_upload_variants import upload, call, json_data, API
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        if a.id:
            r = call('PATCH', f'{API}/songs/{a.id}', tok, json={'jsonData': json_data(o), 'song': a.name})
            print('PATCH', r.status_code, r.text[:120])
        else:
            r, err = upload(tok, a.name, o, hp3_base=True)
            print(err or r)
