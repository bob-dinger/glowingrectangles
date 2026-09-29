"""Reduce a melody to its 'simple' form — the two measure types, not just held notes.

The user: "the 'simple' library isn't just 1 measure held notes. it's also the
measures that have 4 quarter notes." So every measure is one of:

    run    four (or so) onsets, nothing sustained — the line is moving
    hold   a long note that stops the motion, the phrase seam
    mixed  both, usually the last bar of an answer phrase

Naming those per measure gives the section a FORM in the user's letter vocabulary
(ABABAAC...), which is the melodic twin of the chord-shape letters.

Three reductions are written, coarse to fine:
    chord    one note per chord — the tone that held the most time, full bar
    seams    only the long notes that end each segment, plus each segment's entry
    form     run bars keep a note per beat, hold bars keep one long note

    themap_venv/python simplify_melody.py <melody.json> --base 69 --name call-me
"""
import json, os, argparse, collections

OUT = os.path.expanduser('~/Desktop/chord_perms/_simple')
LET = 'CDEFGAB'
BAR = 4

def load(path, base):
    d = json.load(open(path))
    ns = sorted([n for n in d['notes'] if not n.get('isRest')], key=lambda n: n['beat'])
    notes = [dict(n, beat=n['beat'] - base) for n in ns]
    chords = [dict(c, beat=c['beat'] - base) for c in sorted(d['chords'], key=lambda c: c['beat'])]
    return notes, chords

def bars_of(notes):
    end = max(n['beat'] + n['duration'] for n in notes)
    return -(-int(end * 100) // (BAR * 100))        # ceil: a held tail still owns its bar

def classify(notes, m):
    """run / hold / mixed / empty for measure m (0-based)."""
    lo, hi = m*BAR, (m+1)*BAR
    inbar = [n for n in notes if lo <= n['beat'] < hi]
    if not inbar: return 'hold', inbar      # no onset = the previous note still ringing
    long_ = [n for n in inbar if n['duration'] >= 2]
    if long_ and len(inbar) <= 2: return 'hold', inbar
    if long_: return 'mixed', inbar
    return 'run', inbar

def letters(kinds):
    """Assign form letters to the measure-type sequence, in first-seen order."""
    seen, out = {}, ''
    for k in kinds:
        if k not in seen: seen[k] = chr(ord('A') + len(seen))
        out += seen[k]
    return out, seen

def held_tone(inbar):
    d = collections.Counter()
    for n in inbar: d[(n['sd'], n['octave'])] += n['duration']
    return max(d, key=d.get)

def note(sd, octave, beat, duration):
    return {"sd": str(sd), "octave": int(octave),
            "beat": beat + 1 if float(beat + 1).is_integer() is False else int(beat + 1),
            "duration": int(duration) if float(duration).is_integer() else duration,
            "isRest": False, "recordingEndBeat": None}

def sounding(notes, beat):
    live = [n for n in notes if n['beat'] <= beat + 1e-9 < n['beat'] + n['duration']]
    if live: return live[-1]
    after = [n for n in notes if n['beat'] > beat]
    return after[0] if after else notes[-1]

def reduce_chord(notes, chords, nbars):
    out = []
    for i, c in enumerate(chords):
        b0 = c['beat']; b1 = chords[i+1]['beat'] if i+1 < len(chords) else b0 + BAR
        inspan = [n for n in notes if b0 <= n['beat'] < b1]
        if not inspan: continue
        sd, oc = held_tone(inspan)
        out.append(note(sd, oc, b0, b1 - b0))
    return out

def reduce_seams(notes, nbars):
    out, i = [], 0
    for i, n in enumerate(notes):
        nxt = notes[i+1]['beat'] if i+1 < len(notes) else None
        gap = (nxt - n['beat']) if nxt is not None else n['duration']
        entry = i == 0 or (notes[i-1]['duration'] >= 2)
        if gap >= 2 or entry:
            out.append(note(n['sd'], n['octave'], n['beat'], max(n['duration'], 1)))
    return out

def reduce_form(notes, nbars):
    out = []
    for m in range(nbars):
        kind, inbar = classify(notes, m)
        if kind in ('hold', 'mixed'):
            if not inbar: continue                 # already covered by the held note
            sd, oc = held_tone(inbar)
            out.append(note(sd, oc, m*BAR, BAR))
        else:
            for b in range(BAR):
                n = sounding(notes, m*BAR + b)
                out.append(note(n['sd'], n['octave'], m*BAR + b, 1))
    return out

def paste(notes, chords, bpm=110):
    return {"version":1,
            "chords":[{**{k:v for k,v in c.items() if k!='beat'},
                       "beat": int(c['beat'])+1, "duration": c.get('duration', BAR),
                       "type": c.get('type',5), "inversion":0, "applied":0, "adds":[],
                       "omits":[], "alterations":[], "suspensions":[], "substitutions":[],
                       "pedal":None, "alternate":"", "borrowed":"", "isRest":False,
                       "recordingEndBeat":None} for c in chords],
            "notes":notes,
            "keys":[{"beat":1,"scale":"major","tonic":"C"}],
            "tempos":[{"beat":1,"bpm":bpm,"swingBeat":0.5,"swingFactor":0}],
            "meters":[{"beat":1,"numBeats":4,"beatUnit":1}],
            "breaks":[], "sections":[{"beat":1,"name":"simple"}],
            "endBeat": int(max(n['beat']+n['duration'] for n in notes))+1,
            "audioTracks":[]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('melody'); ap.add_argument('--base', type=float, required=True)
    ap.add_argument('--name', required=True); ap.add_argument('--bpm', type=int, default=110)
    a = ap.parse_args()
    notes, chords = load(a.melody, a.base)
    nbars = bars_of(notes)

    kinds = [classify(notes, m)[0] for m in range(nbars)]
    form, mapping = letters(kinds)
    print(f"{nbars} measures\n")
    for m, k in enumerate(kinds):
        _, inbar = classify(notes, m)
        seq = ' '.join(f"{LET[int(n['sd'])-1]}{'+' if n['octave']>0 else ''}/{n['duration']:g}" for n in inbar)
        print(f"  m{m+1}  {k:6} {form[m]}   {seq}")
    print(f"\n  form: {form}    ({', '.join(f'{v}={k}' for k,v in mapping.items())})")

    os.makedirs(OUT, exist_ok=True)
    for label, fn in (('chord', reduce_chord), ('seams', reduce_seams), ('form', reduce_form)):
        red = fn(notes, chords, nbars) if label == 'chord' else fn(notes, nbars)
        obj = paste(red, chords, a.bpm)
        path = os.path.join(OUT, f"{a.name}-simple-{label}.txt")
        open(path,'w').write(json.dumps(obj, separators=(',',':'), ensure_ascii=False))
        print(f"  {label:6} {len(red):3} notes  ->  {path}")

if __name__ == '__main__':
    main()
