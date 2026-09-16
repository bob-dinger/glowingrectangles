"""Find sections with uniform phrase-end metric position (Level C fuzziness).

A section is "uniform" if every phrase's last-onset position-within-bar is within
a small tolerance of every other phrase's. The consensus position (computed via
circular mean) is the section's signature.

NO ROUNDING — all values kept at full precision. Sections with similar consensus
positions cluster naturally without forced bucketing.
"""
import os, json, re, math
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

TARGET_BARS = {8, 10, 12, 14, 16, 24}
GAP_THRESHOLD = 2.0
UNIFORMITY_TOL = 0.1   # bar-fraction tolerance for "same metric position"
EXCLUDE_SECS = {'intro','outro','solo','instrumental','interlude','break',
                'tag','coda','ending','section','instrumental bridge'}


def detect_phrase_starts(notes, threshold=GAP_THRESHOLD):
    if not notes: return []
    starts = [notes[0]['beat']]
    prev = notes[0]['beat']
    for n in notes[1:]:
        if n['beat'] - prev >= threshold:
            starts.append(n['beat'])
        prev = n['beat']
    return starts


def circular_uniform(fracs, tol):
    """True iff all fractional positions are within tol of each other (on the circle).
    Returns (is_uniform, consensus_mean) where consensus_mean is circular mean."""
    if len(fracs) < 2: return True, fracs[0] if fracs else None
    # Pairwise circular distance
    for i in range(len(fracs)):
        for j in range(i+1, len(fracs)):
            d = abs(fracs[i] - fracs[j])
            d = min(d, 1.0 - d)
            if d > tol:
                return False, None
    # Circular mean via sin/cos
    sin_sum = sum(math.sin(2*math.pi*f) for f in fracs)
    cos_sum = sum(math.cos(2*math.pi*f) for f in fracs)
    if abs(sin_sum) < 1e-9 and abs(cos_sum) < 1e-9: return True, sum(fracs)/len(fracs)
    mean_angle = math.atan2(sin_sum, cos_sum)
    mean_frac = mean_angle / (2*math.pi)
    if mean_frac < 0: mean_frac += 1.0
    return True, mean_frac


def signature(notes, s_beat, e_beat, bpb):
    sec_notes = sorted((n for n in notes if s_beat <= n.get('beat',0) < e_beat and not n.get('isRest')),
                       key=lambda n: n['beat'])
    if len(sec_notes) < 3: return None
    starts = detect_phrase_starts(sec_notes)
    if len(starts) < 2: return None

    phrases = []
    for i, st in enumerate(starts):
        nxt = starts[i+1] if i+1 < len(starts) else e_beat
        phrase_notes = [n for n in sec_notes if st <= n.get('beat',0) < nxt]
        if not phrase_notes: continue
        last_onset_beat = phrase_notes[-1]['beat']
        end_pos_bars = (last_onset_beat - s_beat) / bpb
        length_beats = nxt - st
        density = len(phrase_notes) / length_beats
        phrases.append({
            'end_pos': end_pos_bars,
            'frac': end_pos_bars % 1.0,
            'density': density,
            'n': len(phrase_notes),
        })

    if len(phrases) < 2: return None
    fracs = [p['frac'] for p in phrases]
    is_uniform, consensus = circular_uniform(fracs, UNIFORMITY_TOL)
    return {'phrases': phrases, 'is_uniform': is_uniform, 'consensus': consensus}


def norm(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())[:20]


def canon_section(name):
    """Collapse 'Verse 1', 'Verse II', 'Verse (instrumental)' → 'verse'."""
    s = (name or '').lower().strip()
    s = re.sub(r'\s*\([^)]*\)', '', s)                            # strip parentheticals
    s = re.sub(r'\s+(\d+|i+|ii|iii|iv|v|vi|vii|viii|1st|2nd|3rd|4th)\s*$', '', s)
    s = re.sub(r'[_-]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def main():
    rows = (SB.schema('parcels').table('songs')
            .select('artist,title,bpm,hookpad_json')
            .not_.is_('hookpad_json','null').execute().data)
    print(f"scanning {len(rows)} songs...\n")

    uniform_hits = []   # (consensus, bars, artist, title, sec_name, phrases)
    seen = set()
    n_sections_seen = 0
    for r in rows:
        hj = r['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        if not hj: continue
        bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        secs = hj.get('sections') or []
        notes = hj.get('notes') or (hj.get('polyphonicNotes') or [[]])[0]
        end_beat = hj.get('endBeat') or 1

        for i, sec in enumerate(secs):
            name = (sec.get('name','') or '').strip()
            if name.lower() in EXCLUDE_SECS: continue
            s_beat = sec.get('beat',1)
            e_beat = secs[i+1]['beat'] if i+1 < len(secs) else end_beat
            bars = int(round((e_beat - s_beat)/bpb))
            if bars not in TARGET_BARS: continue
            k = (norm(r['artist']), norm(r['title']), canon_section(name), bars)
            if k in seen: continue
            seen.add(k)
            n_sections_seen += 1

            sig = signature(notes, s_beat, e_beat, bpb)
            if not sig: continue
            if sig['is_uniform']:
                uniform_hits.append((sig['consensus'], bars, r['artist'], r['title'], name, sig['phrases']))

    print(f"  total qualifying sections:           {n_sections_seen}")
    print(f"  sections with UNIFORM end position:  {len(uniform_hits)}  ({100*len(uniform_hits)/n_sections_seen:.1f}%)")

    # Cluster by consensus position
    bins = defaultdict(list)  # rough bin (round to 0.05 for grouping display) → hits
    for hit in uniform_hits:
        c = round(hit[0] * 20) / 20   # bin to nearest 0.05 just for display grouping
        bins[c].append(hit)

    print(f"\n=== Uniform-position sections by consensus position ===")
    for pos in sorted(bins.keys()):
        n = len(bins[pos])
        if n < 3: continue   # only show clusters of 3+
        print(f"\n  position ≈ {pos:.2f}  (= beat {pos*4 + 1:.2f} of bar) — {n} sections")
        # Show up to 6 examples
        for c, b, a, t, sn, ph in sorted(bins[pos], key=lambda x: -len(x[5]))[:6]:
            phrase_lengths = []
            for i in range(len(ph)):
                if i == 0: phrase_lengths.append(ph[i]['end_pos'])
                else: phrase_lengths.append(ph[i]['end_pos'] - ph[i-1]['end_pos'])
            lens_str = '+'.join(f"{x:.1f}" for x in phrase_lengths)
            densities = '/'.join(f"{p['density']:.1f}" for p in ph)
            print(f"    {b}-bar  {len(ph)} phr  lens=[{lens_str}]  d=[{densities}]  ·  {a[:18]} — {t[:24]} [{sn[:9]}]")


if __name__ == '__main__':
    main()
