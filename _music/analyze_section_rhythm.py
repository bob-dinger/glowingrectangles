"""For each section in the Hookpad library, detect rhythm-phrase structure
   and report the recurring patterns at each section length (8, 10, 12, 14, 16, 24 bars).

Phrase detection: inter-onset gap >= threshold (default 1.5 beats) marks a phrase
boundary. Pattern signature = tuple of phrase lengths in bars (rounded to nearest 0.5).
"""
import os, json
from collections import Counter, defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

TARGET_BARS = {8, 10, 12, 14, 16, 24}
GAP_THRESHOLD = 2.0   # beats — inter-onset gap that signals a new phrase
EXCLUDE_SECS  = {'intro','outro','solo','instrumental','interlude','break',
                 'tag','coda','ending','section','instrumental bridge'}


def detect_phrase_starts(notes, threshold=GAP_THRESHOLD):
    """Return list of (start_beat) for each phrase — onset positions only."""
    if not notes: return []
    starts = [notes[0]['beat']]
    prev_onset = notes[0]['beat']
    for n in notes[1:]:
        onset = n['beat']
        if onset - prev_onset >= threshold:
            starts.append(onset)
        prev_onset = onset
    return starts


def round_half(x):
    return round(x * 2) / 2


def round_quarter(x):
    return round(x * 4) / 4


def main():
    rows = (SB.schema('parcels').table('songs')
            .select('artist,title,key_tonic,key_scale,hookpad_json')
            .not_.is_('hookpad_json', 'null').execute().data)
    print(f"scanning {len(rows)} songs...\n")

    by_length = defaultdict(list)   # bars → list of (artist, title, sec_name, pattern_tuple)
    seen_song_section = set()       # dedupe (artist_norm, title_norm, section_norm)

    def norm(s):
        import re
        return re.sub(r'[^a-z0-9]+', '', (s or '').lower())[:20]

    for r in rows:
        hj = r['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        if not hj: continue
        bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        secs = hj.get('sections') or []
        chords = hj.get('chords') or []
        notes = hj.get('notes') or (hj.get('polyphonicNotes') or [[]])[0]
        end_beat = hj.get('endBeat') or 1

        for i, sec in enumerate(secs):
            name = (sec.get('name','') or '').strip()
            if name.lower() in EXCLUDE_SECS: continue
            s_beat = sec.get('beat', 1)
            e_beat = secs[i+1]['beat'] if i+1 < len(secs) else end_beat
            bars = int(round((e_beat - s_beat) / bpb))
            if bars not in TARGET_BARS: continue
            # Dedupe by (artist, title, section name, bar count) — multiple Hookpad copies of same song
            dedup_key = (norm(r['artist']), norm(r['title']), norm(name), bars)
            if dedup_key in seen_song_section: continue
            seen_song_section.add(dedup_key)

            sec_notes = sorted(
                (n for n in notes if s_beat <= n.get('beat',0) < e_beat and not n.get('isRest')),
                key=lambda n: n['beat']
            )
            if len(sec_notes) < 3: continue

            # Phrase ALLOTMENTS: starts → consecutive starts give the allotted length of each phrase
            # (the LAST phrase's allotment = section_end - last_start)
            starts = detect_phrase_starts(sec_notes)
            if len(starts) < 2: continue
            allotments = []
            for j in range(len(starts)):
                end = starts[j+1] if j+1 < len(starts) else e_beat
                allotments.append((end - starts[j]) / bpb)
            # Round to half bars
            pattern = tuple(round_half(a) for a in allotments)
            # Drop noisy patterns: any phrase < 1 bar OR more than 6 phrases
            if any(p < 1 for p in pattern): continue
            if len(pattern) > 6: continue
            if sum(pattern) < bars * 0.5: continue   # weird truncation
            by_length[bars].append((r['artist'], r['title'], name, pattern))

    # Per section length, report top patterns
    for bars in sorted(TARGET_BARS):
        hits = by_length.get(bars, [])
        if not hits: continue
        ctr = Counter(p for _,_,_,p in hits)
        print(f"\n{'='*75}")
        print(f"  {bars}-bar sections — {len(hits)} sections found, {len(ctr)} distinct patterns")
        print(f"{'='*75}")
        for pattern, n in ctr.most_common(10):
            # Show example songs
            examples = [(a,t,sn) for a,t,sn,p in hits if p == pattern][:4]
            ex_str = '; '.join(f"{a[:18]} — {t[:22]} [{sn[:9]}]" for a,t,sn in examples)
            pattern_str = '+'.join(str(int(p)) if p == int(p) else str(p) for p in pattern)
            print(f"  ×{n:>3}  {pattern_str:<24}  {ex_str}")


if __name__ == '__main__':
    main()
