"""Multi-level, multi-modal section template analyzer.

For each section (chorus / verse / bridge) in Beatles + Guitar 50 + Guitar 100:
- Compute letter strings at chunk sizes 4, 2, 1 bars
- In three modes: melody (pitch sequence), rhythm (onset+duration), progression
  (chord identity per measure)
- For a curated set of 10 archetypes per section type, pick one canonical song
  and show its full multi-modal fingerprint.

Writes ~/Desktop/song-templates.txt.
"""
import os, re, json
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = '/Users/robert/Desktop/glowinggardens_claude/_music'
OUT = os.path.expanduser('~/Desktop/song-templates.txt')


def slugs_from_page(fn):
    html = open(f'{HERE}/{fn}').read()
    m = re.search(r'const SONGS\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    return [(s['slug'], s.get('title',''), s.get('artist',''))
            for s in json.loads(m.group(1)) if s.get('slug')]


def parse_sd(sd):
    s = str(sd); acc = 0
    while s and s[0] in 'b#':
        acc += -1 if s[0]=='b' else 1; s = s[1:]
    if not s.isdigit(): return None
    deg = int(s)
    if deg < 1 or deg > 7: return None
    return [0,2,4,5,7,9,11][deg-1] + acc


def hashable(x):
    if isinstance(x, list): return tuple(hashable(v) for v in x)
    if isinstance(x, dict): return tuple(sorted((k, hashable(v)) for k,v in x.items()))
    return x


def chord_id(c):
    return (str(c.get('root','')), str(c.get('type','')), c.get('applied') or 0,
            hashable(c.get('borrowed') or ''), hashable(c.get('adds') or []))


Q = lambda v: round(v * 4) / 4  # 1/16-note quantization


def melody_sig(notes, ws, we):
    in_w = sorted([n for n in notes if not n.get('isRest') and ws <= n.get('beat', 0) < we],
                  key=lambda n: n.get('beat', 0))
    out = []
    for n in in_w:
        sd = parse_sd(n.get('sd', '1'))
        if sd is None: continue
        out.append((n.get('octave') or 0)*12 + sd)
    return tuple(out)


def rhythm_sig(notes, ws, we):
    in_w = sorted([n for n in notes if not n.get('isRest') and ws <= n.get('beat', 0) < we],
                  key=lambda n: n.get('beat', 0))
    out = []
    for n in in_w:
        beat_rel = Q(n.get('beat', 0) - ws)
        dur = min(n.get('duration', 0), we - n.get('beat', 0))
        out.append((beat_rel, Q(dur)))
    return tuple(out)


def per_measure_progression(chords, sec_start, sec_end, bpb):
    """Resolve the chord sounding at the start of each measure across the WHOLE
    section. Honors chords whose duration crosses measure boundaries."""
    n_bars = round((sec_end - sec_start) / bpb)
    measures = [None] * n_bars
    sorted_chords = sorted(chords, key=lambda c: c.get('beat', 0))
    for c in sorted_chords:
        if c.get('isRest'): continue
        cb = c.get('beat', 0)
        cd = c.get('duration', 0)
        # The chord sounds over beats [cb, cb+cd). Mark every measure it touches.
        if cb + cd <= sec_start or cb >= sec_end: continue
        first_m = max(0, int((cb - sec_start) / bpb))
        # End measure: last measure whose START is before chord ends
        last_m = min(n_bars - 1, int((cb + cd - 1e-9 - sec_start) / bpb))
        for m in range(first_m, last_m + 1):
            if measures[m] is None:
                measures[m] = chord_id(c)
    # Final carry-forward for measures with truly no chord
    last = None
    for i in range(n_bars):
        if measures[i] is None: measures[i] = last
        else: last = measures[i]
    return measures


def letters_for(sigs):
    L, seen = [], {}
    for s in sigs:
        if s not in seen: seen[s] = chr(ord('A') + len(seen))
        L.append(seen[s])
    return ''.join(L)


