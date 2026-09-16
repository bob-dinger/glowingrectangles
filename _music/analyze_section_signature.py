"""For every Hookpad section (8/10/12/14/16/24 bars), compute a unified phrase signature:
   tuple of (end_position_in_bars, density_in_notes_per_beat) per phrase.

The position dimension captures structure (phrase length pattern + metric end positions).
The density dimension captures feel (notes per beat — independent of BPM).

Outputs top signatures per section length with example songs.
"""
import os, json, re
from collections import Counter, defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

TARGET_BARS = {8, 10, 12, 14, 16, 24}
GAP_THRESHOLD = 2.0
EXCLUDE_SECS  = {'intro','outro','solo','instrumental','interlude','break',
                 'tag','coda','ending','section','instrumental bridge'}


def detect_phrase_starts(notes, threshold=GAP_THRESHOLD):
    if not notes: return []
    starts = [notes[0]['beat']]
    prev = notes[0]['beat']
    for n in notes[1:]:
        onset = n['beat']
        if onset - prev >= threshold:
            starts.append(onset)
        prev = onset
    return starts


def round_to(x, step):
    return round(x / step) * step


def norm(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())[:20]


def signature_of_section(notes, s_beat, e_beat, bpb):
    """Return list of (end_pos_bars, density_per_beat, n_notes) per phrase."""
    sec_notes = sorted((n for n in notes if s_beat <= n.get('beat', 0) < e_beat and not n.get('isRest')),
                       key=lambda n: n['beat'])
    if len(sec_notes) < 3: return None
    starts = detect_phrase_starts(sec_notes)
    if len(starts) < 1: return None

    out = []
    for i, st in enumerate(starts):
        nxt = starts[i+1] if i+1 < len(starts) else e_beat
        phrase_length_beats = nxt - st
        if phrase_length_beats <= 0: continue
        # Count notes in this phrase
        n_count = sum(1 for n in sec_notes if st <= n.get('beat', 0) < nxt)
        density = n_count / phrase_length_beats
        end_pos_bars = (nxt - s_beat) / bpb
        out.append((end_pos_bars, density, n_count))
    return out


def main():
    rows = (SB.schema('parcels').table('songs')
            .select('artist,title,bpm,bpm_canonical,hookpad_json')
            .not_.is_('hookpad_json','null').execute().data)
    print(f"scanning {len(rows)} songs...\n")

    by_length = defaultdict(list)  # bars → list of (artist, title, sec_name, signature, bpm)
    seen = set()
    for r in rows:
        hj = r['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        if not hj: continue
        bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        secs = hj.get('sections') or []
        notes = hj.get('notes') or (hj.get('polyphonicNotes') or [[]])[0]
        end_beat = hj.get('endBeat') or 1
        bpm = r.get('bpm_canonical') or r.get('bpm') or 120

        for i, sec in enumerate(secs):
            name = (sec.get('name','') or '').strip()
            if name.lower() in EXCLUDE_SECS: continue
            s_beat = sec.get('beat', 1)
            e_beat = secs[i+1]['beat'] if i+1 < len(secs) else end_beat
            bars = int(round((e_beat - s_beat) / bpb))
            if bars not in TARGET_BARS: continue
            k = (norm(r['artist']), norm(r['title']), norm(name), bars)
            if k in seen: continue
            seen.add(k)

            sig_raw = signature_of_section(notes, s_beat, e_beat, bpb)
            if not sig_raw or len(sig_raw) < 2: continue

            # Round for clustering: positions to nearest 0.5 bar, density to nearest 0.5 notes/beat
            sig_rounded = tuple((round_to(p, 0.5), round_to(d, 0.5)) for p, d, _ in sig_raw)
            if any(p == 0 for p, _ in sig_rounded): continue

            by_length[bars].append((r['artist'], r['title'], name, sig_rounded, sig_raw, bpm))

    # Report per length
    for bars in sorted(TARGET_BARS):
        hits = by_length.get(bars, [])
        if not hits: continue
        ctr = Counter(sig for _,_,_,sig,_,_ in hits)
        print(f"\n{'='*85}")
        print(f"  {bars}-bar sections — {len(hits)} unique sections, {len(ctr)} distinct signatures")
        print(f"{'='*85}")
        for sig, n in ctr.most_common(8):
            sig_str = ' | '.join(f"pos={p} d={d}/b" for p, d in sig)
            # Show 3 examples + their raw densities
            examples = [(a,t,sn,raw,bpm) for a,t,sn,s,raw,bpm in hits if s == sig][:3]
            print(f"\n  ×{n:>3}  signature: {sig_str}")
            for a,t,sn,raw,bpm in examples:
                raw_str = ', '.join(f"{p:.2f}@{d:.2f}n/b" for p,d,_ in raw)
                notes_per_sec = sum(c for _,_,c in raw) / (sum(raw[i+1][0] if i+1<len(raw) else (raw[-1][0]) for i in range(len(raw))) / 1)  # rough
                print(f"      · {a[:20]:<20} — {t[:24]:<24} [{sn[:9]}]  raw: {raw_str}")


if __name__ == '__main__':
    main()
