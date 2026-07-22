"""Per-section arrangement dynamics from demucs stems.

Measures each stem's energy (RMS) in each section of a song, giving the dynamic contour:
which instruments are loud / present / absent per section. The stems come from demucs; the
section boundaries come from the Hookpad structure in parcels.songs.

Aligning Hookpad bars to audio time: Hookpad BPM is unreliable, so instead of trusting it we
FIT the total bar-count to the audio duration (constant-tempo assumption), with an optional
--offset for a lead-in. Good enough to see gating; refine with --offset if the grid drifts.

  .venv_audio/bin/python dynamics.py "<stems dir>" --title "Getting Better"
"""
import os, re, glob, json, argparse
import numpy as np
import soundfile as sf

def bars_of(hj):
    """(name, start_bar, n_bars) per section, meter-aware."""
    ms = sorted(hj.get('meters') or [{'beat': 1, 'numBeats': 4}], key=lambda m: m.get('beat', 1))
    def npb_at(b):
        cur = ms[0]
        for m in ms:
            if m.get('beat', 1) <= b: cur = m
        return cur.get('numBeats') or 4
    def bars_between(b0, b1):
        tot, pos = 0.0, b0
        while pos < b1:
            nxt = min([m['beat'] for m in ms if m.get('beat', 1) > pos] + [b1])
            tot += (min(nxt, b1) - pos) / npb_at(pos); pos = min(nxt, b1)
        return tot
    secs = sorted(hj.get('sections') or [], key=lambda s: s.get('beat', 0))
    end = hj.get('endBeat', 0) + 1
    out, cum = [], 0.0
    for i, s in enumerate(secs):
        b0 = s['beat']; b1 = secs[i + 1]['beat'] if i + 1 < len(secs) else end
        nb = bars_between(b0, b1)
        if nb <= 0: continue
        out.append((s.get('name', '').strip() or '—', cum, nb)); cum += nb
    return out, cum

def rms_envelope(path, hop=0.05):
    audio, sr = sf.read(path, always_2d=True)
    mono = audio.mean(axis=1)
    win = int(sr * hop)
    n = len(mono) // win
    env = np.sqrt(np.array([np.mean(mono[i*win:(i+1)*win]**2) for i in range(n)]) + 1e-12)
    return env, hop, len(mono) / sr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stemdir')
    ap.add_argument('--title', default='')
    ap.add_argument('--sections', required=True, help='JSON [[name,start_bar,n_bars],...] (make with sections_json.py)')
    ap.add_argument('--offset', type=float, default=0.0, help='seconds of lead-in before bar 1')
    a = ap.parse_args()

    sections = [(n, float(sb), float(nb)) for n, sb, nb in json.load(open(a.sections))]
    total_bars = sum(nb for _, _, nb in sections)

    stems = {os.path.splitext(os.path.basename(p))[0]: p for p in sorted(glob.glob(os.path.join(a.stemdir, '*.wav')))
             if not os.path.basename(p).startswith('_mix')}
    order = [s for s in ['vocals', 'guitar', 'piano', 'bass', 'drums', 'other'] if s in stems]

    envs, dur = {}, None
    for name in order:
        env, hop, d = rms_envelope(stems[name]); envs[name] = (env, hop); dur = d
    span = dur - a.offset
    sec_per_bar = span / total_bars                       # fit bars to audio duration

    # per-section mean RMS for each stem
    rows = []
    for name, sb, nb in sections:
        t0 = a.offset + sb * sec_per_bar
        t1 = a.offset + (sb + nb) * sec_per_bar
        vals = {}
        for st in order:
            env, hop = envs[st]
            i0, i1 = int(t0 / hop), int(t1 / hop)
            vals[st] = float(np.mean(env[i0:i1])) if i1 > i0 else 0.0
        rows.append((name, sb, nb, t0, t1, vals))

    # normalize each stem to its own max across sections -> 0..1 presence
    peak = {st: max(r[5][st] for r in rows) or 1.0 for st in order}
    print(f'{a.title}  ·  {dur:.0f}s  ·  {total_bars:g} bars  ·  ~{sec_per_bar:.2f}s/bar  (offset {a.offset}s)\n')
    print(f"{'section':16}{'bars':>5}{'time':>10}   " + '  '.join(f'{st[:4]:>5}' for st in order))
    for name, sb, nb, t0, t1, vals in rows:
        bar = ''
        cells = []
        for st in order:
            v = vals[st] / peak[st]
            cells.append(f'{v:>5.2f}')
        blocks = ''.join('█' if vals[st] / peak[st] > 0.55 else ('▪' if vals[st] / peak[st] > 0.25 else '·') for st in order)
        print(f"{name[:16]:16}{nb:>5g}{t0:>6.0f}-{t1:<3.0f}   " + '  '.join(cells) + '   ' + blocks)
    print('\n  0..1 = each stem vs its own loudest section.  █ present · ▪ faint · · out')

if __name__ == '__main__':
    main()
