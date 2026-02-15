#!/usr/bin/env python3
"""
Song Browser — local web app for browsing ~1000 hookpad songs.
Run: python3 song_browser.py
Open: http://localhost:8080
"""

import json
import os
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
HOOKPAD_DIR = "/Users/robert/Desktop/hookpad_songs/hookpad_songs"
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "song-browser.html")
STATIC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# Cached on startup
_song_database = None

def parse_filename(filename):
    """Extract artist and title from filename like 'beatles_Day Tripper_o_.json'"""
    name = filename.replace('.json', '')
    # Remove trailing flags like _o_, _ly, _ly_o_, etc.
    import re
    name = re.sub(r'(_o_|_ly_o_|_ly|_j_|_nv_|_v_)*$', '', name)
    parts = name.split('_', 1)
    if len(parts) == 2:
        artist, title = parts
        return artist.title(), title.title()
    return '', name.title()

def scan_songs_directory():
    """Scan HOOKPAD_DIR and build song list from JSON files."""
    songs = []
    for filename in os.listdir(HOOKPAD_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(HOOKPAD_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)

            artist, title = parse_filename(filename)

            # Extract key info
            keys = data.get('keys', [])
            key_info = keys[0] if keys else {}
            tonic = key_info.get('tonic', 'C')
            scale = key_info.get('scale', 'major')
            key_str = f"{tonic} {scale}"

            # Extract tempo
            tempos = data.get('tempos', [])
            bpm = tempos[0].get('bpm', 120) if tempos else 120

            # Extract duration
            end_beat = data.get('endBeat', 0)
            duration_sec = int((end_beat / bpm) * 60) if bpm else 0

            # Count measures (assuming 4/4)
            total_measures = end_beat // 4 if end_beat else 0

            has_chords = bool(data.get('chords'))
            has_melody = bool(data.get('notes'))

            if has_chords:
                status = 'complete' if has_melody else 'chords_only'
            else:
                status = 'melody_only' if has_melody else 'empty'

            songs.append({
                'title': title,
                'artist': artist,
                'filename': filename,
                'key': key_str,
                'bpm': bpm,
                'duration_sec': duration_sec,
                'total_measures': total_measures,
                'has_chords': has_chords,
                'has_melody': has_melody,
                'status': status,
                'structure': [],
                'notes': ''
            })
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"Skipping {filename}: {e}")
            continue

    # Sort by artist, then title
    songs.sort(key=lambda s: (s['artist'].lower(), s['title'].lower()))
    return songs

# ── Scale / chord constants ──────────────────────────────────────────

MAJOR_SCALE = {
    "C":  ["C",  "D",  "E",  "F",  "G",  "A",  "B"],
    "C#": ["C#", "D#", "E#", "F#", "G#", "A#", "B#"],
    "Db": ["Db", "Eb", "F",  "Gb", "Ab", "Bb", "C"],
    "D":  ["D",  "E",  "F#", "G",  "A",  "B",  "C#"],
    "Eb": ["Eb", "F",  "G",  "Ab", "Bb", "C",  "D"],
    "E":  ["E",  "F#", "G#", "A",  "B",  "C#", "D#"],
    "F":  ["F",  "G",  "A",  "Bb", "C",  "D",  "E"],
    "F#": ["F#", "G#", "A#", "B",  "C#", "D#", "E#"],
    "Gb": ["Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"],
    "G":  ["G",  "A",  "B",  "C",  "D",  "E",  "F#"],
    "Ab": ["Ab", "Bb", "C",  "Db", "Eb", "F",  "G"],
    "A":  ["A",  "B",  "C#", "D",  "E",  "F#", "G#"],
    "Bb": ["Bb", "C",  "D",  "Eb", "F",  "G",  "A"],
    "B":  ["B",  "C#", "D#", "E",  "F#", "G#", "A#"],
}

# Chromatic note order for computing intervals
CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ENHARMONIC = {
    "Db": "C#", "Eb": "D#", "E#": "F", "Fb": "E", "Gb": "F#",
    "Ab": "G#", "Bb": "A#", "B#": "C", "Cb": "B",
}

# Diatonic qualities in major: I=maj ii=min iii=min IV=maj V=maj vi=min vii°=dim
MAJOR_DIATONIC = {1: "", 2: "m", 3: "m", 4: "", 5: "", 6: "m", 7: "dim"}

# Natural minor diatonic: i=min ii°=dim III=maj iv=min v=min VI=maj VII=maj
MINOR_DIATONIC = {1: "m", 2: "dim", 3: "", 4: "m", 5: "m", 6: "", 7: ""}

