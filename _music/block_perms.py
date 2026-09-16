#!/usr/bin/env python3
"""
Take a 4-bar block (chords + melody + rhythm) and permute the chords, moving
the melody with them.

The template's melody sits at a fixed scale-degree offset from whatever chord
is sounding. Friday Night Blues simplified is I-I-IV-ii with the melody on
each chord's root, so re-voicing it as V-V-I-vi puts the melody on 5, 5, 1, 6
— your G, C, A. The rhythm of both parts is untouched, so every variant
sounds like the same phrase wearing different harmony.

    python3 block_perms.py --template fnb.json --n 24
    python3 block_perms.py --template fnb.json --shape XXYZ --n 40
"""
import argparse, collections, itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bars as B
import pao_pools as pp
import build_rhythm_library as brl

SIX = [1, 2, 3, 4, 5, 6]          # I ii iii IV V vi
RN = {1:'I', 2:'ii', 3:'iii', 4:'IV', 5:'V', 6:'vi', 7:'bVII'}
LET = {1:'C', 2:'Dm', 3:'Em', 4:'F', 5:'G', 6:'Am', 7:'A#'}


def chord_at(chords, beat):
    cur = None
    for c in sorted(chords, key=lambda x: x['beat']):
        if c['beat'] <= beat: cur = c
        else: break
    return cur


def popularity(pools=('G50', 'G100', 'BEATLES')):
    """how often each ordered trio shows up, so the musical ones come first"""
    use = collections.Counter(); idx = pp.build_index()
    inv = {v: k for k, v in LET.items()}
    for sl in brl.slugs_for(set(pools)):
        path = pp.find(sl, idx)
        if not path: continue
        try: _, _, _, secs = B.bars_for(path)
        except Exception: continue
        for name, bb in secs:
            core, _, tail = B.phrase_chords(bb)
            seq = [inv[c] for c in core + tail if c in inv]
            n = len(seq)
            if n < 3: continue
            for i in range(n):
                use[tuple(seq[(i+j) % n] for j in range(3))] += 1
    return use


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True, help='a Hookpad paste JSON')
    ap.add_argument('--shape', default='XXYZ',
                    help='letters per bar; same letter = same chord')
    ap.add_argument('--n', type=int, default=24)
    ap.add_argument('--repeat', type=int, default=2, help='passes per variant')
    ap.add_argument('--tonic', default='C')
    ap.add_argument('--bpm', type=int, default=96)
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/block-perms.txt'))
    a = ap.parse_args()

    tpl = json.load(open(a.template))
    tch = sorted(tpl['chords'], key=lambda c: c['beat'])
    tno = sorted(tpl.get('notes') or [], key=lambda x: x['beat'])
    lo = min(c['beat'] for c in tch)
    span = max(c['beat'] + c['duration'] for c in tch) - lo
    bars = int(round(span / 4))
    shape = a.shape[:bars]
    slots = sorted(set(shape), key=shape.index)
    print(f'template: {bars} bars, {len(tch)} chords, {len(tno)} notes, '
          f'shape {shape} ({len(slots)} distinct)\n')

    # each note's offset, in scale degrees, from the chord sounding under it
    off = []
    for nt in tno:
        c = chord_at(tch, nt['beat'])
        base = int(str(c['root']).lstrip('b#')) if c else 1
        sd = int(str(nt['sd']).lstrip('b#'))
        off.append(((sd - base) % 7, nt, base))

    pop = popularity()
    cands = [p for p in itertools.permutations(SIX, len(slots))]
    def score(p):
        m = dict(zip(slots, p))
        seq = tuple(m[s] for s in shape)
        trio = tuple(sorted(set(seq), key=list(seq).index))[:3]
        return -pop.get(trio, 0)
    cands.sort(key=score)
    cands = cands[:a.n]

    chords, notes, sections = [], [], []
    beat = 1
    for p in cands:
        m = dict(zip(slots, p))
        seq = [m[s] for s in shape]
        sections.append({'beat': beat, 'name': '-'.join(LET[d] for d in seq)})
        for rep in range(a.repeat):
            base0 = beat + rep * bars * 4
            for c in tch:
                bi = int((c['beat'] - lo) // 4)
                nc = dict(c)
                nc['root'] = seq[min(bi, len(seq)-1)]
                nc['beat'] = base0 + (c['beat'] - lo)
                chords.append(nc)
            for o, nt, oldbase in off:
                bi = int((nt['beat'] - lo) // 4)
                newbase = seq[min(bi, len(seq)-1)]
                nn = dict(nt)
                nn['sd'] = str(((newbase - 1 + o) % 7) + 1)
                nn['beat'] = base0 + (nt['beat'] - lo)
                notes.append(nn)
        beat += bars * 4 * a.repeat

    song = {'version': 1, 'chords': chords, 'notes': notes,
            'keys': [{'beat': 1, 'scale': 'major', 'tonic': a.tonic}],
            'tempos': [{'beat': 1, 'bpm': a.bpm, 'swingFactor': 0, 'swingBeat': 0.5}],
            'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
            'breaks': [], 'sections': sections, 'audioTracks': [],
            'endBeat': beat}
    open(a.out, 'w').write(json.dumps(song, separators=(',', ':')))
    print(f'{len(cands)} variants x {a.repeat} passes = {(beat-1)//4} bars, '
          f'{len(chords)} chords, {len(notes)} notes')
    print(f'-> {a.out}\n')
    for p in cands[:12]:
        m = dict(zip(slots, p)); seq = [m[s] for s in shape]
        mel = []
        for o, nt, _ in off[:6]:
            bi = int((nt['beat'] - lo) // 4)
            mel.append(str(((seq[min(bi,len(seq)-1)] - 1 + o) % 7) + 1))
        print(f"   {'-'.join(LET[d] for d in seq):<18}"
              f"{'-'.join(RN[d] for d in seq):<18} melody starts {' '.join(mel)}")


if __name__ == '__main__':
    main()
