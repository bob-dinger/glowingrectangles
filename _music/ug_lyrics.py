"""Extract lyrics per section from local UG tab text files.

Tabs live at ~/Desktop/music/ug_tabs/{artist-slug}_{title-slug}.txt
Format: [SectionName] headers, chord lines (all tokens look like chords), lyric lines.

Public API:
    find_tab(artist, title) -> path or None
    extract_lyrics_by_section(tab_path) -> {section_name: [lyric_line, ...]}
    normalize_section_name(s) -> canonical name for matching to Hookpad section names
"""
import os, re

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')

# Chord token: A-G + optional accidental + quality + extension + bass
CHORD_RE = re.compile(
    r'^([A-G])'
    r'([#b])?'
    r'(maj|min|m|aug|dim|sus[24]?|\+|°|ø)?'
    r'(\d+)?'
    r'(?:add\d+)?'
    r'(?:[#b]\d+)*'
    r'(?:/([A-G][#b]?))?'
    r'$'
)
SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$')


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[''′`]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def find_tab(artist: str, title: str):
    """Find a UG tab path for the given artist + title. Fuzzy-match on filename."""
    if not os.path.isdir(UG_DIR):
        return None
    a = slugify(artist)
    t = slugify(title)
    files = [fn for fn in os.listdir(UG_DIR) if fn.endswith('.txt')]
    best, best_score = None, 0
    for fn in files:
        base = fn[:-4].lower()
        if '_' not in base: continue
        fa, ft = base.split('_', 1)
        score = 0
        # Title match (heavier weight)
        if t == ft: score += 8
        elif t in ft or ft in t: score += 5
        # Artist match
        if a == fa: score += 5
        elif a in fa or fa in a: score += 3
        # Word overlap
        for w in t.split('-'):
            if len(w) > 2 and w in ft: score += 1
        for w in a.split('-'):
            if len(w) > 2 and w in fa: score += 1
        if score > best_score:
            best_score, best = score, fn
    return os.path.join(UG_DIR, best) if best_score >= 6 else None


def is_chord_line(line: str) -> bool:
    """True if every whitespace-separated token looks like a chord."""
    toks = line.split()
    if not toks: return False
    if len(toks) > 30: return False  # likely a lyric line crammed with words
    return all(bool(CHORD_RE.match(t)) for t in toks)


def is_lyric_line(line: str) -> bool:
    s = line.strip()
    if not s: return False
    if SECTION_RE.match(line): return False
    if is_chord_line(line): return False
    if s.startswith('#') or s.startswith('//'): return False
    # Tab-like notation lines (E|---0---|) — skip
    if re.match(r'^[A-G][|]', s): return False
    # Metadata: "Capo:", "Tuning:", "tabbed by:" etc.
    if re.match(r'^(capo|tuning|tabbed|key|tempo|bpm)\s*:', s, re.IGNORECASE): return False
    # View/save metadata UG injects
    if re.match(r'^\d+(,\d{3})*\s+(views|saves|comments)', s): return False
    return True


_SEC_ALIASES = {
    'pre verse': 'pre-verse',
    'preverse': 'pre-verse',
    'pre chorus': 'pre-chorus',
    'prechorus': 'pre-chorus',
    'pre-chorus': 'pre-chorus',
    'post chorus': 'post-chorus',
    'postchorus': 'post-chorus',
    'intro': 'intro',
    'outro': 'outro',
    'verse': 'verse',
    'chorus': 'chorus',
    'bridge': 'bridge',
    'solo': 'solo',
    'interlude': 'interlude',
    'instrumental': 'instrumental',
    'breakdown': 'breakdown',
    'refrain': 'refrain',
    'tag': 'tag',
}

def normalize_section_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r'\s*\d+\s*$', '', n).strip()  # drop trailing number ("Verse 1")
    n = re.sub(r'[_]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return _SEC_ALIASES.get(n, n)


def extract_lyrics_by_section(tab_path: str) -> dict:
    """Return {normalized_section_name: [lyric_lines]} for the tab file.

    If the same section name appears twice (e.g. Verse 1 and Verse 2 both normalize to 'verse'),
    we keep the FIRST occurrence's lyrics (so 'verse' returns Verse 1's content). Both are
    preserved under their raw normalized names if they differ.
    """
    with open(tab_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    out = {}
    current = None
    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            current = normalize_section_name(m.group(1))
            # Only initialize if first occurrence
            if current not in out:
                out[current] = []
            continue
        if current is None: continue
        if is_lyric_line(line):
            out[current].append(line.strip())
    return {k: v for k, v in out.items() if v}


def end_word(lyric_line: str) -> str:
    """Return the last bare word of a lyric line (lowercase, no punctuation)."""
    # Drop bracketed annotations like (x2), [solo], etc.
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', lyric_line)
    words = re.findall(r"[A-Za-z']+", s)
    return words[-1].lower() if words else ''


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('usage: ug_lyrics.py <artist> <title>')
        sys.exit(1)
    path = find_tab(sys.argv[1], sys.argv[2])
    if not path:
        print(f'no tab found for {sys.argv[1]} / {sys.argv[2]}')
        sys.exit(1)
    print(f'tab: {path}')
    lyrics = extract_lyrics_by_section(path)
    for sec, lines in lyrics.items():
        print(f'\n[{sec}]')
        for ln in lines:
            print(f'  {ln}    →  {end_word(ln)!r}')
