"""YouTube link -> audio -> isolated stems (-> optional MIDI).

    .venv_audio/bin/python yt_to_stems.py "<youtube url>"
    .venv_audio/bin/python yt_to_stems.py "<url>" --model htdemucs_ft   # cleanest 4-stem
    .venv_audio/bin/python yt_to_stems.py "<url>" --midi                # also transcribe stems

Stems land in ~/Desktop/stems/<video title>/. Reads mp3/m4a/wav via ffmpeg.
"""
import sys, os, subprocess, argparse, glob

PY = sys.executable                      # the .venv_audio python running this
DEST = os.path.expanduser('~/Desktop/stems')


def run(cmd):
    print('  $', ' '.join(cmd[:6]), '...')
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--model', default='htdemucs_6s',
                    help='htdemucs_6s (guitar/piano) | htdemucs_ft (cleanest 4) | htdemucs')
    ap.add_argument('--two-stems', default=None, help='e.g. vocals (fast karaoke split)')
    ap.add_argument('--midi', action='store_true', help='also transcribe each stem to MIDI')
    ap.add_argument('-o', '--out', default=DEST)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # 1) download audio as wav, named by video title
    tmpl = os.path.join(a.out, '%(title)s.%(ext)s')
    run([PY, '-m', 'yt_dlp', '-x', '--audio-format', 'wav', '--audio-quality', '0',
         '--extractor-args', 'youtube:player_client=android',   # bypasses the JS/sign-in block
         '--no-playlist', '-o', tmpl, a.url])
    wavs = sorted(glob.glob(os.path.join(a.out, '*.wav')), key=os.path.getmtime)
    audio = wavs[-1]
    print(f'\naudio: {audio}')

    # 2) separate
    cmd = [PY, '-m', 'demucs', '-n', a.model, '-o', a.out, audio]
    if a.two_stems:
        cmd[4:4] = ['--two-stems', a.two_stems]
    run(cmd)
    stem_dir = os.path.join(a.out, a.model, os.path.splitext(os.path.basename(audio))[0])
    print(f'\nstems -> {stem_dir}')
    for s in sorted(glob.glob(os.path.join(stem_dir, '*.wav'))):
        print('   ', os.path.basename(s))

    # 3) optional transcription
    if a.midi:
        from basic_pitch.inference import predict_and_save
        from basic_pitch import ICASSP_2022_MODEL_PATH
        for s in sorted(glob.glob(os.path.join(stem_dir, '*.wav'))):
            predict_and_save([s], stem_dir, save_midi=True, sonify_midi=False,
                             save_model_outputs=False, save_notes=False,
                             model_or_model_path=ICASSP_2022_MODEL_PATH)
        print('MIDI written alongside stems.')


if __name__ == '__main__':
    main()
