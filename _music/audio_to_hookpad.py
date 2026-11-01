#!/usr/bin/env python3
"""
A recording -> a Hookpad song with the sung melody (and rough chords).

    .venv_audio/bin/python audio_to_hookpad.py <audio> --name "artist_title-auto" \
        [--key G] [--mode major] [--base <hookpad json>] [--upload]

Built 2026-11-01 on Cory Morrow's Nashville Blues, where it got 72% of a
hand-checked verse right to the half beat (82% within a beat). A draft to
clean up by ear, not a finished transcription.

1. demucs splits the vocal from the band (cached, it is the slow step).
2. basic-pitch turns the vocal into notes; only notes where the vocal is loud
   and in a singing range are kept, and where two overlap the stronger wins,
   so it is one line.
3. The band's beats (librosa) set the grid: beat 1 = the first beat it hears,
   every note snapped to the half beat. --first-beat SECONDS moves bar 1.
4. Notes become scale degrees in the key (--key, else guessed from the band).
   A chromatic note between two scale notes is almost always a slide, so it
   becomes whichever neighbour the line is on next to it.
5. Chords (audio_chords.py): with --base, that song's chords, sections and
   lyrics are kept and only the melody is replaced. Without one, the chords
   come from the song's UG chart when ~/Desktop/music/ug_tabs has it (its chord
   list, after the capo, moved to the record's key if the chart is in another,
   with their extensions: Am7, Cadd9), else the key's six triads; each half bar
   of the band is scored against them (chroma + bass note) and smoothed so a
   chord holds unless the band moves. About 3 in 4 beats right.

Work files go to ~/Desktop/music/audio_work/<name>/ (outside the repo: the
audio is someone else's recording). The song JSON is written there too;
--upload creates it as a private Hookpad song (via the main venv, which has the
upload helpers).
"""
import argparse, copy, json, math, os, re, subprocess, sys
import numpy as np, librosa

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = '/Users/robert/Desktop/themap/themap_claude/.venv/bin/python'
SKELETON = os.path.expanduser('~/Desktop/music/hookpad_songs_full/cory morrow_nashville blues.json')
NAMES = 'C C# D Eb E F F# G Ab A Bb B'.split()
PCS = {n: i for i, n in enumerate(NAMES)} | {'Db': 1, 'D#': 3, 'Gb': 6, 'G#': 8, 'A#': 10}
MODES = {'major': 0, 'dorian': 1, 'phrygian': 2, 'lydian': 3, 'mixolydian': 4, 'minor': 5, 'aeolian': 5, 'locrian': 6}
MAJ = [0, 2, 4, 5, 7, 9, 11]


def scale(mode):
    r = MODES[mode]
    return [(MAJ[(r + i) % 7] - MAJ[r]) % 12 for i in range(7)]


def separate(wav, work):
    out = os.path.join(work, 'htdemucs', 'mix')
    if not os.path.exists(os.path.join(out, 'vocals.wav')):
        subprocess.run([os.path.join(os.path.dirname(sys.executable), 'demucs'), '--two-stems=vocals',
                        '-o', work, wav], check=True)
    return os.path.join(out, 'vocals.wav'), os.path.join(out, 'no_vocals.wav')


def vocal_notes(vocals, work):
    cache = os.path.join(work, 'basic_pitch.json')
    if not os.path.exists(cache):
        from basic_pitch.inference import predict
        from basic_pitch import ICASSP_2022_MODEL_PATH
        _, midi, notes = predict(vocals, ICASSP_2022_MODEL_PATH, onset_threshold=0.5, frame_threshold=0.3,
                                 minimum_note_length=80, minimum_frequency=80, maximum_frequency=700,
                                 melodia_trick=True)
        midi.write(os.path.join(work, 'vocals.mid'))
        json.dump(sorted((float(s), float(e), int(p), float(a)) for s, e, p, a, *_ in notes), open(cache, 'w'))
    return json.load(open(cache))


def one_line(ev, vocals):
    v, sr = librosa.load(vocals, sr=22050)
    rms = librosa.feature.rms(y=v)[0]
    rt = librosa.times_like(rms, sr=sr)
    gate = np.percentile(rms, 60) * 0.6

    def loud(s, e):
        m = (rt >= s) & (rt < e)
        return m.any() and rms[m].mean() > gate
    ev = [x for x in ev if loud(x[0], x[1]) and 40 <= x[2] <= 72]
    line = []
    for s, e, p, a in sorted(ev, key=lambda x: -x[3]):
        if all(e <= s2 + 0.03 or s >= e2 - 0.03 for s2, e2, *_ in line):
            line.append([s, e, p, a])
    return sorted(line)


