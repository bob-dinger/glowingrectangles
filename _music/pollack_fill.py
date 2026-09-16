"""Generic Pollack->Hookpad chord filler.

INVARIANT: Hookpad section lengths are ground truth. Chords are fit INTO each
section's exact bar count -- never resize a section. If Pollack's progression is
shorter it is looped/held to fill; if longer it is truncated (the overflow is the
"his Verse = your verse+chorus" case, handled by assigning his long figure to the
first section and letting the tail flow into the next).

Usage:
    python3 pollack_fill.py <title> <pollack_slug>
    python3 pollack_fill.py --all        # batch every target, print confidence
"""
import os, sys, json, hashlib, re, itertools
import psycopg2
from dotenv import load_dotenv
from pollack_parse import parse_song
from pollack_assemble import expand_figure
from chord_to_hookpad import chord_to_hookpad

load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
BPB = 4
OUT_DIR = os.path.expanduser('~/Desktop/pollack_pastes')
CHORD_ORDER = ['root', 'beat', 'duration', 'type', 'inversion', 'applied',
               'adds', 'omits', 'alterations', 'suspensions', 'substitutions',
               'pedal', 'alternate', 'borrowed', 'isRest', 'recordingEndBeat']

NOTE_PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
           'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def _db():
    return psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', 5432))

# ---- Hookpad side -----------------------------------------------------------

def load_hookpad(cur, title, artist_like='%beatl%'):
    cur.execute("""select key_tonic, key_scale, hookpad_json from parcels.songs
        where title ilike %s and artist ilike %s and hookpad_json is not null
        order by jsonb_array_length(hookpad_json->'sections') desc nulls last limit 1""",
        (title, artist_like))
    row = cur.fetchone()
    if not row: return None
    kt, ks, hj = row
    secs = hj['sections']; end = hj['endBeat']
    bpb = (hj.get('meters') or [{'numBeats': 4}])[0].get('numBeats', 4)
    out = []
    for i, s in enumerate(secs):
        nb = secs[i+1]['beat'] if i+1 < len(secs) else end
        out.append({'name': s['name'], 'beat': s['beat'], 'bars': round((nb - s['beat'])/bpb)})
    return {'key_tonic': kt, 'key_scale': ks, 'hj': hj, 'sections': out, 'end': end, 'bpb': bpb}

# section-name -> role
def role(name):
    n = name.lower()
    for key in ['pre-chorus', 'prechorus', 'pre chorus']:
        if key in n: return 'prechorus'
    for r in ['intro', 'verse', 'chorus', 'refrain', 'bridge', 'solo', 'interlude',
              'instrumental', 'outro', 'coda']:
        if r in n: return r
    return 'other'

# ---- fit chords into an exact bar count -------------------------------------

def fit(bars, target):
    """bars = list of per-bar chord-name lists. Return exactly `target` bars by
    looping (pad) or truncating (overflow). Returns (fitted, overflow)."""
    if not bars:
        return [[] for _ in range(target)], []
    if len(bars) == target:
        return bars, []
    if len(bars) > target:
        return bars[:target], bars[target:]
    # shorter: tile the progression to fill, truncating the final repeat
    out = list(itertools.islice(itertools.cycle(bars), target))
    return out, []

# ---- assignment: Hookpad section -> Pollack chords --------------------------

def take_bars(barlist, offset, count):
    """Slice `count` bars from barlist starting at offset, looping if short."""
    if not barlist:
        return [[] for _ in range(count)]
    return [barlist[(offset + k) % len(barlist)] for k in range(count)]

def assign(hp_sections, figures):
    """Assign each Hookpad section a (figure, offset) source and fit its chords to
    the section's exact bar count. Handles the Beatles 'his Verse = your
    verse+chorus' case via spillover. Returns (fill, report, confidence)."""
    figs = [{'id': f.get('figure_id'), 'bars': expand_figure(f)} for f in figures]
    figs = [f for f in figs if f['bars']]

    role_len = {}
    for s in hp_sections:
        role_len.setdefault(role(s['name']), s['bars'])

    # 1) greedy: each distinct role claims the closest-length unused figure
    used, role_src = set(), {}   # role -> {'fig','offset'}
    for r in sorted(role_len, key=lambda r: -role_len[r]):
        tl = role_len[r]
        cands = sorted((abs(len(figs[i]['bars']) - tl), i) for i in range(len(figs)) if i not in used)
        if not cands: continue
        _, bi = cands[0]
        role_src[r] = {'fig': figs[bi], 'offset': 0}
        used.add(bi)

    # 2) spillover: a chorus/refrain lacking its own exact figure, right after a
    #    verse whose figure is exactly verse+chorus bars long, is that figure's tail.
    order_roles = [role(s['name']) for s in hp_sections if s['bars']]
    for a, b in zip(order_roles, order_roles[1:]):
        bl = role_len.get(b)
        if b in ('chorus', 'refrain') and (b not in role_src or len(role_src[b]['fig']['bars']) != bl):
            va = role_src.get(a)
            if a == 'verse' and va and len(va['fig']['bars']) == role_len[a] + bl:
                role_src[b] = {'fig': va['fig'], 'offset': role_len[a]}

    def fallback(r):
        for pref in ['verse', 'chorus', 'refrain']:
            if pref in role_src: return role_src[pref]
        return {'fig': figs[0], 'offset': 0} if figs else None

    fill, report, clean = {}, [], 0
    for i, s in enumerate(hp_sections):
        if s['bars'] == 0:
            continue
        r = role(s['name'])
        src = role_src.get(r)
        is_fallback = src is None
        if is_fallback:
            src = fallback(r)
        bars = take_bars(src['fig']['bars'], src['offset'], s['bars']) if src else \
               [[] for _ in range(s['bars'])]
        avail = len(src['fig']['bars']) - src['offset'] if src else 0
        padded = avail < s['bars']                 # figure shorter than section -> looped
        is_clean = (not is_fallback) and not padded
        if is_clean: clean += 1
        fill[i] = bars
        report.append({'section': s['name'], 'bars': s['bars'],
                       'fig': src['fig']['id'] if src else None,
                       'offset': src['offset'] if src else 0,
                       'status': 'fallback' if is_fallback else ('pad' if padded else 'clean')})
    filled = sum(1 for s in hp_sections if s['bars'] > 0)
    return fill, report, (clean / filled if filled else 0)

