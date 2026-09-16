"""For Format 0 single-track MIDIs, split by MIDI channel.
Each channel becomes its own track in the output, and we also write per-channel files
so you can audition each in GarageBand and pick the vocal/melody one.
"""
import os, sys
import mido
from collections import defaultdict

GM_NAMES = [
    'Acoustic Grand Piano','Bright Acoustic Piano','Electric Grand','Honky-tonk',
    'Electric Piano 1','Electric Piano 2','Harpsichord','Clavinet',
    'Celesta','Glockenspiel','Music Box','Vibraphone','Marimba','Xylophone','Tubular Bells','Dulcimer',
    'Drawbar Organ','Percussive Organ','Rock Organ','Church Organ','Reed Organ','Accordion','Harmonica','Tango Accordion',
    'Acoustic Guitar (nylon)','Acoustic Guitar (steel)','Electric Guitar (jazz)','Electric Guitar (clean)','Electric Guitar (muted)','Overdriven Guitar','Distortion Guitar','Guitar Harmonics',
    'Acoustic Bass','Electric Bass (finger)','Electric Bass (pick)','Fretless Bass','Slap Bass 1','Slap Bass 2','Synth Bass 1','Synth Bass 2',
    'Violin','Viola','Cello','Contrabass','Tremolo Strings','Pizzicato Strings','Orchestral Harp','Timpani',
    'String Ensemble 1','String Ensemble 2','SynthStrings 1','SynthStrings 2','Choir Aahs','Voice Oohs','Synth Voice','Orchestra Hit',
    'Trumpet','Trombone','Tuba','Muted Trumpet','French Horn','Brass Section','SynthBrass 1','SynthBrass 2',
    'Soprano Sax','Alto Sax','Tenor Sax','Baritone Sax','Oboe','English Horn','Bassoon','Clarinet',
    'Piccolo','Flute','Recorder','Pan Flute','Blown Bottle','Shakuhachi','Whistle','Ocarina',
    'Lead 1 (square)','Lead 2 (sawtooth)','Lead 3 (calliope)','Lead 4 (chiff)','Lead 5 (charang)','Lead 6 (voice)','Lead 7 (fifths)','Lead 8 (bass + lead)',
    'Pad 1 (new age)','Pad 2 (warm)','Pad 3 (polysynth)','Pad 4 (choir)','Pad 5 (bowed)','Pad 6 (metallic)','Pad 7 (halo)','Pad 8 (sweep)',
] + [f'GM #{i}' for i in range(96, 128)]


def split(midi_path):
    mid = mido.MidiFile(midi_path)
    if len(mid.tracks) != 1:
        print(f'{os.path.basename(midi_path)}: not single-track, skipping')
        return

    src = mid.tracks[0]

    # Collect per-channel info
    channel_msgs = defaultdict(list)  # channel -> list of (abs_tick, msg)
    meta_msgs = []  # (abs_tick, msg) for global meta (tempo, time-sig, etc.)
    abs_tick = 0
    for msg in src:
        abs_tick += msg.time
        if msg.is_meta:
            meta_msgs.append((abs_tick, msg))
        elif hasattr(msg, 'channel'):
            channel_msgs[msg.channel].append((abs_tick, msg))

    # Per-channel stats
    print(f'\n{"="*60}\n{os.path.basename(midi_path)}: {len(channel_msgs)} channels')
    channel_info = {}
    for ch, msgs in sorted(channel_msgs.items()):
        notes = [m for _, m in msgs if m.type == 'note_on' and m.velocity > 0]
        if not notes:
            continue
        pitches = [n.note for n in notes]
        # Find program change
        program = next((m.program for _, m in msgs if m.type == 'program_change'), 0)
        # Detect monophonic-ness
        events = sorted([(t, m) for t, m in msgs if m.type in ('note_on', 'note_off')], key=lambda x: x[0])
        active = 0
        max_active = 0
        for t, m in events:
            if m.type == 'note_on' and m.velocity > 0:
                active += 1
                max_active = max(max_active, active)
            elif m.type == 'note_off' or (m.type == 'note_on' and m.velocity == 0):
                if active > 0: active -= 1
        inst = 'DRUMS' if ch == 9 else GM_NAMES[program] if program < len(GM_NAMES) else f'#{program}'
        avg = sum(pitches) / len(pitches)
        print(f'  ch {ch:>2}: {inst[:30]:30} notes={len(notes):>4} pitch={min(pitches):>3}-{max(pitches):>3} '
              f'avg={avg:>4.1f} max_concurrent={max_active}')
        channel_info[ch] = {'inst': inst, 'avg': avg, 'count': len(notes),
                            'max_concurrent': max_active, 'is_drum': (ch == 9)}

    # Write per-channel MIDI files
    base = midi_path.replace('.mid', '')
    for ch, info in channel_info.items():
        if info['is_drum']: continue  # skip drums
        if info['count'] < 10: continue
        # Build a track with this channel's events + global meta
        new_track = mido.MidiTrack()
        # Get all events for this channel + meta events
        events = []
        for t, m in meta_msgs:
            events.append((t, m))
        for t, m in channel_msgs[ch]:
            events.append((t, m))
        events.sort(key=lambda x: x[0])
        # Convert absolute back to delta
        prev_tick = 0
        for t, m in events:
            new_track.append(m.copy(time=t - prev_tick))
            prev_tick = t
        new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        new_mid.tracks.append(new_track)
        safe_inst = info['inst'].lower().replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')[:25]
        out = f'{base}_ch{ch}_{safe_inst}.mid'
        new_mid.save(out)
        print(f'    → {os.path.basename(out)}')

    # Also auto-pick the most-likely melody channel: monophonic + mid-to-high register, not drums
    candidates = [(ch, i) for ch, i in channel_info.items()
                  if not i['is_drum'] and i['max_concurrent'] <= 2 and 50 <= i['avg'] <= 85]
    candidates.sort(key=lambda x: -x[1]['avg'])  # prefer higher avg pitch
    if candidates:
        ch, i = candidates[0]
        print(f'  → BEST GUESS: channel {ch} ({i["inst"]}) avg pitch {i["avg"]:.1f}')
    else:
        print(f'  ⚠ no clean monophonic channel — vocal might be polyphonic or use chords')


if __name__ == '__main__':
    paths = sys.argv[1:] if len(sys.argv) > 1 else [
        '/Users/robert/Desktop/midis/no_doubt_its_my_life.mid',
        '/Users/robert/Desktop/midis/steve_miller_band_jet_airliner.mid',
    ]
    for p in paths:
        split(p)
