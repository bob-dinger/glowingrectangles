"""Read the hand-annotated lyrics out of the Hookpad JSONs and grade them.

389 songs carry lyric text in the `lyrics` field and 141 of those carry rhyme
markers. The annotation already encodes the three things that matter:

    syllables   split by spaces — one token per note ("phe nom e non")
    rhymes      a letter in parens at the line end — "( a)", "(b)"
    sections    a [v]/[ch] tag inline, plus a sectionLyrics array that runs
                parallel to the song's own sections

It is NOT uniform: some songs fill only `values` with no section split, some have
sectionLyrics shorter than the section list, and the text often runs CONTINUOUSLY
across a section boundary (Yesterday's verse 2 opens with the tail of verse 1's
last line). So this grades every song rather than trusting it, and the grades are
the point — pick the clean ones, fix the rest.

    themap_venv/python parse_lyrics.py                # triage table
    themap_venv/python parse_lyrics.py --song yesterday --detail
    themap_venv/python parse_lyrics.py --write        # -> ~/Desktop/lyrics_parsed.json
"""
import os, re, sys, json, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus

OUT = os.path.expanduser('~/Desktop/lyrics_parsed.json')
# Two notations are in use, and the newer one carries more:
#   OLD  "...so far a way( a)"     a letter in parens at the LINE END — the line rhymes
#   NEW  "...so far a [a]way-"     [letter] opens on the RHYMING SYLLABLE, "-" closes it,
#                                  so the rhyme's position in the line is recorded too
# THREE different things share the bracket syntax. Disambiguated by POSITION and by
# the LETTER — not by a trailing dash, which turns out to be Hookpad's own
# "this word is one syllable" override (it stops the built-in detector splitting a
# pasted word) and is used only 65 times in 9 songs, always on words that are one
# syllable anyway. So it carries no information here:
#   line START      -> SECTION tag.  [v] 531, [ch] 153, [pc] 60, [i], [o], [r]
#   mid-line, [m]   -> MELISMA.  "dont op en your ey [m]es to night"  ([m] x103)
#   mid-line, a-h   -> RHYME on that syllable.  "so far a [a]way-"
#
# Syllable counting: the convention is to space-split ("phe nom e non"), but 376
# tokens are whole unsplit words, which Hookpad's detector would expand
# ("sleepwalker" -> 3 notes). Those are syllabified with pyphen, which takes exact
# note matches from 287 to 303. A token ending in "-" is pinned to one.
RHYME_END = re.compile(r'\(\s*([a-zA-Z])\s*\)\s*$')
BRACKET   = re.compile(r'\[([a-zA-Z]{1,3})\](\S*)')
TAG       = re.compile(r'^\s*\[([a-zA-Z]{1,3})\]')
MELISMA_LETTER = 'm'
RHYME_LETTERS  = set('abcdefgh')
# Melisma has two notations and they coexist:
#   [m] marker    "your ey [m]es to night"     57 uses — a flag on the continuation
#   quoted group  'he "fe els" "li ike" it'    wraps the whole word, so it also
#                                              records HOW MANY notes it is held over
# Quotes collide with dialogue — 36 of them across 9 songs ("She said, \"You don't
# understand\""). Dialogue runs long, melisma wraps one word, so a quoted run only
# counts as melisma when it is short.
MELISMA_QUOTE_MAX = 4
try:
    import pyphen
    _DIC = pyphen.Pyphen(lang='en_US')
except Exception:
    _DIC = None

def syllables_in(tok):
    """How many notes this token takes. A trailing "-" pins it to one; otherwise an
    unsplit word is expanded the way Hookpad's detector would."""
    t = tok.strip()
    if t.endswith('-'): return 1
    w = re.sub(r"[^a-zA-Z']", '', t)
    if not w or _DIC is None: return 1
    return max(1, len(_DIC.inserted(w).split('-')))

def parse_line(line):
    """-> (syllables, rhyme, tag, rhyme_at, notation, melisma_positions).
    `rhyme_at` is the index of the syllable carrying the rhyme, when the notation
    says so; `notation` is 'inline', 'line-end' or None."""
    tag = None
    m = TAG.match(line)
    if m:
        tag = m.group(1).lower(); line = line[m.end():]
    rhyme = rhyme_at = None; notation = None; melisma = []

    # quoted melisma groups: record which token indices they cover, then strip the
    # quotes so the tokens themselves are unchanged
    quoted = []
    if line.count('"') >= 2:
        pos = 0; idx = 0; pend = None
        for tok in re.split(r'(\s+)', line):
            if not tok.strip():
                continue
            opens = tok.startswith('"')
            closes = tok.rstrip('-,.?!').endswith('"')
            if opens and pend is None: pend = [idx]
            if pend is not None: pend.append(idx)
            if closes and pend is not None:
                grp = sorted(set(pend))
                if len(grp) <= MELISMA_QUOTE_MAX: quoted.extend(grp)
                pend = None
            idx += 1
        line = line.replace('"', '')

    # walk the remaining brackets: dash-closed = rhyme, bare = melisma
    syl, i = [], 0
    for tok in re.split(r'\s+', line.strip()):
        if not tok: continue
        b = BRACKET.match(tok)
        if b:
            letter, rest = b.group(1).lower(), b.group(2)
            if letter == MELISMA_LETTER:
                melisma.append(i)
            elif letter in RHYME_LETTERS:
                rhyme, rhyme_at, notation = letter, i, 'inline'
            else:
                melisma.append(i)          # unknown marker: do not call it a rhyme
            if rest: syl.append(rest)
            else: continue
        else:
            syl.append(tok)
        i = len(syl)
    melisma.extend(i for i in quoted if i not in melisma)
    if rhyme is None:
        m = RHYME_END.search(' '.join(syl))
        if m:
            notation = 'line-end'
            rhyme = m.group(1).lower()
            syl = [w for w in re.split(r'\s+', ' '.join(syl)[:m.start()].strip()) if w]
            rhyme_at = len(syl)-1 if syl else None
    if rhyme_at is not None and syl:
        rhyme_at = min(rhyme_at, len(syl)-1)
    return syl, rhyme, tag, rhyme_at, notation, melisma

