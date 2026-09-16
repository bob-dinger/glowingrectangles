"""Isolate the melody track from every MIDI in ~/Desktop/dylan_midis/ into a
melodies/ subfolder (single-track MIDIs for Hookpad import). Flags low-confidence
picks so you know which to eyeball.
"""
import os, glob
from collections import defaultdict
import mido
from midi_melody_extract import score_track, monophony_ratio
from beatles_cover_melody_midis import meta_track

SRC = os.path.expanduser('~/Desktop/dylan_midis')
OUT = os.path.join(SRC, 'melodies')
os.makedirs(OUT, exist_ok=True)

def split_by_channel(track):
    """Type-0 MIDIs merge every channel into one track. Split note events back out
    by channel (drums=9 dropped) so each channel can be scored as its own track."""
    abs_t = 0
    perch = defaultdict(list)
    for msg in track:
        abs_t += msg.time
        if msg.type in ('note_on', 'note_off') and hasattr(msg, 'channel') and msg.channel != 9:
            perch[msg.channel].append((abs_t, msg))
    out = []
    for ch, events in sorted(perch.items()):
        tr = mido.MidiTrack(); prev = 0
        for at, msg in events:
            tr.append(msg.copy(time=at - prev)); prev = at
        tr.append(mido.MetaMessage('end_of_track', time=0))
        out.append(tr)
    return out

def process(path):
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    cand = mid.tracks
    if mid.type == 0 and len(mid.tracks) == 1:
        cand = split_by_channel(mid.tracks[0]) or mid.tracks
    scored = [score_track(tr, tpb) for tr in cand]
    best = max(range(len(scored)), key=lambda i: scored[i][0])
    sc, notes = scored[best]
    if sc < 0 or not notes:
        return None
    name = ' '.join(m.name for m in cand[best] if m.type == 'track_name') or '(unnamed)'
    named = any(k in name.lower() for k in ('vocal', 'melody', 'lead', 'voice', 'sing'))
    mono = monophony_ratio(notes)
    new = mido.MidiFile(ticks_per_beat=tpb)
    new.tracks.append(meta_track(mid))
    new.tracks.append(cand[best])
    base = os.path.basename(path)[:-4]
    new.save(os.path.join(OUT, base + '_melody.mid'))
    # quality flag
    if named and mono >= 0.6 and 60 <= len(notes) <= 500: q = 'good'
    elif named or (mono >= 0.85 and 60 <= len(notes) <= 500): q = 'ok'
    else: q = 'check'
    return q, name, sc, len(notes), mono

def main():
    rows = []
    for p in sorted(glob.glob(SRC + '/*.mid')):
        try:
            r = process(p)
        except Exception as e:
            rows.append((os.path.basename(p)[:-4], 'ERR', str(e)[:30], 0, 0, 0)); continue
        if r:
            rows.append((os.path.basename(p)[:-4], *r))
        else:
            rows.append((os.path.basename(p)[:-4], 'none', '-', 0, 0, 0))
    order = {'good': 0, 'ok': 1, 'check': 2}
    rows.sort(key=lambda r: (order.get(r[1], 3), r[0]))
    print(f"{'FLAG':6} {'SONG':34} {'TRACK':20} notes mono")
    for song, q, name, sc, nn, mono in rows:
        print(f"{q:6} {song[:34]:34} {str(name)[:20]:20} {nn:>5} {mono:.0%}" if isinstance(mono, float) else f"{q:6} {song}")
    good = sum(1 for r in rows if r[1] == 'good'); ok = sum(1 for r in rows if r[1] == 'ok')
    print(f"\n{good} good, {ok} ok, {len(rows)-good-ok} to check  -> {OUT}")

if __name__ == '__main__':
    main()
