"""Lyrics into the Hookpad songs: fill the ones that have none, clean the ones that do.

    lyrics_fill.py --pilot 30            # fill: score 30 songs locally, write nothing
    lyrics_fill.py --show "<file name>"  # one song's lines, notes and tokens
    lyrics_fill.py --clean --pilot 30    # clean: what the markup strip would change

FILL. The downloaded lyrics (audio_work/lyrics, LRCLIB) carry a time per line. A
line starts where a melody phrase starts, so the chart is laid on the record's
clock by the offset and speed (x0.5/1/2, +-6%) that put the most line starts on
phrase starts. Each line then owns the notes from its start to the next line's.
Inside a line the syllables go one per note; spare notes become `_` (Hookpad's
"hold this syllable", `_N_` = N notes), chosen where a held syllable is likeliest
(a changed pitch, a short note, the line's last syllable). Too many syllables:
a word is sung on one note (written whole with Hookpad's one-syllable `-`).
Notes no line owns (riffs, unsung parts) get `_` so the next line still lands.
Lyrics are written per section (lyrics.sectionLyrics), which is how Hookpad maps
them: a section's text starts on that section's first note.

CLEAN. Section tags ([v] [ch] [pc] ...) and rhyme marks ("( a)", "[a]way") come
out; the user doesn't need the markup. Melisma and bleed marks ([m] [n] [p], `_`,
`_N_`, `*`) stay: they place the syllables. A letter in parens at a line end is a rhyme mark, "(A)" included (Furr: seventeen(A) / whisperin(A)).

Copyrighted text stays local except inside the user's own private Hookpad songs.
"""
import argparse, bisect, glob, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus as C
from melisma_align import count_syllables, _syllabify, _vowel_groups

M = os.path.expanduser('~/Desktop/music')
LYR = f'{M}/audio_work/lyrics'
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower().replace('&', 'and'))
tn = lambda t: norm(re.sub(r'^(the|a) ', '', re.sub(r'\(.*?\)|\[.*?\]| - .*$', '', (t or '').lower()).strip()))
an = lambda a: norm(re.sub(r'^the ', '', (a or '').lower().strip()))[:5]
STAMP = re.compile(r'^\[(\d+):(\d\d(?:\.\d+)?)\]\s?(.*)$')
COPY = re.compile(r'-[a-z]*\d+$|-[a-z]+$|-[A-G]\w*$')     # version copies, tempo readings


# ---------- inputs ----------

def lyric_index():
    idx = {}
    for f in glob.glob(f'{LYR}/*.json'):
        try: j = json.load(open(f))
        except Exception: continue
        if str(j.get('found')) != 'True' or str(j.get('instrumental')) == 'True': continue
        if not (j.get('synced') or '').strip(): continue
        idx.setdefault((tn(j.get('title')), an(j.get('artist'))), j)
    return idx


def record_tempos():
    """(title, artist) -> the record's measured bpm (audio_work/tempo.json)"""
    A = f'{M}/audio_work'
    try: T = json.load(open(f'{A}/tempo.json'))
    except Exception: return {}
    out = {}
    for mf in glob.glob(f'{A}/youtube/*manifest.json'):
        for r in json.load(open(mf)):
            p = r.get('file')
            if p in T and T[p].get('bpm') and not r.get('error'):
                out.setdefault((tn(r.get('title')), an(r.get('artist'))), T[p]['bpm'])
    return out


def has_lyrics(d):
    L = d.get('lyrics')
    if not isinstance(L, dict): return False
    if any(isinstance(v, str) and re.search(r'[A-Za-z]', v) for v in L.get('values') or []): return True
    for s in L.get('sectionLyrics') or []:
        ly = s.get('lyrics')
        if isinstance(ly, list) and any(isinstance(x, str) and re.search(r'[A-Za-z]', x) for x in ly): return True
    return False


def synced_lines(j):
    out = []
    for raw in (j.get('synced') or '').splitlines():
        m = STAMP.match(raw.strip())
        if not m: continue
        text = m.group(3).strip()
        if not re.search(r'[A-Za-z]', text): continue
        out.append((int(m.group(1)) * 60 + float(m.group(2)), text))
    return out