def beat_grid(band, first_beat):
    y, sr = librosa.load(band, sr=22050)
    _, perc = librosa.effects.hpss(y)
    tempo, beats = librosa.beat.beat_track(y=perc, sr=sr, units='time')
    if first_beat is not None:
        beats = beats[beats >= first_beat - 0.05]
    return beats, 60 / float(np.median(np.diff(beats))), y, sr


def to_beat(t, beats):
    step = beats[1] - beats[0]
    if t < beats[0]:
        return 1 + (t - beats[0]) / step
    if t > beats[-1]:
        return len(beats) + (t - beats[-1]) / (beats[-1] - beats[-2])
    return 1 + float(np.interp(t, beats, np.arange(len(beats))))


def guess_key(y, sr):
    """Krumhansl profiles against the band's chroma -> (tonic, 'major'|'minor')"""
    c = librosa.feature.chroma_cqt(y=y, sr=sr).sum(1)
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    best = max(((np.corrcoef(c, np.roll(p, t))[0, 1], t, m) for t in range(12)
                for p, m in ((maj, 'major'), (mnr, 'minor'))))
    return NAMES[best[1]], best[2]


def melody(line, beats, tonic, mode, proto):
    sc = scale(mode)
    t0 = PCS[tonic]
    low = 55 + ((t0 - 7) % 12) - (12 if (t0 - 7) % 12 > 6 else 0)   # sd 1 octave 0 = the tonic nearest G3
    # snap to the half beat, one line
    out = []
    for s, e, p, a in line:
        b0, b1 = round(to_beat(s, beats) * 2) / 2, round(to_beat(e, beats) * 2) / 2
        b1 = max(b1, b0 + 0.5)
        if out and b0 < out[-1][0] + out[-1][1]:
            if b0 <= out[-1][0]:
                continue
            out[-1][1] = b0 - out[-1][0]
        out.append([b0, b1 - b0, p])
    # chromatic -> the neighbouring scale note the line is on either side
    inkey = lambda p: (p - t0) % 12 in sc
    for i, n in enumerate(out):
        if not inkey(n[2]):
            nb = {x[2] for x in out[max(0, i - 1):i + 2] if x is not n}
            up, dn = n[2] + 1, n[2] - 1
            n[2] = up if (up in nb or not inkey(dn)) and inkey(up) else dn
    notes = []
    for b, du, p in out:
        if notes and notes[-1]['beat'] + notes[-1]['duration'] == b and notes[-1]['_p'] == p \
                and du < 0.5 and notes[-1]['duration'] < 0.5:
            notes[-1]['duration'] += du
            continue
        x = copy.deepcopy(proto)
        x.update(sd=str(sc.index((p - t0) % 12) + 1), octave=(p - low) // 12, beat=b, duration=du,
                 isRest=False, recordingEndBeat=None, _p=p)
        notes.append(x)
    for n in notes:
        n.pop('_p')
    return notes


def chords(y, sr, beats, tonic, mode, proto, end):
    sc = scale(mode)
    t0 = PCS[tonic]
    ch = librosa.feature.chroma_cqt(y=librosa.effects.hpss(y)[0], sr=sr)
    ct = librosa.times_like(ch, sr=sr)
    tri = {r: {(t0 + sc[(r - 1 + k) % 7]) % 12 for k in (0, 2, 4)} for r in range(1, 8)}
    out = []
    for i in range(0, len(beats) - 2, 2):
        m = (ct >= beats[i]) & (ct < beats[i + 2])
        if not m.any():
            continue
        v = ch[:, m].mean(1)
        r = max(range(1, 7), key=lambda r: sum(v[p] for p in tri[r]))    # skip the diminished 7
        b = 1 + i
        if out and out[-1]['root'] == r:
            out[-1]['duration'] += 2
            continue
        c = copy.deepcopy(proto)
        c.update(root=r, beat=b, duration=2, type=5, inversion=0, applied=0, adds=[], borrowed='',
                 suspensions=[], isRest=False, recordingEndBeat=None)
        out.append(c)
    return [c for c in out if c['beat'] < end]


def song_chords(a, band, beats, tonic, mode, proto, end):
    """The UG chart's chords (moved to the record's key if the chart is in
    another), else the key's six triads; a chord per half bar, smoothed.
    Settings from a 9-song test against hand Hookpad chords (2026-11-01):
    74% of beats right against 73% for one-triad-per-half-bar."""
    import audio_chords as AC
    ug = None
    if not a.no_ug:
        ug = a.ug or AC.find_ug(*(re.sub(r'-[^ ]*$', '', a.name).split('_', 1) + [''])[:2])
    if ug:
        capo, counts, _ = AC.ug_chart(ug)
        cand = AC.sounding(AC.candidates(counts), capo)
        s, _ = AC.chart_key(band, beats, list(cand), treble='mid')
        cand = {AC.transpose(c, s): n for c, n in cand.items()}
        path = AC.best_path(band, beats, list(cand), change=0.1, bass_w=0.3, unit=2, prior=cand, treble='mid')
        how = (f'chords from UG {os.path.basename(ug)}: {" ".join(cand)}'
               + (f' (chart moved {s} semitones to the record)' if s else ''))
    else:
        path = AC.best_path(band, beats, AC.diatonic(tonic, mode), change=0.05, bass_w=0.15, unit=2, treble='mid')
        how = f'chords: the six triads of {tonic} {mode} (no UG chart)'
    out = [AC.to_hookpad(n, tonic, mode, proto, b, du) for n, b, du in path if b < end]
    return out, how


