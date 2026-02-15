#!/usr/bin/env python3
"""
Build 3-level song form structures for the Beatles database.

Three levels:
1. Song form - how sections relate (e.g., ABACBA where A=Chorus, B=Verse, C=Bridge)
2. Section structure - how 4-bar phrases relate within a section (e.g., AABC)
3. Phrase structure - how individual bars relate within a 4-bar phrase (e.g., ABCD)

Run:
  cd ~/Desktop && python glowinggardens_claude/build_song_forms.py
"""

import json
import os

HOOKPAD_DIR = "/Users/robert/Desktop/hookpad_songs/hookpad_songs"
DATABASE_PATH = "/Users/robert/Desktop/hookpad_songs/all_songs_database.json"

# G major scale degrees: 1=G, 2=A, 3=B, 4=C, 5=D, 6=E, 7=F#
MAJOR_SCALE = {
    "C": ["C", "D", "E", "F", "G", "A", "B"],
    "C#": ["C#", "D#", "E#", "F#", "G#", "A#", "B#"],
    "Db": ["Db", "Eb", "F", "Gb", "Ab", "Bb", "C"],
    "D": ["D", "E", "F#", "G", "A", "B", "C#"],
    "Eb": ["Eb", "F", "G", "Ab", "Bb", "C", "D"],
    "E": ["E", "F#", "G#", "A", "B", "C#", "D#"],
    "F": ["F", "G", "A", "Bb", "C", "D", "E"],
    "F#": ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
    "Gb": ["Gb", "Ab", "Bb", "Cb", "Db", "Eb", "F"],
    "G": ["G", "A", "B", "C", "D", "E", "F#"],
    "Ab": ["Ab", "Bb", "C", "Db", "Eb", "F", "G"],
    "A": ["A", "B", "C#", "D", "E", "F#", "G#"],
    "Bb": ["Bb", "C", "D", "Eb", "F", "G", "A"],
    "B": ["B", "C#", "D#", "E", "F#", "G#", "A#"],
}

# Minor keys map to their relative major for scale degree lookup
MINOR_TO_RELATIVE = {
    "Am": "C", "Bm": "D", "Cm": "Eb", "Dm": "F", "Em": "G",
    "Fm": "Ab", "Gm": "Bb", "F#m": "A", "C#m": "E", "G#m": "B",
    "Bbm": "Db", "Ebm": "Gb",
}

# Default diatonic chord qualities in major: I=maj, ii=min, iii=min, IV=maj, V=maj, vi=min, vii=dim
DIATONIC_QUALITY = {1: "", 2: "m", 3: "m", 4: "", 5: "", 6: "m", 7: "dim"}


def hookpad_chord_to_name(chord, key_tonic):
    """Convert a Hookpad chord object to a chord name string."""
    root = chord["root"]  # 1-indexed scale degree
    applied = chord.get("applied", 0)
    borrowed = chord.get("borrowed", "")
    chord_type = chord.get("type", 5)  # 5 = triad
    adds = chord.get("adds", [])

    # Get the scale
    if key_tonic in MAJOR_SCALE:
        scale = MAJOR_SCALE[key_tonic]
    else:
        scale = MAJOR_SCALE.get("C")

    # Get the root note name
    root_note = scale[(root - 1) % 7]

    # Determine quality
    if borrowed == "harmonicMinor":
        # Borrowed from harmonic minor - typically makes the iv chord minor
        # In G major, root 4 borrowed harmonicMinor = Cm
        quality = "m"
    elif applied > 0:
        # Secondary dominant - V/V, V/vi, etc.
        # The chord is typically major (dominant)
        # The root is calculated relative to the target chord
        # applied=5 means V/V, so in G major, V/V = A (major)
        # For simplicity, secondary dominants are major
        quality = ""
    else:
        quality = DIATONIC_QUALITY.get(root, "")

    # Handle 7th chords
    suffix = quality
    if chord_type == 7:  # dominant 7th
        suffix += "7"

    return root_note + suffix


