#!/usr/bin/env python3
"""One source of truth for reading the Hookpad corpus.

Three rules that every analysis in this folder needs to apply the same way, and
that each got re-derived (and got wrong at least once) in a separate script:

  1. MERGE RE-STRIKES. One chord held for a bar and the same chord struck twice
     across two half-bars are the SAME THING. Layer 1 is chord-change
     durations; re-strikes are texture. 680 songs here contain at least one
     re-struck chord, so a script that quantises raw chord entries instead of
     merged runs is wrong about most of the library.
  2. EXCLUDE the user's own songs (mine*) and the generated workbenches
     (perms_*, music_*, date names). perms_abababcc is a permutation dump that
     otherwise buries every real match for that shape.
  3. MATCH NAMES CASE-INSENSITIVELY. A Hookpad rename that only changes
     capitalisation leaves the old filename on this case-insensitive disk;
     exact matching both drops the song and counts its file as an orphan.

Also: read the meter per song. 29 songs here are in 3 and 12 in 6, and
hardcoding four beats to the bar silently skips all of them.
"""
import json, glob, os, re

CORPUS = os.path.expanduser('~/Desktop/music/hookpad_songs_full')
LIST = os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')
SCRATCH = re.compile(r'^(music_|perms_|mine|\d+-\d+-\d+)', re.I)


def is_scratch(name):
    return bool(SCRATCH.match(name))


def live_names():
    """Lowercased song names currently in the Hookpad account, or None if the
    cached list is missing (refresh: download_one.py --refresh-list)."""
    if not os.path.exists(LIST):
        return None
    return {s['song'].replace('/', '_').lower() for s in json.load(open(LIST))}


def identity(c):
    """What makes two chord entries the same chord.

    Includes adds and suspensions: Dm(add9)->Dm IS a change, which is the whole
    point of the push in Simple Kind of Life. Deliberately EXCLUDES inversion --
    D/F# collapses to D, per music_ignore_slash_chords."""
    return (c.get('root'), c.get('type'), tuple(c.get('adds') or []),
            tuple(c.get('suspensions') or []), c.get('borrowed'),
            c.get('applied'))


def is_unreadable(c):
    """Chords the translator cannot honestly name, to be dropped from analysis
    rather than counted under a guess. The user, shown all seven ambiguous
    cases: "these should be thrown out from analysis."

        no root at all        286   stored as bare {"type": 5}
        borrowed is a LIST    100   a custom scale, not a named mode
        substitutions           9   e.g. ["tri"], a tritone sub -- different root
        pedal                   1

    NOT excluded, because these are readable and legitimate:
        omits [3]             962   a power chord, correctly labelled I5
        applied + borrowed     65
        applied = 7            52   secondary leading-tone dim -- Dream On's
                                    real diminished chords live here
    """
    return (not c.get('root')
            or isinstance(c.get('borrowed'), list)
            or bool(c.get('substitutions'))
            or bool(c.get('pedal')))


def merged(chords):
    """[{...}] -> [(chord, beat, duration)] with adjacent same-chord runs
    collapsed into one. Rule 1 above."""
    out = []
    for c in sorted(chords, key=lambda x: x['beat']):
        if is_unreadable(c):
            continue
        i = identity(c)
        if out and out[-1][0] == i and abs(out[-1][2] + out[-1][3] - c['beat']) < 1e-6:
            out[-1][3] += c['duration']
        else:
            out.append([i, c, c['beat'], c['duration']])
    return [(c, b, d) for _, c, b, d in out]


# --- naming a chord -------------------------------------------------------
# The white-note wheel. Every mode is a ROTATION of it, so degree 1 starts at a
# different spoke: ionian on C, dorian on Dm, ... aeolian on Am. Assuming major
# for everything names 21% of the library wrongly -- 231 songs across six other
# modes. The bug that surfaced this: bare root=7 in A-minor Polly is G (bVII),
# not Bdim, and in a minor key the DIMINISHED chord is degree 2, not degree 7.
WHITE = ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim']
MODE_OFFSET = {'major': 0, 'ionian': 0, 'dorian': 1, 'phrygian': 2, 'lydian': 3,
               'mixolydian': 4, 'minor': 5, 'aeolian': 5, 'locrian': 6,
               'harmonicMinor': 5, 'phrygianDominant': 2}


