"""With A Little Help From My Friends -> a multi-track MIDI file for GarageBand.

One track per part, and the DYNAMICS come from the record. Every bar's velocity and drum
pattern is set from the demucs stems of the 2017 mix, measured on a beat grid. The parts:

    Lead Vocal      Ringo. The Hookpad melody, minus the lines the chorus sings alone
    Backing Vocals  the chorus. Pollack's vocal map, line by line (unison with the lead)
    Piano           Hookpad chords, struck on every beat
    Bass            chord roots on every beat. Paul's line "prances"; this is the skeleton
    Drums           GM kit: off / light (hat + kick) / full by measured drum energy,
                    a crash where it peaks, and the fill in refrain 1's two empty bars
    Organ           George Martin's Hammond, intro and outro only (Pollack)

Hookpad has no intro or outro, so those chords come from Pollack: intro bVI bVII I -,
outro bVII IV bVI bVII I (five bars, which is also what the audio measures, not the
eight bars in Hookpad). Written in the record's key, E major, at the measured 112 bpm.

    themap_venv/python walhfmf_garageband.py
"""
import os, json
import mido

SONG = os.path.expanduser('~/Desktop/music/hookpad_songs_full/beatles_with a little help from my friends.json')
BARS = '/private/tmp/claude-501/-Users-robert-Desktop-glowinggardens-claude/702b3f6b-901d-4ed3-a2a2-e73c5d0b291d/scratchpad/walhfmf_bars.json'
OUT = os.path.expanduser('~/Desktop/with a little help - garageband')
TPB, BPM, KEY = 480, 112, 4          # E = C + 4 semitones
PIANO2_FROM = 49                     # refrain 1, "oh I get by" -- heard by the user
MAJ = [0, 2, 4, 5, 7, 9, 11]
MODES = {'major': MAJ, 'minor': [0, 2, 3, 5, 7, 8, 10], 'mixolydian': [0, 2, 4, 5, 7, 9, 10],
         'dorian': [0, 2, 3, 5, 7, 9, 10], 'lydian': [0, 2, 4, 6, 7, 9, 11],
         'phrygian': [0, 1, 3, 5, 7, 8, 10], 'harmonicMinor': [0, 2, 3, 5, 7, 8, 11]}

# (name, hookpad start beat, bars) -- the outro is cut to the five bars the record has
SECTIONS = [('intro', 1, 4), ('verse 1', 17, 8), ('refrain 1', 49, 8), ('verse 2', 81, 8),
            ('refrain 2', 113, 6), ('bridge 1', 137, 8), ('verse 3', 169, 8),
            ('refrain 3', 201, 6), ('bridge 2', 225, 8), ('refrain 4', 257, 8), ('outro', 289, 5)]

