"""Extract every 8-measure section that has melody from Supabase parcels.songs.
Dedupes within song: if a song has 3 verses, keep only the first.

Output: ~/Desktop/eight_bar_sections.csv  (one row per unique section)
Columns: artist, title, section_name, start_beat, end_beat, n_chords, n_notes, key, bpm, song_slug
"""
import os, csv, json
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
OUT = os.path.expanduser('~/Desktop/eight_bar_sections.csv')


def beats_per_measure(hj):
    """Get beats-per-measure from the first meter event (assumes single time sig per song)."""
    meters = hj.get('meters') or []
    if not meters: return 4.0
    m = meters[0]
    num = m.get('numBeats', 4)
    bu = m.get('beatUnit', 1)
    # beatUnit in Hookpad: 0=8th, 1=quarter, 2=half. Convert to quarter-note units.
    if bu == 0: return num * 0.5   # 6/8 etc.
    if bu == 2: return num * 2.0
    return float(num)   # quarter-note based (4/4, 3/4, etc.)


def main():
    print('loading songs from supabase...')
    rows = SB.schema('parcels').table('songs').select(
        'slug,title,artist,bpm,key_tonic,key_scale,hookpad_json'
    ).not_.is_('hookpad_json', 'null').execute().data
    print(f'  {len(rows)} songs with hookpad_json')

    out_rows = []
    n_sections_total = 0
    n_eight_bar = 0
    n_with_melody = 0

    for song in rows:
        hj = song['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        sections = hj.get('sections') or []
        if not sections: continue
        bpm_beats = beats_per_measure(hj)
        if bpm_beats <= 0: continue
        end_beat_song = hj.get('endBeat') or 1
        notes = hj.get('notes') or []
        chords = hj.get('chords') or []

        # Compute section start/end beats. Each section runs from its beat to the NEXT section's beat
        # (or song endBeat for the last section).
        section_spans = []
        for i, sec in enumerate(sections):
            s_beat = sec['beat']
            e_beat = sections[i+1]['beat'] if i+1 < len(sections) else end_beat_song
            section_spans.append({'name': sec.get('name', ''), 'start': s_beat, 'end': e_beat})

        # Filter to 8-measure sections with melody, then dedupe by name (keep first occurrence)
        seen_names = set()
        for span in section_spans:
            n_sections_total += 1
            n_beats = span['end'] - span['start']
            n_meas = n_beats / bpm_beats
            # Allow small tolerance (7.95-8.05) for float jitter
            if not (7.9 <= n_meas <= 8.1): continue
            n_eight_bar += 1
            # Count notes + chords inside this span
            notes_in = [n for n in notes if span['start'] <= n['beat'] < span['end']]
            chords_in = [c for c in chords if span['start'] <= c['beat'] < span['end']]
            if not notes_in: continue   # need a melody
            n_with_melody += 1
            # Dedupe by normalized section name within song. Strip leading/trailing roman numerals
            # and arabic numbers so "Verse I", "Verse 2", "1st verse" all collapse to "verse".
            import re as _re
            name_key = (span['name'] or '').strip().lower()
            name_key = _re.sub(r'\b(1st|2nd|3rd|[1-9]th)\b', '', name_key)
            name_key = _re.sub(r'\b[ivx]+\b', '', name_key)   # roman numerals
            name_key = _re.sub(r'\b\d+\b', '', name_key)
            name_key = _re.sub(r'\s+', ' ', name_key).strip()
            if name_key in seen_names: continue
            seen_names.add(name_key)
            out_rows.append({
                'artist': song['artist'] or '',
                'title': song['title'] or '',
                'song_slug': song['slug'] or '',
                'section_name': span['name'] or '',
                'start_beat': span['start'],
                'end_beat': span['end'],
                'n_chords': len(chords_in),
                'n_notes': len(notes_in),
                'key': f"{song.get('key_tonic','')} {song.get('key_scale','')}".strip(),
                'bpm': song.get('bpm', ''),
            })

    print(f'\nstats:')
    print(f'  sections scanned:     {n_sections_total}')
    print(f'  exactly 8 measures:   {n_eight_bar}')
    print(f'  + has melody:         {n_with_melody}')
    print(f'  + deduped by name:    {len(out_rows)}')

    out_rows.sort(key=lambda r: (r['artist'].lower(), r['title'].lower()))
    fields = ['artist','title','section_name','start_beat','end_beat','n_chords','n_notes','key','bpm','song_slug']
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in out_rows: w.writerow(r)

    # Section-name breakdown
    from collections import Counter
    name_counts = Counter(r['section_name'].lower() for r in out_rows)
    print(f'\ntop 15 section names:')
    for n, c in name_counts.most_common(15):
        print(f'  {c:>4}  {n}')
    print(f'\nspreadsheet → {OUT}')


if __name__ == '__main__': main()
