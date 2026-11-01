#!/usr/bin/env python3
"""
Check hand transcriptions against the record: for every song in the Music
library that also has a Hookpad melody, hear what is actually sung and say
how well the Hookpad melody matches it.

    .venv_audio/bin/python check_transcriptions.py [--days 2] [--only "viva la vida"]

Uses audio_to_hookpad's pipeline (demucs vocal -> basic-pitch -> one line on
the band's beat grid). Per song it reports:

  shift    the transposition that best lines the Hookpad melody's notes up with
           the sung notes (by how long each pitch class is held). 0 = right;
           Nashville Blues came out +5 (a 4th: entered as if in D, sung in G).
  tempo    the record's bpm against the file's (x2 / x0.5 = doubled or halved)
  match    share of Hookpad notes with a sung note of the same pitch class
           within half a beat, at the best time offset (searched, since the
           file's bar 1 need not be the record's first beat). Nashville Blues
           -fixed scored 72%.

Results: ~/Desktop/music/audio_work/_checks/results.json (one entry per song,
written as it goes, so a stopped run resumes where it left off).
"""
import argparse, glob, json, os, re, sys, time, traceback
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_to_hookpad as A

LIB = os.path.expanduser('~/Music/Music/Media.localized/Music')
HP = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
OUT = os.path.expanduser('~/Desktop/music/audio_work/_checks')
SUFFIX = re.compile(r'-[^ ]*$')
MODE_SCALE = {'major': 'major', 'minor': 'minor', 'aeolian': 'minor', 'dorian': 'dorian', 'mixolydian': 'mixolydian',
              'lydian': 'lydian', 'phrygian': 'phrygian', 'locrian': 'locrian'}


def norm(s):
    return re.sub(r'\(.*?\)|feat\..*|[^a-z0-9 ]', '', s.lower().replace('&', 'and')).strip()


def library(days):
    out = []
    for dp, _, fs in os.walk(LIB):
        for f in fs:
            p = os.path.join(dp, f)
            if f.lower().endswith(('.m4a', '.mp3')) and time.time() - os.path.getmtime(p) < days * 86400:
                out.append((p, re.sub(r'^[\d-]+\s+|\.m4a$|\.mp3$', '', f, flags=re.I)))
    return out


def hookpad_files():
    """normalised title -> the copy with the most melody"""
    best = {}
    for f in glob.glob(os.path.join(HP, '*.json')):
        b = os.path.basename(f)[:-5]
        try:
            d = json.load(open(f))
        except Exception:
            continue
        n = len([x for x in d.get('notes') or [] if not x.get('isRest')])
        if not n:
            continue
        k = norm(SUFFIX.sub('', b.split('_', 1)[-1]))
        plain = SUFFIX.sub('', b) == b
        if k not in best or (plain, n) > best[k][0]:
            best[k] = ((plain, n), f)
    return {k: v[1] for k, v in best.items()}


def note_pc(n, keys):
    k = max((k for k in keys if k['beat'] <= n['beat']), key=lambda k: k['beat'], default=keys[0])
    sd = str(n['sd'])
    acc = sd.count('#') - sd.count('b')
    deg = int(sd.strip('#b'))
    mode = k.get('scale', 'major')
    sc = A.scale(MODE_SCALE.get(mode, 'major'))
    pc = A.PCS[k['tonic']] + sc[deg - 1] + acc
    if mode == 'harmonicMinor' and deg == 7: pc += 1
    if mode == 'phrygianDominant' and deg == 3: pc += 1
    return pc % 12


def check(audio, hp_file, work):
    d = json.load(open(hp_file))
    keys = d.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    hn = [(n['beat'], n['duration'], note_pc(n, keys)) for n in d['notes'] if not n.get('isRest') and n.get('sd')]
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, 'mix.wav')
    if not os.path.exists(wav):
        A.subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', audio, '-ar', '44100', wav], check=True)
    vocals, band = A.separate(wav, work)
    line = A.one_line(A.vocal_notes(vocals, work), vocals)
    beats, bpm, y, sr = A.beat_grid(band, None)
    # sung notes in record beats, half-beat grid
    sung = [(round(A.to_beat(s, beats) * 2) / 2, p % 12, e - s) for s, e, p, a in line]
    file_bpm = float((d.get('tempos') or [{}])[0].get('bpm') or 0)
    # 1. key: pitch-class time profiles, best rotation
    hp_prof, sung_prof = np.zeros(12), np.zeros(12)
    for b, du, pc in hn: hp_prof[pc] += du
    for b, pc, du in sung: sung_prof[pc] += du
    corr = [float(np.corrcoef(np.roll(hp_prof, s), sung_prof)[0, 1]) for s in range(12)]
    shift = int(np.argmax(corr))
    # 2. tempo factor: the file's beats against the record's
    ratio = bpm / file_bpm if file_bpm else 1
    factor = min((0.5, 1, 2), key=lambda f: abs(np.log(ratio / f)))
    # 3. match at the best offset (file beat * factor + offset = record beat)
    by_pc = {}
    for b, pc, _ in sung: by_pc.setdefault(pc, []).append(b)
    by_pc = {k: np.array(v) for k, v in by_pc.items()}
    def score(off, sh):
        hit = 0
        for b, du, pc in hn:
            t = (b - 1) * factor + 1 + off
            arr = by_pc.get((pc + sh) % 12)
            if arr is not None and np.min(np.abs(arr - t)) <= 0.5: hit += 1
        return hit / len(hn)
    span = int(max(b for b, *_ in sung) + 32)
    offs = np.arange(-64, span, 0.5)
    coarse = [(score(o, shift), o) for o in offs[::2]]
    o0 = max(coarse)[1]
    m_shift, off = max((score(o, shift), o) for o in np.arange(o0 - 2, o0 + 2.5, 0.5))
    as_is = max(score(o, 0) for o in np.arange(off - 2, off + 2.5, 0.5)) if shift else m_shift
    return dict(hookpad=os.path.basename(hp_file)[:-5], key=f"{keys[0]['tonic']} {keys[0].get('scale')}",
                notes=len(hn), file_bpm=file_bpm, record_bpm=round(bpm, 1), tempo_factor=factor,
                shift=shift, shift_corr=round(corr[shift], 2), corr_as_is=round(corr[0], 2),
                match_as_is=round(as_is, 2), match_shifted=round(m_shift, 2), offset=float(off))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=float, default=2)
    ap.add_argument('--only')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    res_path = os.path.join(OUT, 'results.json')
    res = json.load(open(res_path)) if os.path.exists(res_path) else {}
    hp = hookpad_files()
    todo = [(p, t, hp[norm(t)]) for p, t in sorted(library(a.days), key=lambda x: x[1].lower())
            if norm(t) in hp and (not a.only or a.only.lower() in t.lower())]
    print(f'{len(todo)} songs to check', flush=True)
    for i, (p, t, f) in enumerate(todo, 1):
        if t in res and 'error' not in res[t]:
            continue
        t0 = time.time()
        try:
            r = check(p, f, os.path.join(os.path.expanduser('~/Desktop/music/audio_work'), norm(t)))
        except Exception as e:
            r = dict(error=f'{type(e).__name__}: {e}', trace=traceback.format_exc()[-600:])
        r['audio'] = os.path.relpath(p, LIB)
        res[t] = r
        json.dump(res, open(res_path, 'w'), indent=1)
        msg = r.get('error') or f"shift {r['shift']} match {r['match_as_is']:.0%}"
        print(f'[{i}/{len(todo)}] {t}: {msg} ({time.time() - t0:.0f}s)', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
