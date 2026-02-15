#!/usr/bin/env python3
"""
Build Beatles Song Database

Populates key, BPM, duration, and total measures for all Beatles songs.
Structure arrays left empty for manual entry.

Run:
  cd ~/Desktop && source midi_env/bin/activate && python glowinggardens_claude/build_beatles_database.py
"""

import json
import time

# Complete Beatles song list from Pollack's index
# Format: (title, code, key, bpm, duration_sec)
# Key and BPM from research, duration from Spotify/standard releases

BEATLES_CATALOG = [
    # Please Please Me (1963)
    ("I Saw Her Standing There", "ishst", "E", 163, 175),
    ("Misery", "m1", "C", 134, 110),
    ("Anna (Go to Him)", "covers1", "D", 128, 170),  # Cover
    ("Chains", "covers1", "Bb", 129, 147),  # Cover
    ("Boys", "covers1", "E", 163, 145),  # Cover
    ("Ask Me Why", "amw", "E", 133, 145),
    ("Please Please Me", "ppm", "E", 138, 120),
    ("Love Me Do", "lmd", "G", 148, 142),
    ("P.S. I Love You", "psily", "D", 126, 124),
    ("Baby It's You", "covers1", "E", 118, 161),  # Cover
    ("Do You Want to Know a Secret", "dywtkas", "E", 123, 117),
    ("A Taste of Honey", "covers1", "F#m", 125, 123),  # Cover
    ("There's a Place", "tap", "E", 134, 110),
    ("Twist and Shout", "covers1", "D", 125, 155),  # Cover

    # With the Beatles (1963)
    ("It Won't Be Long", "iwbl", "E", 138, 130),
    ("All I've Got to Do", "aigtd", "E", 117, 124),
    ("All My Loving", "aml", "E", 156, 125),
    ("Don't Bother Me", "dbm", "Em", 122, 146),
    ("Little Child", "lc", "E", 129, 103),
    ("Till There Was You", "covers2", "F", 120, 134),  # Cover
    ("Please Mister Postman", "covers2", "A", 134, 149),  # Cover
    ("Roll Over Beethoven", "covers2", "D", 166, 170),  # Cover
    ("Hold Me Tight", "hmt", "C", 145, 154),
    ("You Really Got a Hold on Me", "covers2", "A", 131, 182),  # Cover
    ("I Wanna Be Your Man", "iwbym", "E", 142, 118),
    ("Devil in Her Heart", "covers2", "Bb", 128, 154),  # Cover
    ("Not a Second Time", "nast", "G", 121, 130),
    ("Money", "covers2", "Em", 145, 170),  # Cover

    # A Hard Day's Night (1964)
    ("A Hard Day's Night", "ahdn", "G", 139, 154),
    ("I Should Have Known Better", "ishkb", "G", 144, 166),
    ("If I Fell", "iif", "D", 102, 142),
    ("I'm Happy Just to Dance with You", "ihjtdwy", "E", 140, 116),
    ("And I Love Her", "ailh", "E", 122, 150),
    ("Tell Me Why", "tmw", "D", 149, 137),
    ("Can't Buy Me Love", "cbml", "C", 176, 135),
    ("Any Time at All", "ataa", "D", 143, 133),
    ("I'll Cry Instead", "ici", "G", 167, 105),
    ("Things We Said Today", "twst", "A", 138, 156),
    ("When I Get Home", "wigh", "A", 148, 137),
    ("You Can't Do That", "ycdt", "G", 153, 155),
    ("I'll Be Back", "ibb", "A", 124, 140),

    # Beatles for Sale (1964)
    ("No Reply", "nr", "C", 134, 136),
    ("I'm a Loser", "ial", "G", 150, 146),
    ("Baby's in Black", "bib", "A", 110, 125),
    ("Rock and Roll Music", "covers3", "Bb", 180, 147),  # Cover
    ("I'll Follow the Sun", "ifts", "C", 116, 113),
    ("Mr. Moonlight", "covers3", "E", 130, 162),  # Cover
    ("Kansas City/Hey-Hey-Hey-Hey!", "covers3", "G", 162, 156),  # Cover
    ("Eight Days a Week", "edaw", "D", 138, 163),
    ("Words of Love", "covers3", "A", 130, 132),  # Cover
    ("Honey Don't", "covers3", "E", 150, 166),  # Cover
    ("Every Little Thing", "elt", "A", 130, 125),
    ("I Don't Want to Spoil the Party", "idwtstp", "G", 131, 146),
    ("What You're Doing", "wyd", "D", 150, 162),
    ("Everybody's Trying to Be My Baby", "covers3", "E", 158, 140),  # Cover

    # Help! (1965)
    ("Help!", "h!", "A", 95, 139),
    ("The Night Before", "tnb", "D", 142, 153),
    ("You've Got to Hide Your Love Away", "ygthyla", "G", 184, 129),
    ("I Need You", "iny", "A", 118, 148),
    ("Another Girl", "ag", "A", 142, 124),
    ("You're Going to Lose That Girl", "ygtltg", "E", 126, 140),
    ("Ticket to Ride", "ttr", "A", 117, 191),
    ("Act Naturally", "covers4", "G", 110, 149),  # Cover
    ("It's Only Love", "iol", "C", 130, 115),
    ("You Like Me Too Much", "ylmtm", "G", 120, 156),
    ("Tell Me What You See", "tmwys", "G", 125, 139),
    ("I've Just Seen a Face", "ijsaf", "A", 168, 127),
    ("Yesterday", "y", "F", 98, 125),
    ("Dizzy Miss Lizzy", "covers4", "A", 178, 165),  # Cover

    # Rubber Soul (1965)
    ("Drive My Car", "dmc", "D", 125, 157),
    ("Norwegian Wood", "nw", "E", 177, 125),
    ("You Won't See Me", "ywsm", "A", 120, 201),
    ("Nowhere Man", "nm", "E", 120, 164),
    ("Think for Yourself", "tfy", "G", 133, 138),
    ("The Word", "tw", "D", 130, 161),
    ("Michelle", "m4", "F", 118, 160),
    ("What Goes On", "wgo", "E", 132, 169),
    ("Girl", "g", "Cm", 120, 153),
    ("I'm Looking Through You", "ilty", "Ab", 180, 147),
    ("In My Life", "iml", "A", 103, 147),
    ("Wait", "w", "A", 128, 136),
    ("If I Needed Someone", "iins", "A", 131, 144),
    ("Run for Your Life", "rfyl", "D", 150, 138),

    # Revolver (1966)
    ("Taxman", "t", "D", 122, 158),
    ("Eleanor Rigby", "er", "Em", 137, 125),
    ("I'm Only Sleeping", "ios", "Em", 100, 181),
    ("Love You To", "lyt", "C", 115, 182),
    ("Here, There and Everywhere", "htae", "G", 84, 145),
    ("Yellow Submarine", "ys", "G", 111, 159),
    ("She Said She Said", "ssss", "Bb", 140, 157),
    ("Good Day Sunshine", "gds", "A", 118, 129),
    ("And Your Bird Can Sing", "aybcs", "E", 126, 120),
    ("For No One", "fno", "B", 86, 122),
    ("Doctor Robert", "dr", "A", 120, 137),
    ("I Want to Tell You", "iwtty", "A", 120, 149),
    ("Got to Get You into My Life", "gtgyiml", "G", 125, 148),
    ("Tomorrow Never Knows", "tnk", "C", 125, 178),

    # Sgt. Pepper (1967)
    ("Sgt. Pepper's Lonely Hearts Club Band", "splhcb", "G", 96, 122),
    ("With a Little Help from My Friends", "walhfmf", "E", 112, 164),
    ("Lucy in the Sky with Diamonds", "litswd", "A", 128, 207),
    ("Getting Better", "gb", "C", 122, 167),
    ("Fixing a Hole", "fah", "F", 113, 156),
    ("She's Leaving Home", "slh", "E", 95, 215),
    ("Being for the Benefit of Mr. Kite!", "bftbomk", "Dm", 110, 157),
    ("Within You Without You", "wywy", "C#", 110, 304),
    ("When I'm Sixty-Four", "wisf", "C", 140, 157),
    ("Lovely Rita", "lr", "E", 88, 164),
    ("Good Morning Good Morning", "gmgm", "A", 120, 161),
    ("Sgt. Pepper's Lonely Hearts Club Band (Reprise)", "aditl", "G", 120, 79),
    ("A Day in the Life", "aditl", "G", 78, 335),

    # Magical Mystery Tour (1967)
    ("Magical Mystery Tour", "mmt", "E", 192, 169),
    ("The Fool on the Hill", "foth", "D", 75, 180),
    ("Flying", "f", "C", 150, 138),
    ("Blue Jay Way", "bjw", "C", 105, 239),
    ("Your Mother Should Know", "ymsk", "A", 110, 149),
    ("I Am the Walrus", "iatw", "A", 86, 274),
    ("Hello, Goodbye", "hg", "C", 108, 210),
    ("Strawberry Fields Forever", "sff", "Bb", 92, 250),
    ("Penny Lane", "pl", "B", 114, 180),
    ("All You Need Is Love", "aynil", "G", 104, 237),
    ("Baby You're a Rich Man", "byarm", "G", 110, 182),

    # The Beatles (White Album) (1968)
    ("Back in the U.S.S.R.", "bitu", "A", 144, 163),
    ("Dear Prudence", "dp", "D", 140, 236),
    ("Glass Onion", "go", "Am", 114, 130),
    ("Ob-La-Di, Ob-La-Da", "oo", "Bb", 114, 189),
    ("Wild Honey Pie", "whp", "G", 110, 52),
    ("The Continuing Story of Bungalow Bill", "tcsobb", "C", 119, 187),
    ("While My Guitar Gently Weeps", "wmggw", "Am", 116, 284),
    ("Happiness Is a Warm Gun", "hiawg", "Am", 72, 163),
    ("Martha My Dear", "mmd", "Eb", 152, 148),
    ("I'm So Tired", "ist", "A", 76, 123),
    ("Blackbird", "b2", "G", 94, 138),
    ("Piggies", "p", "Ab", 88, 124),
    ("Rocky Raccoon", "rr", "Am", 166, 213),
    ("Don't Pass Me By", "dpmb", "C", 120, 228),
    ("Why Don't We Do It in the Road?", "wdwdiitr", "D", 100, 101),
    ("I Will", "iw", "F", 104, 105),
    ("Julia", "j", "D", 86, 168),
    ("Birthday", "b", "A", 139, 168),
    ("Yer Blues", "yb", "E", 79, 240),
    ("Mother Nature's Son", "mns", "D", 109, 162),
    ("Everybody's Got Something to Hide Except Me and My Monkey", "egsthefmamm", "E", 170, 145),
    ("Sexy Sadie", "ss", "F", 116, 188),
    ("Helter Skelter", "hs", "E", 94, 270),
    ("Long, Long, Long", "lll", "F", 98, 186),
    ("Revolution 1", "r", "A", 59, 258),
    ("Honey Pie", "hp", "G", 108, 156),
    ("Savoy Truffle", "st", "E", 130, 155),
    ("Cry Baby Cry", "cbc", "Em", 118, 189),
    ("Revolution 9", "r9", "N/A", 100, 496),
    ("Good Night", "gn", "G", 74, 192),

    # Yellow Submarine (1969)
    ("Only a Northern Song", "oans", "Gb", 125, 206),
    ("All Together Now", "atn", "G", 110, 131),
    ("Hey Bulldog", "hb", "B", 102, 190),
    ("It's All Too Much", "iatm", "G", 125, 384),

    # Abbey Road (1969)
    ("Come Together", "ct", "Dm", 82, 259),
    ("Something", "s", "C", 66, 182),
    ("Maxwell's Silver Hammer", "msh", "D", 111, 207),
    ("Oh! Darling", "od", "A", 84, 206),
    ("Octopus's Garden", "og", "E", 96, 171),
    ("I Want You (She's So Heavy)", "iwyssh", "Dm", 74, 467),
    ("Here Comes the Sun", "hcts", "A", 129, 185),
    ("Because", "b4", "C#m", 91, 165),
    ("You Never Give Me Your Money", "yngmym", "Am", 110, 242),
    ("Sun King", "sk", "E", 126, 146),
    ("Mean Mr. Mustard", "mmm", "E", 126, 66),
    ("Polythene Pam", "pp", "E", 180, 72),
    ("She Came in Through the Bathroom Window", "scittbw", "A", 96, 117),
    ("Golden Slumbers", "gs", "Am", 76, 91),
    ("Carry That Weight", "ctw", "C", 91, 97),
    ("The End", "te", "A", 112, 141),
    ("Her Majesty", "hm", "D", 134, 23),

    # Let It Be (1970)
    ("Two of Us", "tou", "G", 122, 214),
    ("Dig a Pony", "dap", "A", 84, 224),
    ("Across the Universe", "atu", "D", 76, 228),
    ("I Me Mine", "imm", "Am", 80, 140),
    ("Dig It", "di", "G", 100, 51),
    ("Let It Be", "lib", "C", 73, 243),
    ("Maggie Mae", "mmfrag", "D", 160, 40),
    ("I've Got a Feeling", "igaf", "A", 132, 223),
    ("One After 909", "oa909", "B", 152, 177),
    ("The Long and Winding Road", "tlawr", "Eb", 73, 222),
    ("For You Blue", "fyb", "D", 127, 152),
    ("Get Back", "gb2", "A", 120, 190),

    # Singles/Others
    ("She Loves You", "sly", "G", 151, 141),
    ("I Want to Hold Your Hand", "iwthyh", "G", 131, 145),
    ("From Me to You", "fmty", "C", 127, 117),
    ("Thank You Girl", "tyg", "D", 120, 118),
    ("I'll Get You", "igy", "D", 137, 132),
    ("This Boy", "tb", "D", 76, 135),
    ("I Feel Fine", "iff", "G", 178, 139),
    ("She's a Woman", "saw", "A", 157, 180),
    ("I'm Down", "id", "G", 168, 145),
    ("Day Tripper", "dt", "E", 137, 169),
    ("We Can Work It Out", "wcwio", "D", 115, 136),
    ("Paperback Writer", "pw_and_r", "G", 160, 144),
    ("Rain", "pw_and_r", "G", 112, 178),
    ("Lady Madonna", "lm", "A", 104, 142),
    ("The Inner Light", "til", "C#", 116, 152),
    ("Hey Jude", "hj", "F", 74, 431),
    ("Revolution (Single)", "r", "A", 124, 207),
    ("Don't Let Me Down", "dlmd", "E", 130, 213),
    ("The Ballad of John and Yoko", "tbojay", "E", 132, 178),
    ("Old Brown Shoe", "obs", "C", 160, 186),
    ("Free as a Bird", "faab", "A", 95, 264),
    ("Real Love", "rl", "E", 92, 233),
]

