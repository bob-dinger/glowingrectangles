"""Chord-usage analysis across UG tab files.

For each tab:
  1. Read Key + Capo from header metadata
  2. Extract chord tokens from chord lines (not lyric lines)
  3. Transpose by capo (chords as written are in fingered key; capo shifts UP)
  4. Convert each chord to its Roman-numeral function in the song's key
  5. Classify: diatonic, borrowed (and from which mode), or candidate secondary

Outputs aggregate stats: most common Roman numerals, borrowed-chord usage,
candidate secondary-dominant usage, and per-section non-diatonic ratio
(a proxy for key changes / modulation candidates).
"""
import os, re
from collections import Counter, defaultdict

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')

KEY_RE  = re.compile(r'Key:\s*([A-G][b#]?m?)', re.IGNORECASE)
CAPO_RE = re.compile(r'Capo:\s*([^\n]+?)(?:\s\s|\n|$)')
SEC_RE  = re.compile(r'^\s*\[([^\]]+)\]\s*$')

# Chord token regex: root + accidental + quality + extension + bass
CHORD_RE = re.compile(
    r'^([A-G])([#b])?(maj|min|m|aug|dim|sus[24]?|\+|°|ø)?(\d+)?(?:add\d+)?(?:[#b]\d+)*(?:/([A-G][#b]?))?$'
)

PC = {'C':0, 'C#':1, 'Db':1, 'D':2, 'D#':3, 'Eb':3, 'E':4, 'Fb':4, 'F':5, 'E#':5,
      'F#':6, 'Gb':6, 'G':7, 'G#':8, 'Ab':8, 'A':9, 'A#':10, 'Bb':10, 'B':11,
      'Cb':11, 'B#':0}
PC_NAME = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

MAJ_INT = {1:0, 2:2, 3:4, 4:5, 5:7, 6:9, 7:11}
MIN_INT = {1:0, 2:2, 3:3, 4:5, 5:7, 6:8, 7:10}

ORDINAL = {'no':0, '1st':1, '2nd':2, '3rd':3, '4th':4, '5th':5,
           '6th':6, '7th':7, '8th':8, '9th':9, '10th':10}


def parse_capo(s):
    s = s.lower().strip()
    if 'no capo' in s: return 0
    m = re.search(r'(\d+)', s)
    if m: return int(m.group(1)) % 12
    for w, n in ORDINAL.items():
        if w in s: return n
    return None


def is_chord_token(t):
    return bool(CHORD_RE.match(t))


def is_chord_line(line):
    """A line is a chord line iff every whitespace token matches the chord regex."""
    toks = line.split()
    if not toks or len(toks) > 25: return False
    return all(is_chord_token(t) for t in toks)


def parse_chord(tok):
    """Return (root_pc, quality_str) where quality is 'maj', 'min', 'dim', 'aug', or '7' for dom7."""
    m = CHORD_RE.match(tok)
    if not m: return None
    letter, acc, qual, ext, _bass = m.groups()
    root = PC[letter + (acc or '')]
    q = qual or ''
    is_min = q in ('m', 'min')
    is_dim = q in ('dim', '°', 'ø')
    is_aug = q in ('aug', '+')
    is_sus = q and q.startswith('sus')
    # dom7 detection: presence of 7 without maj/m
    is_dom7 = (ext == '7' and not is_min and not is_dim and not is_aug)
    if is_dim: quality = 'dim'
    elif is_aug: quality = 'aug'
    elif is_min: quality = 'min'
    elif is_sus: quality = 'sus'
    else: quality = 'maj'
    return root, quality, is_dom7


def transpose(pc, semitones):
    return (pc + semitones) % 12


