"""v2 chord extractor = SEGMENT-based (change-point detection via DP).

Rather than label each beat then merge, find the segmentation of the beat grid that
best explains the chroma: each segment is one chord held for a duration. DP minimizes
  sum_segments( -best_chord_score(pooled_chroma) ) + lambda * n_segments
Pooling chroma over a whole segment gives a much cleaner chord estimate than one beat,
and the output IS chords-with-durations (the real target). Scored vs Hookpad.

    themap_venv/python v2_chord_extract.py <hookpad_song_name>
"""
import sys, os, json, glob
from v0_chord_extract import load_midi_beats, ground_truth, PC, TEMPLATES
from v1_chord_extract import MAJ_FAM, MIN_FAM, STATES, align_score

def beat_features(notes, nbeats):
    chroma = [[0.0]*12 for _ in range(nbeats)]
    bass = [[0.0]*12 for _ in range(nbeats)]
    for pitch, sb, eb in notes:
        for b in range(int(sb), int(min(eb, nbeats))+1):
            if b >= nbeats: break
            ov = min(eb, b+1) - max(sb, b)
            if ov <= 0: continue
            chroma[b][pitch % 12] += ov
            if pitch < 52:                      # low register ~ bass
                bass[b][pitch % 12] += ov
    return chroma, bass

def prefix(mat):
    n = len(mat); P = [[0.0]*12 for _ in range(n+1)]
    for i in range(n):
        for k in range(12): P[i+1][k] = P[i][k] + mat[i][k]
    return P

def seg_best(ch, bs, bass_w):
    tot = sum(ch) or 1
    c = [x/tot for x in ch]
    bt = sum(bs); b = [x/bt for x in bs] if bt else [0]*12
    best, br, bq = -9, 0, 'maj'
    for root in range(12):
        for q, fam in (('maj', MAJ_FAM), ('min', MIN_FAM)):
            s = -9
            for tname in fam:
                tmpl = TEMPLATES[tname]
                sc = sum(c[(root+iv) % 12] for iv in tmpl)
                sc -= 0.5*sum(c[i] for i in range(12) if i not in {(root+iv) % 12 for iv in tmpl})
                s = max(s, sc)
            s += bass_w * b[root]               # bass mass on the root
            if s > best: best, br, bq = s, root, q
    return best, br, bq

def segment(notes, nbeats, lam, bass_w):
    chroma, bass = beat_features(notes, nbeats)
    PC_, PB_ = prefix(chroma), prefix(bass)
    def pooled(i, j): return ([PC_[j][k]-PC_[i][k] for k in range(12)],
                              [PB_[j][k]-PB_[i][k] for k in range(12)])
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def cost(i, j):
        ch, bs = pooled(i, j)
        if sum(ch) < 1e-6: return (0.5, None)      # empty = cheap "no chord"
        s, r, q = seg_best(ch, bs, bass_w)
        return (-s, (r, q))
    INF = float('inf')
    best = [0.0] + [INF]*nbeats
    back = [None]*(nbeats+1)
    for j in range(1, nbeats+1):
        for i in range(max(0, j-16), j):           # cap segment length at 16 beats
            c, lab = cost(i, j)
            v = best[i] + c + lam
            if v < best[j]: best[j] = v; back[j] = (i, lab)
    # backtrack -> per-beat labels + segment list
    pred = [None]*nbeats; segs = []
    j = nbeats
    while j > 0 and back[j]:
        i, lab = back[j]
        for b in range(i, j): pred[b] = lab
        if lab: segs.append((i, j-i, lab))
        j = i
    return pred, segs[::-1]

def run(name, lam, bass_w):
    pairs = json.load(open(os.path.join(os.path.dirname(__file__), 'midi_hookpad_pairs.json')))
    mp = next(glob.iglob(os.path.expanduser('~/Desktop/**/'+pairs[name]), recursive=True))
    hk = json.load(open(os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{name}.json')))
    notes, nbeats = load_midi_beats(mp)
    pred, segs = segment(notes, nbeats, lam, bass_w)
    gt = ground_truth(hk)
    h, t, tr, off = align_score(pred, gt)
    qh = qt = 0
    for b in range(len(gt)):
        pb = b+off
        if gt[b] and 0 <= pb < len(pred) and pred[pb] and (pred[pb][0]+tr) % 12 == gt[b][0]:
            qt += 1; qh += (pred[pb][1] == gt[b][1])
    return h/t, qh/max(qt,1), (tr, off, segs, hk)

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'beatles_yesterday'
    print(f'== v2 segment DP tuning on {name} ==')
    best = None
    for bass_w in (0.3, 0.6, 1.0):
        for lam in (0.05, 0.1, 0.2, 0.3, 0.5):
            root, qual, meta = run(name, lam, bass_w)
            print(f'  lam={lam:<4} bass={bass_w:<4} -> root {root:.0%}  qual {qual:.0%}')
            if best is None or root > best[0]: best = (root, qual, lam, bass_w, meta)
    root, qual, lam, bass_w, (tr, off, segs, hk) = best
    print(f'\nBEST v2: root {root:.0%}  qual {qual:.0%}  (lam={lam}, bass_w={bass_w})')
    print('v0: 76%/93%   v1: 82%/92%')
    print('\nextracted segments (beat+off -> chord):')
    for i, dur, (r, q) in segs[:16]:
        print(f'  beat {i:>3}  x{dur:<2}  {PC[(r+tr)%12]}{q}')

if __name__ == '__main__':
    main()
