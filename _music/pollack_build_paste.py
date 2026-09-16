"""Build a Hookpad paste-JSON .txt filling Pollack chords into a chordless
Hookpad skeleton. Prototype: 'do you want to know a secret'.

Pipeline: parse_song -> expand_figure (structural) -> map figures to the song's
actual sections -> chord_to_hookpad (absolute chord + key -> Hookpad dict) ->
inject chords into the real song object -> recompute fp -> write .txt.
"""
import os, json, hashlib
from pollack_parse import parse_song
from pollack_assemble import expand_figure
from chord_to_hookpad import chord_to_hookpad

# E major key context for the converter (pitch class of E = 4)
KEY_ROOT, KEY_MODE = 4, 'major'
BPB = 4                                    # beats per bar (4/4)
OUT_DIR = os.path.expanduser('~/Desktop/pollack_pastes')

CHORD_ORDER = ['root', 'beat', 'duration', 'type', 'inversion', 'applied',
               'adds', 'omits', 'alterations', 'suspensions', 'substitutions',
               'pedal', 'alternate', 'borrowed', 'isRest', 'recordingEndBeat']

def make_chord(name, beat, duration):
    # Real Hookpad chords: type is INT (5=triad, 7=dom7), duration is INT,
    # borrowed is null (not '') when absent.
    h = chord_to_hookpad(name, KEY_ROOT, KEY_MODE) or {}
    type_int = 7 if str(h.get('type')) == '7' else 5
    borrowed = h.get('borrowed') or None
    c = {
        'root': h.get('root', 1), 'beat': beat, 'duration': int(duration),
        'type': type_int, 'inversion': h.get('inversion', 0),
        'applied': h.get('applied', 0), 'adds': h.get('adds', []),
        'omits': h.get('omits', []), 'alterations': h.get('alterations', []),
        'suspensions': h.get('suspensions', []), 'substitutions': [],
        'pedal': h.get('pedal', None), 'alternate': '',
        'borrowed': borrowed, 'isRest': False,
        'recordingEndBeat': None,
    }
    return {k: c[k] for k in CHORD_ORDER}, h.get('_raw', name)

def _int_durations(n, total=BPB):
    """Split `total` beats into n integer durations summing to total."""
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]

def bars_to_chords(bars, start_beat):
    """bars = list of per-bar chord-name lists. Returns (chord_dicts, debug)."""
    chords, dbg = [], []
    beat = start_beat
    for bar in bars:
        names = [n for n in bar if n]
        if not names:
            beat += BPB; continue
        for nm, dur in zip(names, _int_durations(len(names))):
            cd, raw = make_chord(nm, beat, dur)
            chords.append(cd)
            dbg.append((beat, nm, cd['root'], cd['type'], cd.get('borrowed')))
            beat += dur
    return chords, dbg

def build():
    hj = json.load(open('/tmp/dywtkas_hookpad.json'))
    secs = hj['sections']
    end = hj['endBeat']
    # section bar counts from real beats
    def barcount(i):
        nb = secs[i+1]['beat'] if i+1 < len(secs) else end
        return round((nb - secs[i]['beat']) / BPB)

    figs = parse_song('dywtkas')
    intro = expand_figure(figs[0])            # 4 bars
    vc    = expand_figure(figs[1])            # 14 bars = verse(10)+chorus(4)
    bridge= expand_figure(figs[2])            # 6 bars
    verse, chorus = vc[:10], vc[10:14]

    # fill per section (in Hookpad order); intro padded +1 (hold B), outro vamp
    FILL = {
        0: intro + [['B']],          # intro:5
        1: verse,                    # verse:10
        2: chorus,                   # chorus:4
        3: verse,
        4: chorus,
        5: bridge,                   # bridge:6
        6: verse,
        7: chorus,
        8: verse[:5],                # outro:5  (verse vamp, fade)
    }

    all_chords, debug = [], []
    for i, s in enumerate(secs):
        if i not in FILL:
            continue
        bars = FILL[i]
        want = barcount(i)
        if len(bars) != want:
            print(f"  ! section '{s['name']}' bars {len(bars)} != hookpad {want}")
        cds, dbg = bars_to_chords(bars, s['beat'])
        all_chords += cds
        debug.append((s['name'], s['beat'], want, dbg))

    obj = {
        'version': 1,
        'chords': all_chords,
        'notes': hj.get('notes', []),
        'keys': hj.get('keys', [{'beat': 1, 'scale': 'major', 'tonic': 'E'}]),
        'tempos': hj.get('tempos', [{'beat': 1, 'bpm': 100, 'swingFactor': 0, 'swingBeat': 0.5}]),
        'meters': hj.get('meters', [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}]),
        'breaks': hj.get('breaks', []),
        'sections': secs,
        'endBeat': end,
        'audioTracks': [],
    }
    compact = json.dumps(obj, separators=(',', ':'))
    obj['fp'] = hashlib.sha1(compact.encode('utf-8')).hexdigest()

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, 'do_you_want_to_know_a_secret.txt')
    json.dump(obj, open(path, 'w'), separators=(',', ':'))
    return path, obj, debug

if __name__ == '__main__':
    path, obj, debug = build()
    print(f"\nwrote {path}")
    print(f"chords={len(obj['chords'])}  endBeat={obj['endBeat']}  fp={obj['fp'][:12]}...\n")
    for name, beat, want, dbg in debug:
        print(f"[{name} @beat{beat} {want}bars]")
        line = '  '.join(f"{nm}({root}{typ or ''}{'/'+bor if bor else ''})"
                          for _, nm, root, typ, bor in dbg)
        print('   ', line)
