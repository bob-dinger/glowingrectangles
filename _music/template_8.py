"""template_8: every 8-bar section shape (verse, chorus, pre, bridge): the 8-bar rhythms the library uses, on a four-chord loop (I V vi IV, ABCD)
or, for the three-chord shapes (runners, mountains), on I IV V.

    template_8.py            # writes ~/Desktop/music/template_8.json
    template_8.py --upload   # also creates it in Hookpad (private), as a Hookpad 3 song
    template_8.py --upload --id <ID>        # overwrite an existing one (either Hookpad)
    template_8.py --upload --hp2            # create it in the Hookpad 2 format instead

The Hookpad 3 song borrows its instruments and mixer from
hookpad_upload_variants.HP3_BASE. The Hookpad 2 original is 101367296;
the Hookpad 3 one (2026-11-20) is 101374908.

Each section is 8 bars of 4/4. Its rhythm is written in the 16-slot notation:
chord onsets in eighths across a 2-bar window, odd slot = pushed. The chords
cycle A B C D through the onsets. The melody is one legato note per chord on its
root. Counts are from the library's 319 four-chord 8-bar sections (2026-11-12).
Built on mine_choruses.json, a whole saved project, so Hookpad opens it.
"""
import copy, json, os, sys

D = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
OUT = os.path.expanduser('~/Desktop/music/template_8.json')
NAME = 'template_8'
LOOP = [1, 5, 6, 4]                     # I V vi IV

RUN = [1, 4, 5]                         # I IV V, for the three-chord shapes
HALVER_AABA =[1, 5, 6, 4] * 2 + [2, 4] + [1, 5, 6, 4]   # B slows to one chord a bar

# (name, slot pattern per 2-bar window, cycled over the 4 windows)
SECTIONS = [
    ('ABCD [0,8] one per bar', [[0, 8]]),                       # 60: You Learn, Pompeii
    ('ABCD [0,7] push', [[0, 7]]),                              # 7: Dancing in the Dark, Viva la Vida
    ('ABCD [0,4,8,12] halver', [[0, 4, 8, 12]]),                # 44: I Saw the Sign
    ('ABCD [0,3,8,11] halver push', [[0, 3, 8, 11]]),           # 11: Warning Sign
    ('ABCD [0,3,7,11] halver all push', [[0, 3, 7, 11]]),      # Fire Escape verse: every change inside the window early
    ('ABCD [0,5,8,13] late', [[0, 5, 8, 13]]),                  # 5: Boom Clap, Drain You
    ('ABCD [0] slow', [[0]]),                                   # 9: Help!, As It Was
    ('ABCD [0][0,8,12] front runner', [[0], [0, 8, 12]]),       # 2: Wouldn't It Be Nice, Born to Run
    ('ABCD [0,4,8][0] back runner', [[0, 4, 8], [0]]),          # the mirror; none in the library exactly
    # runners are three chords over four slots: I IV V repeats in every window
    ('front runner x4 I | IV V [0,8,12]', [[0, 8, 12]], RUN * 4),      # AABC: 1-.5-.5 every 2 bars
    ('back runner x4 I IV | V [0,4,8]', [[0, 4, 8]], RUN * 4),         # ABCC: .5-.5-1 every 2 bars
    ('front runner bar scale I I | IV V [0][0,8]', [[0], [0, 8]], RUN * 2),  # 12: AABC at 2-1-1 bars
    ('back runner bar scale I IV | V V [0,8][0]', [[0, 8], [0]], RUN * 2),   # 29: ABCC at 1-1-2 bars
    ('mountain held I IV V I | I IV V I [0,8][0,8][8][0,8]', [[0, 8], [0, 8], [8], [0, 8]], RUN + [1] + RUN[1:] + [1]),  # 15: ABCA x2, the A's join across bars 4-5
    ('halver mountain [0,4,8,12][4,8,12]x3', [[0, 4, 8, 12]] + [[4, 8, 12]] * 3, RUN + [1] + (RUN[1:] + [1]) * 3),  # 6: ABCA at two a bar, the A's join
    ('slow three I x4 | IV | V x3 [0][0][0,8][0]', [[0], [0], [0, 8], [0]], [1, 1, 4, 5, 5]),  # 9
    ('long hold I x6 | IV | V [0][0][0][0,8]', [[0], [0], [0], [0, 8]], [1, 1, 1, 4, 5]),      # 7: the ender at 8-bar scale
    # endings: the last window changes shape (the ender)
    ('ABCD [0,8]x3 [0] ender hold', [[0, 8]] * 3 + [[0]]),      # How You Remind Me, American Girl
    ('ABABABCC I IV x3 | V V', [[0, 8]] * 3 + [[0]], [1, 4, 1, 4, 1, 4, 5]),  # 8: Maggie May, Message in a Bottle choruses
    ('ABCD [0,4,8,12]x3 [0,4,8] ender', [[0, 4, 8, 12]] * 3 + [[0, 4, 8]]),  # If I Die Young, Cherub Rock
    ('ABCD [0,8]x3 [0,8,12] turnaround', [[0, 8]] * 3 + [[0, 8, 12]], {8: 5}),  # bar 8 splits IV V, leads home
    ('ABCD [0,12] 3-1', [[0, 12]]),                             # Real World, Yellow Submarine
    ('vamp home push IV ii | IV ii I [0,8][0,8,11]', [[0, 8], [0, 8, 11]], [4, 2, 4, 2, 1] * 2),  # Birthday: I sneaks in early
    ('front runner push x4 I | IV V [0,7,11]', [[0, 7, 11]], RUN * 4),
    ('back runner push x4 I IV | V [0,3,7]', [[0, 3, 7]], RUN * 4),
    # AABA: four 2-bar phrases, the third swapped. A list = the roots spelled out.
    ('AABA [0,8] I V, B ii IV', [[0, 8]], [1, 5, 1, 5, 2, 4, 1, 5]),
    ('AABA [0,7] I V, B ii IV', [[0, 7]], [1, 5, 1, 5, 2, 4, 1, 5]),            # Nineteen verse
    ('AABA [0,4,8,12] halver, B ii IV', [[0, 4, 8, 12]] * 2 + [[0, 8], [0, 4, 8, 12]], HALVER_AABA),
    ('AABA [0,3,8,11] halver push, B ii IV', [[0, 3, 8, 11]] * 2 + [[0, 8], [0, 3, 8, 11]], HALVER_AABA),
    ('AABA [0,3,7,11] halver all push, B ii IV', [[0, 3, 7, 11]] * 2 + [[0, 8], [0, 3, 7, 11]], HALVER_AABA),  # Fire Escape verse (B = I IV there)
    ('AABA [0,5,8,13] late, B ii IV', [[0, 5, 8, 13]] * 2 + [[0, 8], [0, 5, 8, 13]], HALVER_AABA),
]


