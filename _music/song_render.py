#!/usr/bin/env python3
"""
A Hookpad song -> a finished, mixed demo: Synthesizer V vocal + guitar + bass +
drums, every part automated, no GarageBand.

    themap_venv/python song_render.py ~/Desktop/midis/alabama_dixieland-delight_hookpad.json \
        --from-bar 18 --bars 16 --name dixie \
        --voice Liam --guitar clean --strum folk --pedals "1:compressor+reverb,9:crunch" \
        --bass finger --bass-line root8 --drums rock

Out: ~/Desktop/song_renders/<name>/  mix.wav, mix.mp3, and stems/{vocal,guitar,bass,drums}.wav,
all starting at the same bar 1, so they can still be stacked anywhere else.

PARTS come from the Hookpad song itself: the melody and lyrics (sung by
Synthesizer V via synthv_render, hands-free), and the chords, resolved to real
pitches through the key in force (modes, borrowed chords, applied dominants,
sevenths, sus). Guitar, bass and drums are generated over those chords from a
small vocabulary of patterns, written as MIDI and played by FluidSynth with the
GeneralUser GS sound set. The guitar is rendered dry and then run through
pedals that can change at any bar (--pedals "1:clean,9:fuzz"; a fractional bar
like 8.625 switches mid-bar, the Teen Spirit move).

PEDALS (combine with +): compressor, tremolo, phaser, flanger, chorus, octave,
crunch, fuzz (heavy distortion), delay, reverb, clean (= compressor + a little reverb).
"""
import argparse, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthv_song as S

SF2 = os.path.expanduser('~/Desktop/music/soundfonts/GeneralUser-GS-main/GeneralUser-GS.sf2')
OUT = os.path.expanduser('~/Desktop/song_renders')
SR = 44100
AUDIO_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv_audio', 'bin', 'python')

# GM programs (0-based) for the sounds you can ask for by name
GUITARS = {'acoustic': 25, 'nylon': 24, 'clean': 27, 'jazz': 26, 'muted': 28, 'overdrive': 29, 'distortion': 30}
BASSES = {'finger': 33, 'pick': 34, 'fretless': 35, 'acoustic': 32, 'synth': 38}


# ---------------------------------------------------------------- chords -> pitches
def scale_of(key, borrowed):
    tonic = S.PC[key['tonic']]
    if isinstance(borrowed, list) and borrowed:           # custom scale, degrees in order
        iv = []
        for sd in borrowed:
            m = re.match(r'^([b#]*)(\d)$', str(sd))
            iv.append(S.MODES['major'][int(m.group(2)) - 1] + m.group(1).count('#') - m.group(1).count('b'))
        return tonic, iv
    mode = borrowed if isinstance(borrowed, str) and borrowed in S.MODES else (key.get('scale') or 'major')
    return tonic, S.MODES.get(mode, S.MODES['major'])


def chord_pcs(c, keys):
    """-> (root pitch class, [intervals above the root])"""
    key = S.key_at(keys, c['beat'])
    tonic, sc = scale_of(key, c.get('borrowed'))
    r = int(c['root'])
    seventh = str(c.get('type')) in ('7', '9', '11', '13', '65', '43', '42')
    if c.get('applied'):                                    # V/x or vii/x of a degree of the KEY scale
        _, ksc = scale_of(key, None)
        target = tonic + ksc[(int(c['applied']) - 1) % 7]
        if r == 7: return (target + 11) % 12, [0, 3, 6] + ([9] if seventh else [])
        return (target + 7) % 12, [0, 4, 7] + ([10] if seventh else [])
    deg = r - 1
    root = sc[deg % len(sc)]
    def up(k):
        x = sc[(deg + k) % len(sc)] - root
        return x % 12
    third, fifth = up(2), up(4)
    sus = c.get('suspensions') or []
    if 2 in sus or '2' in sus: third = 2
    elif 4 in sus or '4' in sus: third = 5
    iv = [0, third, fifth] + ([up(6)] if seventh else [])
    return (tonic + root) % 12, iv


def chords_in(d, b0, b1):
    keys = d.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    out = []
    for c in sorted(d.get('chords') or [], key=lambda c: c['beat']):
        if c.get('isRest'): continue
        s, e = c['beat'], c['beat'] + c['duration']
        if e <= b0 or s >= b1: continue
        root, iv = chord_pcs(c, keys)
        out.append((max(s, b0) - b0, min(e, b1) - b0, root, iv))
    return out


