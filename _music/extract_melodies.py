"""Extract per-section melody sequences from Hookpad data.

Hookpad notes are stored as scale-degree strings (`sd`: '1'..'7' with possible 'b'/'#' accidentals)
plus a relative `octave` integer. This is already key-agnostic, so motifs match across songs
regardless of key.

For each section in a song this produces:
    - notes_raw:      list of note dicts (with isRest, beat, duration, sd, octave)
    - sd_seq:         scale-degree-only sequence ['3','3','5','6','2',...] (rests dropped)
    - sd_oct_seq:     (sd, octave) tuples — distinguishes high vs low same-degree notes
    - interval_seq:   semitone deltas between consecutive notes — transposition-invariant
    - rhythm_seq:     durations of the kept notes (beats)
    - skeleton_seq:   subset of sd_seq for "structural" notes (duration > 1 beat OR on beat 1)
    - bars:           section length in bars
    - n_notes:        non-rest note count

Usage:
    from extract_melodies import extract_song_melodies
    for sec in extract_song_melodies(hookpad_json):
        print(sec['name'], sec['sd_seq'][:8])
"""
import os, json
from typing import Iterator

# Scale-degree string → semitones from tonic (major-mode reference)
SD_TO_SEMI = {
    '1': 0, 'b2': 1, '2': 2, 'b3': 3, '3': 4, '4': 5, '#4': 6,
    'b5': 6, '5': 7, 'b6': 8, '6': 9, 'b7': 10, '7': 11,
}
# Minor-mode reference (rare — hookpad usually stores sd in major-relative form even for minor songs)
SD_TO_SEMI_MINOR = {
    '1': 0, 'b2': 1, '2': 2, '3': 3, '4': 5, '#4': 6,
    'b5': 6, '5': 7, '6': 8, 'b7': 10, '7': 11,
}


def sd_to_semitones(sd: str, scale: str = 'major') -> int:
    """Convert a Hookpad scale-degree token to semitones-from-tonic."""
    if sd in SD_TO_SEMI:
        return SD_TO_SEMI[sd]
    # Fallback: strip accidental
    if sd and sd[0] in 'b#' and sd[1:] in SD_TO_SEMI:
        base = SD_TO_SEMI[sd[1:]]
        return (base + (-1 if sd[0] == 'b' else 1)) % 12
    return 0  # unparseable → tonic


def note_semitone(note: dict, scale: str = 'major') -> int:
    """Absolute semitone offset including octave (relative to song's tonic at octave 0)."""
    return sd_to_semitones(note.get('sd', '1'), scale) + 12 * (note.get('octave') or 0)


def is_structural(note: dict, beats_per_bar: int) -> bool:
    """Per the existing skeleton rule: duration > 1 beat OR on beat 1 of a bar."""
    dur = note.get('duration', 0)
    if dur > 1:
        return True
    beat = note.get('beat', 0)
    # beat-in-bar: beat is song-absolute, so check (beat - 1) % bpb == 0 (1-indexed beats)
    return ((beat - 1) % beats_per_bar) == 0


def _find_pickup_notes(prev_sec_notes, long_threshold=2.0):
    """Return notes at the end of `prev_sec_notes` that should bleed forward into the
    NEXT section. Rule: take any notes that come AFTER the last non-rest note with
    duration >= long_threshold. That long note marks the end of the previous section's
    melodic phrase, so anything after it is pickup material for the next section.

    If the previous section has no long-duration note, OR the last long note is the
    final note (no pickups), return [].
    """
    if not prev_sec_notes: return []
    last_long_idx = -1
    for i in range(len(prev_sec_notes) - 1, -1, -1):
        n = prev_sec_notes[i]
        if not n.get('isRest') and n.get('duration', 0) >= long_threshold:
            last_long_idx = i
            break
    if last_long_idx == -1 or last_long_idx == len(prev_sec_notes) - 1:
        return []
    pickups = [n for n in prev_sec_notes[last_long_idx + 1:] if not n.get('isRest')]
    return pickups