def analyze_section(section, sections, end_beat, bpb, notes, chords):
    start = section.get('beat', 0)
    i = sections.index(section)
    end = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
    bars = round((end - start) / bpb)
    if bars < 1: return None
    per_measure = per_measure_progression(chords, start, end, bpb)
    levels = {}
    for cs in (4, 2, 1):
        if bars % cs or bars // cs < 2: continue
        n_phrases = bars // cs
        mel = [melody_sig(notes, start + p*cs*bpb, start + (p+1)*cs*bpb) for p in range(n_phrases)]
        rhy = [rhythm_sig(notes, start + p*cs*bpb, start + (p+1)*cs*bpb) for p in range(n_phrases)]
        pro = [tuple(per_measure[p*cs:(p+1)*cs]) for p in range(n_phrases)]
        levels[cs] = {
            'melody':      letters_for(mel),
            'rhythm':      letters_for(rhy),
            'progression': letters_for(pro),
        }
    return {'bars': bars, 'name': section.get('name', '?'), 'levels': levels}


def section_analyses(d, section_kw):
    sections = sorted(d.get('sections') or [], key=lambda s: s.get('beat', 0))
    bpb = ((d.get('meters') or [{}])[0].get('numBeats')) or 4
    end_beat = d.get('endBeat') or 0
    notes = d.get('notes') or []
    chords = d.get('chords') or []
    for s in sections:
        nm = (s.get('name') or '').lower().strip()
        if section_kw not in nm: continue
        a = analyze_section(s, sections, end_beat, bpb, notes, chords)
        if a: yield a


# ---------- Curated archetypes (define by 2-bar melody letters + bar count) ----------
CURATED = {
    'choruses': [
        ('8 bars, 4+4 — two identical 4-bar phrases',          {'bars': 8, 'cs': 4, 'mel': 'AA'}),
        ('8 bars, 4+4 — antecedent + consequent',              {'bars': 8, 'cs': 4, 'mel': 'AB'}),
        ('8 bars, 2-bar — call-response (← your starter)',     {'bars': 8, 'cs': 2, 'mel': 'ABAB'}),
        ('8 bars, 2-bar — three same + a turn (← user)',       {'bars': 8, 'cs': 2, 'mel': 'AAAB'}),
        ('8 bars, 2-bar — mini Tin Pan Alley',                 {'bars': 8, 'cs': 2, 'mel': 'AABA'}),
        ('8 bars, 2-bar — return with a twist',                {'bars': 8, 'cs': 2, 'mel': 'ABAC'}),
        ('12 bars, 4+4+4 — extended AAB (← user)',             {'bars': 12, 'cs': 4, 'mel': 'AAB'}),
        ('16 bars, 4-bar — classic Tin Pan Alley (← user)',    {'bars': 16, 'cs': 4, 'mel': 'AABA'}),
        ('16 bars, 4-bar — long-form repetitive AAAA',         {'bars': 16, 'cs': 4, 'mel': 'AAAA'}),
        ('16 bars, 4-bar — extended ABAB',                     {'bars': 16, 'cs': 4, 'mel': 'ABAB'}),
    ],
    'verses': [
        ('8 bars, 4+4 — two identical phrases (← user)',       {'bars': 8, 'cs': 4, 'mel': 'AA'}),
        ('8 bars, 4+4 — antecedent + consequent',              {'bars': 8, 'cs': 4, 'mel': 'AB'}),
        ('8 bars, 2-bar — call-response',                      {'bars': 8, 'cs': 2, 'mel': 'ABAB'}),
        ('8 bars, 2-bar — mini Tin Pan Alley',                 {'bars': 8, 'cs': 2, 'mel': 'AABA'}),
        ('8 bars, 2-bar — sets up tension (← user)',           {'bars': 8, 'cs': 2, 'mel': 'ABBC'}),
        ('10 bars, 5+5 — 10-bar two-phrase (← user)',          {'bars': 10, 'cs': 5, 'mel': 'AA'}),
        ('12 bars, 4+4+4 — extended AAB (← user)',             {'bars': 12, 'cs': 4, 'mel': 'AAB'}),
        ('16 bars, 4-bar — "Hurricane" shape (← user)',        {'bars': 16, 'cs': 4, 'mel': 'AABC'}),
        ('16 bars, 4-bar — "Sunny Came Home" shape (← user)',  {'bars': 16, 'cs': 4, 'mel': 'ABAC'}),
        ('16 bars, 4-bar — classic AABA',                      {'bars': 16, 'cs': 4, 'mel': 'AABA'}),
    ],
    'bridges': [
        ('8 bars, 2-bar — three same + turn (← user)',         {'bars': 8, 'cs': 2, 'mel': 'AAAB'}),
        ('8 bars, 2-bar — frame returns (← user)',             {'bars': 8, 'cs': 2, 'mel': 'ABCB'}),
        ('8 bars, 4+4 — simple AB',                            {'bars': 8, 'cs': 4, 'mel': 'AB'}),
        ('8 bars, 2-bar — all-new material',                   {'bars': 8, 'cs': 2, 'mel': 'ABCD'}),
        ('4 bars, 2-bar — mini bridge',                        {'bars': 4, 'cs': 2, 'mel': 'AB'}),
        ('4 bars, 2-bar — mini repeating',                     {'bars': 4, 'cs': 2, 'mel': 'AA'}),
        ('8 bars, 2-bar — call-response bridge',               {'bars': 8, 'cs': 2, 'mel': 'ABAB'}),
        ('8 bars, 2-bar — AABA-shaped bridge',                 {'bars': 8, 'cs': 2, 'mel': 'AABA'}),
        ('12 bars, 4-bar — extended bridge',                   {'bars': 12, 'cs': 4, 'mel': 'ABC'}),
        ('16 bars, 4-bar — long call-response bridge',         {'bars': 16, 'cs': 4, 'mel': 'ABAB'}),
    ],
}


