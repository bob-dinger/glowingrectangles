"""Spreadsheet of every chord progression David Bennett has a video about.

Source: ~/Desktop/bennett_transcripts (410 auto-caption transcripts; see
channel_transcripts.py in [[music_audio_pipeline]]).

Two things make this harder than it looks and both are handled here:

1. **The name is in the TITLE, the figure is in the TRANSCRIPT.** He names a
   progression by a song ("Songs that use the Angels chord progression"), and states
   the numbers in the body. So the title gives `name`, the transcript gives `figure`.

2. **The figure is written every possible way.** Run-together ("1564"), separated
   ("1-5-6-4"), or spelled out and comma-joined -- Wonderwall is "the chords 1, 3, 7,
   and four". A plain digit regex finds only the first form and mis-reads the rest:
   it returned 3412 for Purple Rain, which the transcript plainly calls 1654.
   Counting across the whole corpus is worse still, because the captions render
   spoken digits and ID fragments as figures (`1234` appears 150 times, `2341` 37).
   So: match digits AND number-words, and weight each hit by its distance to the word
   "chord"/"progression" -- the captions mangle "chord" into core/cord/score, so all
   spellings are matched.

Every row carries `figure_confidence` and `runner_up` so a weak reading is visible
rather than silently trusted. About a third of the named videos state no numbers at
all (he gives chord letters instead) and are left blank on purpose.

Also cross-references GOOSEFISH (C F G Am = I IV V vi, chord_words.json): its 24
orderings are the permutations of 1/4/5/6, and only a few of them have names.

    themap_venv/python bennett_progressions.py
"""
import os, re, glob, itertools, collections

SRC = os.path.expanduser('~/Desktop/bennett_transcripts')
OUT = os.path.expanduser('~/Desktop/bennett_progressions.xlsx')

WORD = {'one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7'}
TOK  = r'(?:(?:flat|sharp)\s+)?(?:[1-7]|one|two|three|four|five|six|seven)'
FULL = re.compile(r'\b' + TOK + r'(?:\s*(?:,\s*|\s*,?\s*and\s+|\s*[-–]\s*|\s+)' + TOK + r'){2,4}\b', re.I)
RUN  = re.compile(r'(?<![0-9])([1-7]{3,4})(?![0-9])')
PROG = re.compile(r'\b(?:core|cord|chord|chords|score)\b|\bprogression\b', re.I)
# only these title shapes actually NAME a progression
NAMED = re.compile(r'^(?:songs that use\s+|when did\s+)(?:the\s+)?[“"”]?(.+?)[”"“]?'
                   r'\s+(?:chord\s+)?progression', re.I)
OTHER = re.compile(r"^(.+?)'?s? (?:unique|favourite|favorite) chord progression", re.I)

def videos():
    for p in sorted(glob.glob(os.path.join(SRC, '*.txt'))):
        base = os.path.basename(p)[:-4]
        m = re.match(r'^(.*) \[([A-Za-z0-9_-]{6,})\]$', base)
        yield p, (m.group(1) if m else base), (m.group(2) if m else '')

def norm(s):
    out = []
    for t in re.findall(TOK, s, re.I):
        t = t.lower().strip(); acc = ''
        if t.startswith('flat'):  acc, t = 'b', t[4:].strip()
        elif t.startswith('sharp'): acc, t = '#', t[5:].strip()
        out.append(acc + WORD.get(t, t))
    return '-'.join(out)

def figures(t):
    """Counter of chord figures, weighted by nearness to the word chord/progression."""
    spans = [m.start() for m in PROG.finditer(t)]
    c = collections.Counter()
    def add(f, at):
        n = len(f.split('-'))
        if not 3 <= n <= 4: return
        d = min((abs(at - s) for s in spans), default=10**9)
        if d <= 60: c[f] += 3
        elif d <= 200: c[f] += 1
    for m in FULL.finditer(t): add(norm(m.group(0)), m.start())
    for m in RUN.finditer(t):  add('-'.join(m.group(1)), m.start())
    return c

# Names he uses in the BODY rather than a title. Each is counted only when a 4-chord
# figure appears within 400 characters of it, so the pairing is evidenced, not assumed.
NAME_PHRASES = ['50s progression', 'fifties progression', 'plagal cascade', 'pop punk',
                'pop-punk', 'sensitive female', 'axis progression', 'doo-wop', 'doo wop',
                'four chord song', 'ice cream', 'montage', 'royal road', 'andalusian']

def body_names(paths):
    """{figure: Counter(name)} from name phrases stated in the transcripts."""
    out = collections.defaultdict(collections.Counter)
    for p in paths:
        t = open(p, errors='ignore').read(); low = t.lower()
        for nm in NAME_PHRASES:
            for m in re.finditer(re.escape(nm), low):
                win = t[max(0, m.start()-400): m.start()+400]
                for mm in FULL.finditer(win):
                    f = norm(mm.group(0))
                    if len(f.split('-')) == 4: out[f][nm] += 1
                for mm in RUN.finditer(win):
                    if len(mm.group(1)) == 4: out['-'.join(mm.group(1))][nm] += 1
    return out