def calculate_measures(duration_sec, bpm):
    """Calculate total measures from duration and BPM."""
    return round((duration_sec * bpm) / 240)

def build_database():
    """Build the complete Beatles database."""
    songs = []

    for title, code, key, bpm, duration_sec in BEATLES_CATALOG:
        total_measures = calculate_measures(duration_sec, bpm)

        song = {
            "title": title,
            "artist": "The Beatles",
            "code": code,
            "key": key,
            "bpm": bpm,
            "duration_sec": duration_sec,
            "total_measures": total_measures,
            "structure": [],  # Empty for manual entry
            "notes": ""
        }
        songs.append(song)

    return songs

def main():
    print("Building Beatles database...")
    songs = build_database()

    # Sort by title
    songs.sort(key=lambda x: x['title'])

    output = {
        "description": "Beatles song database - structure arrays to be filled manually",
        "total_songs": len(songs),
        "songs": songs
    }

    output_path = "/Users/robert/Desktop/hookpad_songs/beatles_complete.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nCreated database with {len(songs)} songs")
    print(f"Saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("BEATLES CATALOG SUMMARY")
    print("=" * 60)

    # Stats
    total_duration = sum(s['duration_sec'] for s in songs)
    avg_bpm = sum(s['bpm'] for s in songs) / len(songs)

    print(f"Total songs: {len(songs)}")
    print(f"Total duration: {total_duration // 3600}h {(total_duration % 3600) // 60}m")
    print(f"Average BPM: {avg_bpm:.0f}")

    # Key distribution
    keys = {}
    for s in songs:
        k = s['key']
        keys[k] = keys.get(k, 0) + 1

    print("\nTop keys:")
    for k, count in sorted(keys.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k}: {count} songs")

if __name__ == "__main__":
    main()
