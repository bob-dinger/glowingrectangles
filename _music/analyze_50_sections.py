"""Look up and analyze user-curated sections for phrase-structure study.

For each (title, section_name) pair:
  - Resolve to a Supabase row
  - Find the named section in hookpad_json.sections
  - Extract melody (sd sequence, bars, n_notes)
  - Run motif detection
  - Detect phrase structure (AA, AABA, ABCB, etc.) by splitting into
    candidate phrase lengths (2-bar, 4-bar) and labeling chunks by similarity

Output is a markdown-style report.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_melodies import extract_song_melodies
from melody_motifs import find_motifs
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

from ug_lyrics import find_tab, extract_lyrics_by_section, end_word, normalize_section_name

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])


def get_lyrics_and_rhyme(song, section_name, hookpad_json, s_beat, e_beat):
    """Return (lyric_lines, end_words, source).

    Hookpad is the canonical source (lyrics are note-aligned, and user will add
    rhyme/bleed/structure symbology there). UG is a bridge fallback for songs whose
    Hookpad lyric field is still empty. Each song auto-switches to Hookpad once
    populated — no code change needed per song.
    """
    lines, ends = extract_section_lyrics(hookpad_json, s_beat, e_beat)
    if lines:
        return lines, ends, 'Hookpad'
    tab = find_tab(song['artist'], song['title'])
    if tab:
        ug = extract_lyrics_by_section(tab)
        target = normalize_section_name(section_name)
        if target in ug:
            ug_lines = ug[target]
            ug_ends = [end_word(l) for l in ug_lines]
            return ug_lines, ug_ends, 'UG'
    return [], [], None

CORPUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'melody_corpus.json')


def load_corpus():
    """Read the curated section list from melody_corpus.json."""
    with open(CORPUS_FILE) as f:
        data = json.load(f)
    return [(s['title'], s['section'], s.get('artist')) for s in data['sections']]


CORPUS = load_corpus()


def extract_section_lyrics(hookpad_json, sec_s_beat, sec_e_beat):
    """Extract lyric lines that belong to a section.

    Hookpad stores lyrics as one big string in `lyrics.values[0]` with whitespace-separated
    syllables and newline-separated lines. Each whitespace-separated TOKEN (excluding bracket
    markers like [V], [C]) maps sequentially to the song's non-rest notes.

    We pull notes in this section by beat range, find their indices in the global notes
    array, and grab the corresponding lyric tokens — then re-assemble by line.

    Returns (lyric_lines, end_words). end_words = last bare word per line (for rhyme).
    """
    import re
    if isinstance(hookpad_json, str): hookpad_json = json.loads(hookpad_json)
    lyr_dict = hookpad_json.get('lyrics') or {}
    vals = lyr_dict.get('values') or []
    if not vals or not vals[0]: return [], []
    lyric_text = vals[0]

    all_notes = hookpad_json.get('notes') or []
    # All non-rest notes in song order (so we can index syllables to notes)
    non_rest = [(i, n) for i, n in enumerate(all_notes) if not n.get('isRest')]
    # Build the syllable-token list with line indices, skipping bracket markers
    # and continuation tokens like _1_.
    tokens = []  # (line_idx, token_text)
    for line_idx, line in enumerate(lyric_text.splitlines()):
        for tok in line.split():
            # Strip section markers like [V] [c] [i ] [ch] [pc] etc.
            t = re.sub(r'\[[A-Za-z]{1,3}\s?\]', '', tok)
            if not t: continue
            # _N_ tokens are melisma continuation markers — they still consume a note
            tokens.append((line_idx, t))

    # Match tokens to non-rest notes by index. We assume sequential alignment.
    # Some songs have more tokens than notes or vice versa; clamp to min.
    n_pairs = min(len(tokens), len(non_rest))

    # Identify token indices that fall in this section's beat range
    section_token_indices = []
    for ti in range(n_pairs):
        _, note = non_rest[ti]
        if sec_s_beat <= note['beat'] < sec_e_beat:
            section_token_indices.append(ti)
    if not section_token_indices: return [], []

    # Group tokens by line, but only include those whose token-index is in this section
    lines = {}
    for ti in section_token_indices:
        line_idx, tok = tokens[ti]
        lines.setdefault(line_idx, []).append(tok)

    out_lines = []
    end_words = []
    for line_idx in sorted(lines.keys()):
        line_text = ' '.join(lines[line_idx])
        out_lines.append(line_text)
        # Last bare word (strip _N_ tokens, punctuation)
        bare_words = [w for w in lines[line_idx]
                      if not re.match(r'^_\d+_$', w) and re.search(r'[A-Za-z]', w)]
        if bare_words:
            ew = re.sub(r"[^A-Za-z']", '', bare_words[-1]).lower()
            end_words.append(ew)
        else:
            end_words.append('')
    return out_lines, end_words


def rhyme_letters(end_words):
    """Cluster end_words by rhyme (slant rhyme tolerated — same vowel sound is enough).

    Pop lyrics frequently use slant rhymes (days/stay, room/move, mind/find/wine).
    We cluster on the last stressed vowel phoneme — that catches both perfect and slant.
    """
    import re
    try:
        import cmudict
        cmu = cmudict.dict()
    except Exception:
        cmu = {}

    # Phonemes considered vowels in CMU dict
    VOWEL_PHONES = {'AA','AE','AH','AO','AW','AY','EH','ER','EY','IH','IY','OW','OY','UH','UW'}

    def rhyme_key(w):
        if not w: return None
        if w in cmu and cmu[w]:
            phones = cmu[w][0]
            # Find the LAST stressed vowel — that's the rhyme-bearing nucleus
            for i in range(len(phones) - 1, -1, -1):
                p = phones[i]
                if p[:2] in VOWEL_PHONES and p[-1] in '12':
                    return ('cmu', p[:2])  # vowel only (slant rhyme)
            # Fallback: any last vowel
            for i in range(len(phones) - 1, -1, -1):
                p = phones[i]
                if p[:2] in VOWEL_PHONES:
                    return ('cmu', p[:2])
        # Heuristic for unknown words: last vowel sound (just the vowel cluster)
        m = re.search(r'([aeiouy]+)[^aeiouy]*$', w.lower())
        return ('approx', m.group(1)) if m else None

    seen = []  # (rhyme_key, letter)
    labels = []
    next_letter = 'A'
    for w in end_words:
        k = rhyme_key(w)
        if not k:
            labels.append('·')
            continue
        matched = False
        for sk, sl in seen:
            if sk == k:
                labels.append(sl); matched = True; break
        if not matched:
            seen.append((k, next_letter))
            labels.append(next_letter)
            next_letter = chr(ord(next_letter) + 1)
    return ''.join(labels)


def lookup_song(title_sub, artist_hint=None):
    """Find best song match for a title substring + optional artist hint."""
    q = SB.schema('parcels').table('songs').select(
        'artist,title,key_tonic,key_scale,bpm,hookpad_json'
    ).ilike('title', f'%{title_sub}%').not_.is_('hookpad_json', 'null')
    if artist_hint:
        q = q.ilike('artist', f'%{artist_hint}%')
    rows = q.limit(20).execute().data
    if not rows: return None
    # Prefer the row whose title most closely matches (shortest title containing the sub)
    rows.sort(key=lambda r: (len(r['title']), r['title']))
    return rows[0]


def find_section(secs, name_sub):
    """Return the section dict whose name best matches name_sub.

    Priority: exact word match > whole-name match (case insensitive) > substring (but
    NOT inside a longer compound like 'pre-chorus' matching 'chorus').
    """
    import re
    nm = name_sub.lower().strip()
    candidates = [s for s in secs if s['n_notes'] > 0]
    if not candidates: return None
    # 1. Exact case-insensitive match
    for s in candidates:
        if s['name'].lower().strip() == nm:
            return s
    # 2. Word-boundary match (e.g., 'chorus' matches 'Chorus' or 'Intro/Chorus'
    #    but NOT 'pre-chorus' or 'Bridge-chorus')
    pat = re.compile(rf'\b{re.escape(nm)}\b', re.IGNORECASE)
    for s in candidates:
        # Replace hyphens with spaces so word boundary respects them
        normed = s['name'].replace('-', ' ').lower()
        if pat.search(normed):
            return s
    # 3. Last resort: substring (only if no word-boundary hit)
    for s in candidates:
        if nm in s['name'].lower():
            return s
    return None


# ---------- phrase-structure detection ----------

def label_chunks_by_similarity(chunks):
    """Given a list of chunks (each a tuple of sd-tokens), assign letter labels A B C...
    by exact-match clustering. Returns a string like 'AABA'."""
    seen = []  # (representative_chunk, letter)
    labels = []
    next_letter = 'A'
    for c in chunks:
        # Look for an exact match first
        for rep, lbl in seen:
            if rep == c:
                labels.append(lbl); break
        else:
            seen.append((c, next_letter))
            labels.append(next_letter)
            next_letter = chr(ord(next_letter) + 1)
    return ''.join(labels)


def edit_distance(a, b):
    """Standard Levenshtein on two iterables of tokens."""
    if a == b: return 0
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j-1] + 1, prev[j] + 1, prev[j-1] + cost)
        prev = curr
    return prev[-1]


def lcs_len(a, b):
    """Longest common subsequence length (not substring)."""
    if not a or not b: return 0
    if len(a) < len(b): a, b = b, a
    prev = [0] * (len(b) + 1)
    for ca in a:
        curr = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            if ca == cb:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(curr[j - 1], prev[j])
        prev = curr
    return prev[-1]


def similar(a, b, edit_tol=0.3, lcs_tol=0.85, lcs_min_len=10):
    """Are chunks `a` and `b` melodically similar?

    Two-test rule:
      (1) Edit distance: edit(a,b) / max(|a|, |b|) <= edit_tol — catches small
          substitutions / rhythmic variants of similar length
      (2) LCS overlap (only when both chunks are >= lcs_min_len notes):
          LCS(a,b) / min(|a|, |b|) >= lcs_tol — catches "A is contained in B with
          extension/ornamentation" (e.g. I'm Looking Through You's 4+4 where the
          second phrase elaborates the first)

    LCS is gated by lcs_min_len because for short chunks (single-bar measures),
    coincidental subsequence overlap is too easy and over-collapses everything.

    Returns (is_similar, normalized_edit_distance).
    """
    if a == b: return True, 0.0
    if not a or not b: return False, 1.0
    d = edit_distance(a, b) / max(len(a), len(b))
    if d <= edit_tol:
        return True, d
    if min(len(a), len(b)) >= lcs_min_len:
        if lcs_len(a, b) / min(len(a), len(b)) >= lcs_tol:
            return True, d
    return False, d


def label_with_variation(chunks, tol=0.3):
    """Mark near-matches with a prime: A vs A'. Uses normalized edit distance ≤ tol."""
    seen = []  # (representative_chunk, base_letter, variant_count)
    labels = []
    next_letter = 'A'
    for c in chunks:
        matched = False
        for entry in seen:
            rep, lbl, _ = entry
            ok, d = similar(rep, c, tol)
            if ok:
                if d == 0.0:
                    labels.append(lbl)
                else:
                    entry[2] += 1
                    labels.append(lbl + "'" * entry[2])
                matched = True
                break
        if not matched:
            seen.append([c, next_letter, 0])
            labels.append(next_letter)
            next_letter = chr(ord(next_letter) + 1)
    return ''.join(labels)


