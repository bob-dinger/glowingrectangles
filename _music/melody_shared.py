"""Melodic figures shared BETWEEN songs, compared scale-free.

Line breaks are where the user pressed return, not where the music does anything —
matching sections on line lengths finds coincidences. This matches on the notes.

Two features, both free of key, tempo and metric level, so a figure played in
eighths at 80bpm matches the same figure in quarters at 160:

    intervals   the differences between consecutive scale degrees
    rhythm      each note's length as a multiple of the WINDOW's shortest note,
                normalised per window so context cannot shift it

A figure counts as shared only if it turns up in two different SONGS.

    themap_venv/python melody_shared.py            # the exactly-aligned sections
    themap_venv/python melody_shared.py --all      # every section in the corpus
"""
import os, re, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from lyric_melody import aligned

DEG = {'1':0,'2':1,'3':2,'4':3,'5':4,'6':5,'7':6}
KMIN, KMAX = 4, 7
LET = 'CDEFGAB'
# Data quality, the user's rule: "usually I've got the first verse of a song done
# well, same with chorus, etc. and the same sections after aren't." So keep only the
# FIRST instance of each role in a song. And per melody_map.py: "I'm not as
# interested in outros and intros and solos. we do need pre-chorus's however."
ROLES = ('pre-chorus', 'prechorus', 'chorus', 'verse', 'bridge', 'refrain')
SKIP  = ('intro', 'outro', 'solo', 'instrumental', 'interlude', 'tag', 'coda')

def role_of(sec):
    s = re.sub(r'[^a-z ]', ' ', (sec or '').lower())
    if any(k in s for k in SKIP): return None
    for r in ROLES:
        if r.replace('-', '') in s.replace('-', '').replace(' ', ''): return r
    return None

def idx(n):
    m = re.match(r'^[b#]*([1-7])$', str(n.get('sd','')))
    return None if not m else n.get('octave',0)*7 + DEG[m.group(1)]

def windows(notes):
    """Yield (k, intervals, rhythm) for every window, normalised per window."""
    p = [idx(n) for n in notes]
    if any(x is None for x in p): 
        keep = [i for i,x in enumerate(p) if x is not None]
        notes = [notes[i] for i in keep]; p = [p[i] for i in keep]
    for k in range(KMIN, KMAX+1):
        for i in range(len(p)-k+1):
            win = notes[i:i+k]; pp = p[i:i+k]
            m = min(n['duration'] for n in win)
            if not m: continue
            rhythm = tuple(round(n['duration']/m) for n in win)
            iv = tuple(b-a for a,b in zip(pp, pp[1:]))
            yield k, iv, rhythm, i, win

def sections(use_all):
    for name, d, nb in corpus.songs(need_chords=False):
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        used = set()
        if use_all:
            for sec, b0, b1 in corpus.sections(d):
                role = role_of(sec)
                if role is None or role in used: continue      # first instance only
                # phrase-sliced, not marker-sliced: 47% of sections have a pickup
                # before their marker (corpus.section_phrase)
                inn, st, sp = corpus.section_phrase(notes, b0, b1)
                if len(inn) >= KMIN:
                    used.add(role); yield name, sec, inn
        else:
            for r, b0, pairs in aligned(d, nb):
                role = role_of(r['name'])
                if role is None or role in used: continue
                used.add(role); yield name, r['name'], [n for _, n in pairs]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--min-songs', type=int, default=2)
    a = ap.parse_args()

    found = collections.defaultdict(list)
    nsec = 0
    for name, sec, notes in sections(a.all):
        nsec += 1
        seen = set()
        for k, iv, rhythm, i, win in windows(notes):
            if len(set(iv)) == 1 and iv[0] == 0: continue      # one repeated note
            key = (k, iv, rhythm)
            if key in seen: continue
            seen.add(key)
            found[key].append((name, sec, i, win))
    shared = {k:v for k,v in found.items() if len({x[0] for x in v}) >= a.min_songs}
    print(f"  {nsec} sections scanned ({'whole corpus' if a.all else 'exactly aligned only'})")
    print(f"  {len(found):,} distinct figures, {len(shared):,} of them in 2+ different songs\n")

    rank = sorted(shared.items(), key=lambda kv: (-len({x[0] for x in kv[1]}), -kv[0][0]))
    for (k, iv, rhythm), hits in rank[:12]:
        songs = {x[0] for x in hits}
        print(f"  {k} notes  intervals {list(iv)}  rhythm {list(rhythm)}   "
              f"in {len(songs)} songs")
        for name, sec, i, win in hits[:3]:
            tune = ' '.join(f"{LET[DEG[re.match(r'^[b#]*([1-7])$',str(n['sd'])).group(1)]]}"
                            f"{4+n.get('octave',0)}" for n in win)
            print(f"      {name[:32]:32} {sec[:12]:12} {tune}")

if __name__ == '__main__':
    main()


def place_at(inn, at, b0, bar=4.0):
    """Shift that puts a section's first BAR on the marker at `at`.

    The marker, the section's bar 1 and its first chord all coincide: `shift = at - b0`
    and nothing else. Bar lines and chords land exactly where the song has them, and an
    8-bar section occupies 8 bars. A pickup falls BEFORE the marker, into the air
    reserved behind it — which is where the user chose to have it (2026-10-03), after
    being shown the four possible layouts:

      label on bar 1, pickup before it   <- CHOSEN.  marker == bar 1 == chord I
      lead-in bar for the pickup            label sits a bar early, 8 bars become 9
      label on the pickup, mid-bar          label not on a bar line
      drop the pickup                       loses the real opening of 32% of sections

    With a pickup you cannot have all of: nothing before the marker, marker on a bar
    line, the song's bar lines preserved, and the label on the section's first bar.
    This gives up the first one, so callers must leave air behind each marker.

    Do NOT reintroduce anything melody-derived here. Using `corpus.metric_offset` for
    layout straightened the melody and dragged the CHORDS off the grid: 65% of chords
    sit on a bar downbeat in the source corpus, but only 21-29% did in pastes laid out
    that way. Returns (shift, lead_bars); lead_bars is always 0, kept so callers that
    size their slot as (lead+nbars+gap) keep working.
    """
    return at - b0, 0