# ---------------------------------------------------------------- patterns -> MIDI
def guitar_notes(chords, strum, sound, span=4):
    """(beat, dur, pitch, velocity). Power chords for distorted sounds, open-ish triads otherwise."""
    out = []
    power = sound in ('overdrive', 'distortion')
    pats = {  # beat offsets within a bar, D = down (all strings), U = up (top strings)
        'hold': [(0, 'D')], 'quarters': [(0, 'D'), (1, 'D'), (2, 'D'), (3, 'D')],
        'eighths': [(i / 2, 'D') for i in range(8)],
        'folk': [(0, 'D'), (1, 'D'), (1.5, 'U'), (2.5, 'U'), (3, 'D'), (3.5, 'U')],   # D DU UDU
        'push': [(0, 'D'), (1.5, 'D'), (2.5, 'D'), (3.5, 'D')],
    }[strum]
    for s, e, root, iv in chords:
        base = 40 + (root - 4) % 12                          # lowest string region, E2..D#3
        voicing = [base, base + 7, base + 12] if power else sorted({base + x for x in iv} | {base + 12, base + 12 + iv[1]})
        bar0 = int(s // span) * span
        for b in range(bar0, int(np.ceil(e)), span):
            for off, kind in pats:
                t = b + off * span / 4
                if t < s or t >= e: continue
                nxt = [b + o * span / 4 for o, _ in pats if b + o * span / 4 > t] + [b + span]
                dur = min(min(nxt) - t, e - t) * (0.5 if power and strum == 'eighths' else 0.95)
                strings = voicing if kind == 'D' else voicing[-3:]
                for k, p in enumerate(strings if kind == 'D' else strings[::-1]):
                    out.append((t + k * 0.012 * (1 if kind == 'D' else 0.7), dur, p, 96 if kind == 'D' else 74))
    return out


def bass_notes(chords, line, span=4):
    out = []
    for s, e, root, iv in chords:
        p = 28 + (root - 4) % 12                             # E1..D#2
        if line == 'hold':
            out.append((s, e - s, p, 100)); continue
        step = {'root8': .5, 'root4': 1, 'rootfifth': 1}[line] * span / 4
        t, i = s, 0
        while t < e - 1e-6:
            q = p + (7 if line == 'rootfifth' and i % 2 else 0)
            out.append((t, min(step, e - t) * 0.9, q, 104 if i % 2 == 0 else 92))
            t += step; i += 1
    return out


def drum_notes(nbeats, style, section_starts, span=4):
    K, SN, HH, CR, RD = 36, 38, 42, 49, 51
    out = []
    for b in range(0, int(nbeats), span):
        if style == 'none': break
        hits = {'rock': [(0, K), (1, SN), (2, K), (2.5, K), (3, SN)] + [(i / 2, HH) for i in range(8)],
                'half': [(0, K), (2, SN)] + [(i, HH) for i in range(4)],
                'train': [(0, K), (2, K)] + [(i / 2, SN) for i in range(8)],
                'four': [(i, K) for i in range(4)] + [(1, SN), (3, SN)] + [(i / 2 + .5, HH) for i in range(0, 8, 2)],
                }[style]
        for off, n in hits:
            v = 110 if n in (K, SN) else (78 if off % 1 else 92)
            out.append((b + off * span / 4, .25, n, v))
    for s in section_starts:
        out.append((s, 1, CR, 112)); out.append((s, .25, K, 115))
    return out


def write_midi(notes, tempos, program, path, channel):
    import mido
    TPB = 480
    mid = mido.MidiFile(ticks_per_beat=TPB)
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    ev = [(int(round(b * TPB)), 0, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm))) for b, bpm in tempos]
    if channel != 9: ev.append((0, 1, mido.Message('program_change', program=program, channel=channel)))
    for b, d, p, v in notes:
        on = int(round(b * TPB)); off = on + max(int(round(d * TPB)), 10)
        ev.append((on, 3, mido.Message('note_on', note=int(p), velocity=int(v), channel=channel)))
        ev.append((off, 2, mido.Message('note_off', note=int(p), velocity=0, channel=channel)))
    ev.sort(key=lambda x: (x[0], x[1]))
    t = 0
    for at, _, m in ev:
        tr.append(m.copy(time=at - t)); t = at
    mid.save(path)


