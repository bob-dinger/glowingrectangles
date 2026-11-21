#!/usr/bin/env python3
"""
Drums from a song's MIDI, for drums.html: a drum kit whose pieces light up as
they are hit while the song plays.

    themap_venv/python drum_map.py "smashing pumpkins_1979" [more songs...]   # -> drums.html
    themap_venv/python drum_map.py --beatles                                  # every Beatles song with MIDI drums

MIDI only -- no Hookpad. Drums = channel 10, hits snapped to 16ths. The bar's
downbeat is fitted from the snare on 2 and 4 and the kick on 1 (fan MIDIs often
start on a pickup). Playback follows the MIDI's tempo map (several set_tempo at
one tick: the last wins). PARTS come from the drumming: 4-bar blocks described
by the one-bar grooves they use, a block sharing half its grooves with an
earlier part is that part again (same letter). Only the first time signature is
used: songs that change meter keep the right timing, but bar numbers drift.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mido
import three_way_fill as T   # find_midi: the MIDI paired with a Hookpad song

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'drums.html')
# General MIDI drum notes -> lanes, top to bottom as on a drum chart
LANES = ['crash', 'ride', 'open hat', 'hi-hat', 'perc', 'high tom', 'mid tom', 'snare', 'side stick', 'floor tom', 'kick']
GM = {49: 'crash', 57: 'crash', 52: 'crash', 55: 'crash', 51: 'ride', 59: 'ride', 53: 'ride',
      46: 'open hat', 42: 'hi-hat', 44: 'hi-hat', 50: 'high tom', 48: 'high tom', 47: 'mid tom', 45: 'mid tom',
      38: 'snare', 40: 'snare', 39: 'snare', 37: 'side stick', 43: 'floor tom', 41: 'floor tom',
      35: 'kick', 36: 'kick'}


def drum_hits(path):
    """[(beat, lane, velocity)] from channel 10, beats per bar, and the tempo
    map [(beat, seconds per beat)] -- several set_tempo at one tick: the last wins"""
    mid = mido.MidiFile(path, clip=True); tpb = mid.ticks_per_beat
    hits, bpb, tempos = [], 4, {}
    for tr in mid.tracks:
        t = 0
        for m in tr:
            t += m.time
            if m.type == 'time_signature' and t == 0: bpb = m.numerator * 4 / m.denominator
            if m.type == 'set_tempo': tempos[t / tpb] = m.tempo / 1e6
            if m.type == 'note_on' and m.velocity > 0 and m.channel == 9:
                hits.append((t / tpb, GM.get(m.note, 'perc'), m.velocity))
    return sorted(hits), bpb, sorted(tempos.items()) or [(0, .5)]


def seconds(tmap, beat):
    """beat -> seconds from the start, through every tempo change"""
    t, prev_b, spb = 0.0, 0.0, tmap[0][1]
    for b, sp in tmap:
        if b >= beat: break
        t += (b - prev_b) * spb; prev_b, spb = b, sp
    return t + (beat - prev_b) * spb


_MIDS = None


def find_midi(name):
    """the paired MIDI, else any MIDI on the Desktop named artist_title"""
    global _MIDS
    try: return T.find_midi(name)
    except KeyError: pass
    import glob, re
    n = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
    if _MIDS is None:
        _MIDS = {}
        for p in glob.glob(os.path.expanduser('~/Desktop/**/*.mid'), recursive=True):
            _MIDS.setdefault(n(os.path.basename(p)[:-4]), p)
    hit = _MIDS.get(n(name))
    if not hit: raise SystemExit(f'{name}: no MIDI found')
    return hit


def song(name):
    path = find_midi(name)
    hits, bpb, tmap = drum_hits(path)
    if not hits: raise SystemExit(f'{name}: no drums in {path}')
    steps = int(bpb * 4)
    # where the bar starts: fan MIDIs often begin on a pickup, so try every
    # 16th and keep the phase that puts the backbeat (snare on 2 and 4) and
    # the kick / crash on the one
    def fit(ph):
        sc = 0
        for b, lane, v in hits:
            st = int(round(((b - ph) % bpb) * 4)) % steps
            if lane == 'snare' and st % 8 == 4: sc += 1
            if lane in ('kick', 'crash') and st == 0: sc += 1
        return sc
    phase = max((k / 4 for k in range(steps)), key=fit)
    hits = [(b - phase, l, v) for b, l, v in hits if b - phase >= 0]
    nbars = int(hits[-1][0] // bpb) + 1
    # each bar's start and length in seconds, so playback follows tempo changes
    bt = [round(seconds(tmap, phase + i * bpb), 4) for i in range(nbars + 1)]
    bpm = round(60 / next((sp for b0, sp in reversed(tmap) if b0 <= phase + hits[0][0]), tmap[0][1]))
    bars = [dict() for _ in range(nbars)]
    for b, lane, v in hits:
        bar, st = int(b // bpb), int(round((b % bpb) * 4))
        if st >= steps: bar, st = bar + 1, 0
        if bar < nbars: bars[bar][(lane, st)] = max(v, bars[bar].get((lane, st), 0))
    keys = [frozenset(x) for x in bars]
    count = collections.Counter(k for k in keys if k)
    # common grooves (2+ bars) get letters by how often they play; a rarer bar
    # within two hits of one is its variant
    main = [k for k, n in count.most_common() if n >= 2]
    letter = {k: chr(65 + i) if i < 26 else f'#{i + 1}' for i, k in enumerate(main)}
    groups = []
    for i, k in enumerate(keys):
        if not k: groups.append(None); continue
        if k in letter: groups.append(letter[k]); continue
        near = min(main, key=lambda m: len(k ^ m), default=None)
        groups.append(letter[near] + "'" if near and len(k ^ near) <= 2 else '·')
    pats = [dict(id=letter[k], n=count[k], hits=[[LANES.index(l), s, bars[keys.index(k)][(l, s)]] for l, s in sorted(k)])
            for k in main]
    # every bar as [group, hits], so any bar (variant, fill) can be opened
    allbars = [[g, [[LANES.index(l), s, v] for (l, s), v in sorted(bars[i].items())]] for i, g in enumerate(groups)]
    # PARTS from the drumming alone: 4-bar blocks, each described by the
    # grooves it uses (a variant counts as its groove, fills are ignored);
    # neighbouring blocks that match merge, and a returning part keeps its letter
    def sig(i):
        return frozenset(g.rstrip("'") for g in groups[i:i + 4] if g and g != '·')
    # a block is the same part as an earlier one when they share at least half
    # their grooves (Jaccard >= .5); neighbouring blocks of one part merge
    reps, secs = [], []
    for i in range(0, nbars, 4):
        k = sig(i)
        if not k: continue
        best = max(range(len(reps)), key=lambda r: len(k & reps[r]) / len(k | reps[r]), default=None)
        if best is not None and len(k & reps[best]) / len(k | reps[best]) >= .5: part = best
        else: reps.append(k); part = len(reps) - 1
        nm = chr(65 + part) if part < 26 else f'#{part + 1}'
        if not secs or secs[-1]['name'] != nm: secs.append(dict(name=nm, bar=i + 1))
    used = sorted({l for k in keys for l, _ in k}, key=LANES.index)
    artist, _, title = name.partition('_')
    return dict(name=name, title=title.title(), artist=artist.title(), bpm=bpm, steps=steps, bpb=bpb,
                lanes=LANES, used=[LANES.index(l) for l in used], bars=allbars, patterns=pats,
                sections=secs, bt=bt, tempos=len(tmap), midi=os.path.basename(path))


def beatles():
    """every base beatles_* song in the library (no -variants)"""
    import pao_pools as pp
    lib = {x['song'] for x in json.load(open(os.path.expanduser('~/Desktop/music/.hookpad_song_list.json')))}
    return sorted(n for n in lib if n.lower().startswith('beatles_') and not pp.split_variant(n)[1]
                  and os.path.exists(os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{n}.json')))


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or ['smashing pumpkins_1979']
    if '--beatles' in sys.argv: names = beatles()
    data, skipped = [], {}
    for n in names:
        try: d = song(n)
        except SystemExit as e: skipped[n] = str(e).split(': ', 1)[-1][:40]; continue
        except Exception as e: skipped[n] = type(e).__name__; continue
        data.append(d)
        if len(names) < 5:
            gs = [g for g, _ in d['bars']]
            print(f'{n}: {len(gs)} bars, {len(d["patterns"])} grooves, {len(d["sections"])} sections placed')
    data.sort(key=lambda d: d['title'].lower())
    page = open(os.path.join(HERE, 'drums_template.html')).read()
    open(OUT, 'w').write(page.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':'))))
    print(f'{OUT}: {len(data)} songs' + (f', {len(skipped)} skipped (no MIDI / no drums)' if skipped else ''))


if __name__ == '__main__':
    main()