def mode_of(d):
    """The song's opening mode. Use mode_at() for anything chord-level -- 326
    songs (30%) change key or mode mid-song and keys[0] is only the first."""
    k = (d.get('keys') or [{}])[0]
    return ((k.get('scale') if isinstance(k, dict) else None) or 'major')


def key_spans(d):
    """[(start_beat, end_beat, mode)] -- Hookpad stores keys as a list with
    beats, and a mode change mid-song is invisible if you read only keys[0].
    China Grove is C major to beat 65 and E mixolydian after it."""
    ks = sorted([k for k in (d.get('keys') or []) if isinstance(k, dict)],
                key=lambda k: k.get('beat', 1)) or [{'beat': 1, 'scale': 'major'}]
    out = []
    for i, k in enumerate(ks):
        end = ks[i + 1].get('beat', 1) if i + 1 < len(ks) else float('inf')
        out.append((k.get('beat', 1), end, k.get('scale') or 'major'))
    return out


def mode_at(d, beat):
    """The mode in force at a given beat."""
    m = 'major'
    for st, en, mode in key_spans(d):
        if st <= beat:
            m = mode
    return m


def roman(c, mode='major'):
    """Roman-numeral label, delegated to chord_label.py.

    Do NOT reimplement this. chord_label already encodes the hard-won rules --
    bVII vs vii (a bare degree-7 triad is the subtonic, because the diatonic
    vii-dim essentially never appears as a plain triad), applied=7 secondary
    leading-tone diminished, borrowed-mode accidentals, and the minor shift to
    a relative-major reference. See music_chord_label_accuracy.
    """
    from chord_label import chord_label
    return chord_label(c, mode if mode in ('major', 'minor') else 'major')


def chord_name(c, mode='major'):
    """Degree -> white-note chord name in the song's own mode.

    Does NOT resolve applied/borrowed chords: those name a different pitch
    entirely (Polly's root=7 applied=5 borrowed='major' is a D#, and Hookpad
    labels it V/#vii-dim after its target, not itself). They come back tagged
    with * so they can be excluded or handled separately.
    """
    r = c.get('root')
    if not r:
        return '?'
    # A bare degree-7 triad is bVII, not vii-dim -- chord_label's rule, reached
    # from the same evidence the user reached it from by ear.
    if r == 7 and not c.get('applied') and not c.get('borrowed'):
        return WHITE[(MODE_OFFSET.get(mode, 0) + 3) % 7] + 'b7'
    off = MODE_OFFSET.get(mode, 0)
    name = WHITE[(off + r - 1) % 7]
    if mode == 'harmonicMinor' and r == 7:
        name = 'G#dim'                      # raised 7th
    # #5 on a diminished triad raises the b5 to a perfect 5th, making it MINOR:
    # Billie Jean's degree-7 is stored root=7 alterations=['#5'] inversion=1 and
    # Hookpad displays it as Bm/D. b5 does the reverse to a minor triad.
    alts = c.get('alterations') or []
    if '#5' in alts and name.endswith('dim'):
        name = name[:-3] + 'm'
    elif 'b5' in alts and name.endswith('m'):
        name = name[:-1] + 'dim'
    if c.get('applied') or c.get('borrowed'):
        name += '*'
    return name


def songs(corpus=CORPUS, need_chords=True):
    """Yield (name, data, num_beats) for every live, non-scratch song."""
    live = live_names()
    for f in sorted(glob.glob(os.path.join(corpus, '*.json'))):
        name = os.path.basename(f)[:-5]
        if is_scratch(name) or (live is not None and name.lower() not in live):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if need_chords and not d.get('chords'):
            continue
        yield name, d, (d.get('meters') or [{}])[0].get('numBeats') or 4


def sections(d):
    """Yield (name, start_beat, end_beat). Hookpad beats are 1-based and a song
    with no markers is one unnamed section."""
    secs = sorted(d.get('sections') or [], key=lambda s: s['beat'])
    if not secs:
        secs = [{'beat': 1, 'name': '(whole)'}]
    for i, s in enumerate(secs):
        end = secs[i+1]['beat'] if i + 1 < len(secs) else (d.get('endBeat') or 10**9)
        yield s.get('name', '?'), s['beat'], end