def parse_hookpad_file(filepath, key_tonic=None):
    """Parse a Hookpad JSON file and extract section structure with chords."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    # Get key
    if key_tonic is None:
        keys = data.get("keys", [])
        if keys:
            key_tonic = keys[0].get("tonic", "C")

    # Get sections
    sections = data.get("sections", [])
    chords = data.get("chords", [])
    end_beat = data.get("endBeat", 0)

    # Build section boundaries
    section_bounds = []
    for i, sec in enumerate(sections):
        start = sec["beat"]
        name = sec["name"]
        if i + 1 < len(sections):
            end = sections[i + 1]["beat"]
        else:
            end = end_beat
        section_bounds.append({"name": name, "start": start, "end": end})

    # Assign chords to sections
    result_sections = []
    for sec in section_bounds:
        sec_chords = []
        for chord in chords:
            if sec["start"] <= chord["beat"] < sec["end"]:
                name = hookpad_chord_to_name(chord, key_tonic)
                sec_chords.append(name)

        measures = len(sec_chords)
        if measures > 0:
            result_sections.append({
                "name": sec["name"].capitalize(),
                "measures": measures,
                "chords": sec_chords,
            })

    return key_tonic, result_sections


def compute_bar_pattern(chords):
    """Compute bar pattern from chord list (same chord = same letter).

    e.g., ["G", "G", "Em", "Em"] -> "AABB"
         ["G", "Em", "Bm", "D"] -> "ABCD"
         ["Cm", "D", "G", "G"] -> "ABCC"
    """
    if not chords:
        return ""

    seen = {}
    pattern = []
    next_letter = ord('A')

    for chord in chords:
        if chord not in seen:
            seen[chord] = chr(next_letter)
            next_letter += 1
        pattern.append(seen[chord])

    return "".join(pattern)


def split_into_phrases(chords, phrase_len=4):
    """Split a chord list into phrases of given length."""
    phrases = []
    for i in range(0, len(chords), phrase_len):
        phrase = chords[i:i + phrase_len]
        if len(phrase) == phrase_len:
            phrases.append(phrase)
        elif len(phrase) > 0:
            # Partial phrase at end - include it
            phrases.append(phrase)
    return phrases


def compute_phrase_pattern(phrases):
    """Compute phrase pattern by comparing 4-bar phrases.

    Two phrases get the same letter if they have identical chords.
    e.g., if phrase 0 == phrase 1 != phrase 2 != phrase 3 -> "AABC"
    """
    if not phrases:
        return ""

    seen = {}
    pattern = []
    next_letter = ord('A')

    for phrase in phrases:
        key = tuple(phrase)
        if key not in seen:
            seen[key] = chr(next_letter)
            next_letter += 1
        pattern.append(seen[key])

    return "".join(pattern)


def build_section_form(section_chords):
    """Build enriched section data with phrase_pattern and phrases dict.

    Takes a flat chord list for a section and returns:
    - phrase_pattern: e.g., "AABC"
    - phrases: dict mapping pattern letters to chord/bar_pattern data
    """
    phrases_list = split_into_phrases(section_chords)
    phrase_pattern = compute_phrase_pattern(phrases_list)

    # Build phrases dict - map each unique letter to its chord data
    phrases_dict = {}
    for i, phrase in enumerate(phrases_list):
        letter = phrase_pattern[i]
        if letter not in phrases_dict:
            phrases_dict[letter] = {
                "chords": phrase,
                "bar_pattern": compute_bar_pattern(phrase),
            }

    return phrase_pattern, phrases_dict


def compute_song_pattern(sections):
    """Compute song-level pattern from section names.

    Each unique section name gets a unique letter.
    e.g., [Chorus, Verse, Verse, Chorus] -> "ABBA"
    """
    seen = {}
    pattern = []
    next_letter = ord('A')

    for sec in sections:
        name = sec["name"]
        if name not in seen:
            seen[name] = chr(next_letter)
            next_letter += 1
        pattern.append(seen[name])

    return "".join(pattern), {v: k for k, v in seen.items()}


def build_full_form(sections):
    """Build the complete 3-level form structure for a song.

    Returns (form_dict, enriched_sections).
    """
    # Song-level pattern
    song_pattern, section_map = compute_song_pattern(sections)

    # Enrich each section with phrase-level data
    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    form = {
        "song_pattern": song_pattern,
        "sections": section_map,
    }

    return form, enriched


# ============================================================
# Manual song data for songs where Hookpad data is incomplete
# or we need to fill in the full structure from musical knowledge
# ============================================================

def get_she_loves_you():
    """She Loves You - The Beatles (1963)
    Key: G major, BPM: 151

    Structure from Hookpad data + musical knowledge:
    The song opens with the chorus ("She loves you, yeah yeah yeah"),
    then two verses each followed by the chorus, a bridge (middle eight),
    then verse + chorus again, ending with a coda.

    The Hookpad file covers: Chorus(8) | Verse(16) | Verse(16) | Bridge(8)
    The actual song form is: Chorus-Verse-Chorus-Verse-Chorus-Bridge-Verse-Chorus
    """
    sections = [
        {
            "name": "Chorus",
            "measures": 8,
            "chords": ["Em", "Em", "A", "A", "Cm", "D", "G", "G"],
        },
        {
            "name": "Verse",
            "measures": 16,
            "chords": ["G", "Em", "Bm", "D", "G", "Em", "Bm", "D",
                       "G", "G", "Em", "Em", "Cm", "C", "D", "D"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["Em", "Em", "A", "A", "Cm", "D", "G", "G"],
        },
    ]

    # The actual full song form
    form = {
        "song_pattern": "ABABACAB",
        "sections": {
            "A": "Chorus",
            "B": "Verse",
            "C": "Bridge",
        }
    }

    # Build enriched sections
    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_let_it_be():
    """Let It Be - The Beatles (1970)
    Key: C major, BPM: 73

    Form: Intro-Verse-Chorus-Verse-Chorus-Solo-Verse-Chorus-Outro
    """
    sections = [
        {
            "name": "Intro",
            "measures": 4,
            "chords": ["C", "G", "Am", "F"],
        },
        {
            "name": "Verse",
            "measures": 16,
            "chords": ["C", "G", "Am", "F", "C", "G", "F", "C",
                       "C", "G", "Am", "F", "C", "G", "F", "C"],
        },
        {
            "name": "Chorus",
            "measures": 8,
            "chords": ["Am", "G", "F", "C", "C", "G", "F", "C"],
        },
        {
            "name": "Solo",
            "measures": 8,
            "chords": ["C", "G", "Am", "F", "C", "G", "F", "C"],
        },
    ]

    form = {
        "song_pattern": "ABCBCDBCE",
        "sections": {
            "A": "Intro",
            "B": "Verse",
            "C": "Chorus",
            "D": "Solo",
            "E": "Outro",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_yesterday():
    """Yesterday - The Beatles (1965)
    Key: F major, BPM: 98

    Unusual 7-bar verses. Form: Verse-Verse-Bridge-Verse-Bridge-Verse
    Using actual chord names (the database has Roman numerals, we'll use names).

    In F major: I=F, II=Gm, III=Am, IV=Bb, V=C, VI=Dm, VII=Em (or E7 as V/ii)
    """
    sections = [
        {
            "name": "Verse",
            "measures": 7,
            "chords": ["F", "Em7", "A7", "Dm", "Bb", "C", "F"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["Em7", "A7", "Dm", "C", "Bb", "Dm", "Gm", "C"],
        },
    ]

    form = {
        "song_pattern": "AABABA",
        "sections": {
            "A": "Verse",
            "B": "Bridge",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_hey_jude():
    """Hey Jude - The Beatles (1968)
    Key: F major, BPM: 74

    Form: Verse-Verse-Verse-Verse-Coda (massive coda/outro)
    Each verse has the same structure: 8 bars verse + ~8 bars response
    """
    sections = [
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["F", "C", "C", "F", "Bb", "F", "C", "F"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["F", "F7", "Bb", "Gm", "Bb", "F", "C", "F"],
        },
        {
            "name": "Coda",
            "measures": 4,
            "chords": ["F", "Eb", "Bb", "F"],
        },
    ]

    form = {
        "song_pattern": "ABABABABC",
        "sections": {
            "A": "Verse",
            "B": "Bridge",
            "C": "Coda",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_come_together():
    """Come Together - The Beatles (1969)
    Key: Dm, BPM: 82

    Form: Intro-Verse-Verse-Verse-Verse-Solo-Verse-Outro
    The verse has a distinctive bass riff section + "come together" hook
    """
    sections = [
        {
            "name": "Intro",
            "measures": 4,
            "chords": ["Dm", "Dm", "Dm", "Dm"],
        },
        {
            "name": "Verse",
            "measures": 12,
            "chords": ["Dm", "Dm", "Dm", "Dm", "Dm", "Dm", "Dm", "Dm",
                       "A", "A", "G", "G"],
        },
        {
            "name": "Solo",
            "measures": 8,
            "chords": ["Dm", "Dm", "Dm", "Dm", "A", "A", "G", "G"],
        },
    ]

    form = {
        "song_pattern": "ABBBBEBC",
        "sections": {
            "A": "Intro",
            "B": "Verse",
            "C": "Outro",
            "E": "Solo",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_here_comes_the_sun():
    """Here Comes the Sun - The Beatles (1969)
    Key: A major, BPM: 129
    """
    sections = [
        {
            "name": "Chorus",
            "measures": 8,
            "chords": ["A", "A", "D", "E7", "A", "A", "D", "E7"],
        },
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["A", "D", "A", "D", "A", "D", "B7", "B7"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["F", "C", "G", "D", "F", "C", "G", "D"],
        },
    ]

    form = {
        "song_pattern": "ABABACBA",
        "sections": {
            "A": "Chorus",
            "B": "Verse",
            "C": "Bridge",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_norwegian_wood():
    """Norwegian Wood - The Beatles (1965)
    Key: E major (with mixolydian color), BPM: 177 (in 3/4, so effectively slower)

    Form: Verse-Verse-Bridge-Verse-Bridge-Verse
    The verse is in E mixolydian, bridge shifts to Em
    """
    sections = [
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["E", "E", "D", "E", "E", "E", "D", "E"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["Em", "Em", "A", "A", "Em", "F#m7", "B7", "E"],
        },
    ]

    form = {
        "song_pattern": "AABABA",
        "sections": {
            "A": "Verse",
            "B": "Bridge",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_in_my_life():
    """In My Life - The Beatles (1965)
    Key: A major, BPM: 103

    Form: Intro-Verse-Verse-Bridge-Solo-Verse-Outro
    """
    sections = [
        {
            "name": "Intro",
            "measures": 4,
            "chords": ["A", "E", "A", "E"],
        },
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["A", "E", "F#m", "A7", "D", "Dm", "A", "A"],
        },
        {
            "name": "Bridge",
            "measures": 8,
            "chords": ["F#m", "F#m", "D", "G", "A", "A", "A", "A"],
        },
        {
            "name": "Solo",
            "measures": 8,
            "chords": ["A", "E", "F#m", "A7", "D", "Dm", "A", "A"],
        },
    ]

    form = {
        "song_pattern": "ABBCDBF",
        "sections": {
            "A": "Intro",
            "B": "Verse",
            "C": "Bridge",
            "D": "Solo",
            "F": "Outro",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_blackbird():
    """Blackbird - The Beatles (1968)
    Key: G major, BPM: 94

    Form: Verse-Verse-Bridge-Verse-Bridge-Verse
    """
    sections = [
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["G", "Am", "G/B", "G", "C", "C#dim", "D", "D"],
        },
        {
            "name": "Bridge",
            "measures": 4,
            "chords": ["F", "C/E", "Dm", "C"],
        },
    ]

    form = {
        "song_pattern": "AABABA",
        "sections": {
            "A": "Verse",
            "B": "Bridge",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


def get_penny_lane():
    """Penny Lane - The Beatles (1967)
    Key: B major, BPM: 114

    Form: Verse-Verse-Chorus-Verse-Chorus-Verse-Trumpet Solo-Chorus
    """
    sections = [
        {
            "name": "Verse",
            "measures": 8,
            "chords": ["B", "B", "C#m", "F#", "B", "Bm", "E", "A"],
        },
        {
            "name": "Chorus",
            "measures": 8,
            "chords": ["A", "A", "A#dim", "B", "E", "E", "A", "A"],
        },
    ]

    form = {
        "song_pattern": "AABABABCB",
        "sections": {
            "A": "Verse",
            "B": "Chorus",
            "C": "Trumpet Solo",
        }
    }

    enriched = []
    for sec in sections:
        phrase_pattern, phrases_dict = build_section_form(sec["chords"])
        enriched.append({
            "name": sec["name"],
            "measures": sec["measures"],
            "phrase_pattern": phrase_pattern,
            "phrases": phrases_dict,
        })

    return form, enriched


# Registry of all song builders
SONG_BUILDERS = {
    "She Loves You": get_she_loves_you,
    "Let It Be": get_let_it_be,
    "Yesterday": get_yesterday,
    "Hey Jude": get_hey_jude,
    "Come Together": get_come_together,
    "Here Comes the Sun": get_here_comes_the_sun,
    "Norwegian Wood": get_norwegian_wood,
    "In My Life": get_in_my_life,
    "Blackbird": get_blackbird,
    "Penny Lane": get_penny_lane,
}


def update_database():
    """Update the all_songs_database.json with form data for known songs."""
    with open(DATABASE_PATH, 'r') as f:
        database = json.load(f)

    songs = database.get("songs", database) if isinstance(database, dict) else database
    updated_count = 0

    for song in songs:
        title = song.get("title", "")
        artist = song.get("artist", "")

        # Match Beatles songs
        if "beatles" not in artist.lower() and "beatles" not in title.lower():
            continue

        # Case-insensitive match against builder titles
        builder = None
        for builder_title, builder_fn in SONG_BUILDERS.items():
            if builder_title.lower() == title.lower():
                builder = builder_fn
                break

        if builder:
            form, enriched_sections = builder()

            song["form"] = form
            song["structure"] = enriched_sections
            updated_count += 1
            print(f"  Updated: {title}")

    # Save
    with open(DATABASE_PATH, 'w') as f:
        json.dump(database, f, indent=2)

    print(f"\nUpdated {updated_count} songs in database")
    return updated_count


def print_song_structure(title, form, sections):
    """Pretty-print a song's 3-level structure."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    # Level 1: Song form
    pattern = form["song_pattern"]
    section_map = form["sections"]
    print(f"\n  Song Form: {pattern}")
    print(f"  Section Map: {', '.join(f'{k}={v}' for k, v in sorted(section_map.items()))}")

    # Expand the pattern
    expanded = " -> ".join(section_map.get(c, "?") for c in pattern)
    print(f"  Expanded:  {expanded}")

    # Level 2 & 3: Each section
    for sec in sections:
        print(f"\n  [{sec['name']}] ({sec['measures']} measures)")
        print(f"    Phrase pattern: {sec['phrase_pattern']}")
        for letter, phrase in sorted(sec["phrases"].items()):
            chords_str = " | ".join(phrase["chords"])
            print(f"    {letter}: [{phrase['bar_pattern']}] {chords_str}")

    print()


def main():
    print("Building 3-level song form structures")
    print("=" * 60)

    # Build and display all songs
    for title, builder in SONG_BUILDERS.items():
        form, sections = builder()
        print_song_structure(title, form, sections)

    # Update the database
    print("\nUpdating database...")
    update_database()

    print("\nDone!")


if __name__ == "__main__":
    main()
