"""One progression, every rhythm theme — the transpose of the chord_perms library.

chord_perms holds one rhythm per folder and sweeps all 360 orderings through it.
This does the opposite: pick a progression you like and hear it in every rhythm
you have collected, as one paste with a section per theme.

It reads the built .txt pastes rather than re-deriving anything, so what you hear
is exactly what is in the library. Sections run shortest theme first.

    themap_venv/python theme_crosscut.py Am,Em,Dm,G
    themap_venv/python theme_crosscut.py C,F,G            # 3-chord themes
"""
import json, os, glob, argparse

ROOT  = os.path.expanduser('~/Desktop/chord_perms')
OUT   = os.path.join(ROOT, '_crosscuts')
WORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chord_words.json')

def label(folder):
    """Folder -> a short section name: the song if it has one, else the spec."""
    fields = folder.split('_')
    spec = fields[0]
    song = next((f for f in fields[1:] if not f.isupper() and not set(f) <= set('57p')), None)
    return f"{song} {spec}" if song else spec

def section_of(path, order):
    """Pull the one section matching this chord order out of a built paste."""
    d = json.load(open(path))
    want = '-'.join(order)
    hits = [i for i, s in enumerate(d['sections']) if s['name'].endswith(want)]
    if not hits: return None
    i = hits[0]
    start = d['sections'][i]['beat']
    end = d['sections'][i+1]['beat'] if i+1 < len(d['sections']) else d['endBeat']
    chords = [dict(c, beat=c['beat']-start) for c in d['chords'] if start <= c['beat'] < end]
    return chords, end - start

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chords', help="the progression, in order, e.g. Am,Em,Dm,G")
    ap.add_argument('--bpm', type=int, default=110)
    a = ap.parse_args()

    order = [c.strip() for c in a.chords.split(',')]
    k = len(set(order))
    word = next((w for w, cs in json.load(open(WORDS)).items()
                 if len(cs) == k and set(cs) == set(order)), None)
    if not word:
        raise SystemExit(f"no chord word for {{{', '.join(sorted(set(order)))}}}")

    found = []
    for folder in sorted(os.listdir(os.path.join(ROOT, str(k)))):
        path = os.path.join(ROOT, str(k), folder, f"{word.lower()}.txt")
        if not os.path.isfile(path): continue
        got = section_of(path, order)
        if got: found.append((got[1], label(folder), got[0]))
    if not found:
        raise SystemExit(f"{word} {'-'.join(order)} not found in any {k}-chord theme")
    found.sort(key=lambda r: (r[0], r[1]))

    chords, sections, at = [], [], 1
    for span, name, cs in found:
        sections.append({"beat": at, "name": name})
        for c in cs:
            b = at + c['beat']
            chords.append(dict(c, beat=int(b) if float(b).is_integer() else b))
        at += span
    obj = {"version":1, "chords":chords, "notes":[],
           "keys":[{"beat":1, "scale":"major", "tonic":"C"}],
           "tempos":[{"beat":1, "bpm":a.bpm, "swingBeat":0.5, "swingFactor":0}],
           "meters":[{"beat":1, "numBeats":4, "beatUnit":1}],
           "breaks":[], "sections":sections,
           "endBeat":int(at) if float(at).is_integer() else at, "audioTracks":[]}

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{word.lower()}_{'-'.join(order)}.txt")
    open(path, 'w').write(json.dumps(obj, separators=(',',':'), ensure_ascii=False))
    print(f"{word} {'-'.join(order)} — {len(found)} themes, "
          f"{int((at-1)/4)} bars, {os.path.getsize(path)//1024}K")
    for span, name, cs in found:
        print(f"  {int(span/4):3} bars  {len(cs):3} strikes  {name}")
    print(f"-> {path}")

if __name__ == '__main__':
    main()
