"""Walk every UG text tab and extract its chord progression per section.

Output: ~/Desktop/ug_chord_progressions.json
Schema (per song):
  {
    file: 'ccr_bad-moon-rising',
    artist: 'ccr',
    title: 'bad moon rising',
    key: 'D' | null,
    scale: 'major' | 'minor' | null,
    capo: '...' | null,
    sections: [
      {name: 'Verse', chords: ['D','A','G','D', ...]},
      ...
    ]
  }
"""
import os, re, json, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_ug import parse_tab

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
OUT = os.path.expanduser('~/Desktop/ug_chord_progressions.json')


def main():
    files = sorted(glob.glob(os.path.join(UG_DIR, '*.txt')))
    print(f'parsing {len(files)} UG tabs...')
    out = []
    n_with_sections = n_with_key = n_with_chords = 0
    n_err = 0
    for f in files:
        bn = os.path.splitext(os.path.basename(f))[0]
        artist_kb, _, title_kb = bn.partition('_')
        try:
            meta, sections = parse_tab(open(f, encoding='utf-8', errors='replace').read())
        except Exception as e:
            n_err += 1; continue

        # Flatten each section's chord events into a sequential chord list (order preserved)
        sec_out = []
        for sec in sections:
            chord_names = []
            for kind, payload in sec.get('events', []):
                if kind == 'chord_line':
                    for cname, _col in payload:
                        chord_names.append(cname)
            sec_out.append({'name': sec.get('name', ''), 'chords': chord_names})

        # Drop empty sections (no chords)
        sec_out = [s for s in sec_out if s['chords']]

        if sec_out: n_with_sections += 1
        if meta.get('key'): n_with_key += 1
        if any(s['chords'] for s in sec_out): n_with_chords += 1

        out.append({
            'file': bn,
            'artist': artist_kb.replace('-', ' '),
            'title':  title_kb.replace('-', ' '),
            'key':    meta.get('key'),
            'scale':  meta.get('scale'),
            'capo':   meta.get('capo'),
            'tuning': meta.get('tuning'),
            'bpm':    meta.get('bpm'),
            'sections': sec_out,
        })

    # Compact JSON
    with open(OUT, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'\n  songs parsed:           {len(out)} ({n_err} errors)')
    print(f'  with ≥1 section+chords: {n_with_chords}')
    print(f'  with Key: header:       {n_with_key}')
    print(f'\n  file size: {os.path.getsize(OUT) / 1024:.1f} KB → {OUT}')

    # Quick distribution stats
    from collections import Counter
    section_name_counter = Counter()
    chord_root_counter = Counter()
    for song in out:
        for sec in song['sections']:
            section_name_counter[sec['name'].lower()] += 1
            for c in sec['chords']:
                # Just root letter for distribution
                m = re.match(r'([A-G][#b]?)', c)
                if m: chord_root_counter[m.group(1)] += 1

    print(f'\ntop 10 section names:')
    for n, c in section_name_counter.most_common(10): print(f'  {c:>5}  {n}')
    print(f'\ntop 10 chord roots (any quality):')
    for n, c in chord_root_counter.most_common(10): print(f'  {c:>5}  {n}')


if __name__ == '__main__': main()