# Mode intervals (semitones from root for each degree 1-7)
MODE_INTERVALS = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "minor":            [0, 2, 3, 5, 7, 8, 10],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "locrian":          [0, 1, 3, 5, 6, 8, 10],
    "harmonicMinor":    [0, 2, 3, 5, 7, 8, 11],
    "phrygianDominant": [0, 1, 4, 5, 7, 8, 10],
}

# Diatonic qualities per mode (determined by interval pattern)
MODE_DIATONIC = {
    "major":            {1: "", 2: "m", 3: "m", 4: "", 5: "", 6: "m", 7: "dim"},
    "minor":            {1: "m", 2: "dim", 3: "", 4: "m", 5: "m", 6: "", 7: ""},
    "dorian":           {1: "m", 2: "m", 3: "", 4: "", 5: "m", 6: "dim", 7: ""},
    "phrygian":         {1: "m", 2: "", 3: "", 4: "m", 5: "dim", 6: "", 7: "m"},
    "lydian":           {1: "", 2: "", 3: "m", 4: "dim", 5: "", 6: "m", 7: "m"},
    "mixolydian":       {1: "", 2: "m", 3: "dim", 4: "", 5: "m", 6: "m", 7: ""},
    "locrian":          {1: "dim", 2: "", 3: "m", 4: "m", 5: "", 6: "", 7: "m"},
    "harmonicMinor":    {1: "m", 2: "dim", 3: "+", 4: "m", 5: "", 6: "", 7: "dim"},
    "phrygianDominant": {1: "", 2: "dim", 3: "m", 4: "m", 5: "", 6: "", 7: "dim"},
}


def _note_to_chromatic(note):
    """Convert a note name to chromatic index 0-11."""
    n = ENHARMONIC.get(note, note)
    return CHROMATIC.index(n) if n in CHROMATIC else 0


def _chromatic_to_note(idx, prefer_flat=False):
    """Convert chromatic index to note name."""
    idx = idx % 12
    name = CHROMATIC[idx]
    if prefer_flat:
        flat_map = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}
        name = flat_map.get(name, name)
    return name


def _get_scale_note(tonic, scale_name, degree):
    """Get the note name for a given scale degree (1-indexed) in a scale.

    Uses the tonic and mode intervals to compute the actual note.
    For sharp keys, uses flats when the degree is lowered relative to major.
    """
    intervals = MODE_INTERVALS.get(scale_name, MODE_INTERVALS["major"])
    major_intervals = MODE_INTERVALS["major"]
    tonic_idx = _note_to_chromatic(tonic)
    deg_idx = (degree - 1) % 7

    # Use flats for keys that conventionally use flats
    prefer_flat = tonic in ("F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb")
    # For sharp keys: if this degree is lowered relative to major, use flat
    if not prefer_flat and intervals[deg_idx] < major_intervals[deg_idx]:
        prefer_flat = True

    note_idx = (tonic_idx + intervals[deg_idx]) % 12
    return _chromatic_to_note(note_idx, prefer_flat)


def _resolve_scale_for_key(tonic, scale):
    """Get scale note names for tonic + scale."""
    if scale == "major" and tonic in MAJOR_SCALE:
        return MAJOR_SCALE[tonic]
    # Compute from intervals
    return [_get_scale_note(tonic, scale, d) for d in range(1, 8)]


