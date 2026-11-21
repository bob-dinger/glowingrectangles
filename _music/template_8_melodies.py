"""template_8-melodies: the rest notes of an 8-bar melody over a template_8 progression.

    template_8_melodies.py            # writes ~/Desktop/music/template_8-melodies.json
    template_8_melodies.py --upload   # also creates it in Hookpad (private), as a Hookpad 3 song
    template_8_melodies.py --upload --id N   # overwrite an existing one (either Hookpad)
    template_8_melodies.py --upload --hp2    # create it in the Hookpad 2 format instead

A melody is its rest notes (the notes it sits on) and the rest fits around them, so
each section is one progression x one REST PATTERN: the bars holding a note that
sits 2 beats or more, followed by a gap or the next phrase. Only those notes are
written, on beat 1 of their bar, on the scale degree the library's matching
sections land on most (2026-11-14, 569 sections; counts in the comments). The
space between is left empty to fill. Not legato on purpose: the gaps are the point.
"""
import copy, json, os, sys
import template_8 as T

OUT = os.path.expanduser('~/Desktop/music/template_8-melodies.json')
NAME = 'template_8-melodies'
PROG = {name: (windows, (fix[0] if fix else {})) for name, windows, *fix in T.SECTIONS}

# (template_8 section, {rest bar: (degree, beats held)})
SECTIONS = [
    ('ABCD [0,8] one per bar', {2: ('1', 3), 4: ('1', 3), 6: ('1', 3), 8: ('1', 4)}),   # 17: four 2-bar lines
    ('ABCD [0,8] one per bar', {4: ('1', 3), 8: ('5', 4)}),                            # 8: two 4-bar lines
    ('ABCD [0,8] one per bar', {8: ('1', 4)}),                                         # 7: one long line
    ('ABCD [0,8] one per bar', {1: ('5', 3), 3: ('1', 3), 5: ('1', 3), 7: ('1', 3)}),   # 5: lines land on the next downbeat
    ('ABCD [0,4,8,12] halver', {1: ('1', 3), 3: ('1', 3), 5: ('3', 3), 7: ('1', 3)}),   # 20
    ('ABCD [0,4,8,12] halver', {2: ('1', 3), 4: ('1', 3), 6: ('3', 3), 8: ('1', 4)}),   # 18
    ('ABCD [0] slow', {1: ('1', 3), 3: ('5', 3), 5: ('5', 3), 7: ('5', 3)}),            # 9
    ('ABCD [0] slow', {2: ('5', 3), 4: ('3', 3), 6: ('5', 3), 8: ('1', 4)}),            # 5
    ('ABCD [0,8]x3 [0] ender hold', {2: ('5', 3), 4: ('3', 3), 7: ('1', 7)}),           # 5 (13 in all): Maggie May, Landslide
    ('back runner bar scale I IV | V V [0,8][0]', {1: ('1', 3), 3: ('1', 3), 5: ('3', 3), 7: ('1', 3)}),  # 4 (47 in all)
    ('back runner bar scale I IV | V V [0,8][0]', {3: ('1', 6), 7: ('5', 6)}),          # 3 (17 in all)
    ('mountain held I IV V I | I IV V I [0,8][0,8][8][0,8]', {2: ('1', 3), 4: ('1', 3), 6: ('6', 3), 8: ('1', 4)}),  # 5
]


def build():
    from tempo_variant_pastes import full_json
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    tmpl_c, tmpl_n = base['chords'][0], base['notes'][0]
    chords, notes, secs, beat = [], [], [], 1
    for prog, rests in SECTIONS:
        windows, fix = PROG[prog]
        if isinstance(fix, list): fix = dict(enumerate(fix))
        name = prog.split(' [')[0] + ' / rests ' + ' '.join(map(str, rests))
        secs.append({'beat': beat, 'name': name})
        for x, du, root in T.section_chords(windows, fix):
            c = copy.deepcopy(tmpl_c); c.update(root=root, beat=beat + x / 2, duration=du)
            chords.append(c)
        for bar, (sd, held) in sorted(rests.items()):
            n = copy.deepcopy(tmpl_n); n.update(sd=sd, octave=0, beat=beat + (bar - 1) * 4, duration=held)
            notes.append(n)
        beat += 32
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat,
             breaks=[{'beat': s['beat']} for s in secs[1:]],
             keys=[{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
             meters=[{'beat': 1, 'numBeats': 4, 'beatUnit': 1}])
    o['tempos'][0]['bpm'] = 120
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': s['name'], 'lyrics': ['', '', '', '']} for s in secs]
    return o


if __name__ == '__main__':
    o = build()
    json.dump(o, open(OUT, 'w'), indent=1)
    print(f'{len(o["sections"])} sections, {len(o["notes"])} rest notes -> {OUT}')
    if '--upload' in sys.argv:
        from hookpad_upload_variants import upload, call, json_data, API
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        if '--id' in sys.argv:
            sid = sys.argv[sys.argv.index('--id') + 1]
            r = call('PATCH', f'{API}/songs/{sid}', tok, json={'jsonData': json_data(o), 'song': NAME})
            print('PATCH', r.status_code, r.text[:120])
        else:
            r, err = upload(tok, NAME, o, hp3_base=None if '--hp2' in sys.argv else True)
            print(err or r)
