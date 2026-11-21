"""Tempo of every downloaded recording, measured from the audio.

    measure_tempo.py            # measure anything new in audio_work/youtube + billboard, then exit
    measure_tempo.py --follow   # keep going while the downloads run (checks every 10 min)

Results go to ~/Desktop/music/audio_work/tempo.json, keyed by file path.

Method: librosa beat tracking on the percussive part, started from several
tempos (songbpm's figure, if the manifest has one, at half/normal/double, plus
80/100/120/160), a straight line fitted through every beat time, and the
steadiest fit kept (lowest drift). One-number tempo estimates step coarsely
and fall into the triplet trap (2/3 or 3/2 of the true tempo); the fit
through ~500 beats does not. `alts` keeps the runner-up readings, so a song
whose best two fits are 3:2 apart can be flagged rather than trusted.
"""
import argparse, glob, json, os, sys, time, warnings
import numpy as np
warnings.filterwarnings('ignore')
import librosa

A = os.path.expanduser('~/Desktop/music/audio_work')
OUT = f'{A}/tempo.json'
MANIFESTS = [f'{A}/youtube/{f}' for f in ('pilot_manifest.json', 'batch1_manifest.json', 'library_manifest.json', 'fixes_manifest.json')] + [f'{A}/billboard/manifest.json']


def hints():
    h = {}
    for f in MANIFESTS:
        if os.path.exists(f):
            for r in json.load(open(f)):
                if r.get('file') and r.get('songbpm_bpm'): h[r['file']] = r['songbpm_bpm']
    return h


def measure(path, hint=None):
    y, sr = librosa.load(path, sr=22050, mono=True)
    _, p = librosa.effects.hpss(y)
    starts = {80, 100, 120, 160} | ({round(hint * m) for m in (.5, 1, 2) if 55 <= hint * m <= 210} if hint else set())
    fits = []
    for sb in sorted(starts):
        _, beats = librosa.beat.beat_track(y=p, sr=sr, hop_length=256, units='time', start_bpm=sb, tightness=400)
        if len(beats) < 20: continue
        k = np.arange(len(beats)); fit = np.polyfit(k, beats, 1)
        fits.append((round(float((beats - np.polyval(fit, k)).std()) * 1000), round(60 / fit[0], 1)))
    if not fits: return None
    fits = sorted(set(fits))
    best = fits[0]
    alts = [f for f in fits[1:] if min(abs(f[1] / best[1] - r) for r in (.5, 1, 2)) > .03][:2]   # readings that are not just half/double
    return dict(bpm=best[1], drift_ms=best[0], alts=alts, secs=round(len(y) / sr), hint=hint)


def run_once(res):
    h = hints()
    files = sorted(glob.glob(f'{A}/youtube/*.m4a') + glob.glob(f'{A}/youtube/*.webm') + glob.glob(f'{A}/billboard/*.m4a') + glob.glob(f'{A}/billboard/*.webm'))
    todo = [f for f in files if f not in res and not any(s in os.path.basename(f) for s in ('-live.', '-videoedit.', '-strings-video.'))]
    for i, f in enumerate(todo, 1):
        try:
            res[f] = measure(f, h.get(f))
        except Exception as e:
            res[f] = dict(error=str(e)[:200])
        if i % 10 == 0 or i == len(todo):
            json.dump(res, open(OUT, 'w'), indent=0)
            print(f'{len(res)} measured ({i}/{len(todo)} this pass)', flush=True)
    return len(todo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--follow', action='store_true')
    a = ap.parse_args()
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    while True:
        n = run_once(res)
        downloading = os.popen("pgrep -f 'youtube_audio.py'").read().strip()
        if not a.follow or (n == 0 and not downloading): break
        time.sleep(600)


if __name__ == '__main__':
    main()
