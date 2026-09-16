"""Look up a song in Supabase and open its chord progression in chord-viz.html.

Usage:
    python show_song.py "you won't see me"
    python show_song.py "wide awake" --artist katy
    python show_song.py "dear prudence" --sections all
"""
import os, sys, json, re, argparse, subprocess, urllib.parse
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chord_label import chord_label   # canonical labeler — single source of truth

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])


def normalize(s):
    s = (s or '').lower().strip()
    for ch in [".", ",", "!", "?", "'", "'", "'", "&", ":"]: s = s.replace(ch, "")
    return re.sub(r'\s+', ' ', s)


def best_match(all_songs, qt, qa=None):
    qt = normalize(qt); qa = normalize(qa or '')
    best, best_score = None, 0
    for r in all_songs:
        rt = normalize(r['title']); ra = normalize(r['artist'])
        score = 0
        if qt == rt: score += 4
        elif qt in rt or rt in qt: score += 2
        if qa and (qa == ra or qa in ra or ra in qa): score += 2
        if score > best_score:
            best_score = score; best = r
    return best if best_score >= 2 else None


def find_repeating_progression(sec_chords, bpm, scale):
    """Find the dominant 4-chord cycle (2 or 4 measures, repeating 2+ times, ≥3 distinct)."""
    if len(sec_chords) < 4: return None
    from collections import defaultdict
    prog_counts = defaultdict(int)
    for j in range(len(sec_chords) - 3):
        first = sec_chords[j]
        # Need start position relative to section
        start_in_sec = first.get('_b_in_sec', 0)
        window = sec_chords[j:j+4]
        total = sum(c.get('duration', 1) for c in window)
        measures = total / bpm
        if 1.95 <= measures <= 2.05:
            if abs((start_in_sec / (2*bpm)) - round(start_in_sec / (2*bpm))) > 0.01: continue
            m = 2
        elif 3.95 <= measures <= 4.05:
            if abs((start_in_sec / (4*bpm)) - round(start_in_sec / (4*bpm))) > 0.01: continue
            m = 4
        else: continue
        labels = tuple(chord_label(c, scale) for c in window)
        if len(set(labels)) < 3: continue
        prog_counts[labels] += 1
    if not prog_counts: return None
    # Pick the most repeated; tiebreak by earliest position
    best = max(prog_counts.items(), key=lambda x: x[1])
    if best[1] < 2: return None
    return '-'.join(best[0])


EXCLUDE = {'intro','outro','solo','instrumental bridge','instrumental','interlude','break','tag','coda','ending','section'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('title')
    ap.add_argument('--artist', default=None)
    ap.add_argument('--sections', default='main',
                    help="'main' = most-frequent cycle; 'all' = every distinct section's cycle")
    args = ap.parse_args()

    all_songs = SB.schema('parcels').table('songs').select(
        'slug,title,artist,bpm,key_tonic,key_scale,hookpad_json'
    ).not_.is_('hookpad_json', 'null').execute().data

    m = best_match(all_songs, args.title, args.artist)
    if not m:
        print(f"no match for {args.title!r}"); sys.exit(1)

    hj = m['hookpad_json']
    if isinstance(hj, str): hj = json.loads(hj)
    bpm_meas = (hj.get('meters') or [{}])[0].get('numBeats', 4)
    end_beat = hj.get('endBeat') or 1
    chords = hj.get('chords') or []
    secs = hj.get('sections') or []
    scale = m.get('key_scale') or 'major'

    sections_output = []   # (label, progression)
    seen_keys = set()
    for i, sec in enumerate(secs):
        nm = (sec.get('name','') or '').strip()
        if nm.lower() in EXCLUDE: continue
        key = re.sub(r'\b(\d+|i+|ii|iii|iv|v|vi|vii|1st|2nd|3rd)\b', '', nm.lower()).strip()
        if key in seen_keys: continue
        seen_keys.add(key)
        s_beat = sec['beat']
        e_beat = secs[i+1]['beat'] if i+1 < len(secs) else end_beat
        sec_chords = [dict(c, _b_in_sec=c['beat']-s_beat) for c in chords if s_beat <= c['beat'] < e_beat]
        if not sec_chords: continue
        prog = find_repeating_progression(sec_chords, bpm_meas, scale)
        if prog:
            sections_output.append((nm, prog))

    if not sections_output:
        print(f"no repeating cycle found in any section of {m['title']}")
        sys.exit(1)

    # If "main" mode: keep only the most common progression's first occurrence
    if args.sections == 'main':
        from collections import Counter
        prog_freq = Counter(p for _, p in sections_output)
        top_prog, _ = prog_freq.most_common(1)[0]
        # use the first section that has this prog
        keep = next((nm, p) for nm, p in sections_output if p == top_prog)
        sections_output = [keep]

    # Build URL for chord-viz.html
    base = 'file:///Users/robert/Desktop/glowinggardens_claude/_music/chord-viz.html'
    params = {
        'title': f"{m['title']} — {m['artist']}",
        'meta':  f"{m['key_tonic'] or '?'} {scale}  ·  {m['bpm'] or '?'} BPM",
        'prog':  '|'.join(p for _, p in sections_output),
        'labels':'|'.join(n for n, _ in sections_output),
        'key':   m['key_tonic'] or 'C',
    }
    url = base + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    print(f"{m['artist']} — {m['title']} ({m['key_tonic']} {scale})")
    for nm, p in sections_output:
        print(f"  {nm:18s}  {p}")
    print(f"\nopening {url[:80]}...")

    # Open in default browser
    subprocess.run(['open', url])


if __name__ == '__main__':
    main()
