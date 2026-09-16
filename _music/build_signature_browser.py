"""Export section signature data for the browser page.
Writes to /_music/section-signatures.json — one record per unique song-section in
target bar lengths (8, 10, 12, 14, 16, 24). Includes phrase structure, end positions,
densities, uniformity flag, and consensus position.
"""
import os, json, re, math
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

SB = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

TARGET_BARS = {8, 10, 12, 14, 16, 24}
GAP = 2.0
UNI_TOL = 0.1
EXCLUDE = {'intro','outro','solo','instrumental','interlude','break','tag','coda','ending','section','instrumental bridge'}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'section-signatures.json')


def detect_starts(notes):
    if not notes: return []
    out = [notes[0]['beat']]; prev = notes[0]['beat']
    for n in notes[1:]:
        if n['beat'] - prev >= GAP: out.append(n['beat'])
        prev = n['beat']
    return out


def circular_uniform(fracs, tol):
    if len(fracs) < 2: return True, fracs[0] if fracs else None
    for i in range(len(fracs)):
        for j in range(i+1, len(fracs)):
            d = abs(fracs[i]-fracs[j]); d = min(d, 1-d)
            if d > tol: return False, None
    sin_sum = sum(math.sin(2*math.pi*f) for f in fracs)
    cos_sum = sum(math.cos(2*math.pi*f) for f in fracs)
    if abs(sin_sum) < 1e-9 and abs(cos_sum) < 1e-9: return True, sum(fracs)/len(fracs)
    ang = math.atan2(sin_sum, cos_sum) / (2*math.pi)
    if ang < 0: ang += 1
    return True, ang


def signature(notes, s_beat, e_beat, bpb):
    sn = sorted((n for n in notes if s_beat <= n.get('beat',0) < e_beat and not n.get('isRest')),
                key=lambda n: n['beat'])
    if len(sn) < 3: return None
    sts = detect_starts(sn)
    phr = []
    for i, st in enumerate(sts):
        nxt = sts[i+1] if i+1 < len(sts) else e_beat
        pn = [n for n in sn if st <= n['beat'] < nxt]
        if not pn: continue
        last_onset = pn[-1]['beat']
        phr.append({
            'start_pos': round((st - s_beat)/bpb, 3),
            'end_pos':   round((last_onset - s_beat)/bpb, 3),
            'length':    round((nxt - st)/bpb, 3),
            'density':   round(len(pn) / (nxt - st), 3),
            'n':         len(pn),
        })
    if len(phr) < 2: return None
    fracs = [p['end_pos'] % 1.0 for p in phr]
    is_uni, consensus = circular_uniform(fracs, UNI_TOL)
    # Every note as [start_bars, duration_bars] for piano-roll style horizontal bars
    notes_xy = [[round((n['beat'] - s_beat)/bpb, 3),
                 round(n.get('duration', 0.25)/bpb, 3)] for n in sn]
    return {
        'phrases': phr,
        'is_uniform': is_uni,
        'consensus_position': round(consensus, 3) if consensus is not None else None,
        'n_phrases': len(phr),
        'notes_xy': notes_xy,
    }


def canon_section(name):
    s = (name or '').lower().strip()
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'\s+(\d+|i+|ii|iii|iv|v|vi|vii|viii|1st|2nd|3rd|4th)\s*$', '', s)
    s = re.sub(r'[_-]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '', (s or '').lower())[:20]


def main():
    rows = (SB.schema('parcels').table('songs')
            .select('artist,title,bpm,bpm_canonical,key_tonic,key_scale,hookpad_json')
            .not_.is_('hookpad_json','null').execute().data)
    print(f"scanning {len(rows)} songs...")

    out = []
    seen = set()
    for r in rows:
        hj = r['hookpad_json']
        if isinstance(hj, str): hj = json.loads(hj)
        if not hj: continue
        bpb = (hj.get('meters') or [{}])[0].get('numBeats', 4)
        end_b = hj.get('endBeat') or 1
        notes = hj.get('notes') or (hj.get('polyphonicNotes') or [[]])[0]
        secs = hj.get('sections') or []
        for i, sec in enumerate(secs):
            name = (sec.get('name','') or '').strip()
            if name.lower() in EXCLUDE: continue
            s_b = sec['beat']; e_b = secs[i+1]['beat'] if i+1 < len(secs) else end_b
            bars = int(round((e_b - s_b)/bpb))
            if bars not in TARGET_BARS: continue
            canon = canon_section(name)
            k = (slug(r['artist']), slug(r['title']), canon, bars)
            if k in seen: continue
            seen.add(k)
            sig = signature(notes, s_b, e_b, bpb)
            if not sig: continue
            out.append({
                'artist':            r['artist'],
                'title':             r['title'],
                'section':           name,
                'section_canon':     canon,
                'bars':              bars,
                'bpb':               bpb,
                'key_tonic':         r.get('key_tonic'),
                'key_scale':         r.get('key_scale'),
                'bpm':               r.get('bpm'),
                'bpm_canonical':     r.get('bpm_canonical'),
                'phrases':           sig['phrases'],
                'is_uniform':        sig['is_uniform'],
                'consensus_position': sig['consensus_position'],
                'n_phrases':         sig['n_phrases'],
                'notes_xy':          sig['notes_xy'],
            })

    # Sort: by bar count, then by song
    out.sort(key=lambda x: (x['bars'], x['artist'].lower(), x['title'].lower()))
    with open(OUT, 'w') as f:
        json.dump(out, f)
    print(f"  wrote {len(out)} sections → {OUT}")
    by_bars = {}
    for s in out:
        by_bars[s['bars']] = by_bars.get(s['bars'], 0) + 1
    for b in sorted(by_bars):
        print(f"    {b}-bar: {by_bars[b]} sections")

    # Also write a self-contained HTML with the data embedded inline (avoids CORS on file://).
    # Use string-replace (not re.sub) to avoid JSON unicode escapes breaking the regex.
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'section-signatures.html')
    if os.path.exists(html_path):
        html = open(html_path).read()
        inline = "<script id='inline-data'>window.__SECTION_DATA__ = " + json.dumps(out) + ";</script>"
        # If a previous inline-data block exists, replace it; else insert before main script
        start = "<script id='inline-data'>"
        if start in html:
            end_marker = "</script>"
            i = html.index(start)
            j = html.index(end_marker, i) + len(end_marker)
            new_html = html[:i] + inline + html[j:]
        else:
            new_html = html.replace('<script>\nlet DATA = []', inline + '\n<script>\nlet DATA = []', 1)
        open(html_path, 'w').write(new_html)
        print(f"  embedded data into → {html_path}")


if __name__ == '__main__':
    main()
