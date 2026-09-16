"""Generate 10 mashup songs from Beatles + Guitar 50-250 sources.

Each mashup:
- Random tempo from {75, 90, 105, 120, 135, 150, 165, 180}
- Random bar count from {8, 10, 12, 14, 16, 24}
- 9 in 4/4, 1 in 3/4
- Chord progression from one source song's section
- Melody rhythm from a different source song's section
- Fresh pitches generated to fit the chord progression

Outputs paste-JSON files to ~/Desktop/mashups/ — ready to paste into Hookpad.
"""
import os, json, random, re, hashlib
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

TEMPOS = [75, 90, 105, 120, 135, 150, 165, 180]
BARS_CHOICES = [8, 10, 12, 14, 16, 24]
OUT_DIR = os.path.expanduser('~/Desktop/mashups')
MUSIC_DIR = '/Users/robert/Desktop/glowinggardens_claude/_music'
EXCLUDE_SECS = {'intro','outro','solo','instrumental','interlude','break','tag','coda','ending','section','instrumental bridge'}


# ============================================================
# 1. Load source pool: Beatles + Guitar 50-250
# ============================================================

def extract_var_list(path, var_name):
    """Parse a rebuild script and pull (title, artist) tuples from a named variable."""
    src = open(path).read()
    m = re.search(rf'{var_name}\s*=\s*\[(.+?)\n\]', src, re.DOTALL)
    if not m: return []
    return re.findall(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', m.group(1))


def load_source_titles():
    """Return list of (title, artist) — Beatles handled separately as a query."""
    sources = []
    sources.extend(extract_var_list(f'{MUSIC_DIR}/rebuild_studied_songs.py', 'USER_LIST'))
    sources.extend(extract_var_list(f'{MUSIC_DIR}/rebuild_guitar150.py', 'USER_LIST_2'))
    sources.extend(extract_var_list(f'{MUSIC_DIR}/rebuild_guitar150.py', 'USER_LIST_3'))
    sources.extend(extract_var_list(f'{MUSIC_DIR}/rebuild_guitar200.py', 'USER_LIST_4'))
    sources.extend(extract_var_list(f'{MUSIC_DIR}/rebuild_guitar250.py', 'USER_LIST_5'))
    return sources


def fetch_source_songs():
    print("loading source pool (Beatles + Guitar 50-250)...")
    # Beatles
    beatles = SB.schema('parcels').table('songs').select(
        'artist,title,key_tonic,key_scale,hookpad_json'
    ).ilike('artist', '%beatles%').not_.is_('hookpad_json','null').execute().data
    print(f"  Beatles songs: {len(beatles)}")
    songs = list(beatles)
    # Guitar 50-250
    titles = load_source_titles()
    print(f"  Guitar 50-250 entries to resolve: {len(titles)}")
    resolved = 0
    for title_sub, artist_sub in titles:
        rows = SB.schema('parcels').table('songs').select(
            'artist,title,key_tonic,key_scale,hookpad_json'
        ).ilike('title', f'%{title_sub}%').ilike('artist', f'%{artist_sub}%')\
         .not_.is_('hookpad_json','null').limit(1).execute().data
        if rows:
            songs.append(rows[0])
            resolved += 1
    print(f"  resolved: {resolved}/{len(titles)} Guitar entries")
    # Dedupe
    seen = set(); out = []
    for s in songs:
        k = ((s['artist'] or '').lower().strip(), (s['title'] or '').lower().strip())
        if k in seen: continue
        seen.add(k); out.append(s)
    print(f"  TOTAL source pool: {len(out)} unique songs\n")
    return out


# ============================================================
# 2. Extract usable sections from sources
# ============================================================

def extract_sections(song):
    """Return list of dicts with chords and notes per section, plus meter."""
    hj = song['hookpad_json']
    if isinstance(hj, str): hj = json.loads(hj)
    if not hj: return []
    bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
    secs = hj.get('sections') or []
    chords = hj.get('chords') or []
    notes = hj.get('notes') or (hj.get('polyphonicNotes') or [[]])[0]
    end_beat = hj.get('endBeat') or 1
    out = []
    for i, sec in enumerate(secs):
        name = (sec.get('name','') or '').strip()
        if name.lower() in EXCLUDE_SECS: continue
        s_beat = sec.get('beat', 1)
        e_beat = secs[i+1]['beat'] if i+1 < len(secs) else end_beat
        bars = round((e_beat - s_beat) / bpb, 2)
        if bars < 4: continue
        sec_chords = [c for c in chords if s_beat <= c.get('beat',0) < e_beat]
        sec_notes = sorted(
            (n for n in notes if s_beat <= n.get('beat',0) < e_beat and not n.get('isRest')),
            key=lambda n: n['beat']
        )
        if len(sec_chords) < 2 or len(sec_notes) < 6: continue
        # Normalize beats to start at 0 (in beats)
        chords_norm = []
        for c in sec_chords:
            chords_norm.append({
                'root': c.get('root', 1),
                'type': c.get('type', 5),
                'beat': c['beat'] - s_beat,
                'duration': c.get('duration', bpb),
                'applied': c.get('applied', 0),
                'borrowed': c.get('borrowed', ''),
                'adds': c.get('adds', []) or [],
                'omits': c.get('omits', []) or [],
                'alterations': c.get('alterations', []) or [],
                'suspensions': c.get('suspensions', []) or [],
            })
        notes_norm = []
        for n in sec_notes:
            notes_norm.append({
                'beat': n['beat'] - s_beat,
                'duration': n.get('duration', 0.5),
                'sd': n.get('sd', '1'),
                'octave': n.get('octave', 0),
            })
        out.append({
            'name': name,
            'bars': bars,
            'bpb': bpb,
            'chords': chords_norm,
            'notes': notes_norm,
        })
    return out


# ============================================================
# 3. Adapt source sections to target bar count
# ============================================================

def tile_chords(source_chords, source_bars, target_beats, source_bpb):
    """Tile/truncate source chord progression to fill target_beats."""
    out = []
    src_total = source_bars * source_bpb
    beat = 0
    while beat < target_beats:
        for c in source_chords:
            new_beat = beat + c['beat']
            if new_beat >= target_beats: break
            out.append({**c, 'beat': new_beat})
        beat += src_total
    # Trim chord durations that extend past target
    for c in out:
        if c['beat'] + c['duration'] > target_beats:
            c['duration'] = target_beats - c['beat']
    return [c for c in out if c['duration'] > 0]


def tile_notes(source_notes, source_bars, target_beats, source_bpb, target_bpb):
    """Tile source rhythm; if meter differs, scale durations by target_bpb/source_bpb."""
    scale = target_bpb / source_bpb if target_bpb != source_bpb else 1.0
    out = []
    src_total = source_bars * source_bpb
    beat = 0
    while beat < target_beats:
        for n in source_notes:
            new_beat = beat + n['beat'] * scale
            new_dur = n['duration'] * scale
            if new_beat >= target_beats: break
            out.append({'beat': new_beat, 'duration': new_dur,
                        'octave': n['octave']})
        beat += src_total * scale
    # Truncate trailing notes
    for n in out:
        if n['beat'] + n['duration'] > target_beats:
            n['duration'] = max(0.25, target_beats - n['beat'])
    return [n for n in out if n['beat'] < target_beats]


# ============================================================
# 4. Generate fresh melody pitches that fit chord progression
# ============================================================

CHORD_TONES = {  # scale-degree-of-chord-root → (root, 3rd, 5th, 7th) as scale-degree-of-key
    # For triads in major key
    1: ['1', '3', '5'],
    2: ['2', '4', '6'],
    3: ['3', '5', '7'],
    4: ['4', '6', '1'],
    5: ['5', '7', '2'],
    6: ['6', '1', '3'],
    7: ['7', '2', '4'],
}
SCALE_TONES = ['1', '2', '3', '4', '5', '6', '7']


def active_chord_at(chords, beat):
    """Return the chord active at this beat, or None."""
    for c in chords:
        if c['beat'] <= beat < c['beat'] + c['duration']:
            return c
    return chords[-1] if chords else None


def assign_pitches(notes, chords, rng):
    """For each note, pick a scale degree based on the active chord."""
    out = []
    prev_sd = None
    for n in notes:
        chord = active_chord_at(chords, n['beat'])
        if chord is None:
            sd = rng.choice(['1', '3', '5'])
        else:
            # 65% chord tone, 35% scale tone — biased to nearby scale degrees
            if rng.random() < 0.65:
                tones = CHORD_TONES.get(chord['root'], ['1', '3', '5'])
                sd = rng.choice(tones)
            else:
                sd = rng.choice(SCALE_TONES)
            # Bias toward staying close to previous pitch (smoother contour)
            if prev_sd is not None and rng.random() < 0.5:
                # snap to adjacent scale degree
                candidates = ['1','2','3','4','5','6','7']
                pi = candidates.index(prev_sd) if prev_sd in candidates else 0
                near = [candidates[max(0,pi-1)], candidates[pi], candidates[min(6,pi+1)]]
                sd = rng.choice(near)
        out.append({**n, 'sd': sd})
        prev_sd = sd if sd in SCALE_TONES else prev_sd
    return out


# ============================================================
# 5. Build Hookpad paste-JSON
# ============================================================

CHORD_KEY_ORDER = ['root','beat','duration','type','inversion','applied','adds','omits',
                   'alterations','suspensions','substitutions','pedal','alternate',
                   'borrowed','isRest','recordingEndBeat']


def hookpad_chord(c):
    """Emit chord with strict key order per the paste-JSON spec."""
    full = {
        'root': c['root'],
        'beat': c['beat'] + 1,   # Hookpad uses 1-indexed beats
        'duration': float(c['duration']),
        'type': int(c.get('type', 5)),
        'inversion': 0,
        'applied': c.get('applied', 0),
        'adds': c.get('adds', []),
        'omits': c.get('omits', []),
        'alterations': c.get('alterations', []),
        'suspensions': c.get('suspensions', []),
        'substitutions': [],
        'pedal': None,
        'alternate': '',
        'borrowed': c.get('borrowed', ''),
        'isRest': False,
        'recordingEndBeat': None,
    }
    out = {}
    for k in CHORD_KEY_ORDER:
        out[k] = full[k]
    return out


def hookpad_note(n):
    return {
        'sd': n['sd'],
        'octave': n['octave'],
        'beat': n['beat'] + 1,    # 1-indexed
        'duration': float(n['duration']),
        'isRest': False,
        'recordingEndBeat': None,
    }


def make_paste_json(chords, notes):
    obj = {
        'notes':       [hookpad_note(n) for n in notes],
        'chords':      [hookpad_chord(c) for c in chords],
        'audioTracks': [],
        'version':     1,    # bypasses fp validation
    }
    return obj


# ============================================================
# 6. Generate one mashup
# ============================================================

def generate_mashup(idx, sources, rng, force_three_four=False):
    bpb = 3 if force_three_four else 4
    tempo = rng.choice(TEMPOS)
    bars = rng.choice(BARS_CHOICES)
    target_beats = bars * bpb

    # Pick chord source & melody source (different songs)
    pool = list(sources)
    rng.shuffle(pool)
    chord_src = None; melody_src = None
    chord_sec = None; melody_sec = None
    for s in pool:
        secs = extract_sections(s)
        if not secs: continue
        if chord_src is None:
            chord_src = s; chord_sec = rng.choice(secs); continue
        if melody_src is None and s != chord_src:
            melody_src = s; melody_sec = rng.choice(secs); break
    if chord_sec is None or melody_sec is None:
        return None

    # Tile chord progression and melody rhythm to fill target bars
    chords_out = tile_chords(chord_sec['chords'], chord_sec['bars'], target_beats, chord_sec['bpb'])
    notes_in = tile_notes(melody_sec['notes'], melody_sec['bars'], target_beats,
                          melody_sec['bpb'], bpb)
    notes_out = assign_pitches(notes_in, chords_out, rng)

    # Build paste-JSON
    obj = make_paste_json(chords_out, notes_out)

    # Metadata for the filename / readme
    meta = {
        'idx': idx,
        'tempo': tempo,
        'bars': bars,
        'meter': f"{bpb}/4",
        'chord_source':  f"{chord_src['artist']} — {chord_src['title']} [{chord_sec['name']}]",
        'melody_source': f"{melody_src['artist']} — {melody_src['title']} [{melody_sec['name']}]",
        'n_chords': len(chords_out),
        'n_notes': len(notes_out),
    }
    return obj, meta


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sources = fetch_source_songs()
    rng = random.Random(20260601)

    summaries = []
    print(f"generating 10 mashups → {OUT_DIR}\n")
    three_four_idx = rng.randint(0, 9)
    for i in range(10):
        result = generate_mashup(i+1, sources, rng, force_three_four=(i == three_four_idx))
        if result is None:
            print(f"  [{i+1}/10] FAILED — couldn't pick sources"); continue
        obj, meta = result
        # Save paste-blob as .txt (user preference: paste content always .txt)
        out_path = os.path.join(OUT_DIR, f"mashup-{i+1:02d}.txt")
        with open(out_path, 'w') as fh:
            json.dump(obj, fh, separators=(',',':'))
        # Save metadata (also .txt per user preference)
        meta_path = os.path.join(OUT_DIR, f"mashup-{i+1:02d}.meta.txt")
        with open(meta_path, 'w') as fh:
            json.dump(meta, fh, indent=2)
        summaries.append(meta)
        print(f"  [{i+1}/10] tempo={meta['tempo']} bars={meta['bars']} {meta['meter']}  "
              f"chords={meta['n_chords']} notes={meta['n_notes']}")
        print(f"         chords ← {meta['chord_source']}")
        print(f"         melody ← {meta['melody_source']}")

    # Write a top-level summary (also .txt per user preference)
    with open(os.path.join(OUT_DIR, 'SUMMARY.txt'), 'w') as fh:
        json.dump(summaries, fh, indent=2)
    print(f"\nsummary → {OUT_DIR}/SUMMARY.txt")
    print(f"\nTo use: open a blank Hookpad tab → paste any mashup-NN.json content")


if __name__ == '__main__':
    main()
