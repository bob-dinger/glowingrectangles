"""Mix / mute demucs stems. A stem is one .wav per instrument; muting = leave it out of the sum.

  # everything except drums (drums muted):
  .venv_audio/bin/python stem_mix.py "<stems dir>" --mute drums

  # only bass + guitar (a "low end" mix):
  .venv_audio/bin/python stem_mix.py "<stems dir>" --keep bass guitar

  # scale a stem instead of full mute (drums at 30%):
  .venv_audio/bin/python stem_mix.py "<stems dir>" --gain drums=0.3
"""
import os, sys, glob, argparse
import numpy as np
import soundfile as sf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stemdir', help='folder of <name>.wav stems')
    ap.add_argument('--keep', nargs='*', help='only these stems (default: all)')
    ap.add_argument('--mute', nargs='*', default=[], help='drop these stems')
    ap.add_argument('--gain', nargs='*', default=[], help='per-stem gain, e.g. drums=0.3')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(a.stemdir, '*.wav')))
    stems = {os.path.splitext(os.path.basename(p))[0]: p for p in paths}
    gains = dict(g.split('=') for g in a.gain)

    which = a.keep if a.keep else [s for s in stems if s not in a.mute]
    mix, sr, n = None, None, None
    used = []
    for name in which:
        if name not in stems: print(f'  (no stem {name})'); continue
        audio, sr = sf.read(stems[name], always_2d=True)   # (frames, channels)
        g = float(gains.get(name, 1.0))
        audio = audio * g
        if mix is None:
            mix = np.zeros_like(audio); n = len(audio)
        m = min(len(mix), len(audio))
        mix[:m] += audio[:m]
        used.append(f'{name}{"" if g==1 else f"×{g}"}')

    if mix is None: print('nothing to mix'); return
    peak = np.max(np.abs(mix))
    if peak > 1.0: mix = mix / peak                        # guard clipping
    out = a.out or os.path.join(a.stemdir, '_mix_' + '+'.join(w.split('×')[0] for w in used) + '.wav')
    sf.write(out, mix, sr)
    print(f'wrote {out}\n  stems: {", ".join(used)}  ({sr} Hz)')

if __name__ == '__main__':
    main()