def parse_song(d):
    """-> list of section dicts, plus flags describing how the song is encoded."""
    ly = d.get('lyrics') or {}
    secs = list(corpus.sections(d))
    notes = [n for n in (d.get('notes') or []) if not n.get('isRest')]
    sl = ly.get('sectionLyrics') or []
    flags = []
    if not sl:
        flags.append('no-section-split')
    elif len(sl) != len(secs):
        flags.append(f'sections {len(sl)}v{len(secs)}')

    out = []
    for i, s in enumerate(sl):
        filled = [x for x in (s.get('lyrics') or []) if x and x.strip()]
        if not filled: continue
        lines = []
        for blob in filled:
            for raw in blob.split('\n'):
                if not raw.strip(): continue
                syl, rhyme, tag, at, nota, mel = parse_line(raw)
                if syl: lines.append({'syllables': syl, 'rhyme': rhyme, 'tag': tag,
                                      'rhyme_at': at, 'notation': nota, 'melisma': mel})
        if not lines: continue
        nsyl = sum(syllables_in(t) for l in lines for t in l['syllables'])
        # notes in the song section at the same index, when the arrays line up
        nnotes = None
        if i < len(secs):
            _, b0, b1 = secs[i]
            nnotes = len([n for n in notes if b0 <= n['beat'] < b1])
        out.append({'index': i, 'name': s.get('sectionName', '?'),
                    'lines': lines, 'syllables': nsyl, 'notes': nnotes,
                    'scheme': ''.join(l['rhyme'] or '.' for l in lines)})
    if not out and (ly.get('values') or []):
        text = '\n'.join(x for x in ly['values'] if isinstance(x, str) and x.strip())
        lines = []
        for raw in text.split('\n'):
            if not raw.strip(): continue
            syl, rhyme, tag, at, nota, mel = parse_line(raw)
            if syl: lines.append({'syllables': syl, 'rhyme': rhyme, 'tag': tag,
                                  'rhyme_at': at, 'notation': nota, 'melisma': mel})
        if lines:
            out.append({'index': None, 'name': '(whole)', 'lines': lines,
                        'syllables': sum(syllables_in(t) for l in lines for t in l['syllables']),
                        'notes': len(notes),
                        'scheme': ''.join(l['rhyme'] or '.' for l in lines)})
    return out, flags

def grade(rows, flags):
    """clean / close / rough / unsectioned — how usable this song is as-is."""
    if not rows: return 'empty'
    if 'no-section-split' in flags or rows[0]['index'] is None: return 'unsectioned'
    pairs = [(r['syllables'], r['notes']) for r in rows if r['notes']]
    if not pairs: return 'rough'
    err = [abs(s - n) / max(n, 1) for s, n in pairs]
    worst = max(err)
    return 'clean' if worst <= 0.10 else 'close' if worst <= 0.30 else 'rough'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--song'); ap.add_argument('--detail', action='store_true')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    grades = collections.Counter(); flagc = collections.Counter()
    best = []; store = {}
    for name, d, nb in corpus.songs(need_chords=False):
        if a.song and a.song.lower() not in name.lower(): continue
        rows, flags = parse_song(d)
        if not rows: continue
        g = grade(rows, flags)
        grades[g] += 1
        for f in flags: flagc[f.split()[0]] += 1
        nrhyme = sum(1 for r in rows for l in r['lines'] if l['rhyme'])
        store[name] = {'grade': g, 'flags': flags, 'sections': rows}
        best.append((g, nrhyme, sum(r['syllables'] for r in rows), len(rows), name))
        if a.song and a.detail:
            print(f"\n{name}   grade={g}  flags={flags or 'none'}")
            for r in rows:
                print(f"  [{r['index']}] {r['name'][:14]:14} {r['syllables']:4} syllables / "
                      f"{r['notes']} notes   scheme {r['scheme']}")
                for l in r['lines'][:4]:
                    print(f"        {l['rhyme'] or '-'}  {' '.join(l['syllables'])[:68]}")
    if a.song: 
        if not a.detail: print(json.dumps(store, indent=1)[:1500])
        return

    tot = sum(grades.values())
    print(f"{tot} songs with parseable lyrics\n")
    for g in ('clean', 'close', 'rough', 'unsectioned'):
        print(f"  {g:12} {grades[g]:4} {100*grades[g]/tot:5.1f}%  {'#'*int(40*grades[g]/tot)}")
    print(f"\n  encoding problems: {dict(flagc)}")
    print(f"\n  best candidates (clean, most rhyme-annotated)")
    for g, nr, ns, nsec, name in sorted(best, key=lambda r: (r[0] != 'clean', -r[1]))[:14]:
        print(f"   {g:11} {nr:3} rhymes {ns:5} syll {nsec:2} sec  {name}")
    if a.write:
        json.dump(store, open(OUT, 'w'), indent=1)
        print(f"\n  wrote {len(store)} songs -> {OUT}")

if __name__ == '__main__':
    main()
