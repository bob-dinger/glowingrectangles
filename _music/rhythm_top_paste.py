"""The commonest melodic bar-rhythms, each paired with a real bar that uses it.

melody bar-rhythms are far more varied than chord ones — 5,694 distinct patterns
across 35,253 bars, with the top 100 covering only half. This writes the most
common ones out so they can be heard: for each pattern, two bars —

    bar 1   the rhythm alone, every onset on scale degree 1, so it is pure rhythm
    bar 2   a real bar from a real song that uses exactly that pattern

Section names carry the slot picture and the song, so you can read what you hear.

    themab_venv/python rhythm_top_paste.py --top 10
    themap_venv/python rhythm_top_paste.py --top 10 --full    # whole sections instead
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

def num(x): return int(x) if float(x).is_integer() else float(x)
def pic(t): return ''.join('x' if i in t else ('.' if i%4 else '|') for i in range(16))

def scan(eight_only=False):
    """pattern -> count, plus one real example. With eight_only, restrict to the
    clean set: eight-bar verse/chorus/bridge/pre-chorus, first instance per role —
    2,813 distinct bar rhythms instead of 5,694."""
    cnt = collections.Counter(); ex = {}
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, (d.get('endBeat') or 10**9))
            nbars = int((end-b0)//4)
            # STRICT: marker to section end, no anacrusis (the layout the user
            # approved 2026-10-03). st == b0, so the bar masks below are counted
            # from the notated barline.
            inn = [n for n in notes if b0 <= n['beat'] < end]
            st, sp = b0, end
            if len(inn) < 8 or (eight_only and nbars != 8): continue
            used.add(role)
            ch = [c for c in sorted(d.get('chords') or [], key=lambda c: c['beat'])
                  if st <= c['beat'] < sp]
            for m in range(nbars):
                lo = st + m*4
                bar = [n for n in inn if lo <= n['beat'] < lo+4]
                slots = sorted({int(round((n['beat']-lo)*4)) for n in bar})
                slots = [s for s in slots if 0 <= s < 16]
                if not slots: continue
                t = tuple(slots); cnt[t] += 1
                # keep an example that has several notes, so it sounds like music
                full = ([dict(n, beat=n['beat']-st,
                               duration=min(n['duration'], end-n['beat'])) for n in inn],
                        [dict(c, beat=c['beat']-st,
                               duration=min(c.get('duration',4), end-c['beat'])) for c in ch],
                        b0-st,          # where the notated barline sits in `full` (= 0)
                        d, b0, end)     # for the real key + tempo
                # prefer an example that HAS chords, then one with more notes
                score = (len(full[1]) > 0, len(bar))
                if t not in ex or score > ex[t][4]:
                    ex[t] = (name, sec, [dict(n, beat=n['beat']-lo) for n in bar],
                             m+1, score, full, nbars)
    return cnt, ex

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--full', action='store_true', help="whole sections, with chords")
    ap.add_argument('--bpm', type=int, help="force one tempo; default is each song's own")
    a = ap.parse_args()
    cnt, ex = scan(eight_only=a.full)
    tot = sum(cnt.values())
    notes, secs, at = [], [], 1
    keys, tempos = [], []
    print(f"  {tot:,} bars scanned, {len(cnt):,} distinct patterns\n")
    chords=[]
    for t, c in cnt.most_common(a.top):
        song, sec, bar, barno, _score, full, nbars = ex[t]
        if a.full:
            secs.append({'beat': num(at),
                         'name': f"{pic(t)} @bar{barno} · {song[:24]} {sec[:9]}"[:62]})
            # lead-in bar for a pickup, so the downbeat lands on a bar line and
            # nothing renders before the marker (see melody_shared.place_at)
            shift, lead = place_at(full[0], at, full[2])
            # `full` beats are relative to the section's barline, so a source beat B
            # sits at B - b0 + shift; key_entries works in source beats, hence -sb0
            sd, sb0, send = full[3], full[4], full[5]
            keys   += key_entries(sd, sb0, send, shift - sb0)
            tempos += tempo_entries(sd, sb0, send, shift - sb0, a.bpm)
            for n in full[0]:
                notes.append({'sd':str(n['sd']),'octave':int(n.get('octave',0)),
                              'beat':num(n['beat']+shift),'duration':num(n['duration']),
                              'isRest':False,'recordingEndBeat':None})
            for c2 in full[1]:
                if not c2.get('root'): continue
                chords.append({'root':c2['root'],'beat':num(c2['beat']+shift),
                               'duration':num(c2.get('duration',4)),'type':int(c2.get('type',5)),
                               'inversion':0,'applied':c2.get('applied',0),
                               'adds':c2.get('adds',[]),'omits':c2.get('omits',[]),
                               'alterations':c2.get('alterations',[]),
                               'suspensions':c2.get('suspensions',[]),'substitutions':[],
                               'pedal':None,'alternate':'','borrowed':c2.get('borrowed') or '',
                               'isRest':False,'recordingEndBeat':None})
            print(f"  {pic(t)}  {100*c/tot:4.1f}%  bar {barno}  {song[:30]:30} {sec[:11]:11} "
                  f"{len(full[0]):3} notes {len(full[1]):2} chords")
            at += (lead+nbars+GAP)*4
            continue
        secs.append({'beat': num(at), 'name': f"{pic(t)}  {100*c/tot:.1f}%  {song[:26]} {sec[:10]}"[:62]})
        # bar 1: the rhythm alone, on degree 1
        for j, s in enumerate(t):
            nxt = t[j+1] if j+1 < len(t) else 16
            notes.append({'sd':'1','octave':0,'beat':num(at+s/4),
                          'duration':num((nxt-s)/4),'isRest':False,'recordingEndBeat':None})
        # bar 2: the real bar
        for n in bar:
            notes.append({'sd':str(n['sd']),'octave':int(n.get('octave',0)),
                          'beat':num(at+4+n['beat']),'duration':num(n['duration']),
                          'isRest':False,'recordingEndBeat':None})
        print(f"  {pic(t)}  {100*c/tot:4.1f}%  {len(t)} onsets   "
              f"{song[:30]:30} {sec[:12]:12} bar {barno}")
        at += 8
    obj={'version':1,'chords':chords,'notes':notes,
         'keys': keys or [{'beat':1,'scale':'major','tonic':'C'}],
         'tempos': tempos or [{'beat':1,'bpm':100,'swingBeat':0.5,'swingFactor':0}],
         'meters':[{'beat':1,'numBeats':4,'beatUnit':1}],
         'breaks':[],'sections':secs,'endBeat':num(at),'audioTracks':[]}
    os.makedirs(OUT, exist_ok=True)
    p=os.path.join(OUT, f"top{a.top}_bar_rhythms{'_sections' if a.full else ''}.txt")
    open(p,'w').write(hp3.clipboard(obj))
    print(f"\n  -> {p}")

if __name__ == '__main__':
    main()
