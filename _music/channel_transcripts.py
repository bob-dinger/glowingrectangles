"""Download + clean every English auto-caption transcript from a YouTube channel.

    .venv_audio/bin/python channel_transcripts.py "<channel url>" [-o OUTDIR]

Fetches YouTube's auto-generated English captions for every video (no audio
download), then cleans the messy rolling-VTT into plain readable text, one
.txt per video. Resumable (--no-overwrites); skips videos with no captions.
"""
import sys, os, re, subprocess, glob, argparse

PY = sys.executable


def clean_vtt(path):
    """YouTube auto-VTT -> plain text. Keep only word-timed lines, strip tags,
    which drops the rolling-duplicate plain cues automatically."""
    words = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        if '<c>' in line or re.search(r'<\d\d:\d\d:\d\d', line):
            txt = re.sub(r'<[^>]+>', '', line).strip()
            if txt:
                words.append(txt)
    return re.sub(r'\s+', ' ', ' '.join(words)).strip()


def clean_all(vttdir, outdir):
    n = 0
    for v in glob.glob(os.path.join(vttdir, '*.en.vtt')):
        base = os.path.basename(v)[:-7]          # strip '.en.vtt'
        txt = clean_vtt(v)
        if len(txt.split()) < 20:
            continue
        with open(os.path.join(outdir, base + '.txt'), 'w', encoding='utf-8') as f:
            f.write(txt)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('-o', '--out', default=os.path.expanduser('~/Desktop/bennett_transcripts'))
    a = ap.parse_args()
    vttdir = os.path.join(a.out, '_vtt')
    os.makedirs(vttdir, exist_ok=True)

    subprocess.run([PY, '-m', 'yt_dlp', '--write-auto-subs', '--sub-langs', 'en',
                    '--sub-format', 'vtt', '--skip-download', '--no-overwrites',
                    '--ignore-errors', '--sleep-requests', '1',
                    '-o', os.path.join(vttdir, '%(title)s [%(id)s]'), a.url])

    n = clean_all(vttdir, a.out)
    print(f'\nwrote {n} cleaned transcripts to {a.out}')


if __name__ == '__main__':
    main()
