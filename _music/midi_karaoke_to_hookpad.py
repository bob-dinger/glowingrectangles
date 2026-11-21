#!/usr/bin/env python3
"""
A karaoke MIDI -> a whole Hookpad song: melody with its lyrics, chords from the
backing tracks, key and tempo changes. Built for Dixieland Delight (Alabama,
freemidi.org #9739), whose melody is a lyric-carrying "Harmonica" track.

    themap_venv/python midi_karaoke_to_hookpad.py <in.mid> --melody-track 1 \
        --keys 1:G,593:A [--name "alabama_dixieland delight-midi"] [--upload]

Melody: the lyric track's notes, onsets and ends snapped to the half beat (the
file is played in by hand, about an eighth of a beat loose), overlaps trimmed so
it stays one line. Each note takes the lyric syllable sung on it; a note with
none repeats the previous syllable (the repetition encoding for melisma).
'\\r' in the karaoke text = a new lyric line, '\\n' = a new paragraph, and every
paragraph opens a section at the bar where its first note falls.

Chords: v2_chord_extract.segment over every non-drum note (chords with
durations), change points snapped to the half bar, then named against the key
in force: diatonic as is; a minor I/IV/V or a major bIII/bVI/bVII borrowed from
minor; a major II/III/VI as V/V, V/vi, V/ii. Anything else is marked as a rest
so it can be filled by ear.
"""
import argparse, json, os, re, sys
import mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v0_chord_extract import load_midi_beats
from v2_chord_extract import segment

NAMES = 'C C# D Eb E F F# G Ab A Bb B'.split()
PCS = {n: i for i, n in enumerate(NAMES)} | {'Db': 1, 'D#': 3, 'Gb': 6, 'G#': 8, 'A#': 10}
MAJ = [0, 2, 4, 5, 7, 9, 11]


def q(x, g=.5):
    v = round(x / g) * g
    return int(v) if v == int(v) else v


def key_at(keys, b):
    return [k for k in keys if k[0] <= b][-1][1]


def sd_oct(pitch, tonic_pc):
    """MIDI pitch -> Hookpad (sd, octave) in a major key; octave 0 starts at the tonic above middle C-ish"""
    rel = pitch - (60 + tonic_pc)
    o, pc = divmod(rel, 12)
    if pc in MAJ: return str(MAJ.index(pc) + 1), o
    return {1: '#1', 3: 'b3', 6: '#4', 8: 'b6', 10: 'b7'}[pc], o


def chord_obj(root_pc, qual, tonic_pc, beat, dur):
    iv = (root_pc - tonic_pc) % 12
    base = dict(root=1, beat=beat, duration=dur, type=5, inversion=0, applied=0, adds=[], omits=[],
                alterations=[], suspensions=[], substitutions=[], pedal=None, alternate='', borrowed='',
                isRest=False, recordingEndBeat=None)
    diat = {0: (1, 'maj'), 2: (2, 'min'), 4: (3, 'min'), 5: (4, 'maj'), 7: (5, 'maj'), 9: (6, 'min')}
    if iv in diat and diat[iv][1] == qual: return {**base, 'root': diat[iv][0]}
    if qual == 'min' and iv in (0, 5, 7): return {**base, 'root': {0: 1, 5: 4, 7: 5}[iv], 'borrowed': 'minor'}
    if qual == 'maj' and iv in (3, 8, 10): return {**base, 'root': {3: 3, 8: 6, 10: 7}[iv], 'borrowed': 'minor'}
    if qual == 'maj' and iv in (2, 4, 9): return {**base, 'root': 5, 'applied': {2: 5, 4: 6, 9: 2}[iv]}
    return {**base, 'isRest': True}


# Hookpad will not open a song that lacks the non-musical fields a real Save
# writes (instruments, settings, loop, cursor...): it hangs on "loading" with
# "cannot read 'type' of undefined". So every generated song starts from a
# saved one with its music emptied out.
TEMPLATE = os.path.expanduser('~/Desktop/music/hookpad_songs_full/oasis_wonderwall.json')


def template():
    t = json.load(open(TEMPLATE))
    t.pop('fp', None)
    t['bands'] = [dict(t['bands'][0], beat=1)]
    t.update(inactiveNotes=[[] for _ in t.get('inactiveNotes') or [[], [], [], []]], keyFrames=[],
             cursor={'beat': 1, 'location': 'cursor-note-staff'}, externalAudioFiles=[], audioTracks=[],
             loopGui={'looping': False, 'beat': 1, 'duration': 16, 'loopIndex': -1},
             youtube={'id': None, 'syncStart': 0.05, 'syncEnd': 0.15, 'syncMode': 'youtube-sync-mode-set-start-and-end'})
    return t