# ---- Roman-numeral classification ----
# For a major key K, the diatonic chord pcs and qualities:
#   I (maj) at K+0, ii (min) at K+2, iii (min) at K+4, IV (maj) at K+5,
#   V (maj) at K+7, vi (min) at K+9, vii° (dim) at K+11
DIATONIC_MAJOR = {0:'I', 2:'ii', 4:'iii', 5:'IV', 7:'V', 9:'vi', 11:'vii°'}
DIATONIC_MINOR = {0:'i', 2:'ii°', 3:'bIII', 5:'iv', 7:'v', 8:'bVI', 10:'bVII'}
# Quality expected for each diatonic degree
EXPECTED_QUAL_MAJOR = {0:'maj', 2:'min', 4:'min', 5:'maj', 7:'maj', 9:'min', 11:'dim'}
EXPECTED_QUAL_MINOR = {0:'min', 2:'dim', 3:'maj', 5:'min', 7:'min', 8:'maj', 10:'maj'}

# Common borrow positions (chord pc → Roman label if borrowed)
BORROW_MAJOR = {1:'bII', 3:'bIII', 6:'#IV', 8:'bVI', 10:'bVII'}
# Quality changes (same pc, different quality)
QUALITY_BORROW_MAJOR = {
    (5, 'min'): 'iv (borrowed minor)',
    (7, 'min'): 'v (borrowed minor/dorian)',
    (0, 'min'): 'i (parallel minor tonic)',
    (2, 'maj'): 'II (lydian/V/V if leads to V)',
    (4, 'maj'): 'III (V/vi if leads to vi)',
    (9, 'maj'): 'VI (V/ii if leads to ii)',
    (11, 'maj'): 'VII (V/iii)',
}


def classify_in_major(chord_pc, quality, key_pc):
    """Return a label string for a chord in a major key."""
    rel = (chord_pc - key_pc) % 12
    if rel in DIATONIC_MAJOR:
        exp = EXPECTED_QUAL_MAJOR[rel]
        if quality in ('sus',) or quality == exp:
            return DIATONIC_MAJOR[rel], 'diatonic'
        # Quality mismatch — likely borrowed
        label = QUALITY_BORROW_MAJOR.get((rel, quality), f"{DIATONIC_MAJOR[rel]}({quality})")
        # If major chord on a normally-minor degree AND followed by V (5)? V/X handled at sequence level
        return label, 'quality-shift'
    # Non-diatonic root
    label = BORROW_MAJOR.get(rel, f"?({rel})")
    return label, 'chromatic'


# ---- Main analysis ----
def extract_song_chords(path, key_str, capo):
    """Return list of (section, chord_pc, quality, is_dom7) tuples."""
    tonic = key_str[:-1] if key_str.endswith('m') else key_str
    is_minor = key_str.endswith('m')
    key_pc = PC.get(tonic)
    if key_pc is None: return None, None
    chords = []
    current_section = '(intro)'
    for line in open(path, errors='replace'):
        m = SEC_RE.match(line)
        if m:
            current_section = m.group(1).strip()
            continue
        if not is_chord_line(line): continue
        for tok in line.split():
            parsed = parse_chord(tok)
            if not parsed: continue
            root, qual, dom7 = parsed
            # Transpose by capo (chord text is in fingered key; capo shifts UP to sounded)
            sounded = transpose(root, capo)
            chords.append((current_section, sounded, qual, dom7))
    return key_pc, is_minor, chords