def main():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    pool = {}
    for fn in ['Beatles-Study.html', 'Guitar50.html', 'Guitar100.html']:
        for slug, t, a in slugs_from_page(fn):
            pool.setdefault(slug, {'title': t, 'artist': a})
    all_data = []
    for i in range(0, len(pool), 100):
        chunk = list(pool.keys())[i:i+100]
        rows = sb.schema('parcels').table('songs').select('slug,hookpad_json').in_('slug', chunk).execute().data
        for r in rows:
            if r.get('hookpad_json'): all_data.append(r)
    print(f"loaded {len(all_data)} songs")

    by_section = {'choruses': [], 'verses': [], 'bridges': []}
    for r in all_data:
        meta = pool.get(r['slug'], {})
        for kw, key in [('chorus', 'choruses'), ('verse', 'verses'), ('bridge', 'bridges')]:
            for a in section_analyses(r['hookpad_json'], kw):
                by_section[key].append({**a, **meta, 'slug': r['slug']})

    def find_match(items, criteria):
        bars, cs, mel = criteria['bars'], criteria['cs'], criteria['mel']
        out = []
        for it in items:
            lv = it['levels'].get(cs)
            if not lv: continue
            if it['bars'] == bars and lv['melody'] == mel:
                out.append(it)
        return out

    lines = []
    lines.append("Song Section Templates — Beatles + Guitar 50 + Guitar 100")
    lines.append("Multi-level, multi-modal analyzer:")
    lines.append("  · levels: 4-bar / 2-bar / 1-bar phrase chunks")
    lines.append("  · modes:  melody (pitch sequence), rhythm (onset + duration),")
    lines.append("            progression (chord identity per measure)")
    lines.append("")
    for sec, archetypes in CURATED.items():
        items = by_section[sec]
        lines.append("=" * 72)
        lines.append(f"  10 {sec}")
        lines.append("=" * 72)
        for desc, crit in archetypes:
            matches = find_match(items, crit)
            lines.append(f"\n  {desc}")
            lines.append(f"  → {crit['bars']}-bar @ {crit['cs']}-bar level → melody = {crit['mel']}  ({len(matches)} matches)")
            for ex in matches[:3]:
                lines.append(f"    · {ex['artist']} — {ex['title']}  [{ex['name']}]")
                for cs in (4, 2, 1):
                    lv = ex['levels'].get(cs)
                    if not lv: continue
                    lines.append(f"        {cs}-bar:  melody={lv['melody']:<10}  rhythm={lv['rhythm']:<10}  progression={lv['progression']}")
            if not matches:
                lines.append(f"    (no examples in pool)")
        lines.append("")

    open(OUT, 'w').write('\n'.join(lines))
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