def main():
    import openpyxl
    from openpyxl.utils import get_column_letter
    goose = ['-'.join(p) for p in itertools.permutations('1456')]
    rows = []
    for p, title, vid in videos():
        t = open(p, errors='ignore').read()
        low = title.lower()
        name = ''
        m = NAMED.match(title) or OTHER.match(title)
        if m:
            cand = m.group(1).strip().strip('"“”')
            if 2 <= len(cand) <= 40: name = cand
        fig = figures(t)
        four = sorted(((n, f) for f, n in fig.items() if len(f.split('-')) == 4), reverse=True)
        best = four[0][1] if four else ''
        runner = four[1][1] if len(four) > 1 else ''
        conf = ''
        if best:
            top, second = four[0][0], (four[1][0] if len(four) > 1 else 0)
            conf = ('clear' if top >= 6 and top >= 2*max(1, second)
                    else 'ambiguous' if second >= 0.8*top else 'weak')
        minor = len(re.findall(r'minor key|in\s+[A-G](?:\s*(?:sharp|flat))?\s+minor', t, re.I))
        rows.append({
            'title': title, 'url': f'https://youtu.be/{vid}' if vid else '',
            'named_progression': name,
            'figure': best, 'figure_confidence': conf, 'runner_up': runner,
            'mode_hint': 'minor' if minor >= 3 else '',
            'goosefish_order': 'yes' if best in goose else '',
            'about_chords': 'yes' if re.search(
                r'progression|chord|changes|cadence|turnaround|loop', low) else '',
            'other_figures': ', '.join(f'{f}({n})' for n, f in four[1:5]),
            'words': len(t.split()), 'video_id': vid})

    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'videos'
    cols = ['title','url','named_progression','figure','figure_confidence','runner_up',
            'mode_hint','goosefish_order','about_chords','other_figures','words','video_id']
    ws.append(cols)
    for r in sorted(rows, key=lambda r: (not r['named_progression'],
                                         not r['figure'], r['title'])):
        ws.append([r[c] for c in cols])
    ws.freeze_panes = 'A2'
    for i, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = \
            {'title': 60, 'url': 30, 'named_progression': 24, 'other_figures': 30}.get(c, 16)

    RN = {'1':'I','4':'IV','5':'V','6':'vi'}; CH = {'1':'C','4':'F','5':'G','6':'Am'}
    bn = body_names([p for p, _, _ in videos()])
    RANK = {'clear': 0, 'ambiguous': 1, 'weak': 2, '': 3}
    g = wb.create_sheet('goosefish_24')
    g.append(['figure','roman','chords in C','name_from_title','name_in_transcript',
              'best_confidence','videos','url'])
    for o in goose:
        # CLEAR readings first -- 1-5-6-4 is both the Axis video and the Where Is My
        # Mind video, and taking whichever sorted first mislabelled the Axis row
        hit = sorted((r for r in rows if r['figure'] == o),
                     key=lambda r: (RANK[r['figure_confidence']], not r['named_progression']))
        titles = [r['named_progression'] for r in hit if r['named_progression']]
        spoken = '; '.join(f'{k} ({v})' for k, v in bn.get(o, collections.Counter()).most_common(3))
        g.append([o, '-'.join(RN[c] for c in o.split('-')),
                  ' '.join(CH[c] for c in o.split('-')),
                  '; '.join(dict.fromkeys(titles)), spoken,
                  hit[0]['figure_confidence'] if hit else '',
                  '; '.join(r['title'][:46] for r in hit[:3]),
                  hit[0]['url'] if hit else ''])
    g.freeze_panes = 'A2'
    for i, w in enumerate([10, 16, 14, 24, 30, 14, 58, 30], 1):
        g.column_dimensions[get_column_letter(i)].width = w
    wb.save(OUT)

    named = [r for r in rows if r['named_progression']]
    gf = [r for r in rows if r['goosefish_order']]
    print(f"\n  {len(rows)} transcripts | {sum(1 for r in rows if r['about_chords'])} about chords"
          f" | {len(named)} name a progression | {len(gf)} land on a GOOSEFISH ordering\n")
    print(f"  {'name':26} {'figure':>9} {'conf':>10}  {'runner-up':>9}  mode")
    for r in sorted(named, key=lambda r: r['named_progression'].lower()):
        print(f"  {r['named_progression'][:26]:26} {r['figure']:>9} {r['figure_confidence']:>10}  "
              f"{r['runner_up']:>9}  {r['mode_hint']}")
    print(f"\n  GOOSEFISH orderings with a name:\n")
    for o in goose:
        nm = '; '.join(dict.fromkeys(r['named_progression'] for r in rows
                                     if r['figure'] == o and r['named_progression']))
        sp = ', '.join(k for k, _ in bn.get(o, collections.Counter()).most_common(3))
        if nm or sp:
            print(f"    {o}  {' '.join(CH[c] for c in o.split('-')):10}"
                  f" {'-'.join(RN[c] for c in o.split('-')):12} {nm[:34]:34} {sp}")
    print(f"\n  -> {OUT}")

if __name__ == '__main__':
    main()
