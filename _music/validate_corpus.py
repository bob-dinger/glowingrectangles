"""Run melisma_align on every example in melisma_examples.json
and report how each one matches the verified encoding.

Usage:
    python validate_corpus.py            # full report
    python validate_corpus.py --id 5     # just example with id=5
    python validate_corpus.py --diff     # only show ones that don't match
"""

import argparse
import json
import os
import re
import sys

# Local import
sys.path.insert(0, os.path.dirname(__file__))
from melisma_align import parse_notes, parse_lyrics, align, render

CORPUS = os.path.join(os.path.dirname(__file__), 'melisma_examples.json')


def normalize(s: str) -> str:
    """Normalize encoding for comparison: lowercase, collapse whitespace, strip punctuation."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 \n']", ' ', s)
    s = re.sub(r' +', ' ', s)
    s = '\n'.join(line.strip() for line in s.splitlines())
    return s.strip()


def run_one(ex: dict, verbose: bool = False):
    notes = parse_notes({'notes': ex['notes']})
    words = parse_lyrics(ex['lyrics'])
    result = align(notes, words)
    got = render(result)
    expected = ex.get('encoding', '').strip()
    # Strip "(verified: ...)" placeholder explanations
    expected_clean = re.sub(r'^\([^)]*\)\s*', '', expected, flags=re.MULTILINE)

    n_got = len(notes)
    n_expected_notes = ex.get('total_notes', n_got)
    n_expected_syl = ex.get('total_syllables', 0)
    n_expected_mel = ex.get('melisma_count', 0)
    n_got_syl = sum(w.syllables for w in words)
    n_got_mel = result.actual_melisma

    counts_match = (n_got == n_expected_notes and
                    n_got_syl == n_expected_syl and
                    n_got_mel == n_expected_mel)
    encoding_match = normalize(got) == normalize(expected_clean) if expected_clean else None

    return {
        'id': ex['id'],
        'song': ex['song'],
        'counts_match': counts_match,
        'note_count': (n_got, n_expected_notes),
        'syl_count': (n_got_syl, n_expected_syl),
        'mel_count': (n_got_mel, n_expected_mel),
        'expected': expected_clean,
        'got': got,
        'encoding_match': encoding_match,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', type=int, help='Only run this example id')
    p.add_argument('--diff', action='store_true', help='Only show non-matching examples')
    p.add_argument('--verbose', '-v', action='store_true')
    args = p.parse_args()

    with open(CORPUS) as fh:
        corpus = json.load(fh)

    examples = corpus['examples']
    if args.id:
        examples = [e for e in examples if e['id'] == args.id]

    counts_pass = 0
    encoding_pass = 0
    total = 0
    encoding_evaluable = 0
    for ex in examples:
        r = run_one(ex)
        total += 1
        if r['counts_match']:
            counts_pass += 1
        if r['encoding_match'] is not None:
            encoding_evaluable += 1
            if r['encoding_match']:
                encoding_pass += 1

        is_diff = (not r['counts_match']) or (r['encoding_match'] is False)
        if args.diff and not is_diff:
            continue

        status_counts = '✓' if r['counts_match'] else '✗'
        if r['encoding_match'] is None:
            status_enc = '?'
        elif r['encoding_match']:
            status_enc = '✓'
        else:
            status_enc = '✗'

        print(f'\n[{r["id"]}] {r["song"]}')
        print(f'  counts {status_counts}  notes {r["note_count"][0]}/{r["note_count"][1]}  '
              f'syl {r["syl_count"][0]}/{r["syl_count"][1]}  '
              f'mel {r["mel_count"][0]}/{r["mel_count"][1]}')
        print(f'  encoding {status_enc}')
        if status_enc == '✗' or args.verbose:
            print(f'    expected: {r["expected"]!r}')
            print(f'    got:      {r["got"]!r}')

    print(f'\n=== summary ===')
    print(f'counts:   {counts_pass}/{total}')
    print(f'encoding: {encoding_pass}/{encoding_evaluable} (of {total} total; some have placeholder encodings)')


if __name__ == '__main__':
    main()