def project(base_path, keep_chords):
    d = json.load(open(base_path))
    d = d.get('jsonData', d)
    d = json.loads(d) if isinstance(d, str) else d
    o = copy.deepcopy(d)
    o.pop('fp', None)
    o['cursor'] = {'beat': 1, 'location': (o.get('cursor') or {}).get('location', 'cursor-note-staff')}
    o['audioTracks'], o['externalAudioFiles'] = [], []
    o['inactiveNotes'] = []
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['isOpen'] = o['lyrics']['isFocused'] = False
    if not keep_chords:
        o['sections'] = [{'beat': 1, 'name': 'verse'}]
        o['breaks'] = []
        if isinstance(o.get('lyrics'), dict):
            o['lyrics']['values'] = ['', '', '', '']
            o['lyrics']['sectionLyrics'] = [{'lyrics': ['', '', '', ''], 'sectionName': 'verse'}]
    return o, d


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('audio')
    ap.add_argument('--name', required=True, help='Hookpad song name, e.g. "cory morrow_nashville blues-auto"')
    ap.add_argument('--key', help='tonic, e.g. G or Bb (default: guessed from the band)')
    ap.add_argument('--mode', default=None, help='major, minor, mixolydian ... (default: guessed, major/minor)')
    ap.add_argument('--base', help='Hookpad JSON whose chords/sections/lyrics to keep (only the melody is replaced)')
    ap.add_argument('--first-beat', type=float, help='seconds where bar 1 starts (default: first beat heard)')
    ap.add_argument('--ug', help='UG page to take the chord list from (default: found from --name)')
    ap.add_argument('--no-ug', action='store_true', help='ignore UG: choose among the key\'s six triads')
    ap.add_argument('--upload', action='store_true', help='create it as a private Hookpad song')
    a = ap.parse_args()

    work = os.path.expanduser(f'~/Desktop/music/audio_work/{a.name}')
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, 'mix.wav')
    if not os.path.exists(wav):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', a.audio, '-ar', '44100', wav], check=True)
    print('separating the vocal (demucs) ...')
    vocals, band = separate(wav, work)
    print('vocal -> notes (basic-pitch) ...')
    line = one_line(vocal_notes(vocals, work), vocals)
    beats, bpm, y, sr = beat_grid(band, a.first_beat)
    tonic, mode = a.key, a.mode
    if not tonic:
        tonic, guessed = guess_key(y, sr)
        mode = mode or guessed
    mode = mode or 'major'

    o, base = project(a.base or SKELETON, keep_chords=bool(a.base))
    proto_n = (base.get('notes') or [{'sd': '1', 'octave': 0, 'beat': 1, 'duration': 1, 'isRest': False,
                                      'recordingEndBeat': None}])[0]
    o['notes'] = melody(line, beats, tonic, mode, {k: v for k, v in proto_n.items()})
    end = max(n['beat'] + n['duration'] for n in o['notes'])
    o['endBeat'] = max(o['endBeat'] if a.base else 1, 1 + 4 * math.ceil((end - 1) / 4))
    if not a.base:
        o['chords'], how = song_chords(a, band, beats, tonic, mode, base['chords'][0], o['endBeat'])
        print(how)
    o['keys'] = [{'beat': 1, 'scale': mode, 'tonic': tonic}]
    o['tempos'] = [{**(o.get('tempos') or [{}])[0], 'beat': 1, 'bpm': round(bpm)}]
    out = os.path.join(work, 'song.json')
    json.dump(o, open(out, 'w'))
    print(f'{a.name}: {tonic} {mode}, {round(bpm)} bpm, {len(o["notes"])} notes, {len(o["chords"])} chords '
          f'-> {out}')

    if a.upload:
        code = ('import json,sys; sys.path.insert(0,%r); import hookpad_upload_variants as U, hookpad_token; '
                'r,e=U.upload(hookpad_token.read_saved(),%r,json.load(open(%r))); print(r or e)') % (HERE, a.name, out)
        subprocess.run([MAIN_PY, '-c', code], check=True)


if __name__ == '__main__':
    main()