def hookpad_chord_to_name(chord, tonic, scale="major"):
    """Convert a hookpad chord object to a display name string.

    Handles: triads, 7/9/11/13, sus2/sus4, add9, borrowed chords,
    secondary dominants, minor keys, rests.
    """
    if chord.get("isRest") or chord.get("root", 0) == 0:
        return "N.C."

    root_deg = chord["root"]  # 1-7 scale degree
    chord_type = chord.get("type", 5)
    applied = chord.get("applied", 0)
    borrowed = chord.get("borrowed", "") or ""
    suspensions = chord.get("suspensions", [])
    adds = chord.get("adds", [])
    alterations = chord.get("alterations", [])

    # Determine the active scale for this chord
    active_scale = scale
    active_tonic = tonic

    if borrowed and isinstance(borrowed, str) and borrowed in MODE_INTERVALS:
        # Borrowed chord: resolve root note from the borrowed mode
        active_scale = borrowed

    # Handle applied (secondary) chords: V/x, IV/x, etc.
    if applied and applied > 0:
        # The chord is applied to scale degree `applied`
        # First, find the target note (what we're applied to)
        target_note = _get_scale_note(active_tonic, active_scale, applied)
        # The chord root is relative to the target
        # e.g., applied=5, root=5 means V/V
        # The root note is computed from the target's major scale
        root_note = _get_scale_note(target_note, "major", root_deg)
        # Applied chords are usually major (dominant function)
        quality = ""
        if root_deg == 7:
            quality = "dim"
        elif root_deg == 2:
            quality = "m"
    else:
        # Normal chord: resolve from active scale
        root_note = _get_scale_note(active_tonic, active_scale, root_deg)
        # Get diatonic quality
        diatonic = MODE_DIATONIC.get(active_scale, MAJOR_DIATONIC)
        quality = diatonic.get(root_deg, "")

    # Build suffix: quality + extension + suspension + adds
    suffix = quality

    # Extension (7, 9, 11, 13)
    if chord_type == 7:
        suffix += "7"
    elif chord_type == 9:
        suffix += "9"
    elif chord_type == 11:
        suffix += "11"
    elif chord_type == 13:
        suffix += "13"

    # Suspensions (replace the 3rd — goes after extension)
    if suspensions:
        if 4 in suspensions:
            suffix += "sus4"
        elif 2 in suspensions:
            suffix += "sus2"

    # Adds
    for a in sorted(adds):
        if a == 9 and chord_type == 5:
            suffix += "add9"
        elif a == 4:
            suffix += "add4"
        elif a == 6:
            suffix += "add6"

    # Alterations
    for a in alterations:
        if a == "#5":
            suffix += "(#5)"

    # Build applied chord suffix
    if applied and applied > 0:
        target_note_name = _get_scale_note(tonic, scale, applied)
        return root_note + suffix + "/" + target_note_name

    return root_note + suffix


# ── Song parsing ─────────────────────────────────────────────────────