def pcs(c):
    """Hookpad chord -> pitch classes in C, root first."""
    scale = MAJ
    b = c.get('borrowed')
    if isinstance(b, str) and b in MODES: scale = MODES[b]
    r = c['root'] - 1
    base = 0
    if c.get('applied'):                           # secondary chord: built in the target's major key
        base, scale = MAJ[c['applied'] - 1], MAJ
    deg = lambda k: base + scale[(r + k) % 7] + 12 * ((r + k) // 7)
    tones = [deg(0), deg(2), deg(4)]
    if 2 in (c.get('suspensions') or []): tones[1] = deg(1)
    if 4 in (c.get('suspensions') or []): tones[1] = deg(3)
    if int(c.get('type', 5)) >= 7: tones.append(deg(6))
    if int(c.get('type', 5)) >= 9 or 9 in (c.get('adds') or []): tones.append(deg(8))
    return tones

def chords_in_c(d):
    """[(beat, dur, pcs)] for the whole song, with Pollack's intro and outro added."""
    out = [(c['beat'], c['duration'], pcs(c)) for c in d['chords']
           if not c.get('isRest') and 17 <= c['beat'] < 289]
    Ab, Bb, C, F = [8, 12, 15], [10, 14, 17], [0, 4, 7], [5, 9, 12]
    for i, ch in enumerate([Ab, Bb, C, C]): out.append((1 + 4 * i, 4, ch))
    for i, ch in enumerate([Bb, F, Ab, Bb, C]): out.append((289 + 4 * i, 4, ch))
    return sorted(out)

def vocal_roles(d):
    """note -> 'solo' | 'chorus' | 'all', from Pollack's vocal map.

    Verses are 19 + 19 notes in four lines (10/9/10/9) plus a 4-note pickup
    ("Oh, I get by"), checked against the note-aligned Hookpad lyrics. Refrains
    alternate "with a little help from my friends" (odd bars) and a solo pickup."""
    notes = sorted([n for n in d['notes'] if not n.get('isRest')], key=lambda n: n['beat'])
    roles = []
    for name, b0, nb in SECTIONS:
        inn = [n for n in notes if b0 <= n['beat'] < b0 + nb * 4]
        for i, n in enumerate(inn):
            bar, beat = int((n['beat'] - b0) // 4) + 1, (n['beat'] - b0) % 4 + 1
            line = 0 if i < 10 else 1 if i < 19 else 2 if i < 29 else 3 if i < 38 else 4
            if name.startswith('verse'):
                if line == 4: r = 'solo'                                   # "Oh, I get by"
                elif name == 'verse 2': r = 'chorus' if line in (1, 3) else 'solo'
                elif name == 'verse 3': r = 'chorus' if line in (0, 2) else 'solo'
                else: r = 'solo'
            elif name.startswith('refrain'):
                help_line = bar % 2 == 1 and bar <= 5
                if name == 'refrain 1': r = 'all' if help_line and bar == 5 else 'solo'
                elif bar == nb and n['beat'] >= b0 + (nb - 1) * 4 + 2 and name != 'refrain 4':
                    r = 'chorus'                                           # "Do you" into the bridge
                else: r = 'all' if help_line else 'solo'
            elif name.startswith('bridge'):
                # question: bar 1 -> bar 2 beat 3, and bar 4 beat 3 -> bar 6 beat 3
                pos = (n['beat'] - b0) / 4
                r = 'chorus' if pos < 1.5 or 3.5 <= pos < 5.5 else 'solo'
            else:
                r = 'all'
            roles.append((n, r))
    return roles

def section_of(beat):
    for name, b0, nb in SECTIONS:
        if b0 <= beat < b0 + nb * 4: return name, b0, nb
    return None

def bar_index(beat):
    """Hookpad beat -> index into the measured audio bars (the outro is 5 bars there too)."""
    s = section_of(beat)
    if not s: return None
    idx = 0
    for name, b0, nb in SECTIONS:
        if name == s[0]: return idx + int((beat - b0) // 4)
        idx += nb

def t(beat):
    """Hookpad beat -> MIDI tick on the cut timeline (outro shortened, nothing else moves)."""
    return int(round((beat - 1) * TPB))

def track(name, events, channel=0, program=0):
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('track_name', name=name))
    tr.append(mido.Message('program_change', program=program, channel=channel, time=0))
    events.sort(key=lambda e: (e[0], e[1]))
    last = 0
    for tick, on, pitch, vel in events:
        tr.append(mido.Message('note_on' if on else 'note_off', note=pitch, channel=channel,
                               velocity=vel if on else 0, time=tick - last))
        last = tick
    return tr

def notes(ev, start, end, pitch, vel):
    ev += [(t(start), 1, pitch, vel), (t(end) - 1, 0, pitch, 0)]

def main():
    d = json.load(open(SONG))
    rows = json.load(open(BARS))['rows']
    ref = {k: sorted(r[k] for r in rows)[int(.9 * len(rows))] for k in rows[0] if k != 't'}
    level = lambda k, beat: (min(1.0, rows[bar_index(beat)][k] / ref[k])
                             if bar_index(beat) is not None and bar_index(beat) < len(rows) else 0)
    vel = lambda k, beat, lo=50, hi=110: int(lo + (hi - lo) * level(k, beat))
    end_beat = 289 + 5 * 4

    lead, back = [], []
    for n, r in vocal_roles(d):
        sd = str(n['sd'])
        p = (60 + KEY + MAJ[int(sd[-1]) - 1] + 12 * n.get('octave', 0)
             + sd.count('#') - sd.count('b'))
        stop = n['beat'] + n['duration']
        if r in ('solo', 'all'): notes(lead, n['beat'], stop, p, vel('vocals', n['beat'], 70, 105))
        if r in ('chorus', 'all'): notes(back, n['beat'], stop, p, vel('vocals', n['beat'], 60, 95))

    piano, piano2, bass, organ = [], [], [], []
    for b, dur, ch in chords_in_c(d):
        root = ch[0] % 12
        on = b
        while on < b + dur - 1e-9:                    # struck on every beat; short chords once
            span = min(1, b + dur - on)
            for pc in ch:
                notes(piano, on, on + span * .9, 57 + KEY + (pc - 9 + 12) % 12, vel('guitar', on, 55, 95))
                # a second piano enters at the first refrain (the user, by ear), an octave up
                if on >= PIANO2_FROM and on < 289:
                    notes(piano2, on, on + span * .9, 69 + KEY + (pc - 9 + 12) % 12, vel('guitar', on, 50, 85))
            notes(bass, on, on + span * .9, 36 + KEY + root if root < 8 else 24 + KEY + root,
                  vel('bass', on, 60, 105))
            on += span
        if b < 17 or b >= 289:                        # George Martin's Hammond
            for pc in ch: notes(organ, b, b + dur, 60 + KEY + pc % 12, 70)

    drums = []
    KICK, SNARE, HAT, CRASH, TOM_H, TOM_L = 36, 38, 42, 49, 48, 45
    for name, b0, nb in SECTIONS:
        for m in range(nb):
            bar = b0 + m * 4
            lv = level('drums', bar)
            v = int(55 + 60 * lv)
            if name == 'refrain 1' and m == 7:        # the fill in the two vocal-less bars
                for k in range(16):
                    notes(drums, bar + k / 4, bar + k / 4 + .2, [TOM_H, TOM_H, TOM_L, TOM_L][k // 4], 80 + k * 2)
                continue
            if lv < .15: continue
            for k in range(8): notes(drums, bar + k / 2, bar + k / 2 + .2, HAT, v - 15 if k % 2 else v - 5)
            for k in (0, 2): notes(drums, bar + k, bar + k + .2, KICK, v)
            if lv >= .55:
                for k in (1, 3): notes(drums, bar + k, bar + k + .2, SNARE, v)
            if m == 0 and lv >= .85: notes(drums, bar, bar + 1, CRASH, 100)

    mid = mido.MidiFile(ticks_per_beat=TPB)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage('track_name', name='With A Little Help From My Friends'))
    meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    meta.append(mido.MetaMessage('key_signature', key='E'))
    last = 0
    for name, b0, nb in SECTIONS:
        meta.append(mido.MetaMessage('marker', text=name, time=t(b0) - last)); last = t(b0)
    meta.append(mido.MetaMessage('end_of_track', time=t(end_beat) - last))
    mid.tracks.append(meta)
    mid.tracks.append(track('Lead Vocal (Ringo)', lead, 0, 52))
    mid.tracks.append(track('Backing Vocals', back, 1, 53))
    mid.tracks.append(track('Piano', piano, 2, 0))
    mid.tracks.append(track('Piano 2 (from refrain 1)', piano2, 5, 0))
    mid.tracks.append(track('Bass', bass, 3, 33))
    mid.tracks.append(track('Drums', drums, 9, 0))
    mid.tracks.append(track('Organ', organ, 4, 16))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'with a little help from my friends.mid')
    mid.save(path)

    # read it back
    m = mido.MidiFile(path)
    print(f"  {path}\n  {m.length:.1f}s at {BPM} bpm ({(end_beat-1)/4:.0f} bars); the record is 165s")
    for tr in m.tracks[1:]:
        ons = [x for x in tr if x.type == 'note_on' and x.velocity]
        print(f"    {tr.name:20} {len(ons):5} notes")
    roles = vocal_roles(d)
    print(f"  vocal lines: {sum(r=='solo' for _,r in roles)} solo, "
          f"{sum(r=='chorus' for _,r in roles)} chorus, {sum(r=='all' for _,r in roles)} all")

if __name__ == '__main__':
    main()
