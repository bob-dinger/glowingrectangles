#!/usr/bin/env python3
"""
Beatles Song Structure Parser

Parses Alan W. Pollack's "Notes On..." series to extract:
- Song structure (sections, measures)
- Chord progressions
- Key, tempo, meter

Then generates MIDI files.

Run:
  cd ~/Desktop && source midi_env/bin/activate && python glowinggardens_claude/beatles_parser.py
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import List, Optional
import time

# Song code mappings (from Pollack's index)
SONG_CODES = {
    "She Loves You": "sly",
    "I Want to Hold Your Hand": "iwthyh",
    "Eight Days a Week": "edaw",
    "A Hard Day's Night": "ahdn",
    "I Feel Fine": "iff",
    "Day Tripper": "dt",
    "You've Got to Hide Your Love Away": "ygthyla",
    "Norwegian Wood": "nw",
    "Help!": "h!",
    "Yellow Submarine": "ys",
    "I'm Only Sleeping": "ios",
    "Eleanor Rigby": "er",
    "Getting Better": "gb",
    "With a Little Help from My Friends": "walhfmf",
    "Lovely Rita": "lr",
    "Across the Universe": "atu",
    "Here Comes the Sun": "hcts",
    "Come Together": "ct",
    "Something": "s",
    "Let It Be": "lib",
    "Hey Jude": "hj",
    "Yesterday": "y",
    "In My Life": "iml",
    "Strawberry Fields Forever": "sff",
    "Penny Lane": "pl",
    "A Day in the Life": "aditl",
    "All You Need Is Love": "aynil",
    "Revolution": "r",
    "While My Guitar Gently Weeps": "wmggw",
    "Blackbird": "b2",
    "Back in the U.S.S.R.": "bitu",
    "Dear Prudence": "dp",
    "Helter Skelter": "hs",
    "The Long and Winding Road": "tlawr",
    "Get Back": "gb2",
    "Don't Let Me Down": "dlmd",
    "I Am the Walrus": "iatw",
    "Lucy in the Sky with Diamonds": "litswd",
    "Sgt. Pepper's Lonely Hearts Club Band": "splhcb",
    "Twist and Shout": "covers1",  # In covers
    "Please Please Me": "ppm",
    "Love Me Do": "lmd",
    "From Me to You": "fmty",
    "Can't Buy Me Love": "cbml",
    "Ticket to Ride": "ttr",
    "We Can Work It Out": "wcwio",
    "Paperback Writer": "pw_and_r",
    "All My Loving": "aml",
    "And I Love Her": "ailh",
    "Michelle": "m4",
    "Girl": "g",
    "Drive My Car": "dmc",
    "Nowhere Man": "nm",
    "The Word": "tw",
    "I'm Looking Through You": "ilty",
    "If I Needed Someone": "iins",
    "Taxman": "t",
    "Good Day Sunshine": "gds",
    "Here, There and Everywhere": "htae",
    "For No One": "fno",
    "Got to Get You into My Life": "gtgyiml",
    "Tomorrow Never Knows": "tnk",
    "Fixing a Hole": "fah",
    "She's Leaving Home": "slh",
    "Being for the Benefit of Mr. Kite": "bftbomk",
    "Within You Without You": "wywy",
    "When I'm Sixty-Four": "wisf",
    "Good Morning Good Morning": "gmgm",
    "Magical Mystery Tour": "mmt",
    "The Fool on the Hill": "foth",
    "Blue Jay Way": "bjw",
    "Hello, Goodbye": "hg",
    "Lady Madonna": "lm",
    "Ob-La-Di, Ob-La-Da": "oo",
    "Happiness Is a Warm Gun": "hiawg",
    "Martha My Dear": "mmd",
    "I Will": "iw",
    "Julia": "j",
    "Birthday": "b",
    "Yer Blues": "yb",
    "Mother Nature's Son": "mns",
    "Sexy Sadie": "ss",
    "Honey Pie": "hp",
    "Savoy Truffle": "st",
    "Cry Baby Cry": "cbc",
    "Good Night": "gn",
    "Two of Us": "tou",
    "Dig a Pony": "dap",
    "I've Got a Feeling": "igaf",
    "One After 909": "oa909",
    "For You Blue": "fyb",
    "Maxwell's Silver Hammer": "msh",
    "Oh! Darling": "od",
    "Octopus's Garden": "og",
    "I Want You (She's So Heavy)": "iwyssh",
    "Because": "b4",
    "Sun King": "sk",
    "Mean Mr. Mustard": "mmm",
    "Polythene Pam": "pp",
    "She Came in Through the Bathroom Window": "scittbw",
    "Golden Slumbers": "gs",
    "Carry That Weight": "ctw",
    "The End": "te",
    "Her Majesty": "hm",
    "Free as a Bird": "faab",
    "Real Love": "rl",
}

# BPM data (from our earlier research + common knowledge)
BPM_DATA = {
    "She Loves You": 151,
    "I Want to Hold Your Hand": 131,
    "Eight Days a Week": 138,
    "A Hard Day's Night": 139,
    "I Feel Fine": 178,
    "Day Tripper": 137,
    "You've Got to Hide Your Love Away": 184,
    "Norwegian Wood": 177,
    "Help!": 95,
    "Yellow Submarine": 111,
    "I'm Only Sleeping": 100,
    "Eleanor Rigby": 137,
    "Getting Better": 122,
    "With a Little Help from My Friends": 112,
    "Lovely Rita": 88,
    "Across the Universe": 76,
    "Here Comes the Sun": 129,
    "Come Together": 82,
    "Something": 66,
    "Let It Be": 73,
    "Hey Jude": 74,
    "Yesterday": 98,
    "In My Life": 103,
    "Strawberry Fields Forever": 92,
    "Penny Lane": 114,
    "A Day in the Life": 78,
    "All You Need Is Love": 104,
    "Blackbird": 94,
    "While My Guitar Gently Weeps": 116,
    "Back in the U.S.S.R.": 144,
    "Revolution": 122,
}

BASE_URL = "https://www.recmusicbeatles.com/public/files/awp/"

@dataclass
class Section:
    name: str
    measures: int
    chords: List[str]
    notes: str = ""

@dataclass
class SongStructure:
    title: str
    key: str
    meter: str
    bpm: int
    sections: List[Section]
    form: str
    raw_analysis: str = ""

def fetch_pollack_page(song_code: str) -> Optional[str]:
    """Fetch the HTML content of a Pollack analysis page."""
    url = f"{BASE_URL}{song_code}.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_pollack_analysis(html: str, title: str) -> SongStructure:
    """Parse a Pollack analysis page to extract structure."""
    soup = BeautifulSoup(html, 'html.parser')

    # Get all text content
    text = soup.get_text()

    # Initialize defaults
    key = "C"
    meter = "4/4"
    form = ""
    sections = []

    # Extract key signature
    key_patterns = [
        r'key of ([A-G][#b]?\s*(?:Major|Minor|major|minor))',
        r'in ([A-G][#b]?)\s+(?:Major|Minor|major|minor)',
        r'Key:\s*([A-G][#b]?)',
    ]
    for pattern in key_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            key = match.group(1).strip()
            break

    # Extract meter/time signature
    meter_patterns = [
        r'(\d+/\d+)\s*(?:time|meter)',
        r'time signature[:\s]+(\d+/\d+)',
        r'in\s+(\d+/\d+)',
    ]
    for pattern in meter_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            meter = match.group(1)
            break

    # Extract form
    form_patterns = [
        r'[Ff]orm[:\s]+([^\n]+)',
        r'[Ss]tructure[:\s]+([^\n]+)',
        r'[Oo]verall [Ff]orm[:\s]+([^\n]+)',
    ]
    for pattern in form_patterns:
        match = re.search(pattern, text)
        if match:
            form = match.group(1).strip()
            break

    # Extract sections and measures
    # Look for patterns like "verse is X measures" or "X-measure intro"
    section_patterns = [
        r'([Ii]ntro|[Vv]erse|[Cc]horus|[Bb]ridge|[Oo]utro|[Rr]efrain|[Ss]olo)[^\d]*(\d+)[\s-]*(?:measure|bar)',
        r'(\d+)[\s-]*(?:measure|bar)\s+([Ii]ntro|[Vv]erse|[Cc]horus|[Bb]ridge|[Oo]utro|[Rr]efrain)',
    ]

    found_sections = {}
    for pattern in section_patterns:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            if groups[0].isdigit():
                measures = int(groups[0])
                section_name = groups[1].capitalize()
            else:
                section_name = groups[0].capitalize()
                measures = int(groups[1])

            if section_name not in found_sections:
                found_sections[section_name] = measures

    # Extract chord progressions
    # Look for Roman numeral patterns like "I - IV - V" or "|I |IV |V |I |"
    chord_pattern = r'[|]?\s*([IiVv]+[°]?(?:7|maj7|m7)?)\s*[|]?'

    # Build sections list
    for section_name, measures in found_sections.items():
        sections.append(Section(
            name=section_name,
            measures=measures,
            chords=[],  # We'll enhance chord extraction later
        ))

    # Get BPM
    bpm = BPM_DATA.get(title, 120)

    return SongStructure(
        title=title,
        key=key,
        meter=meter,
        bpm=bpm,
        sections=sections,
        form=form,
        raw_analysis=text[:2000]  # Store first 2000 chars for reference
    )

def analyze_song(title: str) -> Optional[SongStructure]:
    """Fetch and parse a song's analysis."""
    code = SONG_CODES.get(title)
    if not code:
        print(f"No code found for: {title}")
        return None

    print(f"Fetching analysis for: {title} ({code})")
    html = fetch_pollack_page(code)
    if not html:
        return None

    return parse_pollack_analysis(html, title)

def main():
    """Analyze the songs from the user's list."""
    songs_to_analyze = [
        "She Loves You",
        "I Want to Hold Your Hand",
        "Eight Days a Week",
        "A Hard Day's Night",
        "I Feel Fine",
        "Day Tripper",
        "You've Got to Hide Your Love Away",
        "Norwegian Wood",
        "Help!",
        "Yellow Submarine",
        "Eleanor Rigby",
        "Getting Better",
        "With a Little Help from My Friends",
        "Lovely Rita",
        "Across the Universe",
    ]

    results = []

    for title in songs_to_analyze:
        structure = analyze_song(title)
        if structure:
            results.append(asdict(structure))
            print(f"  Key: {structure.key}")
            print(f"  Meter: {structure.meter}")
            print(f"  BPM: {structure.bpm}")
            print(f"  Form: {structure.form}")
            print(f"  Sections found: {len(structure.sections)}")
            for section in structure.sections:
                print(f"    - {section.name}: {section.measures} measures")
            print()

        time.sleep(0.5)  # Be nice to the server

    # Save results
    output_path = "/Users/robert/Desktop/hookpad_songs/beatles_structures.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved {len(results)} song structures to: {output_path}")

if __name__ == "__main__":
    main()
