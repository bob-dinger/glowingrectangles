"""Mixer: tempo x progression x melody rhythm, thrown together to see what sounds interesting.

    mixer.py                       # 16 random combos -> ~/Desktop/music/template_mix-<MMDD>.json, prints them
    mixer.py --n 24 --seed 7       # another batch (same seed = same batch)
    mixer.py --tempo 92            # pin any part; the rest stay random
    mixer.py --loop "vi IV I V" --rhythm "halver push"   # rhythms: see --help
    mixer.py --melody "muse_starlight/Verse"
    mixer.py --same-notes          # melodies keep their own scale degrees instead of following the chords
    mixer.py --upload [--id N]     # create (or overwrite) it in Hookpad 3, private

Each section is one 8-bar combo of three independent picks:
  tempo        a bpm drawn from the library's songs (70-160)
  progression  one of rhythm_combos.LOOPS (the 12 commonest four-chord loops) cycled
               through one of the template_8 ABCD chord rhythms
  melody       the rhythm of a real library melody (8 bars, major, not an
               intro/outro/solo), its notes moved onto the new chords so each keeps
               its place against the chord under it (template_8_full.move)
The section name says all three, so a keeper can be rebuilt or pinned.
The user finishes the good ones by hand.
"""
import argparse, copy, json, os, random, time
import corpus, template_8 as T
from template_8_full import library, move
from rhythm_combos import LOOPS, RN
from same_progressions import same

RHYTHMS = {name.split('] ')[-1]: windows for name, windows, *fix in T.SECTIONS
           if name.startswith('ABCD') and not fix}
NUM = {v: k for k, v in RN.items()}


def chords_for(loop, windows):
    return [(r, x / 2, du) for x, du, r in T.section_chords(windows, {i: loop[i % 4] for i in range(64)})]


def build(a):
    from tempo_variant_pastes import full_json
    rnd = random.Random(a.seed)
    lib = library()
    bpms = [s['bpm'] for s in lib if 70 <= s['bpm'] <= 160]
    loop_pin = tuple(NUM[x] for x in a.loop.split()) if a.loop else None
    mel_pin = [s for s in lib if a.melody and f"{s['song']}/{s['sec']}".lower() == a.melody.lower()]
    if a.melody and not mel_pin:
        raise SystemExit(f'no 8-bar major section {a.melody!r}')
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    tmpl_c, tmpl_n = base['chords'][0], base['notes'][0]
    chords, notes, secs, tempos, used, beat = [], [], [], [], set(), 1
    for _ in range(a.n):
        bpm = a.tempo or rnd.choice(bpms)
        loop = loop_pin or rnd.choice(LOOPS)
        rname = a.rhythm or rnd.choice(sorted(RHYTHMS))
        src = mel_pin[0] if mel_pin else rnd.choice([s for s in lib if same(s['song']) not in used] or lib)
        used.add(same(src['song']))
        ch = chords_for(loop, RHYTHMS[rname])
        mel = src['notes'] if a.same_notes else move(src['notes'], src['chords'], [(r, b) for r, b, _ in ch])
        for r, b, du in ch:
            c = copy.deepcopy(tmpl_c); c.update(root=r, beat=beat + b, duration=du)
            chords.append(c)
        for n in mel:
            m = copy.deepcopy(tmpl_n)
            m.update(sd=str(n['sd']), octave=n.get('octave') or 0, beat=beat + n['beat'],
                     duration=min(n['duration'], 32 - n['beat']))
            notes.append(m)
        song = same(src['song']).split('_', 1)[-1].title()
        secs.append({'beat': beat, 'name': f"{bpm} / {' '.join(RN[r] for r in loop)} {rname} / {song} {src['sec']}"})
        tempos.append({'beat': beat, 'bpm': bpm, 'swingFactor': 0, 'swingBeat': 0.5})
        beat += 32
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat, tempos=tempos,
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
    ap.add_argument('--n', type=int, default=16)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--tempo', type=int)
    ap.add_argument('--loop', help='e.g. "vi IV I V"')
    ap.add_argument('--rhythm', choices=sorted(RHYTHMS))
    ap.add_argument('--melody', help='"<song file>/<section>"')
    ap.add_argument('--same-notes', action='store_true')
    ap.add_argument('--name', default='template_mix-' + time.strftime('%m%d'))
    ap.add_argument('--upload', action='store_true')
    ap.add_argument('--id')
    a = ap.parse_args()
    if a.seed is None:
        a.seed = random.randrange(1000)
    o = build(a)
    out = os.path.expanduser(f'~/Desktop/music/{a.name}.json')
    json.dump(o, open(out, 'w'), indent=1)
    print('\n'.join(s['name'] for s in o['sections']))
    print(f'seed {a.seed}: {len(o["sections"])} combos, {len(o["notes"])} notes -> {out}')
    if a.upload:
        from hookpad_upload_variants import upload, call, json_data, API
        tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
        if a.id:
            r = call('PATCH', f'{API}/songs/{a.id}', tok, json={'jsonData': json_data(o), 'song': a.name})
            print('PATCH', r.status_code, r.text[:120])
        else:
            r, err = upload(tok, a.name, o, hp3_base=True)
            print(err or r)
