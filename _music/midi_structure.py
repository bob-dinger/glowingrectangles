"""Reverse-engineer song STRUCTURE from a MIDI via self-similarity, then attach
the v2 chords+durations per detected section. Pure-python (no numpy).

Per song: measure-chroma -> self-similarity matrix -> checkerboard novelty ->
section boundaries -> label repeated sections A/B/C -> chords per section.
"""
import os, re, math, glob, json, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from v0_chord_extract import load_midi_beats, PC
from v2_chord_extract import segment
from fill_preview import build_midi_index, find_midi

BPM = 4  # beats per measure (assume 4/4)

def measure_chroma(notes, nbeats):
    M = nbeats // BPM + 1
    C = [[0.0]*12 for _ in range(M)]
    for pitch, sb, eb in notes:
        for b in range(int(sb), int(min(eb, nbeats))):
            m = b // BPM
            if m < M: C[m][pitch % 12] += min(eb, b+1) - max(sb, b)
    for row in C:
        s = sum(row) or 1
        for i in range(12): row[i] /= s
    return C

def cos(a, b):
    d = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return d/(na*nb) if na and nb else 0.0

def ssm(C): return [[cos(C[i], C[j]) for j in range(len(C))] for i in range(len(C))]

def novelty(S, k=4):
    M = len(S); nov = [0.0]*M
    for i in range(M):
        lo, hi = max(0, i-k), min(M, i+k)
        within = cross = wn = cn = 0.0
        for a in range(lo, i):
            for b in range(lo, i): within += S[a][b]; wn += 1
        for a in range(i, hi):
            for b in range(i, hi): within += S[a][b]; wn += 1
        for a in range(lo, i):
            for b in range(i, hi): cross += S[a][b]; cn += 1
        nov[i] = (within/(wn or 1)) - (cross/(cn or 1))
    return nov

def boundaries(nov, mindist=4):
    M = len(nov)
    mean = sum(nov)/M; sd = (sum((x-mean)**2 for x in nov)/M)**0.5
    thr = mean + 0.4*sd
    bounds = [0]
    for i in range(2, M-1):
        if nov[i] > thr and nov[i] >= nov[i-1] and nov[i] > nov[i+1] and i-bounds[-1] >= mindist:
            bounds.append(i)
    bounds.append(M)
    return bounds

def label_sections(C, bounds):
    segs = [(bounds[i], bounds[i+1]) for i in range(len(bounds)-1)]
    means = []
    for s, e in segs:
        m = [sum(C[r][k] for r in range(s, e))/(e-s) for k in range(12)]
        means.append(m)
    labels = []; refs = []
    for m in means:
        best, bi = 0.0, -1
        for j, r in enumerate(refs):
            c = cos(m, r)
            if c > best: best, bi = c, j
        if best > 0.9: labels.append(labels[bi])
        else: labels.append(chr(65+len(set(labels)))); refs
        refs.append(m)
    # relabel by first-appearance so labels are A,B,C in order
    seen = {}; out = []
    for l in labels:
        if l not in seen: seen[l] = chr(65+len(seen))
        out.append(seen[l])
    return segs, out

def chords_in(pred, s, e):
    seq = []
    for b in range(s*BPM, e*BPM):
        if b < len(pred) and pred[b]:
            lab = pred[b]
            if not seq or seq[-1] != lab: seq.append(lab)
    return [PC[r % 12]+('m' if q == 'min' else '') for r, q in seq]

def analyze(artist, title, idx):
    mp = find_midi(artist, title, idx)
    if not mp: return f'{artist} - {title}: NO MIDI'
    notes, nbeats = load_midi_beats(mp)
    C = measure_chroma(notes, nbeats)
    S = ssm(C)
    bnds = boundaries(novelty(S))
    segs, labels = label_sections(C, bnds)
    pred, _ = segment(notes, nbeats, 0.5, 0.6)
    out = [f'\n### {artist} - {title}   ({len(C)} bars, {len(segs)} sections)']
    out.append('  structure: ' + ' '.join(labels))
    for (s, e), lab in zip(segs, labels):
        ch = chords_in(pred, s, e)
        # collapse repeats in the chord list for readability
        comp = []
        for c in ch:
            if not comp or comp[-1] != c: comp.append(c)
        out.append(f'  [{lab}] bars {s+1}-{e}:  {" ".join(comp[:12])}')
    return '\n'.join(out)

def main():
    c = psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))
    cur = c.cursor()
    cur.execute("select artist,title from parcels.songs where not has_chords and has_melody and in_hookpad and artist is not null")
    rows = cur.fetchall(); c.close()
    targets = ['september', 'mrs robinson', 'pinball wizard', 'celebration', 'mustang sally',
               'the cave', 'lullaby', 'wont get fooled']
    idx = build_midi_index()
    for tg in targets:
        row = next((r for r in rows if tg in (r[1] or '').lower()), None)
        if row:
            try: print(analyze(row[0], row[1], idx))
            except Exception as e: print(f'\n### {tg}: ERR {str(e)[:60]}')

if __name__ == '__main__':
    main()