def num(x): return int(x) if float(x).is_integer() else float(x)


# Each mode's WHITE-NOTE tonic. Carrying the real mode is the whole point -- a paste
# that forces everything to C major makes a minor section sound wrong (the user, on
# Wallflowers Sleepwalker: "sounds very different in minor vs. major"). The TONIC is
# normalised so every section lands on white notes and stays comparable, per the
# major->C / minor->Am convention; --keep-tonic preserves the song's own instead.
# The corpus uses seven scales: major 2070, minor 300, mixolydian 139, dorian 49,
# lydian 14, harmonicMinor 5, phrygian 5.
WHITE = {'major': 'C', 'minor': 'A', 'dorian': 'D', 'phrygian': 'E', 'lydian': 'F',
         'mixolydian': 'G', 'locrian': 'B', 'harmonicMinor': 'A',
         'phrygianDominant': 'E'}

def key_entries(d, b0, end, shift, keep_tonic=False):
    """Key entries for one section, clipped to it and moved onto the paste timeline.
    20% of songs change key mid-song, so a section can carry more than one."""
    ks = sorted([k for k in (d.get('keys') or []) if isinstance(k, dict)],
                key=lambda k: k.get('beat', 1)) or [{'beat': 1, 'scale': 'major'}]
    out, cur = [], ks[0]
    for k in ks:
        if k.get('beat', 1) <= b0: cur = k
    def entry(k, beat):
        sc = k.get('scale') or 'major'
        return {'beat': num(beat + shift), 'scale': sc,
                'tonic': (k.get('tonic') or 'C') if keep_tonic else WHITE.get(sc, 'C')}
    out.append(entry(cur, b0))
    for k in ks:
        if b0 < k.get('beat', 1) < end: out.append(entry(k, k['beat']))
    return out

def tempo_entries(d, b0, end, shift, force=None):
    """Tempo in force at the section start, plus any change inside it. Swing is
    carried too -- it changes the feel as much as the bpm does."""
    ts = sorted([t for t in (d.get('tempos') or []) if isinstance(t, dict)],
                key=lambda t: t.get('beat', 1)) or [{'beat': 1, 'bpm': 120}]
    cur = ts[0]
    for t in ts:
        if t.get('beat', 1) <= b0: cur = t
    def entry(t, beat):
        return {'beat': num(beat + shift), 'bpm': num(force or t.get('bpm') or 120),
                'swingFactor': t.get('swingFactor', 0), 'swingBeat': t.get('swingBeat', 0.5)}
    out = [entry(cur, b0)]
    for t in ts:
        if b0 < t.get('beat', 1) < end: out.append(entry(t, t['beat']))
    return out

def num(x): return int(x) if float(x).is_integer() else float(x)

# Variant suffixes: `<base>-<tag>` stores an alternate next to a song, so one song
# must not be counted as several.
VARIANT = ('-hooktab', '-right', '-simple', '_dynamics', '-90', '-double')


NOTE = r'(?:[A-G](?:b|#)?m?)'
VARIANT_RE = __import__('re').compile(
    r'[-_](?:' + '|'.join(v.lstrip('-_') for v in VARIANT) + r'|hooktab|wrong|mixolydian|'
    r'dorian|lydian|dynamics|half|\d{2,3}|' + NOTE + r')$')

def base_of(name):
    """Collapse variant suffixes so one song is not counted as several.

    `<base>-<tag>` stores an alternate next to a song (hookpad_variant_naming): -simple,
    -hooktab, -right/-wrong, -double, -mixolydian, a KEY like -C or -Eb, or a TEMPO like
    -150. Stripped repeatedly, because `x-hooktab-C` happens.
    """
    prev = None
    while name != prev:
        prev = name
        for v in VARIANT:
            if name.endswith(v): name = name[: -len(v)]
        name = VARIANT_RE.sub('', name)
    return name


def richest_first(songs):
    """Order (name, data, numBeats) tuples so the BEST file of each variant group
    comes first, then everything else.

    Preferring the *base* file was wrong: `-right` means the variant IS the corrected
    reading, and `-hooktab` imports often fill in a sketch the base never had. Measured
    2026-10-04: of 137 base groups with more than one file, 11 have a variant carrying
    substantially more content than the base -- Beat It (34 notes/36 chords -> 171/43
    as `-right`), Your Woman (80/0 -> 216/113 as `-hooktab`), Sultans of Swing (0/4 ->
    113/33), All I Wanna Do (0/0 -> 112/15). Deduping to the base silently analysed the
    empty one.

    Richness = melody notes + chords entered. Ties break toward the base name.
    """
    def weight(t):
        d = t[1]
        n = len([x for x in (d.get('notes') or []) if not x.get('isRest')])
        c = len([x for x in (d.get('chords') or []) if x.get('root')])
        return n + c
    return sorted(songs, key=lambda t: (base_of(t[0]), -weight(t),
                                        t[0] != base_of(t[0]), t[0]))
