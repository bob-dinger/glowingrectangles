"""v1 chord extractor = v0 + Viterbi temporal smoothing + stronger bass-weighting.

State space = 12 roots x {maj,min}. Per-beat emission = best template score in that
family (+ bass bonus). Viterbi with a switch penalty lambda smooths 1-beat flickers.
lambda and the bass weight are tuned against Hookpad ground truth (dev loop).

    themap_venv/python v1_chord_extract.py <hookpad_song_name>
"""
import sys, os, json, glob
from v0_chord_extract import (load_midi_beats, chroma_per_beat, ground_truth,
                              PC, TEMPLATES)

MAJ_FAM = {'maj','dom','maj7','sus','5'}
MIN_FAM = {'min','min7'}
STATES = [(r, q) for r in range(12) for q in ('maj', 'min')]


def emissions(chroma, bass, bass_w):
    """Per-beat score for each of the 24 states."""
    out = []
    for b in range(len(chroma)):
        norm = sum(chroma[b]) or 1
        ch = [x/norm for x in chroma[b]]
        row = {}
        for (root, q) in STATES:
            fam = MAJ_FAM if q == 'maj' else MIN_FAM
            best = -9
            for tname in fam:
                tmpl = TEMPLATES[tname]
                s = sum(ch[(root+iv) % 12] for iv in tmpl)
                s -= 0.5*sum(ch[i] for i in range(12) if i not in {(root+iv) % 12 for iv in tmpl})
                best = max(best, s)
            if bass[b] is not None and bass[b] == root:
                best += bass_w
            row[(root, q)] = best
        out.append(row)
    return out


def viterbi(emis, lam):
    n = len(emis)
    if not n: return []
    V = [dict() for _ in range(n)]
    B = [dict() for _ in range(n)]
    for s in STATES: V[0][s] = emis[0][s]; B[0][s] = None
    for b in range(1, n):
        for s in STATES:
            best_prev, best_val = None, -1e9
            for sp in STATES:
                val = V[b-1][sp] - (0 if sp == s else lam)
                if val > best_val: best_val, best_prev = val, sp
            V[b][s] = emis[b][s] + best_val
            B[b][s] = best_prev
    last = max(STATES, key=lambda s: V[n-1][s])
    path = [last]
    for b in range(n-1, 0, -1):
        path.append(B[b][path[-1]])
    return path[::-1]


def align_score(pred, gt):
    def sc(tr, off):
        h = t = 0
        for b in range(len(gt)):
            if gt[b] is None: continue
            pb = b+off
            if 0 <= pb < len(pred) and pred[pb]:
                t += 1
                if (pred[pb][0]+tr) % 12 == gt[b][0]: h += 1
        return h, t
    best = (-1, 1, 0, 0)
    for tr in range(12):
        for off in range(-24, 25):
            h, t = sc(tr, off)
            if t and h > best[0]: best = (h, t, tr, off)
    return best


def run(name, lam, bass_w, verbose=False):
    pairs = json.load(open(os.path.join(os.path.dirname(__file__), 'midi_hookpad_pairs.json')))
    mp = next(glob.iglob(os.path.expanduser('~/Desktop/**/'+pairs[name]), recursive=True))
    hk = json.load(open(os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{name}.json')))
    notes, nbeats = load_midi_beats(mp)
    chroma, bass = chroma_per_beat(notes, nbeats)
    emis = emissions(chroma, bass, bass_w)
    pred = viterbi(emis, lam)
    gt = ground_truth(hk)
    h, t, tr, off = align_score(pred, gt)
    qh = qt = 0
    for b in range(len(gt)):
        pb = b+off
        if gt[b] and 0 <= pb < len(pred) and pred[pb] and (pred[pb][0]+tr) % 12 == gt[b][0]:
            qt += 1; qh += (('maj' if pred[pb][1]=='maj' else 'min') == gt[b][1])
    return h/t, qh/max(qt,1), (tr, off, mp)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'beatles_yesterday'
    print(f'== tuning lambda x bass_w on {name} ==')
    best = None
    for bass_w in (0.15, 0.3, 0.5):
        for lam in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5):
            root, qual, meta = run(name, lam, bass_w)
            tag = f'lam={lam:<4} bass={bass_w:<4} -> root {root:.0%}  qual {qual:.0%}'
            print('  '+tag)
            if best is None or root > best[0]:
                best = (root, qual, lam, bass_w)
    print(f'\nBEST: root {best[0]:.0%}  qual {best[1]:.0%}  (lambda={best[2]}, bass_w={best[3]})')
    print(f'v0 was: root 76%  qual 93%')


if __name__ == '__main__':
    main()