def fluid(mid, wav):
    subprocess.run(['fluidsynth', '-ni', '-g', '0.9', '-r', str(SR), '-F', wav, SF2, mid],
                   check=True, capture_output=True)


# ---------------------------------------------------------------- the audio side runs in the audio venv
AUDIO = r'''
import json, sys, numpy as np, soundfile as sf, pedalboard as pb
job = json.load(open(sys.argv[1])); SR = 44100

def load(p, n=None):
    y, sr = sf.read(p, always_2d=True); y = y.T.astype(np.float32)
    if y.shape[0] == 1: y = np.vstack([y, y])
    return y

NAM_DIR = job['nam_dir']
# amp captures sound right only through a speaker cabinet; each amp brings its own
# unless the capture already has one ("-cab") or it is a pedal
CAB = {'twin': 'twin-2x12', 'twin-vibrato': 'twin-2x12', 'vox-ac15': 'vox-2x12', 'jcm-crunch': 'marshall-greenback',
       'jcm-lead': 'marshall-greenback', '5150': 'mesa-4x12', 'bass-dug': 'bass-v30'}
_models = {}

def nam(name):
    """run a .nam capture (48 kHz models) on a stereo track: mono in, level-matched, stereo out"""
    import os, torch, librosa
    from nam.models import init_from_nam
    if name not in _models:
        m = init_from_nam(json.load(open(os.path.join(NAM_DIR, 'amps', name + '.nam')))); m.eval(); _models[name] = m
    def run(y):
        x = y.mean(0); pk = np.abs(x).max() or 1
        x = librosa.resample(x / pk * 0.35, orig_sr=SR, target_sr=48000)    # a guitar DI sits around -9 dBFS
        with torch.no_grad(): z = _models[name](torch.from_numpy(x.astype(np.float32))).numpy()
        z = librosa.resample(z, orig_sr=48000, target_sr=SR)[:y.shape[1]]
        z = np.pad(z, (0, y.shape[1] - len(z)))
        z = z / (np.abs(z).max() or 1) * 0.5
        return np.vstack([z, z]).astype(np.float32)
    return run

def fx(*plugins):
    board = pb.Pedalboard(list(plugins))
    return lambda y: board(y, SR)

def chain(names):
    import os
    st, last_amp = [], None
    for nm in names:
        if nm == 'clean': st.append(fx(pb.Compressor(threshold_db=-18, ratio=3), pb.Reverb(room_size=.25, wet_level=.12, dry_level=.9)))
        elif nm == 'compressor': st.append(fx(pb.Compressor(threshold_db=-22, ratio=5, attack_ms=5, release_ms=200), pb.Gain(4)))
        elif nm == 'crunch': st.append(fx(pb.Gain(6), pb.Distortion(drive_db=14), pb.LowpassFilter(5500), pb.HighpassFilter(90), pb.Gain(-8)))
        elif nm == 'fuzz': st.append(fx(pb.Gain(10), pb.Distortion(drive_db=32), pb.LowpassFilter(4500), pb.HighpassFilter(110), pb.Gain(-17)))
        elif nm == 'phaser': st.append(fx(pb.Phaser(rate_hz=.6, depth=.6, mix=.6)))
        elif nm == 'flanger': st.append(fx(pb.Chorus(rate_hz=.25, depth=.6, centre_delay_ms=2.5, feedback=.5, mix=.5)))
        elif nm == 'chorus': st.append(fx(pb.Chorus(rate_hz=.9, depth=.3, centre_delay_ms=7, mix=.4)))
        elif nm == 'delay': st.append(fx(pb.Delay(delay_seconds=job['beat_s'] * .75, feedback=.3, mix=.25)))
        elif nm == 'reverb': st.append(fx(pb.Reverb(room_size=.55, wet_level=.25, dry_level=.85)))
        elif nm == 'tremolo':                                # 8th-note volume pulse
            def trem(y):
                t = (np.arange(y.shape[1]) / SR) / (job['beat_s'] / 2)
                return y * (0.55 + 0.45 * (0.5 + 0.5 * np.cos(2 * np.pi * t)))
            st.append(trem)
        elif nm == 'octave': st.append(lambda y: y + 0.7 * pb.Pedalboard([pb.PitchShift(-12)])(y, SR))
        elif nm.startswith('cab:'): st.append(fx(pb.Convolution(os.path.join(NAM_DIR, 'cabs', nm[4:] + '.wav'), mix=1.0))); last_amp = None
        elif os.path.exists(os.path.join(NAM_DIR, 'amps', nm + '.nam')):
            st.append(nam(nm)); last_amp = nm if nm in CAB else last_amp
        else: raise SystemExit(f'unknown pedal {nm}')
    if last_amp and not any(n.startswith('cab:') for n in names):
        st.append(fx(pb.Convolution(os.path.join(NAM_DIR, 'cabs', CAB[last_amp] + '.wav'), mix=1.0), pb.Gain(6)))
    return st

def pedal_track(g, segs):
    out = np.zeros_like(g); fade = int(.012 * SR)
    for i, (t0, names) in enumerate(segs):
        t1 = segs[i + 1][0] if i + 1 < len(segs) else g.shape[1] / SR
        a, b = int(t0 * SR), int(t1 * SR)
        lo = max(a - fade, 0)
        y = g[:, :min(b + 4 * SR, g.shape[1])].copy()         # run from the top so reverbs and delays carry
        for stage in chain(names): y = stage(y)
        wet = y[:, lo:b]
        w = np.ones(wet.shape[1], np.float32)
        if a > 0: w[:a - lo] = np.linspace(0, 1, a - lo)
        out[:, lo:b] = out[:, lo:b] * (1 - w) + wet * w
    return out

out = pedal_track(load(job['guitar_dry']), job['pedals'])
sf.write(job['guitar'], out.T, SR)
if job.get('bass_pedals') and job['stems'].get('bass'):
    sf.write(job['stems']['bass'], pedal_track(load(job['stems']['bass']), job['bass_pedals']).T, SR)

stems = {k: load(v) for k, v in job['stems'].items() if v}
stems['guitar'] = out
n = max(s.shape[1] for s in stems.values())
mix = np.zeros((2, n), np.float32)
for k, s in stems.items():
    gain = 10 ** (job['levels'].get(k, 0) / 20)
    rms = float(np.sqrt((s[:, np.abs(s).max(0) > 1e-4] ** 2).mean())) or 1
    mix[:, :s.shape[1]] += s / rms * 0.08 * gain              # level each stem by its loudness first
mix = pb.Pedalboard([pb.Compressor(threshold_db=-10, ratio=2.5), pb.Limiter(threshold_db=-1)])(mix, SR)
sf.write(job['mix'], mix.T, SR)
print('mixed', round(n / SR, 1), 's')
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song'); ap.add_argument('--name')
    ap.add_argument('--from-bar', type=int, default=1); ap.add_argument('--bars', type=int, default=16)
    ap.add_argument('--voice', default='Liam', help='Synthesizer V voice, or "none"')
    ap.add_argument('--guitar', default='clean', choices=list(GUITARS) + ['none'])
    ap.add_argument('--strum', default='folk', choices=['hold', 'quarters', 'eighths', 'folk', 'push'])
    ap.add_argument('--pedals', default='1:clean', help='"bar:pedal+pedal,bar:..." e.g. "1:clean,8.625:fuzz"')
    ap.add_argument('--bass-pedals', default='', help='same form as --pedals, e.g. "1:bass-dug+compressor"')
    ap.add_argument('--bass', default='finger', choices=list(BASSES) + ['none'])
    ap.add_argument('--bass-line', default='root8', choices=['root8', 'root4', 'rootfifth', 'hold'])
    ap.add_argument('--drums', default='rock', choices=['rock', 'half', 'train', 'four', 'none'])
    ap.add_argument('--feel', default='auto', choices=['auto', 'normal', 'half'],
                    help='half = patterns stretched over two bars (a 180 song felt at 90); auto = half above 150 bpm')
    ap.add_argument('--levels', default='vocal:3,guitar:-1,bass:-1,drums:-5', help='dB per stem')
    a = ap.parse_args()

    d = json.load(open(os.path.expanduser(a.song)))
    name = a.name or os.path.splitext(os.path.basename(a.song))[0].replace(' ', '_')
    work = os.path.join(OUT, name); stems = os.path.join(work, 'stems'); os.makedirs(stems, exist_ok=True)
    b0 = (a.from_bar - 1) * 4 + 1; b1 = b0 + a.bars * 4; nbeats = b1 - b0

    tempos = [(max(t['beat'] - b0, 0), float(t['bpm'])) for t in sorted(d.get('tempos') or [{'beat': 1, 'bpm': 120}], key=lambda t: t['beat']) if t['beat'] < b1]
    tempos = [t for i, t in enumerate(tempos) if i + 1 == len(tempos) or tempos[i + 1][0] != t[0]]
    beat_s = 60 / tempos[0][1]
    def sec(beat):                                            # beat (0-based) -> seconds through the tempo map
        s, last_b, last_bpm = 0.0, 0.0, tempos[0][1]
        for tb, bpm in tempos[1:]:
            if tb >= beat: break
            s += (tb - last_b) * 60 / last_bpm; last_b, last_bpm = tb, bpm
        return s + (beat - last_b) * 60 / last_bpm

    chords = chords_in(d, b0, b1)
    span = 8 if a.feel == 'half' or (a.feel == 'auto' and tempos[0][1] > 150) else 4
    secs = sorted({max(s['beat'] - b0, 0) for s in d.get('sections') or [] if b0 <= s['beat'] < b1} | {0})
    print(f'feel: {"half-time" if span == 8 else "normal"}')
    print(f'{name}: bars {a.from_bar}-{a.from_bar + a.bars - 1}, {len(chords)} chords, tempo {tempos[0][1]:g}')

    parts = {}
    if a.guitar != 'none':
        write_midi(guitar_notes(chords, a.strum, a.guitar, span), tempos, GUITARS[a.guitar], os.path.join(work, 'guitar.mid'), 0)
        fluid(os.path.join(work, 'guitar.mid'), os.path.join(stems, 'guitar_dry.wav'))
    if a.bass != 'none':
        write_midi(bass_notes(chords, a.bass_line, span), tempos, BASSES[a.bass], os.path.join(work, 'bass.mid'), 1)
        fluid(os.path.join(work, 'bass.mid'), os.path.join(stems, 'bass.wav')); parts['bass'] = os.path.join(stems, 'bass.wav')
    if a.drums != 'none':
        write_midi(drum_notes(nbeats, a.drums, secs, span), tempos, 0, os.path.join(work, 'drums.mid'), 9)
        fluid(os.path.join(work, 'drums.mid'), os.path.join(stems, 'drums.wav')); parts['drums'] = os.path.join(stems, 'drums.wav')
    if a.voice != 'none':
        import synthv_render as R
        p, nn, nt = S.build(d, name, a.voice, b0, b1)
        svp = os.path.join(S.RENDERS, name + '.svp'); open(svp, 'w').write(json.dumps(p))
        wavs = R.render(svp)
        os.replace(wavs[0], os.path.join(stems, 'vocal.wav')); parts['vocal'] = os.path.join(stems, 'vocal.wav')

    pedals = []
    for seg in a.pedals.split(','):
        bar, _, names = seg.partition(':')
        pedals.append((sec((float(bar) - a.from_bar) * 4 if float(bar) >= a.from_bar else 0), names.split('+')))
    pedals.sort()
    def parse_pedals(spec):
        out = []
        for seg in spec.split(','):
            bar, _, names = seg.partition(':')
            out.append((sec((float(bar) - a.from_bar) * 4 if float(bar) >= a.from_bar else 0), names.split('+')))
        return sorted(out)
    job = dict(nam_dir=os.path.expanduser('~/Desktop/music/nam'),
               bass_pedals=parse_pedals(a.bass_pedals) if a.bass_pedals else None,
               guitar_dry=os.path.join(stems, 'guitar_dry.wav') if a.guitar != 'none' else None,
               guitar=os.path.join(stems, 'guitar.wav'), pedals=pedals, beat_s=beat_s, stems=parts,
               levels={k: float(v) for k, v in (x.split(':') for x in a.levels.split(','))},
               mix=os.path.join(work, 'mix.wav'))
    jf = os.path.join(work, 'job.json'); json.dump(job, open(jf, 'w'))
    af = os.path.join(work, '_audio.py'); open(af, 'w').write(AUDIO)
    if a.guitar == 'none':
        raise SystemExit('a guitar part is required for now')
    subprocess.run([AUDIO_PY, af, jf], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', job['mix'], '-b:a', '256k', os.path.join(work, 'mix.mp3')], check=True)
    os.remove(job['guitar_dry']); os.remove(af)
    print(f'-> {os.path.join(work, "mix.mp3")}\n   stems: {", ".join(sorted(os.listdir(stems)))}')


if __name__ == '__main__':
    main()
