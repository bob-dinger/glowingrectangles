#!/usr/bin/env python3
"""
A Hookpad song -> a Synthesizer V Studio project (.svp) that sings it, with the
render already pointed at ~/Desktop/synthv_renders/, so Render writes a WAV you
can drag into GarageBand.

    themap_venv/python synthv_song.py <hookpad.json> [--from-bar 1 --bars 16] [--voice Liam]

Melody: Hookpad notes (sd + octave) resolved to MIDI pitch through the key in
force at each note (modes and key changes included), tempo changes carried.
Lyrics: Hookpad's lyric text, one token per note. The user's annotations come
out first: line-start section tags ([v] [ch] [pc]...), rhyme marks ("( a)",
"[a]"), the trailing "-" one-syllable override. "[m]" (melisma) and a token
that repeats the previous one ("hard hard") become "-", Synthesizer V's "keep
singing the same syllable". If the token count and note count disagree, the
leftover notes sing "-" and it says so.

The project is built on one the app itself saved (the newest file in its
recovery folder), so every field the app expects is there; only the music,
the voice and the render target are replaced.

Format: time is in blicks, 705,600,000 per quarter note; pitch is the MIDI
note number; the voice is named by `database` on the track's main reference.
"""
import argparse, copy, glob, json, os, re, uuid

Q = 705600000
APP = os.path.expanduser('~/Library/Application Support/Dreamtonics/Synthesizer V Studio 2')
RENDERS = os.path.expanduser('~/Desktop/synthv_renders')
VOICES = {'Liam': {"name": "Liam", "language": "english", "phoneset": "arpabet", "languageOverride": "",
                   "phonesetOverride": "", "backendType": "SVR3", "version": "201"}}
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
      'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
MODES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10],
         'mixolydian': [0, 2, 4, 5, 7, 9, 10], 'lydian': [0, 2, 4, 6, 7, 9, 11], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
         'locrian': [0, 1, 3, 5, 6, 8, 10], 'harmonicMinor': [0, 2, 3, 5, 7, 8, 11],
         'phrygianDominant': [0, 1, 4, 5, 7, 8, 10]}


def key_at(keys, beat):
    k = [k for k in sorted(keys, key=lambda k: k['beat']) if k['beat'] <= beat]
    return (k or keys)[-1]


def midi_pitch(n, keys):
    k = key_at(keys, n['beat'])
    m = re.match(r'^([b#]*)(\d)$', str(n['sd']))
    acc = m.group(1).count('#') - m.group(1).count('b')
    return 60 + PC[k['tonic']] + 12 * n.get('octave', 0) + MODES.get(k.get('scale') or 'major', MODES['major'])[int(m.group(2)) - 1] + acc


def tokens(d):
    vals = (d.get('lyrics') or {}).get('values') or []
    out = []
    for line in '\n'.join(v for v in vals if v).split('\n'):
        line = re.sub(r'^\s*\[(v|ch|pc|i|o|r|b|br)\d*\]', ' ', line)        # section tag at line start
        line = re.sub(r'\(\s*[a-h]\s*\)', ' ', line)                        # "( a)" line-end rhyme
        for t in line.split():
            if t.startswith('[m]'): out.append('-'); t = t[3:]
            t = re.sub(r'^\[[a-h]\]', '', t).rstrip('-')                    # "[a]way-" rhyme on a syllable
            t = re.sub(r'[^\w\'.,!?]', '', t)
            if t: out.append(t)
    return out


def sv_note(beat, dur, pitch, lyr):
    return {"uuid": uuid.uuid4().hex[:16], "musicalType": "singing", "onset": int(round((beat - 1) * Q)),
            "duration": int(round(dur * Q)), "lyrics": lyr, "phonemes": "", "accent": "", "pitch": pitch,
            "detune": 0, "attributes": {"evenSyllableDuration": True, "muted": False},
            "takes": {"activeTakeId": 0, "takes": [{"id": 0, "seedDuration": 0, "seedPitch": 0, "seedTimbre": 0, "liked": False}]}}


def voice_range(voice):
    """(low, high) MIDI from the voice's catalog entry, e.g. Liam 'D3 - E4'"""
    names = 'C C# D D# E F F# G G# A A# B'.split()
    for f in glob.glob(os.path.join(APP, 'databases', 'meta', '*.json')):
        try: m = json.load(open(f))
        except Exception: continue
        if m.get('name') == voice and m.get('pitchRange'):
            a, b = [x.strip() for x in m['pitchRange'].split('-')]
            mm = lambda x: 12 * (int(x[-1]) + 1) + names.index(x[:-1])
            return mm(a), mm(b)
    return None, None