def melody(mid, ti, keys):
    tpb = mid.ticks_per_beat
    t, on, ns, ly = 0, {}, [], []
    for x in mid.tracks[ti]:
        t += x.time
        if x.type == 'lyrics': ly.append((t / tpb + 1, x.text))
        elif x.type == 'note_on' and x.velocity > 0: on[x.note] = t
        elif x.type in ('note_off', 'note_on') and x.note in on:
            s = on.pop(x.note); ns.append([q(s / tpb + 1), q(t / tpb + 1), x.note])
    ns.sort()
    out = []
    for s, e, p in ns:
        if out and out[-1][0] == s: continue              # chord-stab on the lead: keep the first
        if out and out[-1][1] > s: out[-1][1] = s           # one line: trim the overlap
        out.append([s, max(e, s + .5), p])
    # syllables: each lyric event belongs to the note starting nearest to it
    tokens, breaks = [None] * len(out), {}
    for b, txt in ly:
        if txt in ('\r', '\n'):
            nxt = next((i for i, n in enumerate(out) if n[0] > b + .25), None)   # the break follows the line's last syllable
            if nxt is not None: breaks[nxt] = max(breaks.get(nxt, ''), txt, key=len) if txt == '\n' else breaks.get(nxt, '\r')
            continue
        i = min(range(len(out)), key=lambda i: abs(out[i][0] - b))
        if abs(out[i][0] - b) <= .5:
            syl = re.sub(r'[^\w\']', '', txt)
            tokens[i] = syl if tokens[i] is None else tokens[i] + syl
    notes, prev = [], 'oo'
    for i, (s, e, p) in enumerate(out):
        sd, o = sd_oct(p, PCS[key_at(keys, s)])
        notes.append(dict(sd=sd, octave=o, beat=s, duration=q(e - s), isRest=False, recordingEndBeat=None))
        prev = tokens[i] or prev; tokens[i] = prev
    return notes, tokens, breaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mid'); ap.add_argument('--melody-track', type=int, required=True)
    ap.add_argument('--keys', required=True, help='beat:tonic,... e.g. 1:G,577:A (major)')
    ap.add_argument('--name'); ap.add_argument('--upload', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--patch', type=int, help='numeric ID of an existing song to save over')
    a = ap.parse_args()
    keys = [(float(b), k) for b, k in (x.split(':') for x in a.keys.split(','))]
    mid = mido.MidiFile(a.mid)

    notes, tokens, breaks = melody(mid, a.melody_track, keys)

    allnotes, nb = load_midi_beats(a.mid)
    _, segs = segment(allnotes, nb, .5, .6)
    chords = []
    for i, n, (r, qu) in segs:
        s, e = q(i, 2) + 1, q(i + n, 2) + 1
        if e <= s: continue
        if chords and chords[-1]['beat'] + chords[-1]['duration'] > s: continue
        c = chord_obj(r, qu, PCS[key_at(keys, s)], s, e - s)
        if chords and not c['isRest'] and all(chords[-1].get(k) == c.get(k) for k in ('root', 'applied', 'borrowed', 'isRest')) \
                and chords[-1]['beat'] + chords[-1]['duration'] == s:
            chords[-1]['duration'] += c['duration']; continue
        chords.append(c)

    tpb, t, tempos = mid.ticks_per_beat, 0, []
    for x in mid.tracks[0]:
        t += x.time
        if x.type == 'set_tempo':
            bpm = round(mido.tempo2bpm(x.tempo))
            if not tempos or tempos[-1]['bpm'] != bpm:
                tempos.append(dict(beat=q(t / tpb + 1, 1), bpm=bpm, swingFactor=0, swingBeat=.5))
    # sections: every lyric paragraph, from the start of its bar; an intro before the first
    starts = sorted({0} | {i for i, k in breaks.items() if k == '\n'})
    sections = [dict(beat=1, name='Intro')] if notes and notes[0]['beat'] > 5 else []
    for j, i in enumerate(starts):
        b = int((notes[i]['beat'] - 1) // 4) * 4 + 1
        if notes[i]['beat'] - b < 1 and b > 1: b = b    # pickup inside the bar: keep this bar
        if sections and sections[-1]['beat'] >= b: continue
        sections.append(dict(beat=b, name=f'Part {j + 1}'))
    # lyric text: one token per note, lines on \r, a blank line per paragraph
    text = ''
    for i, tok in enumerate(tokens):
        if i in breaks: text = text.rstrip(' ') + ('\n\n' if breaks[i] == '\n' else '\n')
        text += tok + ' '
    end = max([n['beat'] + n['duration'] for n in notes] + [c['beat'] + c['duration'] for c in chords])
    song = template() | dict(chords=chords, notes=notes,
                keys=[dict(beat=q(b, 1), scale='major', tonic=k) for b, k in keys],
                tempos=tempos, meters=[dict(beat=1, numBeats=4, beatUnit=1)], breaks=[], sections=sections,
                lyrics=dict(isOpen=False, isFocused=False, values=[text.strip()]),
                audioTracks=[], endBeat=int((end - 1) // 4 + 1) * 4 + 1)
    print(f'{len(notes)} melody notes, {sum(1 for t in tokens if t)} with syllables, {len(chords)} chords '
          f'({sum(c["isRest"] for c in chords)} left blank), {len(sections)} sections, tempos {[x["bpm"] for x in tempos]}')
    out = a.out or os.path.expanduser(f'~/Desktop/{(a.name or "midi_song").replace(" ", "_")}.json')
    json.dump(song, open(out, 'w'))
    print('wrote', out)
    if a.upload:
        import hookpad_upload_variants as U, hookpad_token
        tok = hookpad_token.read_saved()
        rec, err = U.upload(tok, a.name, song)
        print(err or rec)
    if a.patch:
        # save over an existing song, the way Hookpad's own Save does
        import hookpad_upload_variants as U, hookpad_token
        r = U.call('PATCH', f'{U.API}/songs/{a.patch}', hookpad_token.read_saved(),
                   json={'jsonData': U.json_data(song), 'cloudBackupsEnabled': True})
        print('PATCH', r.status_code, r.text[:200])


if __name__ == '__main__':
    main()
