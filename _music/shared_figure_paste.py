"""Hear a shared figure in CONTEXT: one Hookpad paste, one full section per song.

melody_shared.py finds melodic figures that turn up in several songs, matched free
of key, tempo and metric level. This writes them out so you can actually listen.

Each instance becomes its own section, named for the song. Rhythm is normalised so
the figure's shortest note is an eighth in every instance — otherwise one song's
eighths play against another's quarters and the match is inaudible. Pitches keep
their original scale degrees and octaves, so what you hear differing is register,
not key.

    themap_venv/python shared_figure_paste.py --intervals 1,1,-1,-1 --rhythm 1,1,2,1,1
    themap_venv/python shared_figure_paste.py --list 6 4     # 6+ notes, 4+ songs
"""
import os, re, sys, json, argparse, collections
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from melody_shared import windows, sections, DEG, LET, place_at

OUT = os.path.expanduser('~/Desktop/shared_figures')
UNIT = 0.5          # the figure's shortest note becomes an eighth
GAP  = 1            # bars of silence between instances (longest pickup is 2 beats)

def num(x): return int(x) if float(x).is_integer() else float(x)

def collect(use_all=True):
    """figure -> [(song, section, window, full notes, full chords, section start)]"""
    import corpus
    from melody_shared import role_of
    found = collections.defaultdict(list)
    for name, d, nb in corpus.songs(need_chords=False):
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        chords = sorted(d.get('chords') or [], key=lambda c: c['beat'])
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            inn, st, sp = corpus.section_phrase(notes, b0, b1)
            if len(inn) < 4: continue
            used.add(role)
            ch = [c for c in chords if st <= c['beat'] < sp]
            bar0 = b0                    # the NOTATED barline, kept for layout
            b0 = st                      # everything below is relative to the phrase
            seen = set()
            for k, iv, rhythm, i, win in windows(inn):
                if len(set(iv)) == 1 and iv[0] == 0: continue
                key = (k, iv, rhythm)
                if key in seen: continue
                seen.add(key)
                found[key].append((name, sec, win, inn, ch, b0, bar0))
    return found

def paste(hits, bpm=104):
    """One FULL section per instance, each scaled so the figure's shortest note is
    an eighth, laid out on bar lines with a gap between."""
    notes, chords, secs, at = [], [], [], 1
    for name, sec, win, inn, ch, b0, bar0 in hits:
        f = UNIT / min(n['duration'] for n in win)       # one factor for the section
        # scale first, THEN place: a pickup gets its own lead-in bar so the real
        # downbeat sits on a bar line (see melody_shared.place_at)
        sc = [dict(n, beat=(n['beat']-b0)*f, duration=n['duration']*f) for n in inn]
        # the barline, carried through the same scaling as the notes.  With a
        # non-power-of-two factor the original bar cannot land on an output bar
        # line at all, so alignment here is best-effort.
        shift, lead = place_at(sc, at, (bar0-b0)*f)
        where = (win[0]['beat'] - b0) * f + shift - at    # where the figure sits, scaled
        secs.append({'beat': num(at),
                     'name': f"{name} · {sec} · fig@bar{int(where//4)+1}"[:58]})
        for n in sc:
            notes.append({'sd': str(n['sd']), 'octave': int(n.get('octave', 0)),
                          'beat': num(n['beat'] + shift),
                          'duration': num(n['duration']),
                          'isRest': False, 'recordingEndBeat': None})
        for c in ch:
            if not c.get('root'): continue
            chords.append({'root': c['root'], 'beat': num((c['beat']-b0)*f + shift),
                           'duration': num(c.get('duration',4)*f),
                           'type': int(c.get('type',5)), 'inversion':0,
                           'applied': c.get('applied',0), 'adds': c.get('adds',[]),
                           'omits': c.get('omits',[]), 'alterations': c.get('alterations',[]),
                           'suspensions': c.get('suspensions',[]), 'substitutions': [],
                           'pedal': None, 'alternate':'', 'borrowed': c.get('borrowed') or '',
                           'isRest': False, 'recordingEndBeat': None})
        span = max(n['beat'] + n['duration'] for n in sc)
        at += (lead + int(span//4)+1+GAP)*4
    return {'version':1, 'chords':chords, 'notes':notes,
            'keys':[{'beat':1,'scale':'major','tonic':'C'}],
            'tempos':[{'beat':1,'bpm':bpm,'swingBeat':0.5,'swingFactor':0}],
            'meters':[{'beat':1,'numBeats':4,'beatUnit':1}],
            'breaks':[], 'sections':secs, 'endBeat':num(at), 'audioTracks':[]}

def nm(n):
    m = re.match(r'^([b#]*)([1-7])$', str(n['sd']))
    return f"{LET[DEG[m.group(2)]]}{m.group(1)}{4+n.get('octave',0)}" if m else str(n['sd'])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--intervals'); ap.add_argument('--rhythm')
    ap.add_argument('--name'); ap.add_argument('--max', type=int, default=8)
    ap.add_argument('--list', nargs=2, type=int, metavar=('MINNOTES','MINSONGS'))
    a = ap.parse_args()
    found = collect(True)

    if a.list:
        kmin, smin = a.list
        rows=[]
        for (k, iv, rhythm), hits in found.items():
            songs={h[0] for h in hits}
            if k>=kmin and len(set(rhythm))>1 and len(songs)>=smin:
                rows.append((len(songs), k, iv, rhythm))
        rows.sort(key=lambda r:(-r[0],-r[1]))
        for nsongs,k,iv,rhythm in rows[:25]:
            print(f"  {nsongs:3} songs  {k} notes  --intervals {','.join(map(str,iv))} "
                  f"--rhythm {','.join(map(str,rhythm))}")
        return

    iv=tuple(int(x) for x in a.intervals.split(','))
    rh=tuple(int(x) for x in a.rhythm.split(','))
    key=(len(rh), iv, rh)
    hits=found.get(key)
    if not hits: sys.exit('  no instances of that figure')
    # one instance per song, longest first
    byname={}
    for h in hits: byname.setdefault(h[0], h)
    picked=list(byname.values())[:a.max]
    os.makedirs(OUT, exist_ok=True)
    label = a.name or ('fig_' + '_'.join(map(str,iv)).replace('-','m'))
    path=os.path.join(OUT, f"{label}.txt")
    open(path,'w').write(hp3.clipboard(paste(picked)))
    print(f"  {len(picked)} songs, {len(rh)} notes each -> {path}")
    for name,sec,win,inn,ch,b0 in picked:
        f = UNIT/min(n['duration'] for n in win)
        print(f"     {name[:34]:34} {sec[:11]:11} {len(inn):3} notes  "
              f"{len(ch):2} chords  figure: {' '.join(nm(n) for n in win)}")

if __name__ == '__main__':
    main()