def template():
    recs = sorted(glob.glob(os.path.join(APP, 'recovery', '*', '*.svp')), key=os.path.getmtime)
    if not recs: raise SystemExit('no project saved by the app yet: open Synthesizer V once and save anything')
    raw = open(recs[-1], 'rb').read()
    return json.loads(raw[:raw.rindex(b'}') + 1])


def build(d, name, voice='Liam', b0=1, b1=None):
    notes = sorted((n for n in d.get('notes') or [] if not n.get('isRest')), key=lambda n: n['beat'])
    toks = tokens(d)
    keys = d.get('keys') or [{'beat': 1, 'tonic': 'C', 'scale': 'major'}]
    sung, prev = [], None
    for i, n in enumerate(notes):
        lyr = toks[i] if i < len(toks) else '-'
        if prev is not None and lyr.lower() == prev.lower() and lyr != '-': lyr = '-'   # repetition = melisma
        prev = toks[i] if i < len(toks) else prev
        if n['beat'] < b0 or (b1 and n['beat'] >= b1): continue
        sung.append(sv_note(n['beat'] - b0 + 1, n['duration'], midi_pitch(n, keys), lyr))
    # keep it in the singer's range: shift by whole octaves so the melody's middle sits
    # in the middle of the voice (karaoke melodies are often written an octave up)
    lo, hi = voice_range(voice)
    if sung and lo:
        ps = sorted(n['pitch'] for n in sung)
        mid = (ps[0] + ps[-1]) / 2
        shift = 12 * round(((lo + hi) / 2 - mid) / 12)
        for n in sung: n['pitch'] += shift
    p = template()
    p['uuid'] = str(uuid.uuid4())
    tempos = sorted(d.get('tempos') or [{'beat': 1, 'bpm': 120}], key=lambda t: t['beat'])
    tm = [{'position': int(round(max(t['beat'] - b0, 0) * Q)), 'bpm': float(t['bpm'])}
          for t in tempos if not b1 or t['beat'] < b1]
    tm = [t for i, t in enumerate(tm) if i + 1 == len(tm) or tm[i + 1]['position'] != t['position']]
    p['time']['tempo'] = tm or [{'position': 0, 'bpm': float(tempos[0]['bpm'])}]
    p['library'] = []
    track = copy.deepcopy(p['tracks'][0])
    track.update(name=voice, renderEnabled=True, groups=[])
    track['mainGroup']['notes'] = sung
    # any installed English voice: Synthesizer V matches on the name; the rest is the
    # standard English (arpabet, SVR3) entry, the same shape as Liam's
    track['mainRef']['database'] = VOICES.get(voice) or dict(VOICES['Liam'], name=voice)
    p['tracks'] = [track]
    os.makedirs(RENDERS, exist_ok=True)
    p['renderConfig'].update(destination=RENDERS, filename=name, numChannels=2, exportMixDown=True)
    return p, len(notes), len(toks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song'); ap.add_argument('--voice', default='Liam')
    ap.add_argument('--from-bar', type=int, default=1); ap.add_argument('--bars', type=int)
    ap.add_argument('--name'); ap.add_argument('--out')
    a = ap.parse_args()
    d = json.load(open(a.song))
    name = a.name or os.path.splitext(os.path.basename(a.song))[0].replace(' ', '_')
    b0 = (a.from_bar - 1) * 4 + 1
    b1 = b0 + a.bars * 4 if a.bars else None
    p, nn, nt = build(d, name, a.voice, b0, b1)
    out = a.out or os.path.join(RENDERS, name + '.svp')
    open(out, 'w').write(json.dumps(p))
    sung = p['tracks'][0]['mainGroup']['notes']
    print(f'{out}\n  {len(sung)} notes sung by {a.voice}, tempo {p["time"]["tempo"][0]["bpm"]:g}'
          + ('' if nn == nt else f'   (lyric tokens {nt} vs notes {nn}: extra notes sing "-")'))
    print('  first words:', ' '.join(n['lyrics'] for n in sung[:16]))


if __name__ == '__main__':
    main()