def section_chords(windows, fix):
    """[(onset slot, duration in beats, root)] for one 8-bar section; a repeated root is held"""
    on = [w * 16 + s for w in range(4) for s in windows[w % len(windows)]]
    roots = [fix.get(i, LOOP[i % 4]) for i in range(len(on))]
    keep = [i for i in range(len(on)) if i == 0 or roots[i] != roots[i - 1]]
    return [(on[i], ((on[keep[j + 1]] if j + 1 < len(keep) else 64) - on[i]) / 2, roots[i])
            for j, i in enumerate(keep)]


def build():
    from tempo_variant_pastes import full_json
    base = json.load(open(f'{D}/mine_choruses.json'))
    o = full_json(base, 1)
    tmpl_c, tmpl_n = base['chords'][0], base['notes'][0]
    chords, notes, secs, beat = [], [], [], 1
    for name, windows, *fix in SECTIONS:
        fix = fix[0] if fix else {}
        if isinstance(fix, list): fix = dict(enumerate(fix))
        secs.append({'beat': beat, 'name': name})
        for x, du, root in section_chords(windows, fix):
            st = beat + x / 2
            c = copy.deepcopy(tmpl_c); c.update(root=root, beat=st, duration=du)
            n = copy.deepcopy(tmpl_n); n.update(sd=str(root), beat=st, duration=du)
            chords.append(c); notes.append(n)
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
    print(f'{len(o["sections"])} sections, {len(o["chords"])} chords -> {OUT}')
    if '--upload' in sys.argv:
        import hookpad_token
        from hookpad_upload_variants import upload
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        if '--id' in sys.argv:          # overwrite the existing song in place
            from hookpad_upload_variants import call, json_data, API
            sid = sys.argv[sys.argv.index('--id') + 1]
            r = call('PATCH', f'{API}/songs/{sid}', tok, json={'jsonData': json_data(o), 'song': NAME})
            print('PATCH', r.status_code, r.text[:200])
        else:
            r, err = upload(tok, NAME, o, hp3_base=None if '--hp2' in sys.argv else True)
            print(err or r)
