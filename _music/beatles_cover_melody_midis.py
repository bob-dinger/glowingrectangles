"""For each Beatles cover that has chords but no melody yet, isolate the melody
track from its source MIDI (using the validated scored picker in
midi_melody_extract) and write a clean single-track MIDI for Hookpad import.

Output: ~/Desktop/beatles_cover_melodies_midi/<song>_melody.mid
"""
import os, re, glob
import mido
from midi_melody_extract import score_track

OUT = os.path.expanduser('~/Desktop/beatles_cover_melodies_midi')
SRC_DIRS = ['~/Desktop/7-10-26/midi_files_beatles_new', '~/Desktop/midi_files_beatles_new',
            '~/Desktop/midi_files3', '~/Desktop/midi_files', '~/Desktop/midis']
os.makedirs(OUT, exist_ok=True)

COVERS = ["act naturally", "a taste of honey", "baby its you", "bad boy",
    "devil in her heart", "dizzy miss lizzy", "everybody's trying to be my baby",
    "honey don't", "long tall sally", "please mister postman", "rock and roll music",
    "roll over beethoven", "slow down", "words of love", "you really got a hold on me"]

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def find_midi(title):
    n = norm(title)
    for d in SRC_DIRS:
        for p in glob.glob(os.path.expanduser(d) + '/**/*.mid', recursive=True):
            b = re.sub(r'^(beatles[-_]midis?[-_]|beatles[-_])', '', os.path.basename(p)[:-4], flags=re.I)
            if norm(b) == n or (len(n) > 6 and n in norm(b)):
                return p
    return None

def meta_track(mid):
    """A conductor track with just tempo / time-sig / key-sig (no notes)."""
    mt = mido.MidiTrack()
    for tr in mid.tracks:
        t = 0
        for msg in tr:
            t += msg.time
            if msg.is_meta and msg.type in ('set_tempo', 'time_signature', 'key_signature'):
                m = msg.copy(time=0)
                mt.append(m)
        if mt:  # take meta from the first track that has any
            break
    mt.append(mido.MetaMessage('end_of_track', time=0))
    return mt

def isolate(midi_path, out_path):
    mid = mido.MidiFile(midi_path)
    tpb = mid.ticks_per_beat
    scored = [score_track(tr, tpb) for tr in mid.tracks]
    best = max(range(len(scored)), key=lambda i: scored[i][0])
    if scored[best][0] < 0:
        return None
    name = ' '.join(m.name for m in mid.tracks[best] if m.type == 'track_name') or '(unnamed)'
    new = mido.MidiFile(ticks_per_beat=tpb)
    new.tracks.append(meta_track(mid))
    new.tracks.append(mid.tracks[best])           # the melody track, timing intact
    new.save(out_path)
    return name, scored[best][0], len(scored[best][1])

def main():
    print(f"{'SONG':34} {'TRACK':20} score notes")
    ok = 0
    for title in COVERS:
        midi = find_midi(title)
        if not midi:
            print(f"{title[:34]:34} NO MIDI FOUND"); continue
        out = os.path.join(OUT, norm(title) + '_melody.mid')
        try:
            res = isolate(midi, out)
        except Exception as e:
            print(f"{title[:34]:34} ERROR {str(e)[:40]}"); continue
        if not res:
            print(f"{title[:34]:34} no melody track"); continue
        name, sc, nn = res
        print(f"{title[:34]:34} {name[:20]:20} {sc:5.1f} {nn:>5}")
        ok += 1
    print(f"\n{ok}/{len(COVERS)} melody MIDIs written to {OUT}")

if __name__ == '__main__':
    main()