def label_with_fuzzy(chunks, tol=0.3):
    """Like label_chunks_by_similarity but treats near-matches as the same letter
    (no prime). Used to compute the 'cleanest' structure."""
    seen = []  # (representative_chunk, letter)
    labels = []
    next_letter = 'A'
    for c in chunks:
        matched = False
        for rep, lbl in seen:
            ok, _ = similar(rep, c, tol)
            if ok:
                labels.append(lbl); matched = True; break
        if not matched:
            seen.append((c, next_letter))
            labels.append(next_letter)
            next_letter = chr(ord(next_letter) + 1)
    return ''.join(labels)


def detect_phrase_structure(sd_seq, notes_raw, beats_per_bar, total_bars):
    """Try common phrase lengths (1, 2, 4 bars) and return the cleanest structure.

    'Cleanest' = the one with the fewest distinct letters (most internal repetition).
    Returns: list of {'phrase_bars', 'chunks_sd', 'letters', 'letters_var'}
    """
    if total_bars < 2: return []
    results = []
    # Try 2-bar and 4-bar splits primarily; 1-bar is too noisy as a default.
    for phrase_bars in (2, 4, 1):
        if total_bars % phrase_bars != 0: continue
        n_phrases = total_bars // phrase_bars
        if n_phrases < 2: continue
        # Split notes by phrase: phrase_i contains notes whose beat-in-section is in
        # [i*phrase_bars*bpb, (i+1)*phrase_bars*bpb)
        phrase_beats = phrase_bars * beats_per_bar
        phrases = [[] for _ in range(n_phrases)]
        # need note beat-in-section. notes_raw has song-absolute beats; section starts at s_beat
        # we'll compute relative to the first note's section-start (which is sec['s_beat']).
        # Just iterate, sorting bins by floor(rel_beat / phrase_beats).
        for n in notes_raw:
            if n.get('isRest'): continue
            rel = n['_rel_beat']
            idx = int(rel // phrase_beats)
            if 0 <= idx < n_phrases:
                phrases[idx].append(n.get('sd', '?'))
        chunks = [tuple(p) for p in phrases]
        # Skip if any phrase is empty
        if any(len(c) == 0 for c in chunks): continue
        strict = label_chunks_by_similarity(chunks)
        fuzzy = label_with_fuzzy(chunks)
        with_var = label_with_variation(chunks)
        results.append({
            'phrase_bars': phrase_bars,
            'n_phrases': n_phrases,
            'chunks_sd': chunks,
            'letters': strict,
            'letters_fuzzy': fuzzy,
            'letters_var': with_var,
        })
    return results


def best_structure(structs):
    """Pick the structure with the most internal repetition. Strong preference for
    2-bar and 4-bar phrase units — 1-bar is musically too granular to be a 'phrase'
    most of the time, so it only wins if it has DRAMATICALLY more repetition
    (50%+ fewer unique letters than the best 2/4-bar option)."""
    if not structs: return None
    non_one = [s for s in structs if s['phrase_bars'] != 1]
    one = [s for s in structs if s['phrase_bars'] == 1]

    def score(s):
        n_unique_fuzzy = len(set(s['letters_fuzzy'].replace("'", "")))
        return n_unique_fuzzy / s['n_phrases']

    if non_one:
        best_non_one = min(non_one, key=score)
        if not one:
            return best_non_one
        best_one = min(one, key=score)
        # Only prefer 1-bar if it has >=50% fewer unique letters per phrase.
        if score(best_one) <= 0.5 * score(best_non_one):
            return best_one
        return best_non_one
    return min(one, key=score) if one else None


def measure_split(notes_raw, beats_per_bar, total_bars):
    """Split a section's notes into per-measure chunks.

    Each measure i covers rel_beat in [i * bpb, (i+1) * bpb). Pickup notes with
    rel_beat < 0 get assigned to measure 0 (they're the anacrusis).
    Returns list of (sd_tuple_for_measure, beat_in_measure_tuple_for_measure).
    """
    measures = [[] for _ in range(total_bars)]
    for n in notes_raw:
        if n.get('isRest'): continue
        rel = n.get('_rel_beat', 0)
        idx = int(rel // beats_per_bar)
        if idx < 0: idx = 0  # pickup → first measure
        if idx >= total_bars: continue
        beat_in_meas = rel - idx * beats_per_bar
        if beat_in_meas < 0: beat_in_meas = 0  # for pickups, clamp
        measures[idx].append((n.get('sd', '?'), round(beat_in_meas, 3)))
    sd_only = [tuple(s for s, _ in m) for m in measures]
    rhythm_aware = [tuple(measures[i]) for i in range(total_bars)]
    return sd_only, rhythm_aware


def cluster_measures(measure_seqs, lcs_tol=0.7, edit_tol=0.3):
    """Cluster measures by similarity. Returns (labels_string, group_examples).

    Two measures get the same letter if `similar()` returns True. Empty measures
    are labeled '·' (silence/no notes).
    """
    seen = []  # list of (representative_sd_tuple, letter)
    labels = []
    next_letter = 'A'
    for m in measure_seqs:
        if len(m) == 0:
            labels.append('·')
            continue
        matched = False
        for rep, lbl in seen:
            if rep == m:
                labels.append(lbl); matched = True; break
            ok, _ = similar(rep, m, lcs_tol, edit_tol)
            if ok:
                labels.append(lbl); matched = True; break
        if not matched:
            seen.append((m, next_letter))
            labels.append(next_letter)
            next_letter = chr(ord(next_letter) + 1)
    return ''.join(labels), seen


# ---------- main analysis ----------

def analyze_section(sec, beats_per_bar):
    """Add melody-analysis fields to a section dict (in place return)."""
    # Add relative beat to notes (pickups will have negative rel_beat).
    s_beat = sec['s_beat']
    for n in sec['notes_raw']:
        n['_rel_beat'] = n.get('beat', 0) - s_beat
    total_bars = int(round(sec['bars']))

    structs = detect_phrase_structure(sec['sd_seq'], sec['notes_raw'], beats_per_bar, total_bars)
    best = best_structure(structs)

    # Measure-level cross-position labels — catches non-adjacent reuse like
    # John Deere Green's m1 ≡ m14.
    measure_sd, _ = measure_split(sec['notes_raw'], beats_per_bar, total_bars)
    measure_labels, measure_examples = cluster_measures(measure_sd)

    motifs = find_motifs(sec['sd_seq'], min_len=3, max_len=64, min_count=2)
    n_pickups = sum(1 for n in sec['notes_raw'] if n.get('_is_pickup'))
    return {
        'bars': sec['bars'],
        'n_notes': sec['n_notes'],
        'n_pickups': n_pickups,
        'sd_seq': sec['sd_seq'],
        'structs_tried': structs,
        'best_struct': best,
        'measure_labels': measure_labels,
        'measure_sd': measure_sd,
        'motifs': motifs[:5],
    }


def main():
    print('=' * 80)
    print('Phrase-structure analysis on 25-section starter corpus')
    print('=' * 80)
    print()

    found = 0
    not_found = []
    for title_sub, section_sub, artist_hint in CORPUS:
        song = lookup_song(title_sub, artist_hint)
        if not song:
            not_found.append((title_sub, section_sub, 'no song match'))
            continue
        hj = song['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        secs = list(extract_song_melodies(hj))
        sec = find_section(secs, section_sub)
        if not sec:
            not_found.append((title_sub, section_sub,
                              f"section '{section_sub}' not found in {song['title']} "
                              f"(have: {[s['name'] for s in secs if s['n_notes']>0]})"))
            continue
        found += 1
        a = analyze_section(sec, bpb)
        lyric_lines, end_words_l, source = get_lyrics_and_rhyme(
            song, sec['name'], hj, sec['s_beat'], sec['e_beat']
        )
        rhyme = rhyme_letters(end_words_l) if end_words_l else ''
        print(f"### {song['artist']} — {song['title']}  ·  {sec['name']}")
        print(f"    {song['key_tonic']} {song['key_scale']}  ·  {song['bpm']} BPM  ·  "
              f"{a['bars']:.0f} bars  ·  {a['n_notes']} notes  ·  bar = {bpb} beats")
        if lyric_lines:
            print(f"    lyrics ({source}) · rhyme: {rhyme}")
            for i, line in enumerate(lyric_lines):
                rhyme_lbl = rhyme[i] if i < len(rhyme) else '?'
                ew = end_words_l[i] if i < len(end_words_l) else ''
                if len(line) > 65: line = line[:65] + '…'
                print(f"      [{rhyme_lbl}] {line}    ({ew})")
        if a.get('n_pickups'):
            print(f"    +{a['n_pickups']} pickup notes from previous section")
        # Measure-level cross-position labels
        print(f"    measures: {' '.join(a['measure_labels'])}")
        if a['best_struct']:
            b = a['best_struct']
            print(f"    structure (fuzzy): **{b['letters_fuzzy']}**  "
                  f"(phrase = {b['phrase_bars']} bars × {b['n_phrases']} phrases)")
            print(f"    structure (strict / variation): {b['letters']}  /  {b['letters_var']}")
            # Use variation labels (A, A', B, B') in the per-phrase dump
            var_labels = b['letters_var']
            tokens = []
            i = 0
            for ch in var_labels:
                if ch == "'":
                    if tokens: tokens[-1] += "'"
                else:
                    tokens.append(ch)
            for i, c in enumerate(b['chunks_sd']):
                lbl = tokens[i] if i < len(tokens) else '?'
                print(f"      [{lbl}] {' '.join(c)}")
        else:
            print(f"    structure: (no clean split found at 1/2/4 bars)")
        print(f"    sd:  {' '.join(a['sd_seq'][:32])}{' …' if len(a['sd_seq'])>32 else ''}")
        if a['motifs']:
            for m in a['motifs'][:3]:
                token = ' '.join(str(x) for x in m['motif'])
                if len(token) > 50: token = token[:50] + '…'
                print(f"    motif ×{m['count']:>2}  ({len(m['motif']):>2} notes)  {token}")
        print()

    print('-' * 80)
    print(f"Found and analyzed: {found}/{len(CORPUS)}")
    if not_found:
        print("\nNot found (need disambiguation):")
        for t, s, why in not_found:
            print(f"  · {t} / {s} — {why}")


if __name__ == '__main__':
    main()
