"""Align lyrics to Hookpad melody notes and identify melismatic notes.

Encodes the 12 heuristic rules from memory/music_melisma_alignment.md.
Validate against the corpus with `python validate_corpus.py`.

CLI:
    python melisma_align.py --notes song.json --lyrics "..."
    python melisma_align.py --notes song.json --lyrics-file path.txt --debug
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Lyric / syllable handling
# ============================================================

SYLLABLE_OVERRIDES = {
    'diamonds': 3,
    'fire':     1,
    'whenever': 3,
    'anybody':  3,    # commonly sung as 'an-y-bod' in pop
    'going':    1,    # 'gonna' contraction
    'remember': 3,
}

# Manual syllable-split for words pyphen gets wrong — used when melisma falls
# inside a polysyllabic word and we need to split it (Rule 8)
SYLLABLE_PARTS = {
    'diamonds': ['di', 'a', 'monds'],
    'remember': ['re', 'mem', 'ber'],
    'anymore':  ['an', 'y', 'more'],
    'forever':  ['for', 'ev', 'er'],
    'whenever': ['when', 'ev', 'er'],
    'anybody':  ['an', 'y', 'body'],
    'superposition': ['Su', 'per', 'po', 'si', 'tion'],
    'position': ['po', 'si', 'tion'],
    'vision':   ['vi', 'sion'],
}

try:
    import cmudict
    _CMU = cmudict.dict()
except Exception:
    _CMU = None


def _vowel_groups(word: str) -> int:
    count = 0
    prev_vowel = False
    for c in word:
        is_v = c in 'aeiouy'
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    if word.endswith('e') and count > 1 and not word.endswith('le'):
        count -= 1
    return max(1, count)


def count_syllables(word: str) -> int:
    bare = re.sub(r"[^A-Za-z']", '', word).lower()
    if not bare:
        return 0
    if bare in SYLLABLE_OVERRIDES:
        return SYLLABLE_OVERRIDES[bare]
    if _CMU is not None:
        prons = _CMU.get(bare) or _CMU.get(bare.replace("'", ''))
        if prons:
            return sum(1 for ph in prons[0] if ph[-1].isdigit())
    return _vowel_groups(bare)


def final_vowel(word: str) -> str:
    bare = re.sub(r"[^A-Za-z']", '', word).lower()
    for c in reversed(bare):
        if c in 'aeiouy':
            return c
    return bare[-1] if bare else 'a'


@dataclass
class Word:
    text: str           # original token (with punctuation)
    bare: str           # letters only
    syllables: int      # # syllables in normal pronunciation
    line: int           # which line this word is on (0-indexed)


def parse_lyrics(text: str) -> list[Word]:
    out = []
    for line_idx, line in enumerate(text.splitlines()):
        for tok in line.split():
            bare = re.sub(r"[^A-Za-z']", '', tok)
            if not bare:
                continue
            out.append(Word(text=tok, bare=bare, syllables=count_syllables(bare), line=line_idx))
    return out


# ============================================================
# Note handling
# ============================================================

@dataclass
class Note:
    beat: float
    duration: float
    sd: str
    octave: int
    is_rest: bool


def parse_notes(data) -> list[Note]:
    if isinstance(data, dict):
        if 'notes' in data and data['notes']:
            raw = data['notes']
        elif 'polyphonicNotes' in data and data['polyphonicNotes']:
            raw = data['polyphonicNotes'][0]
        else:
            raw = []
    else:
        raw = data
    notes = []
    for n in raw:
        notes.append(Note(
            beat=float(n['beat']),
            duration=float(n['duration']),
            sd=str(n.get('sd', '')),
            octave=int(n.get('octave', 0)),
            is_rest=bool(n.get('isRest', False)),
        ))
    notes.sort(key=lambda x: x.beat)
    return [n for n in notes if not n.is_rest]


_SCALE = [0, 2, 4, 5, 7, 9, 11]

def midi_pitch(sd: str, octave: int) -> int:
    acc = 0
    s = sd
    while s and s[0] in 'b#':
        acc += -1 if s[0] == 'b' else 1
        s = s[1:]
    if not s.isdigit():
        return 0
    deg = int(s)
    base = _SCALE[(deg - 1) % 7] if 1 <= deg <= 7 else 0
    return octave * 12 + base + acc


def detect_phrases(notes: list[Note], gap_threshold: float = 1.5) -> list[list[int]]:
    """Group notes into phrases based on inter-note gaps. Returns list of index-lists."""
    if not notes:
        return []
    phrases = [[0]]
    for i in range(1, len(notes)):
        end_prev = notes[i-1].beat + notes[i-1].duration
        gap = notes[i].beat - end_prev
        if gap >= gap_threshold:
            phrases.append([i])
        else:
            phrases[-1].append(i)
    return phrases


# ============================================================
# Pattern detection — mark notes with melisma likelihood
# ============================================================

@dataclass
class NoteContext:
    """Per-note features used for melisma scoring."""
    idx: int
    note: Note
    prev: Optional[Note]
    next: Optional[Note]
    is_phrase_start: bool
    is_phrase_end: bool
    same_pitch_run_before: int   # length of same-pitch run ending at prev (incl prev)
    interval_from_prev: int      # in semitones
    pos_in_bar: float            # (beat-1) % 4


def build_contexts(notes: list[Note], phrases: list[list[int]]) -> list[NoteContext]:
    phrase_starts = {p[0] for p in phrases}
    phrase_ends = {p[-1] for p in phrases}
    contexts = []
    for i, n in enumerate(notes):
        prev = notes[i-1] if i > 0 else None
        nxt  = notes[i+1] if i+1 < len(notes) else None

        # same-pitch run ending at prev
        run = 0
        if prev is not None:
            run = 1
            p_pitch = midi_pitch(prev.sd, prev.octave)
            for k in range(i-2, -1, -1):
                if midi_pitch(notes[k].sd, notes[k].octave) == p_pitch:
                    run += 1
                else:
                    break

        interval = 0
        if prev is not None:
            interval = midi_pitch(n.sd, n.octave) - midi_pitch(prev.sd, prev.octave)

        contexts.append(NoteContext(
            idx=i, note=n, prev=prev, next=nxt,
            is_phrase_start=(i in phrase_starts),
            is_phrase_end=(i in phrase_ends),
            same_pitch_run_before=run,
            interval_from_prev=interval,
            pos_in_bar=(n.beat - 1) % 4,
        ))
    return contexts


def melisma_score(c: NoteContext) -> float:
    """How likely is this note a melisma extension of the previous syllable?

    Higher = more likely melisma. Phrase-start notes are NEVER melisma (return -inf).
    """
    if c.is_phrase_start:
        return float('-inf')

    n, prev = c.note, c.prev
    score = 0.0

    # Rule 4: very short ornamental notes
    if n.duration <= 0.25:
        if prev.duration <= 0.25:
            score += 6      # second of two consecutive 0.25 — almost certainly melisma
        elif prev.duration >= 1.0:
            score += 5      # short tail after held = textbook melisma
        else:
            score += 2

    # Rule 5: descending step right after a same-pitch run.
    # Strong only when the descending note is HELD (>= last run note's duration) —
    # the held vowel sustains down. If the descending note is SAME duration as the run,
    # it's just a normal syllabic move to the next syllable, not melisma.
    if -3 <= c.interval_from_prev < 0 and c.same_pitch_run_before >= 2:
        held_descent = n.duration >= prev.duration
        if c.same_pitch_run_before >= 3 and held_descent:
            score += 9          # Lucy "sky→y", Friday "work"
        elif c.same_pitch_run_before >= 3:
            score += 2          # descending move but not held
        elif held_descent:
            score += 4
        else:
            score += 1
    elif -3 <= c.interval_from_prev < 0:
        score += 1.5        # plain descending step (no run)

    # Rule 2: repeated same pitch usually = separate syllable
    if c.interval_from_prev == 0:
        # exception: if it's the LAST note of phrase AND it's longer than prev,
        # could be a held melisma extension (Rule 11 — Superposition pattern)
        if c.is_phrase_end and n.duration > prev.duration and prev.duration <= 0.5:
            score += 4
        elif c.is_phrase_end and n.duration > prev.duration:
            score += 2
        else:
            score -= 3   # otherwise = separate syllable

    # Rule 3: very short tail after a TRULY long held note (>=1.5 beats).
    # Tightened to avoid false positives where prev is just a 1-beat syllable.
    if prev.duration >= 1.5 and n.duration <= 0.25 and c.interval_from_prev != 0:
        score += 3

    # Long notes are usually anchors, but there are exceptions:
    if n.duration >= 2.0:
        score -= 6
    elif n.duration >= 1.0:
        # only mildly penalize — In My Life's note 6 (descending step, 1-beat) is melisma
        if score < 5:
            score -= 2

    # Strong-beat penalty — downbeats usually hold syllables, BUT if a melodic-pattern
    # rule (Rule 5: run+descending) already scored very high, the downbeat is the
    # melisma landing point (e.g., Friday Night Blues "work" on bar downbeat).
    if score < 6:
        if abs(c.pos_in_bar - 0) < 0.05:
            score -= 4
        elif abs(c.pos_in_bar - 2) < 0.05:
            score -= 2

    return score


# ============================================================
# Cluster-aware refinement
# ============================================================

def detect_long_short_short_long(notes: list[Note]) -> set[int]:
    """Find LONG–short–short–LONG clusters where all 4 notes belong to ONE syllable.
    Returns set of note indices that are *melisma extensions* (i.e., every note in
    the cluster except the first).

    The 'Girl' pattern: anchor LONG → 2 quick ornamental → resolution LONG.
    Heuristic: durations LONG≥1.0, SHORT≤0.5, LONG≥1.0, with both LONGs at distinct pitches
    and pitch range moving (not all same pitch).
    """
    extensions = set()
    i = 0
    while i + 3 < len(notes):
        a, b, c, d = notes[i], notes[i+1], notes[i+2], notes[i+3]
        if (a.duration >= 1.0 and
            b.duration <= 0.5 and
            c.duration <= 0.5 and
            d.duration >= 1.0):
            pa = midi_pitch(a.sd, a.octave)
            pb = midi_pitch(b.sd, b.octave)
            pc = midi_pitch(c.sd, c.octave)
            pd = midi_pitch(d.sd, d.octave)
            # Real "Girl" pattern: held high → flutter → held resolve LOWER.
            # Requires: descending overall (d <= a), the two SHORTs at different
            # pitches (ornamental flutter), AND the SHORTs stay within ~5 semitones
            # of the anchor (no big leaps that signal a transition not melisma).
            anchor_range = max(abs(pb - pa), abs(pc - pa))
            if pa > pd and pb != pc and anchor_range <= 5:
                extensions.update([i+1, i+2, i+3])
                i += 4
                continue
        i += 1
    return extensions


# ============================================================
# Alignment
# ============================================================

@dataclass
class AlignmentResult:
    melisma_indices: list[int]      # which notes are melisma extensions
    word_assignments: list[list[str]]   # per word: list of tokens to emit
    notes: list[Note]
    words: list[Word]
    expected_syllables: int
    actual_melisma: int


def align(notes: list[Note], words: list[Word]) -> AlignmentResult:
    expected = sum(w.syllables for w in words)
    n_notes = len(notes)
    n_melisma = n_notes - expected

    if n_melisma < 0:
        return AlignmentResult(
            melisma_indices=[],
            word_assignments=[[f'?? more syllables ({expected}) than notes ({n_notes}) ??']],
            notes=notes, words=words,
            expected_syllables=expected,
            actual_melisma=n_melisma,
        )

    phrases = detect_phrases(notes)
    contexts = build_contexts(notes, phrases)

    # First pass: detect strong cluster patterns (LONG-short-short-LONG = 'Girl')
    forced = detect_long_short_short_long(notes)

    # Second pass: score every other non-phrase-start note
    scored = []
    for c in contexts:
        if c.idx in forced:
            scored.append((c.idx, 100.0))   # always picked
        elif c.is_phrase_start:
            continue                         # never melisma
        else:
            scored.append((c.idx, melisma_score(c)))

    # Pick top n_melisma scores
    scored.sort(key=lambda x: -x[1])
    melisma_idx = sorted(i for i, _ in scored[:n_melisma])

    # Walk forward — each non-melisma note advances the syllable pointer
    # Track word_idx, syllable_in_word, and per-syllable melisma extension counts
    word_idx = 0
    syllable_in_word = 0
    melisma_per_syllable: list[list[int]] = [[]]   # for current syllable
    syllables_seen_in_word: list[list[list[int]]] = [[[]]]  # per word, per syllable, list of mel notes

    def ensure_word_slot(wi):
        while len(syllables_seen_in_word) <= wi:
            syllables_seen_in_word.append([[]])

    for i, n in enumerate(notes):
        if i in melisma_idx and i > 0:
            # melisma extension of current syllable
            if word_idx < len(words):
                ensure_word_slot(word_idx)
                while len(syllables_seen_in_word[word_idx]) <= syllable_in_word:
                    syllables_seen_in_word[word_idx].append([])
                syllables_seen_in_word[word_idx][syllable_in_word].append(i)
        else:
            # advance to next syllable (if not first note)
            if i > 0:
                syllable_in_word += 1
                if word_idx < len(words) and syllable_in_word >= words[word_idx].syllables:
                    word_idx += 1
                    syllable_in_word = 0
            ensure_word_slot(word_idx)
            while len(syllables_seen_in_word[word_idx]) <= syllable_in_word:
                syllables_seen_in_word[word_idx].append([])
            # this note IS the syllable's anchor; no melisma yet
            # (the anchor itself is implicit; only extensions are tracked here)

    # Render: for each word, emit either the word (if no melisma inside it)
    # or split the word into syllables (when melisma is internal).
    word_assignments: list[list[str]] = []
    for wi, w in enumerate(words):
        ensure_word_slot(wi)
        sylls = syllables_seen_in_word[wi]
        # pad to expected syllable count (in case alignment ran short)
        while len(sylls) < w.syllables:
            sylls.append([])
        any_internal_melisma = any(len(sylls[s]) > 0 for s in range(w.syllables - 1))
        last_syl_extensions = sylls[w.syllables - 1] if w.syllables > 0 else []
        tokens = []
        # Decide if we need to split the word into syllables
        has_any_melisma = any_internal_melisma or len(last_syl_extensions) > 0
        parts = _syllabify(w.bare) if has_any_melisma else None

        if any_internal_melisma and parts and len(parts) == w.syllables:
            # Split: emit each syllable, then its melisma extensions
            for s, part in enumerate(parts):
                tokens.append(part)
                for _ in sylls[s]:
                    tokens.append(_part_vowel(part))
        else:
            # Keep word intact; trailing melisma extensions repeat the LAST syllable
            tokens.append(w.text)
            ext = _last_syllable_token(w.bare)
            for _ in last_syl_extensions:
                tokens.append(ext)
        word_assignments.append(tokens)

    return AlignmentResult(
        melisma_indices=melisma_idx,
        word_assignments=word_assignments,
        notes=notes, words=words,
        expected_syllables=expected,
        actual_melisma=n_melisma,
    )


def _syllabify(word: str) -> list[str]:
    """Best-effort syllabification: manual override → pyphen → single-syllable fallback."""
    bare = re.sub(r"[^A-Za-z']", '', word).lower()
    if bare in SYLLABLE_PARTS:
        return SYLLABLE_PARTS[bare]
    try:
        import pyphen
        d = pyphen.Pyphen(lang='en')
        parts = d.inserted(bare).split('-')
        parts = [p for p in parts if p]
        return parts if parts else [bare]
    except Exception:
        return [bare]


def _part_vowel(syll: str) -> str:
    """Get vowel sound for a syllable part — used as melisma extension token
    when splitting a polysyllabic word and the melisma is internal."""
    s = syll.lower()
    for c in reversed(s):
        if c in 'aeiouy':
            return c
    return s[-1] if s else 'a'


def _last_syllable_token(word: str) -> str:
    """Return the melisma-extension token for end-of-word melisma:
    the last syllable of the word (or the whole word if monosyllabic).
    Used for trailing extensions when the word stays intact."""
    parts = _syllabify(word)
    return parts[-1] if parts else word


def render(result: AlignmentResult, line_breaks: bool = True) -> str:
    """Render aligned tokens, preserving lyric line breaks if requested."""
    if line_breaks:
        # Group word_assignments by line
        lines: list[list[str]] = [[]]
        for wi, tokens in enumerate(result.word_assignments):
            if wi < len(result.words):
                line = result.words[wi].line
                while len(lines) <= line:
                    lines.append([])
                lines[line].append(' '.join(tokens))
            else:
                lines[-1].append(' '.join(tokens))
        return '\n'.join(' '.join(line) for line in lines if line)
    else:
        return ' '.join(' '.join(t) for t in result.word_assignments)


# ============================================================
# CLI
# ============================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--notes', required=True, help='Path to a Hookpad JSON file (or "-" for stdin)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--lyrics', help='Lyric text inline')
    g.add_argument('--lyrics-file', help='Path to a text file of lyrics')
    p.add_argument('--debug', action='store_true', help='Print per-note scoring')
    args = p.parse_args()

    if args.notes == '-':
        data = json.load(sys.stdin)
    else:
        with open(args.notes) as fh:
            data = json.load(fh)
    notes = parse_notes(data)

    lyric_text = args.lyrics if args.lyrics else open(args.lyrics_file).read()
    words = parse_lyrics(lyric_text)

    expected = sum(w.syllables for w in words)
    print(f'notes: {len(notes)}  expected syllables: {expected}  '
          f'melisma: {len(notes) - expected}')

    if args.debug:
        phrases = detect_phrases(notes)
        contexts = build_contexts(notes, phrases)
        forced = detect_long_short_short_long(notes)
        print(f'\nphrases: {len(phrases)} (sizes: {[len(p) for p in phrases]})')
        print(f'forced melisma (Girl pattern): {sorted(forced)}')
        print(f'\n{"#":>3} {"beat":>6} {"sd":>4} {"oct":>3} {"dur":>5}  '
              f'{"phr":>3}  {"score":>6}')
        for c in contexts:
            tag = 'S' if c.is_phrase_start else ('E' if c.is_phrase_end else ' ')
            sc = melisma_score(c)
            sc_str = '----' if sc == float('-inf') else f'{sc:.2f}'
            print(f'{c.idx+1:>3} {c.note.beat:>6.2f} {c.note.sd:>4} '
                  f'{c.note.octave:>3} {c.note.duration:>5.2f}  {tag:>3}  {sc_str:>6}')

    result = align(notes, words)
    print(f'\nmelisma at notes: {[i+1 for i in result.melisma_indices]}')
    print('\n' + render(result))


if __name__ == '__main__':
    main()
