"""Extract the top note at each time point from a polyphonic MIDI track.
Useful when a track has chords + melody bundled (the melody usually sits on top).
"""
import mido
import sys
from collections import defaultdict

def extract_top_line(midi_path, track_idx, out_path):
    mid = mido.MidiFile(midi_path)
    src = mid.tracks[track_idx]

    # Walk track, collecting notes with absolute timing
    notes = []  # list of dicts: start_tick, end_tick, pitch, velocity
    active = {}  # pitch -> (start_tick, velocity)
    abs_tick = 0
    meta_msgs = []
    for msg in src:
        abs_tick += msg.time
        if msg.is_meta:
            meta_msgs.append((abs_tick, msg))
        elif msg.type == 'note_on' and msg.velocity > 0:
            active[msg.note] = (abs_tick, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active:
                start, vel = active.pop(msg.note)
                notes.append({'start': start, 'end': abs_tick, 'pitch': msg.note, 'vel': vel})

    # Build time-slice grid. For each grid tick, find the highest active note.
    # Then keep only "transitions" where the top note changes.
    if not notes:
        print(f'no notes in track {track_idx}'); return
    notes.sort(key=lambda n: n['start'])
    # Find all event times
    events = sorted({n['start'] for n in notes} | {n['end'] for n in notes})
    top_segments = []  # list of (start, end, pitch, vel)
    for i in range(len(events) - 1):
        t_start, t_end = events[i], events[i+1]
        # Active notes at t_start
        actives = [n for n in notes if n['start'] <= t_start < n['end']]
        if not actives: continue
        top = max(actives, key=lambda n: n['pitch'])
        # Merge into previous if same pitch
        if top_segments and top_segments[-1][2] == top['pitch'] and top_segments[-1][1] == t_start:
            top_segments[-1] = (top_segments[-1][0], t_end, top['pitch'], top_segments[-1][3])
        else:
            top_segments.append((t_start, t_end, top['pitch'], top['vel']))

    # Write new MIDI with just the top line
    new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    new_track = mido.MidiTrack()
    # Include meta
    msgs_with_tick = list(meta_msgs)
    for s, e, p, v in top_segments:
        msgs_with_tick.append((s, mido.Message('note_on', note=p, velocity=v, time=0)))
        msgs_with_tick.append((e, mido.Message('note_off', note=p, velocity=0, time=0)))
    msgs_with_tick.sort(key=lambda x: x[0])
    prev = 0
    for t, m in msgs_with_tick:
        m2 = m.copy(time=t - prev)
        new_track.append(m2)
        prev = t
    new_mid.tracks.append(new_track)
    new_mid.save(out_path)
    print(f'  → {out_path}: {len(top_segments)} top-line notes (from {len(notes)} total)')


if __name__ == '__main__':
    # Default: extract top line from Mr. Jones track 1 (Clean Guitar)
    extract_top_line(
        '/Users/robert/Desktop/midis/counting_crows_mr_jones.mid',
        1,
        '/Users/robert/Desktop/midis/counting_crows_mr_jones_topline.mid')