def chart_clock(d):
    """beat -> seconds on the chart's own tempo map"""
    T = sorted(d.get('tempos') or [{'beat': 1, 'bpm': 120}], key=lambda t: t['beat'])
    starts, secs = [], []
    s = 0.0
    for i, t in enumerate(T):
        if i: s += (t['beat'] - T[i - 1]['beat']) * 60 / T[i - 1]['bpm']
        starts.append(t['beat']); secs.append(s)
    def f(b):
        i = max(bisect.bisect_right(starts, b) - 1, 0)
        return secs[i] + (b - starts[i]) * 60 / T[i]['bpm']
    return f


def melody(d):
    return sorted((n for n in C.dedupe_notes(d.get('notes') or []) if not n.get('isRest') and n.get('duration')),
                  key=lambda n: n['beat'])


def pitch(n):
    m = re.match(r'^([b#]*)([1-7])$', str(n.get('sd', '')))
    if not m: return None
    return [0, 2, 4, 5, 7, 9, 11][int(m.group(2)) - 1] + m.group(1).count('#') - m.group(1).count('b') + 12 * (n.get('octave') or 0)


# ---------- fit the chart to the record's clock ----------

def fit(notes, lines, clock, speed=None):
    on = np.array([clock(n['beat']) for n in notes])
    ends = [n['beat'] + n['duration'] for n in notes]
    ps = [0] + [i for i in range(1, len(notes)) if notes[i]['beat'] - ends[i - 1] >= .75]
    P = on[ps]
    t = np.array([x for x, _ in lines])
    best = (-1, None, None)
    grid = [b * x for b in (.5, 1, 2) for x in np.arange(.94, 1.0601, .005)]
    if speed: grid = [speed * x for x in np.arange(.98, 1.0201, .0025)]
    for f in grid:
        if True:
            Q = np.sort(P * f)
            # offsets that put some line start on some phrase start, refined below
            cand = np.unique(np.round((t[:, None] - Q[None, :]).ravel() / .05) * .05)
            cand = cand[(cand > -20) & (cand < 20)]      # chart beat 1 is near the record's start
            if not len(cand): continue
            for off in cand[::max(1, len(cand) // 4000)]:
                q = Q + off
                j = np.clip(np.searchsorted(q, t), 1, len(q) - 1)
                dist = np.minimum(np.abs(t - q[j - 1]), np.abs(t - q[j]))
                inside = (t >= q[0] - 2) & (t <= q[-1] + 2)
                sc = np.sum(np.exp(-(dist[inside] / .25) ** 2))
                if sc > best[0]: best = (sc, f, off)
    sc, f, off = best
    if f is None: return None
    tt = on * f + off
    q = np.sort(P * f + off)
    j = np.clip(np.searchsorted(q, t), 1, len(q) - 1)
    dist = np.minimum(np.abs(t - q[j - 1]), np.abs(t - q[j]))
    inside = (t >= tt[0] - 2) & (t <= tt[-1] + 2)
    hit = float(np.mean(dist[inside] <= .3)) if inside.any() else 0.0
    return dict(f=float(f), off=float(off), times=tt, phrase=set(ps), hit=hit, inside=int(inside.sum()))


# ---------- syllables onto notes ----------

try:
    import pyphen; _PY = pyphen.Pyphen(lang='en_US')
except Exception: _PY = None
VG = re.compile(r"[aeiouy]+", re.I)
try:
    import cmudict; _CMU = cmudict.dict()
except Exception: _CMU = {}


def n_syll(core):
    p = _CMU.get(core.lower())
    return min(sum(ch[-1].isdigit() for ch in x) for x in p) if p else count_syllables(core)   # fewest: how it's sung


def split_word(w, k):
    """w (original case) cut into k syllables; [w] if it can't be done cleanly"""
    if k <= 1: return [w]
    cuts = []
    if _PY: cuts = [int(p) for p in _PY.positions(w)]
    parts = [w[a:b] for a, b in zip([0] + cuts, cuts + [len(w)])]
    while len(parts) < k:                       # cut the part with most vowel groups between its groups
        i = max(range(len(parts)), key=lambda i: len(VG.findall(parts[i])))
        g = list(VG.finditer(parts[i]))
        if len(g) < 2: break
        a, b = g[0].end(), g[1].start()
        cut = a + max(0, (b - a) // 2) if b - a > 1 else a
        if cut <= 0 or cut >= len(parts[i]): break
        parts[i:i + 1] = [parts[i][:cut], parts[i][cut:]]
    while len(parts) > k:                       # join the shortest neighbours
        i = min(range(len(parts) - 1), key=lambda i: len(parts[i]) + len(parts[i + 1]))
        parts[i:i + 2] = [parts[i] + parts[i + 1]]
    return parts if len(parts) == k else [w]


def word_sylls(w):
    core = re.sub(r"[^A-Za-z']", '', w)
    if not core: return []
    parts = split_word(core, n_syll(core))
    if len(parts) == 1 and _vowel_groups(core) > 1: parts = [core + '-']   # pin: Hookpad would split it
    return parts


def n_sylls(text):
    return sum(len(word_sylls(w)) for w in re.split(r'[\s\-\u2013\u2014]+', text) if re.search(r'[A-Za-z]', w))


def mismatch(S, N):
    return 3 * (S - N) if S > N else .5 * (N - S)    # too many syllables is worse than a held note


def line_tokens(text, nn, ln):
    """tokens for one line over nn notes (ln = those notes). None if it can't fit."""
    words = [w for w in re.split(r'[\s\-\u2013\u2014]+', text) if re.search(r'[A-Za-z]', w)]
    W = [word_sylls(w) or [w] for w in words]
    S = sum(len(p) for p in W)
    if S > nn:                                  # sing whole words on one note, longest first
        order = sorted(range(len(W)), key=lambda i: -len(W[i]))
        for i in order:
            if S <= nn: break
            if len(W[i]) > 1:
                S -= len(W[i]) - 1
                W[i] = [re.sub(r"[^A-Za-z']", '', words[i]).rstrip('-') + '-']
        if S > nn: return None
    syl = [x for p in W for x in p]
    extra = nn - len(syl)
    if extra == 0: return syl
    # DP: syllable k takes notes [a, b); cost of each held (extra) note
    def hold_cost(i, k):
        c = 1.0
        p0, p1 = pitch(ln[i - 1]), pitch(ln[i])
        if p0 is not None and p0 == p1: c += 1.0        # a repeated pitch is usually a new syllable
        if ln[i]['duration'] <= .5: c -= .4
        if k == len(syl) - 1: c -= .5
        return c
    INF = 1e9; K = len(syl)
    D = [[INF] * (nn + 1) for _ in range(K + 1)]; B = [[0] * (nn + 1) for _ in range(K + 1)]
    D[0][0] = 0
    for k in range(K):
        for a in range(nn):
            if D[k][a] >= INF: continue
            c = D[k][a]
            for b in range(a + 1, nn + 1 - (K - k - 1)):
                if b > a + 1: c += hold_cost(b - 1, k)
                if c < D[k + 1][b]: D[k + 1][b] = c; B[k + 1][b] = a
    if D[K][nn] >= INF: return None
    spans, b = [], nn
    for k in range(K, 0, -1):
        a = B[k][b]; spans.append((a, b)); b = a
    out = []
    for k, (a, b) in enumerate(reversed(spans)):
        out.append(syl[k]); out += ['_'] * (b - a - 1)
    return out


def compress(toks):
    out = []
    for t in toks:
        if t == '_' and out and re.fullmatch(r'_(\d*)_?', out[-1]):
            n = 1 if out[-1] == '_' else int(out[-1].strip('_'))
            out[-1] = f'_{n + 1}_'
        else: out.append(t)
    return out


def fill(d, j, rec_bpm=None):
    notes = melody(d)
    lines = synced_lines(j)
    if len(notes) < 20 or len(lines) < 4: return None, 'too little'
    speed = None
    if rec_bpm:                                 # chart seconds -> record seconds; the chart may count half/double time
        bpm = (d.get('tempos') or [{'bpm': 120}])[0]['bpm']
        speed = min((bpm / rec_bpm * k for k in (.5, 1, 2)), key=lambda x: abs(np.log(x)))
        if abs(np.log(speed)) > .1: speed = None
    F = fit(notes, lines, chart_clock(d), speed)
    if not F: return None, 'no fit'
    tt = F['times']
    starts = []                                 # (note index, line text)
    for t, text in lines:
        k = int(np.argmin(np.abs(tt - t)))
        near = [i for i in range(max(0, k - 6), min(len(notes), k + 7)) if i in F['phrase'] and abs(tt[i] - t) <= .4]
        if near: k = min(near, key=lambda i: abs(tt[i] - t))
        elif abs(tt[k] - t) > .25: continue
        if starts and k <= starts[-1][0]: continue
        starts.append((k, text, t))
    # each line's notes: from its start to the next line's, cut at a 2-beat gap
    spans = []
    for li, (k, text, t) in enumerate(starts):
        nxt = starts[li + 1][0] if li + 1 < len(starts) else len(notes)
        stop = k + 1
        while stop < nxt and (li + 1 >= len(starts) or tt[stop] < starts[li + 1][2] - .25):
            if notes[stop]['beat'] - (notes[stop - 1]['beat'] + notes[stop - 1]['duration']) >= 2: break
            stop += 1
        spans.append([k, stop])
    S = [n_sylls(text) for _, text, _ in starts]
    for _ in range(2):                          # nudge each touching boundary up to 2 notes
        for li in range(len(spans) - 1):
            a, b = spans[li], spans[li + 1]
            if a[1] != b[0]: continue
            best = min(range(-2, 3), key=lambda m: (mismatch(S[li], a[1] + m - a[0]) + mismatch(S[li + 1], b[1] - b[0] - m)
                                                    if a[0] < a[1] + m < b[1] else 1e9, abs(m)))
            a[1] += best; b[0] += best
    tok = ['_'] * len(notes)
    placed = fitted = 0
    for (k, stop), (_, text, _) in zip(spans, starts):
        T = line_tokens(text, stop - k, notes[k:stop])
        placed += 1
        if T is None: continue
        fitted += 1
        tok[k:stop] = T
    starts = [(k, text, t) for (k, _), (_, text, t) in zip(spans, starts)]
    return dict(notes=notes, tok=tok, fit=F, lines=len(lines), placed=placed, fitted=fitted, starts=starts), None


def section_texts(d, notes, tok, starts):
    secs = sorted(d.get('sections') or [{'beat': 1, 'name': 'Section'}], key=lambda s: s['beat'])
    bounds = [s['beat'] for s in secs] + [1e12]
    brk = {k for k, *_ in starts}
    out = []
    for i in range(len(secs)):
        idx = [x for x in range(len(notes)) if bounds[i] <= notes[x]['beat'] < bounds[i + 1]]
        words, line = [], []
        for x in idx:
            if x in brk and line: words.append(' '.join(compress(line))); line = []
            line.append(tok[x])
        if line: words.append(' '.join(compress(line)))
        text = '\n'.join(words)
        out.append('' if not re.search(r'[A-Za-z]', text) else text)
    return secs, out


def apply(d, secs, texts):
    L = d.setdefault('lyrics', {})
    nv = max(4, len(L.get('values') or []))
    L['values'] = ['\n\n'.join(t for t in texts if t)] + [''] * (nv - 1)
    L['sectionLyrics'] = [{'sectionName': s['name'], 'lyrics': [t, '', '', '']} for s, t in zip(secs, texts)]
    return d


# ---------- clean ----------

TAGS = re.compile(r'\[(?:v|V|vn|VN|v\d|V\d|ch|Ch|CH|c|C|pc|PC|Pc|b|B|br|i|I|o|O|r|R|s|S|in|out)\]')
RHYME_MID = re.compile(r'\[([a-hA-H])\](?=\S)')
RHYME_END = re.compile(r'\s*\(\s*([a-hA-H])\s*\)(?=\s*$)', re.M)


def clean_text(s):
    s = RHYME_END.sub('', s)
    s = RHYME_MID.sub('', s)
    s = TAGS.sub('', s)
    return re.sub(r'[ \t]+\n', '\n', re.sub(r'(?m)^[ \t]+', '', s))


def clean(d):
    L = d.get('lyrics')
    if not isinstance(L, dict): return d, 0
    n = 0
    vals = L.get('values') or []
    for i, v in enumerate(vals):
        if isinstance(v, str):
            c = clean_text(v); n += c != v; vals[i] = c
    for s in L.get('sectionLyrics') or []:
        ly = s.get('lyrics')
        if isinstance(ly, list):
            for i, v in enumerate(ly):
                if isinstance(v, str):
                    c = clean_text(v); n += c != v; ly[i] = c
    return d, n


# ---------- driver ----------

def targets(idx):
    global RT
    RT = record_tempos()
    for name, d, nb in C.songs(need_chords=False):
        if '_' not in name: continue
        a, t = name.split('_', 1)
        if COPY.search(t): continue
        if has_lyrics(d): continue
        j = idx.get((tn(t), an(a)))
        if j: yield name, d, j, RT.get((tn(t), an(a)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', type=int, default=0)
    ap.add_argument('--show')
    ap.add_argument('--clean', action='store_true')
    a = ap.parse_args()
    if a.clean:
        k = 0
        for name, d, nb in C.songs(need_chords=False):
            if not has_lyrics(d): continue
            before = json.dumps(d.get('lyrics'))
            d, n = clean(d)
            if n:
                k += 1
                if k <= (a.pilot or 10):
                    b = json.loads(before)
                    v0 = (b.get('values') or [''])[0][:160].replace('\n', ' / ')
                    v1 = (d['lyrics'].get('values') or [''])[0][:160].replace('\n', ' / ')
                    print(f'{name}\n   was: {v0}\n   now: {v1}')
        print(f'\n{k} songs would change')
        sys.exit()
    idx = lyric_index()
    T = list(targets(idx))
    print(f'{len(T)} songs with no lyrics, a melody, and timed lyrics downloaded')
    if a.show:
        T = [x for x in T if x[0] == a.show]
    import random; random.seed(3)
    pick = T if a.show else random.sample(T, min(a.pilot or 30, len(T)))
    for name, d, j, rb in pick:
        r, err = fill(d, j, rb)
        if err: print(f'  --  {name}: {err}'); continue
        F = r['fit']
        print(f"{'T' if rb else ' '} in-chart {F['inside']:3} {F['hit']:4.0%} on phrase starts  x{F['f']:.3f} {F['off']:+6.1f}s  lines {r['lines']:3} placed {r['placed']:3} fit {r['fitted']:3}  {name}")
        if a.show:
            secs, texts = section_texts(d, r['notes'], r['tok'], r['starts'])
            for s, t in zip(secs, texts):
                print(f"\n[{s['name']}]\n{t}")


def upload_copy(name, suffix='lyrics1114'):
    """the filled song as a private copy <name>-<suffix>; the original is untouched"""
    from tempo_variant_pastes import full_json
    from hookpad_upload_variants import upload
    d = json.load(open(f'{M}/hookpad_songs_full/{name}.json'))
    a, t = name.split('_', 1)
    j = lyric_index_one(t, a)
    r, err = fill(d, j, record_tempos().get((tn(t), an(a))))
    if err: return None, err
    secs, texts = section_texts(d, r['notes'], r['tok'], r['starts'])
    o = apply(full_json(d, 1), secs, texts)
    tok = open(os.path.expanduser('~/.hookpad_token')).read().strip()
    return upload(tok, f'{name}-{suffix}', o)


def lyric_index_one(t, a):
    return lyric_index().get((tn(t), an(a)))
