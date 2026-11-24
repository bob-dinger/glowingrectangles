"""The daily mix: 5-10 song sections at one tempo, each heard as written and mixed up.

    daily.py                     # today's file, 8 songs, a random tempo -> ~/Desktop/music/<M-D-YY>.json
    daily.py --tempo 90 --n 6    # pick the tempo / how many songs
    daily.py --seed 4            # same seed = same picks
    daily.py --upload            # onto the second Hookpad account, named M-D-YY (M-D-YY-2 if taken)

The user's plan (2026-11-24): "mix up 5-10 songs each day", one Hookpad file per
day labelled by the date (11-23-26), on the second account. The tempo comes first
and every section plays at it, whatever the song's own tempo.

Songs are random library sections (8 bars of 4/4, major, a real melody, not an
intro/outro/solo; one per song). Each song gets four sections in a row:
  <song> / as written        its chords and melody at the day's tempo
  <song> / loop X            its chord rhythm under another common loop, its melody's same notes
  <song> / strum X           its own chords re-struck with a strum_library pattern
  <song> melody / <next> chords
                             its melody moved onto the next song's chords and chord rhythm
                             (each note keeps its place against the chord under it)
"""
import argparse, copy, json, os, random, time
import strum, template_8 as T
from template_8_full import library, move
from rhythm_combos import LOOPS, RN
from remix import source, restrum, plain
from same_progressions import same


def build(a):
    from tempo_variant_pastes import full_json
    rnd = random.Random(a.seed)
    lib, picks, seen = library(), [], set()
    for s in rnd.sample(lib, len(lib)):
        if same(s['song']) in seen: continue
        seen.add(same(s['song']))
        src = source(s['song'], s['sec'])
        if src['length'] == 32 and src['nb'] == 4 and src['merged'] and src['merged'][0][1] == 0 and len(src['notes']) >= 8:
            picks.append((s, src))
        if len(picks) == a.n: break
    tempo = a.tempo or rnd.choice(range(70, 155, 5))
    pats = strum.load_lib()
    plan = []
    for i, (s, src) in enumerate(picks):
        title = same(s['song']).split('_', 1)[-1].title() + ' ' + s['sec']
        m = src['merged']
        plan.append((f'{title} / as written', src['raw'], src['notes']))
        roots = tuple(c.get('root') for c, _, _ in m[:4])
        loop = rnd.choice([l for l in LOOPS if l != roots])
        plan.append((f"{title} / loop {' '.join(RN[r] for r in loop)}",
                     [plain(loop[j % 4], b, (m[j + 1][1] if j + 1 < len(m) else 32) - b, m[0][0])
                      for j, (_, b, _) in enumerate(m)], src['notes']))
        pname = rnd.choice(sorted(pats))
        plan.append((f'{title} / strum {pname}', restrum(m, 32, pats[pname], 4), src['notes']))
        ns, nsrc = picks[(i + 1) % len(picks)]
        nm = nsrc['merged']
        mel = move(src['notes'], [(c.get('root'), b) for c, b, _ in m], [(c.get('root'), b) for c, b, _ in nm])
        plan.append((f"{title} melody / {same(ns['song']).split('_', 1)[-1].title()} chords", nsrc['raw'], mel))
    base = json.load(open(f'{T.D}/mine_choruses.json'))
    o = full_json(base, 1)
    chords, notes, secs, beat = [], [], [], 1
    for label, ch, ns in plan:
        secs.append({'beat': beat, 'name': label})
        chords += [dict(copy.deepcopy(c), beat=beat + c['beat'], duration=min(c['duration'], 32 - c['beat'])) for c in ch]
        notes += [dict(copy.deepcopy(n), beat=beat + n['beat'], duration=min(n['duration'], 32 - n['beat'])) for n in ns]
        beat += 32
    o.update(chords=chords, notes=notes, sections=secs, endBeat=beat,
             tempos=[{'beat': 1, 'bpm': tempo, 'swingFactor': 0, 'swingBeat': 0.5}],
             breaks=[{'beat': x['beat']} for x in secs[1:]],
             keys=[{'beat': 1, 'scale': 'major', 'tonic': 'C'}],
             meters=[{'beat': 1, 'numBeats': 4, 'beatUnit': 1}])
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': x['name'], 'lyrics': ['', '', '', '']} for x in secs]
    return o, tempo


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tempo', type=int)
    ap.add_argument('--n', type=int, default=8)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--name')
    ap.add_argument('--upload', action='store_true')
    a = ap.parse_args()
    if a.seed is None:
        a.seed = random.randrange(1000)
    t = time.localtime()
    name = a.name or f'{t.tm_mon}-{t.tm_mday}-{t.tm_year % 100}'
    o, tempo = build(a)
    print('\n'.join(x['name'] for x in o['sections']))
    if a.upload:
        from hookpad_upload_variants import upload, call, API
        tok = open(os.path.expanduser('~/.hookpad_token_alt')).read().strip()
        have = {x['song'].lower() for x in call('GET', f'{API}/songs/h?per-page=100&page=1', tok).json()}
        base, k = name, 2
        while name.lower() in have:
            name, k = f'{base}-{k}', k + 1
    out = os.path.expanduser(f'~/Desktop/music/{name}.json')
    json.dump(o, open(out, 'w'), indent=1)
    print(f'seed {a.seed}, {tempo} bpm: {len(o["sections"])} sections -> {out}')
    if a.upload:
        r, err = upload(tok, name, o, hp3_base=True)
        print(err or r)