# ---- paste emission ---------------------------------------------------------

def make_chord(name, beat, duration, key_root, key_mode):
    h = chord_to_hookpad(name, key_root, key_mode) or {}
    c = {'root': h.get('root', 1), 'beat': beat, 'duration': int(duration),
         'type': 7 if str(h.get('type')) == '7' else 5, 'inversion': h.get('inversion', 0),
         'applied': h.get('applied', 0), 'adds': h.get('adds', []), 'omits': h.get('omits', []),
         'alterations': h.get('alterations', []), 'suspensions': h.get('suspensions', []),
         'substitutions': [], 'pedal': h.get('pedal', None), 'alternate': '',
         'borrowed': h.get('borrowed') or None, 'isRest': False, 'recordingEndBeat': None}
    return {k: c[k] for k in CHORD_ORDER}

def _int_durs(n, total=BPB):
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]

def build_paste(hp, fill, key_root, key_mode):
    chords = []
    for i, s in enumerate(hp['sections']):
        if i not in fill: continue
        beat = s['beat']
        for bar in fill[i]:
            names = [n for n in bar if n]
            if not names:
                beat += BPB; continue
            for nm, d in zip(names, _int_durs(len(names))):
                chords.append(make_chord(nm, beat, d, key_root, key_mode)); beat += d
    hj = hp['hj']
    obj = {'version': 1, 'chords': chords, 'notes': hj.get('notes', []),
           'keys': hj.get('keys', [{'beat': 1, 'scale': key_mode,
                'tonic': [k for k, v in NOTE_PC.items() if v == key_root][0]}]),
           'tempos': hj.get('tempos', [{'beat': 1, 'bpm': 120, 'swingFactor': 0, 'swingBeat': 0.5}]),
           'meters': hj.get('meters', [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}]),
           'breaks': hj.get('breaks', []), 'sections': hj['sections'],
           'endBeat': hp['end'], 'audioTracks': []}
    obj['fp'] = hashlib.sha1(json.dumps(obj, separators=(',', ':')).encode()).hexdigest()
    return obj

def slugify(t): return re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_')

def run_one(cur, title, pol_slug, write=True, verbose=True):
    hp = load_hookpad(cur, title)
    if not hp:
        print(f"  ! no hookpad json for {title}"); return None
    key_root = NOTE_PC.get(hp['key_tonic'], 0)
    key_mode = hp['key_scale'] or 'major'
    figs = parse_song(pol_slug)
    fill, report, conf = assign(hp['sections'], figs)
    obj = build_paste(hp, fill, key_root, key_mode)
    if verbose:
        print(f"\n=== {title}  [{hp['key_tonic']} {key_mode}]  confidence={conf:.0%}  chords={len(obj['chords'])} ===")
        for r in report:
            off = f"@{r['offset']}" if r['offset'] else ''
            tag = {'clean': '·clean', 'pad': '~pad/loop', 'fallback': '~fallback'}[r['status']]
            print(f"   {r['section'][:16]:16s} {r['bars']:>2}bars  fig{r['fig']}{off}  {tag}")
    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, slugify(title) + '.txt')
        json.dump(obj, open(path, 'w'), separators=(',', ':'))
    return conf

if __name__ == '__main__':
    con = _db(); cur = con.cursor()
    if sys.argv[1:2] == ['--all']:
        targets = json.load(open(os.path.expanduser('~/Desktop/music/pollack_fill_targets.json')))
        rows = []
        for t in targets:
            conf = run_one(cur, t['title'], t['pol_key'], write=True, verbose=False)
            if conf is not None: rows.append((conf, t['title'], t['pol_key']))
        rows.sort(reverse=True)
        print(f"\n{'CONF':>5}  {'TITLE':32s} pol")
        for conf, title, pk in rows:
            print(f"{conf:>5.0%}  {title[:32]:32s} {pk}")
        print(f"\n{sum(1 for c,_,_ in rows if c>=0.75)}/{len(rows)} at >=75% confidence")
    else:
        title = sys.argv[1]; slug = sys.argv[2]
        run_one(cur, title, slug)