def extract_song_melodies(hookpad_json, include_pickups=True) -> Iterator[dict]:
    """Yield one dict per section, each with the melody representations described in the docstring.

    If include_pickups=True (default), notes at the very end of the previous section
    that come after a >=2-beat note get included at the start of the next section.
    These bleed-in notes are marked with `_is_pickup=True`.
    """
    if isinstance(hookpad_json, str):
        hookpad_json = json.loads(hookpad_json)
    if not hookpad_json:
        return
    hj = hookpad_json
    notes = hj.get('notes') or []
    secs  = hj.get('sections') or []
    end_beat = hj.get('endBeat') or 1
    bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
    scale = (hj.get('keys') or [{}])[0].get('scale', 'major')

    # If no sections defined, treat the whole song as one section
    if not secs:
        secs = [{'name': '(whole song)', 'beat': 1}]

    for i, sec in enumerate(secs):
        s_beat = sec.get('beat', 1)
        e_beat = secs[i + 1]['beat'] if i + 1 < len(secs) else end_beat
        sec_notes = [n for n in notes if s_beat <= n.get('beat', 0) < e_beat]

        # Bleed-in pickups from the previous section.
        # These notes' beats remain at their original (pre-s_beat) positions; downstream
        # code treats them as anacrusis (rel_beat < 0).
        if include_pickups and i > 0:
            prev_s_beat = secs[i - 1].get('beat', 1)
            prev_sec_notes = [n for n in notes if prev_s_beat <= n.get('beat', 0) < s_beat]
            pickups = _find_pickup_notes(prev_sec_notes)
            for p in pickups:
                p_copy = dict(p)
                p_copy['_is_pickup'] = True
                sec_notes.insert(0, p_copy)

        # Active (non-rest) notes only, in melodic order
        active = [n for n in sec_notes if not n.get('isRest')]
        sd_seq      = [n.get('sd', '?') for n in active]
        sd_oct_seq  = [(n.get('sd', '?'), n.get('octave', 0)) for n in active]
        rhythm_seq  = [n.get('duration', 0) for n in active]
        semis       = [note_semitone(n, scale) for n in active]
        interval_seq = [semis[k + 1] - semis[k] for k in range(len(semis) - 1)]
        skeleton    = [n.get('sd', '?') for n in active if is_structural(n, bpb)]

        yield {
            'index':       i,
            'name':        (sec.get('name') or f'section {i + 1}').strip(),
            's_beat':      s_beat,
            'e_beat':      e_beat,
            'bars':        round((e_beat - s_beat) / bpb, 2),
            'n_notes':     len(active),
            'n_rests':     len(sec_notes) - len(active),
            'notes_raw':   sec_notes,
            'sd_seq':      sd_seq,
            'sd_oct_seq':  sd_oct_seq,
            'rhythm_seq':  rhythm_seq,
            'interval_seq': interval_seq,
            'skeleton_seq': skeleton,
        }


def main():
    """CLI: python extract_melodies.py <title-substring> [--artist X]"""
    import argparse, sys
    from dotenv import load_dotenv
    load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
    from supabase import create_client

    ap = argparse.ArgumentParser()
    ap.add_argument('title')
    ap.add_argument('--artist', default=None)
    args = ap.parse_args()

    SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    q = SB.schema('parcels').table('songs').select(
        'artist,title,key_tonic,key_scale,bpm,hookpad_json'
    ).ilike('title', f'%{args.title}%')
    if args.artist:
        q = q.ilike('artist', f'%{args.artist}%')
    rows = q.limit(5).execute().data
    if not rows:
        sys.exit(f"no song matches {args.title!r}")
    s = rows[0]
    print(f"=== {s['artist']} - {s['title']}  ({s['key_tonic']} {s['key_scale']}, {s['bpm']} BPM) ===\n")

    for sec in extract_song_melodies(s['hookpad_json']):
        if sec['n_notes'] == 0:
            continue
        print(f"[{sec['name']}]  {sec['bars']} bars · {sec['n_notes']} notes")
        # Compact sd display: join by spaces, dim octave-0 absent
        sd_str = ' '.join(sec['sd_seq'][:24])
        if len(sec['sd_seq']) > 24: sd_str += ' …'
        print(f"  sd:       {sd_str}")
        sk_str = ' '.join(sec['skeleton_seq'][:16])
        if len(sec['skeleton_seq']) > 16: sk_str += ' …'
        print(f"  skeleton: {sk_str}")
        print()


if __name__ == '__main__':
    main()