def parse_song(filepath, tonic_override=None):
    """Parse a hookpad JSON file into sections with measures and chords."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    # Key info
    keys_data = data.get("keys", [])
    if keys_data:
        original_tonic = keys_data[0].get("tonic", "C")
        scale = keys_data[0].get("scale", "major")
    else:
        original_tonic, scale = "C", "major"

    tonic = tonic_override if tonic_override else original_tonic

    # Tempo
    tempos = data.get("tempos", [])
    bpm = tempos[0]["bpm"] if tempos else 120

    # Meter
    meters = data.get("meters", [])
    if meters:
        num_beats = meters[0].get("numBeats", 4)
        beat_unit = meters[0].get("beatUnit", 1)
    else:
        num_beats, beat_unit = 4, 1
    beats_per_measure = num_beats  # beatUnit=1 means quarter note

    end_beat = data.get("endBeat", 0)
    sections = data.get("sections", [])
    chords = data.get("chords", [])
    has_melody = len(data.get("notes", [])) > 0

    # Compute transposition interval if tonic was overridden
    transpose_semitones = 0
    if tonic_override:
        transpose_semitones = (_note_to_chromatic(tonic) - _note_to_chromatic(original_tonic)) % 12

    # Build key map: list of (beat, tonic, scale) for key changes
    key_changes = []
    for k in keys_data:
        kt = k.get("tonic", tonic)
        ks = k.get("scale", scale)
        if tonic_override and transpose_semitones:
            # Transpose this key change by the same interval
            new_idx = (_note_to_chromatic(kt) + transpose_semitones) % 12
            prefer_flat = tonic in ("F", "Bb", "Eb", "Ab", "Db", "Gb")
            kt = _chromatic_to_note(new_idx, prefer_flat)
        key_changes.append((k["beat"], kt, ks))
    if not key_changes:
        key_changes.append((1, tonic, scale))

    # Build meter map: list of (beat, beatsPerMeasure) for meter changes
    meter_changes = []
    for m in meters:
        meter_changes.append((m["beat"], m.get("numBeats", 4)))
    if not meter_changes:
        meter_changes.append((1, beats_per_measure))

    def get_key_at(beat):
        """Return (tonic, scale) active at a given beat."""
        active_tonic, active_scale = tonic, scale
        for kb, kt, ks in key_changes:
            if kb <= beat:
                active_tonic, active_scale = kt, ks
            else:
                break
        return active_tonic, active_scale

    def get_bpm_at(beat):
        """Return beats_per_measure active at a given beat."""
        active = beats_per_measure
        for mb, mn in meter_changes:
            if mb <= beat:
                active = mn
            else:
                break
        return active

    # Compute measure boundaries
    measures = []
    current_beat = 1.0
    while current_beat < end_beat:
        bpm_here = get_bpm_at(current_beat)
        m_start = current_beat
        m_end = current_beat + bpm_here
        measures.append((m_start, m_end, bpm_here))
        current_beat = m_end

    total_measures = len(measures)

    # Build section boundaries
    if sections:
        section_bounds = []
        for i, sec in enumerate(sections):
            s_start = sec["beat"]
            s_name = sec.get("name", "Section")
            if i + 1 < len(sections):
                s_end = sections[i + 1]["beat"]
            else:
                s_end = end_beat
            section_bounds.append({
                "name": s_name.capitalize() if s_name else "Section",
                "startBeat": s_start,
                "endBeat": s_end,
            })
    else:
        section_bounds = [{
            "name": "Full Song",
            "startBeat": 1,
            "endBeat": end_beat,
        }]

    # Assign measures and chords to sections
    result_sections = []
    for sec in section_bounds:
        sec_measures = []
        for m_idx, (m_start, m_end, m_bpm) in enumerate(measures):
            # Measure belongs to this section if it starts within section bounds
            if m_start >= sec["startBeat"] and m_start < sec["endBeat"]:
                # Find chords in this measure
                measure_chords = []
                kt, ks = get_key_at(m_start)
                for chord in chords:
                    c_beat = chord["beat"]
                    c_dur = chord.get("duration", 0)
                    # Chord belongs to this measure if it starts in it
                    if c_beat >= m_start and c_beat < m_end:
                        name = hookpad_chord_to_name(chord, kt, ks)
                        # Width fraction: how much of the measure this chord occupies
                        chord_end = min(c_beat + c_dur, m_end)
                        width = (chord_end - c_beat) / m_bpm
                        # Root degree (1-7) for coloring
                        root_deg = chord.get("root", 0)
                        measure_chords.append({
                            "name": name,
                            "widthFraction": round(width, 4),
                            "deg": root_deg,
                        })

                if not measure_chords:
                    # Empty measure (no chords but measure exists)
                    measure_chords = [{"name": "", "widthFraction": 1}]

                sec_measures.append(measure_chords)

        # Skip empty sections (0 measures or all-empty trailing sections)
        if len(sec_measures) == 0:
            continue
        result_sections.append({
            "name": sec["name"],
            "measureCount": len(sec_measures),
            "measures": sec_measures,
        })

    # Trim trailing sections that have no chord content
    while result_sections:
        last = result_sections[-1]
        has_content = any(
            c["name"] for m in last["measures"] for c in m
        )
        if not has_content:
            result_sections.pop()
        else:
            break

    # Format key display
    key_display = tonic
    if scale == "major":
        key_display += " major"
    elif scale == "minor":
        key_display += " minor"
    else:
        key_display += " " + scale

    time_sig = f"{num_beats}/4"

    return {
        "key": key_display,
        "originalTonic": original_tonic,
        "scale": scale,
        "bpm": bpm,
        "timeSig": time_sig,
        "totalMeasures": total_measures,
        "hasChords": len(chords) > 0,
        "hasMelody": has_melody,
        "sections": result_sections,
    }


# ── HTTP handler ─────────────────────────────────────────────────────

class SongBrowserHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/api/songs":
            self._serve_songs()
        elif path.startswith("/api/song/"):
            filename = urllib.parse.unquote(path[len("/api/song/"):])
            self._serve_song(filename)
        else:
            # Serve static files from project root
            self.directory = STATIC_ROOT
            super().do_GET()

    def _serve_html(self):
        try:
            with open(HTML_PATH, "r") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(404, "song-browser.html not found")

    def _serve_songs(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(_song_database).encode("utf-8"))

    def _serve_song(self, filename):
        filepath = os.path.join(HOOKPAD_DIR, filename)
        if not os.path.exists(filepath):
            self.send_error(404, f"Song file not found: {filename}")
            return
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            tonic_override = params.get("tonic", [None])[0]
            result = parse_song(filepath, tonic_override=tonic_override)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        # Quieter logging — only errors
        if args and "404" in str(args[0]):
            super().log_message(format, *args)


def main():
    global _song_database
    print(f"Scanning songs from {HOOKPAD_DIR}...")
    _song_database = scan_songs_directory()
    print(f"Found {len(_song_database)} songs")

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True

    server = ReusableHTTPServer(("localhost", PORT), SongBrowserHandler)
    print(f"Song Browser running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
