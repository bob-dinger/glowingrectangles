"""Eight-bar sections that are two matching four-bar phrases — AA and AA'.

Measured 2026-10-03: comparing bars 1-4 against bars 5-8 position by position,
321 of 1,547 eight-bar sections (20.7%) match on 3 or 4 of the four positions,
against 2.2% from shuffling the same bars. The biggest structural category found.
AA' (three positions) is more common than AA (all four), i.e. the restatement
usually alters exactly one bar.

This writes them out as full sections — melody and chords — so the category can be
heard rather than counted. Rhythm only: two sections match here if their bar
ONSET patterns line up, which does not require the tune to repeat.

Sliced with corpus.section_phrase, NOT on the section marker: 47% of these sections
have a pickup starting before their marker, and 13% had the next section's pickup
hanging off the end. Cutting on the marker made them sound like the music ran
backwards into the section before. The bar grid is anchored to the phrase start, so
bars 1-4 and 5-8 are compared like with like.

    themap_venv/python aa_sections_paste.py              # the 127 exact ones
    themap_venv/python aa_sections_paste.py --tol 1      # within one onset
    themap_venv/python aa_sections_paste.py --min 3      # include AA'
"""
import os, sys, json, argparse, collections
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import role_of, place_at, key_entries, tempo_entries

OUT = os.path.expanduser('~/Desktop/shared_figures')

# One bar of air between sections. The longest pickup in the corpus is 2 beats
# (552 sections carry one; 2 beats is both the max and the 99th percentile), so a
# single bar holds every one of them. Two bars left 10+ beats of dead space and
# made each section look like it started late.
GAP = 0
ORDER = {'verse':0, 'chorus':1, 'pre-chorus':2, 'prechorus':2, 'bridge':3, 'refrain':4}

def num(x): return int(x) if float(x).is_integer() else float(x)

def collect(tol, minmatch):
    out = []
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        chords = sorted(d.get('chords') or [], key=lambda c: c['beat'])
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, (d.get('endBeat') or 10**9))
            if int((end-b0)//4) != 8: continue
            # STRICT: marker to section end, no anacrusis (the layout the user
            # approved 2026-10-03). This also fixes the bar grid -- st == b0 now, so
            # bar masks below are counted from the notated barline.
            end = b0 + 8*4      # the slot, which can be SHORTER than the
                                 # marker-to-marker span; clipping to the
                                 # latter let a chord cross the next marker
            inn = [n for n in notes if b0 <= n['beat'] < end]
            st, sp = b0, end
            if len(inn) < 8: continue
            used.add(role)
            bm = [frozenset(i for i in
                  (int(round((n['beat']-(st+m*4))*4)) for n in inn
                   if st+m*4 <= n['beat'] < st+m*4+4) if 0 <= i < 16) for m in range(8)]
            hits = [i for i in range(4) if len(bm[i] ^ bm[i+4]) <= tol]
            if len(hits) < minmatch: continue
            # relative to the phrase's own first downbeat; place_at then decides
            # where that downbeat sits under the section marker
            off = corpus.metric_offset(inn)
            down = min(n['beat'] for n in inn) + off
            ch = [c for c in chords if st <= c['beat'] < sp and c.get('root')]
            span = max(n['beat']+n['duration'] for n in inn) - st
            out.append({'song':name, 'sec':sec, 'role':role, 'match':len(hits),
                        'odd':[i+1 for i in range(4) if i not in hits],
                        'pickup': round(b0-st, 2), 'span': span, 'off': round(down-b0, 2),
                        'notes':inn, 'chords':ch, 'b0':b0, 'end':end, 'd':d})
    out.sort(key=lambda r: (ORDER.get(r['role'], 9), -r['match'], r['song']))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tol', type=int, default=0, help="onsets of slack per bar")
    ap.add_argument('--min', type=int, default=4, help="4 = AA only, 3 = include AA'")
    ap.add_argument('--bpm', type=int, help="force one tempo; default is each song's own")
    ap.add_argument('--role', help="only this role (chorus, verse, bridge, pre-chorus) "
                    "or 'other' for everything that is not a chorus")
    a = ap.parse_args()
    rows = collect(a.tol, a.min)
    if a.role == 'other':
        rows = [r for r in rows if r['role'] != 'chorus']
    elif a.role:
        rows = [r for r in rows if r['role'] == a.role]

    notes, chords, secs, at = [], [], [], 1          # first section at bar 1
    keys, tempos = [], []
    for r in rows:
        odd = ('' if not r['odd'] else "  not " + ','.join(map(str, r['odd'])))
        pu = (f"  +{r['pickup']:g}pu" if r['pickup'] else '') + (f"  off{r['off']:g}" if r['off'] else '')
        # a whole lead-in bar when the phrase has a pickup, so the downbeat lands
        # on a bar line and NOTHING renders before the marker
        shift, lead = place_at(r['notes'], at, r['b0'])
        # the real mode and tempo, per section: forcing C major makes every
        # minor section sound wrong
        keys   += key_entries(r['d'], r['b0'], r['end'], shift)
        tempos += tempo_entries(r['d'], r['b0'], r['end'], shift, a.bpm)
        secs.append({'beat': num(at),
                     'name': f"{r['song'][:28]} · {r['sec'][:10]}{pu}{odd}"[:62]})
        for n in r['notes']:
            notes.append({'sd':str(n['sd']),'octave':int(n.get('octave',0)),
                          'beat':num(n['beat']+shift),
                          'duration':num(min(n['duration'], r['end']-n['beat'])),
                          'isRest':False,'recordingEndBeat':None})
        for c in r['chords']:
            chords.append({'root':c['root'],'beat':num(c['beat']+shift),
                           'duration':num(min(c.get('duration',4), r['end']-c['beat'])),'type':int(c.get('type',5)),
                           'inversion':0,'applied':c.get('applied',0),'adds':c.get('adds',[]),
                           'omits':c.get('omits',[]),'alterations':c.get('alterations',[]),
                           'suspensions':c.get('suspensions',[]),'substitutions':[],
                           'pedal':None,'alternate':'','borrowed':c.get('borrowed') or '',
                           'isRest':False,'recordingEndBeat':None})
        # lead-in bar (if any) + 8 bars of music + 2 bars of air
        at += (lead+8+GAP)*4
    obj={'version':1,'chords':chords,'notes':notes,
         'keys':keys,'tempos':tempos,
         'meters':[{'beat':1,'numBeats':4,'beatUnit':1}],
         'breaks':[],'sections':secs,'endBeat':num(at),'audioTracks':[]}
    os.makedirs(OUT, exist_ok=True)
    tag = f"AA{'' if a.min==4 else 'prime'}_tol{a.tol}" + (f"_{a.role}" if a.role else "")
    p = os.path.join(OUT, f'{tag}_sections.txt')
    open(p,'w').write(hp3.clipboard(obj))
    roles=collections.Counter(r['role'] for r in rows)
    nochord=sum(1 for r in rows if not r['chords'])
    withpu=sum(1 for r in rows if r['pickup'])
    print(f"  {len(rows)} sections, {int((at-1)/4)} bars, {len(notes)} notes, "
          f"{os.path.getsize(p)//1024}K")
    print(f"  carrying a pickup the marker-slice would have cut: {withpu}")
    print(f"  by role: {dict(roles.most_common())}")
    print(f"  sections with no chords entered: {nochord}")
    print(f"  -> {p}")

if __name__ == '__main__':
    main()
