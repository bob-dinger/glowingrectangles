"""v0 symbolic chord extractor, scored against Hookpad ground truth.
MIDI -> beat-synchronous chroma -> template match -> per-beat (root_pc, quality),
then aligned (best transpose + beat offset) against the Hookpad chords.

    themap_venv/python v0_chord_extract.py <hookpad_song_name>
"""
import sys, os, json
import mido

MAJ_INT = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
PC = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
TONIC_PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
            'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
TEMPLATES = {'maj':{0,4,7},'min':{0,3,7},'dom':{0,4,7,10},'maj7':{0,4,7,11},
             'min7':{0,3,7,10},'sus':{0,5,7},'5':{0,7}}
QMAP = {'maj':'maj','maj7':'maj','dom':'maj','5':'maj','sus':'maj','min':'min','min7':'min'}


def load_midi_beats(path):
    """Return (notes, nbeats). notes = list of (pitch, start_beat, end_beat)."""
    mid = mido.MidiFile(path)
    tpb = mid.ticks_per_beat
    notes, maxb = [], 0
    for track in mid.tracks:
        t = 0
        on = {}
        for msg in track:
            t += msg.time
            if msg.type == 'note_on' and msg.velocity > 0 and getattr(msg, 'channel', 0) != 9:
                on.setdefault((msg.channel, msg.note), []).append(t)
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                k = (getattr(msg, 'channel', 0), msg.note)
                if on.get(k):
                    s = on[k].pop(0)
                    sb, eb = s / tpb, t / tpb
                    if eb > sb:
                        notes.append((msg.note, sb, eb)); maxb = max(maxb, eb)
    return notes, int(maxb) + 1


def chroma_per_beat(notes, nbeats):
    chroma = [[0.0]*12 for _ in range(nbeats)]
    bass = [[None, 999] for _ in range(nbeats)]   # (pc, pitch)
    for pitch, sb, eb in notes:
        b0, b1 = int(sb), int(min(eb, nbeats))
        for b in range(b0, b1+1):
            if b >= nbeats: break
            ov = min(eb, b+1) - max(sb, b)
            if ov <= 0: continue
            chroma[b][pitch % 12] += ov
            if pitch < bass[b][1]:
                bass[b] = [pitch % 12, pitch]
    return chroma, [b[0] for b in bass]


def label(chroma, bass_pc):
    best, bs = (0, 'maj'), -1
    norm = sum(chroma) or 1
    ch = [x/norm for x in chroma]
    for root in range(12):
        for q, tmpl in TEMPLATES.items():
            score = sum(ch[(root+iv) % 12] for iv in tmpl)
            score -= 0.5*sum(ch[i] for i in range(12) if i not in {(root+iv) % 12 for iv in tmpl})
            if bass_pc is not None and bass_pc == root:
                score += 0.15
            if score > bs:
                bs, best = score, (root, QMAP[q])
    if sum(chroma) < 1e-6:
        return None
    return best


def ground_truth(hk):
    tonic = TONIC_PC[hk['keys'][0]['tonic']]
    end = hk.get('endBeat', 200)
    gt = [None]*(end+1)
    for c in hk['chords']:
        r, ap = c['root'], c.get('applied', 0)
        if not r or r < 1 or r > 7:
            continue                       # root=0 passing / NC chord
        if ap and (ap < 1 or ap > 7):
            ap = 0
        if ap > 0:
            rel = (MAJ_INT[ap] + MAJ_INT[r]) % 12; qual = 'maj'
        else:
            rel = MAJ_INT[r]
            bor = c.get('borrowed') or ''
            if bor in ('minor','aeolian') and r in (3,6,7): rel = (rel-1) % 12
            elif bor == 'mixolydian' and r == 7: rel = (rel-1) % 12
            qual = 'maj' if r in (1,4,5) else 'min'
        pc = (tonic + rel) % 12
        b0 = int(c['beat']); b1 = int(c['beat']+c['duration'])
        for b in range(b0, min(b1, end+1)):
            gt[b] = (pc, qual)
    return gt


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'beatles_yesterday'
    pairs = json.load(open(os.path.join(os.path.dirname(__file__), 'midi_hookpad_pairs.json')))
    midfile = pairs[name]
    # locate the midi on disk
    import glob
    mp = None
    for p in glob.glob(os.path.expanduser('~/Desktop/**/'+midfile), recursive=True):
        mp = p; break
    hk = json.load(open(os.path.expanduser(f'~/Desktop/music/hookpad_songs_full/{name}.json')))
    print(f'MIDI: {mp}\nkey: {hk["keys"][0]["tonic"]} {hk["keys"][0]["scale"]}\n')

    notes, nbeats = load_midi_beats(mp)
    chroma, bass = chroma_per_beat(notes, nbeats)
    pred = [label(chroma[b], bass[b]) for b in range(nbeats)]
    gt = ground_truth(hk)

    # align: best (transpose, beat-offset) maximizing root matches on beats where GT exists
    def score_at(tr, off):
        hits = tot = 0
        for b in range(len(gt)):
            g = gt[b]
            if g is None: continue
            pb = b + off
            if 0 <= pb < len(pred) and pred[pb]:
                tot += 1
                if (pred[pb][0]+tr) % 12 == g[0]: hits += 1
        return hits, tot
    best = (-1, 0, 0, 0)
    for tr in range(12):
        for off in range(-24, 25):
            h, t = score_at(tr, off)
            if t and h > best[0]: best = (h, t, tr, off)
    h, tot, tr, off = best
    print(f'best alignment: transpose +{tr}, beat offset {off}')
    print(f'ROOT accuracy: {h}/{tot} = {h/tot:.0%}')
    # quality accuracy where root correct
    qh = qt = 0
    for b in range(len(gt)):
        g = gt[b]; pb = b+off
        if g and 0 <= pb < len(pred) and pred[pb] and (pred[pb][0]+tr) % 12 == g[0]:
            qt += 1; qh += (pred[pb][1] == g[1])
    print(f'QUALITY (given root right): {qh}/{qt} = {qh/max(qt,1):.0%}')
    # eyeball: print the first stretch, GT vs pred
    print('\nbeat  GT        pred')
    for b in range(len(gt)):
        if gt[b] is None: continue
        pb = b+off; p = pred[pb] if 0 <= pb < len(pred) else None
        ps = f'{PC[(p[0]+tr)%12]}{p[1]}' if p else '-'
        mark = '' if (p and (p[0]+tr)%12==gt[b][0]) else '  X'
        print(f'{b:>4}  {PC[gt[b][0]]}{gt[b][1]:<4} {ps:<8}{mark}')
        if b > 60: print('  ...'); break


if __name__ == '__main__':
    main()
