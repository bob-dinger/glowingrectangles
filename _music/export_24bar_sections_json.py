"""Export 24-measure sections with melody from Supabase, with chord+melody detail.

Excludes intro/outro/solo/instrumental-bridge sections. Dedupes within song
(Verse I/II/III collapse to one entry).

Output: ~/Desktop/glowinggardens_claude/_music/twenty_four_bar_sections.json
"""
import os, json, re
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
OUT = '/Users/robert/Desktop/glowinggardens_claude/_music/twenty_four_bar_sections.json'

EXCLUDE = {'intro','outro','solo','instrumental bridge','instrumental','intro/verse','intro verse',
           'guitar solo','interlude','break','breakdown','build','tag','coda','ending'}


def beats_per_measure(hj):
    meters = hj.get('meters') or []
    if not meters: return 4.0
    m = meters[0]
    num = m.get('numBeats', 4); bu = m.get('beatUnit', 1)
    if bu == 0: return num * 0.5
    if bu == 2: return num * 2.0
    return float(num)


def norm_name(s):
    s = (s or '').strip().lower()
    s = re.sub(r'\b(1st|2nd|3rd|[1-9]th)\b', '', s)
    s = re.sub(r'\b[ivx]+\b', '', s)
    s = re.sub(r'\b\d+\b', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def main():
    print('loading songs...')
    rows = SB.schema('parcels').table('songs').select(
        'slug,title,artist,bpm,key_tonic,key_scale,hookpad_json'
    ).not_.is_('hookpad_json', 'null').execute().data
    print(f'  {len(rows)} songs')

    sections_out = []
    for song in rows:
        hj = song['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        sections = hj.get('sections') or []
        if not sections: continue
        bpm = beats_per_measure(hj)
        if bpm <= 0: continue
        end_beat = hj.get('endBeat') or 1
        notes = hj.get('notes') or []
        chords = hj.get('chords') or []

        seen_names = set()
        for i, sec in enumerate(sections):
            s_beat = sec['beat']
            e_beat = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
            nm = sec.get('name', '') or ''
            nm_lower = nm.strip().lower()
            if nm_lower in EXCLUDE: continue
            n_meas = (e_beat - s_beat) / bpm
            if not (23.9 <= n_meas <= 24.1): continue
            notes_in = [n for n in notes if s_beat <= n['beat'] < e_beat]
            if not notes_in: continue
            chords_in = [c for c in chords if s_beat <= c['beat'] < e_beat]
            key = norm_name(nm)
            if key in seen_names: continue
            seen_names.add(key)
            sections_out.append({
                'artist': song['artist'] or '',
                'title': song['title'] or '',
                'slug': song['slug'] or '',
                'sec': nm,
                'key': song.get('key_tonic') or 'C',
                'scale': song.get('key_scale') or 'major',
                'bpm': song.get('bpm') or '',
                'start': s_beat,
                'end': e_beat,
                'chords': [{'r': c.get('root'), 't': c.get('type', 0),
                            'b': round(c['beat'] - s_beat, 3),
                            'd': round(c.get('duration', 1), 3),
                            'bor': c.get('borrowed') or '',
                            'app': c.get('applied') or 0,
                            'adds': c.get('adds') or [],
                            'sus': c.get('suspensions') or []}
                           for c in chords_in],
                'notes': [{'sd': n.get('sd'), 'o': n.get('octave', 0),
                           'b': round(n['beat'] - s_beat, 3),
                           'd': round(n.get('duration', 0.5), 3),
                           'r': bool(n.get('isRest'))}
                          for n in notes_in],
            })

    sections_out.sort(key=lambda r: (r['artist'].lower(), r['title'].lower(), r['sec'].lower()))
    with open(OUT, 'w') as f: json.dump(sections_out, f, separators=(',', ':'))
    print(f'\n{len(sections_out)} sections → {OUT}')
    print(f'  file size: {os.path.getsize(OUT) / 1024:.1f} KB')

    from collections import Counter
    nm = Counter(r['sec'].lower() for r in sections_out)
    print(f'\ntop 10 section names in output:')
    for n, c in nm.most_common(10): print(f'  {c:>4}  {n}')


if __name__ == '__main__': main()