def main():
    songs_processed = songs_w_borrow = songs_w_secondary = songs_w_section_modulation = 0
    roman_counter = Counter()
    borrow_counter = Counter()
    secondary_candidates = Counter()
    sample_secondary_songs = defaultdict(list)
    sample_borrow_songs = defaultdict(list)
    modulation_candidates = []

    for fn in sorted(os.listdir(UG_DIR)):
        if not fn.endswith('.txt'): continue
        path = os.path.join(UG_DIR, fn)
        head = open(path).read(500)
        km = KEY_RE.search(head); cm = CAPO_RE.search(head)
        if not km or not cm: continue
        key = km.group(1).strip()
        if key.endswith('m'): continue  # major only for now
        capo = parse_capo(cm.group(1))
        if capo is None: continue

        result = extract_song_chords(path, key, capo)
        if not result or not result[2]: continue
        key_pc, _is_minor, chords = result
        if not chords: continue
        songs_processed += 1

        # Per-song accounting
        song_has_borrow = False
        song_has_secondary = False
        per_section_nondiatonic = defaultdict(lambda: [0, 0])  # section → [nondia, total]

        for i, (sec, pc, q, dom7) in enumerate(chords):
            label, kind = classify_in_major(pc, q, key_pc)
            roman_counter[label] += 1
            per_section_nondiatonic[sec][1] += 1
            if kind != 'diatonic':
                per_section_nondiatonic[sec][0] += 1
                borrow_counter[label] += 1
                song_has_borrow = True
                if len(sample_borrow_songs[label]) < 8:
                    sample_borrow_songs[label].append(fn[:-4])
            # Secondary-dominant candidate: a major-quality chord with dom7 (or sometimes without)
            # whose pc is +7 from the NEXT chord's pc
            if i + 1 < len(chords):
                nxt_pc = chords[i+1][1]
                target_relative = (nxt_pc - key_pc) % 12
                if q == 'maj' and ((pc - nxt_pc) % 12) == 7 and target_relative != 0:
                    # Skip if it's just V → I (= V → root, both diatonic & expected)
                    # Detect when current chord is non-diatonic OR has dom7
                    sec_label, _ = classify_in_major(pc, q, key_pc)
                    if kind != 'diatonic' or dom7:
                        target_roman = DIATONIC_MAJOR.get(target_relative, f"({target_relative})")
                        sec_key = f"V/{target_roman}"
                        secondary_candidates[sec_key] += 1
                        song_has_secondary = True
                        if len(sample_secondary_songs[sec_key]) < 8:
                            sample_secondary_songs[sec_key].append(fn[:-4])

        if song_has_borrow: songs_w_borrow += 1
        if song_has_secondary: songs_w_secondary += 1

        # Section-modulation candidate: any section where >40% of chords are non-diatonic
        flagged_sections = []
        for sec, (nd, tot) in per_section_nondiatonic.items():
            if tot >= 4 and nd / tot >= 0.4:
                flagged_sections.append((sec, nd, tot))
        if flagged_sections:
            songs_w_section_modulation += 1
            modulation_candidates.append((fn[:-4], flagged_sections))

    print(f"=== UG MAJOR-KEY corpus chord analysis ({songs_processed} songs) ===\n")
    print(f"Songs containing at least one BORROWED chord:    {songs_w_borrow}  ({100*songs_w_borrow/songs_processed:.1f}%)")
    print(f"Songs with at least one SECONDARY-DOMINANT cand: {songs_w_secondary}  ({100*songs_w_secondary/songs_processed:.1f}%)")
    print(f"Songs with a section >=40% non-diatonic (mod?):  {songs_w_section_modulation}  ({100*songs_w_section_modulation/songs_processed:.1f}%)")

    print(f"\n=== Most common Roman numerals (chord-level counts) ===")
    for r, n in roman_counter.most_common(20):
        bar = '█' * (n // 200)
        print(f"  {r:<30s} {n:>5}  {bar}")

    print(f"\n=== Top BORROWED chord labels ===")
    for r, n in borrow_counter.most_common(15):
        examples = sample_borrow_songs.get(r, [])[:3]
        ex = ', '.join(examples)
        print(f"  {r:<30s} {n:>4}  ({ex})")

    print(f"\n=== Candidate secondary-dominants ===")
    for r, n in secondary_candidates.most_common(15):
        examples = sample_secondary_songs.get(r, [])[:3]
        ex = ', '.join(examples)
        print(f"  {r:<10s} {n:>4}  ({ex})")

    print(f"\n=== Top modulation candidates (sections >=40% non-diatonic) ===")
    for fn, flagged in modulation_candidates[:25]:
        sec_str = '; '.join(f"[{s}] {nd}/{tot}" for s, nd, tot in flagged[:3])
        print(f"  {fn:<55s} {sec_str}")


if __name__ == '__main__':
    main()
