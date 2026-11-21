"""Write real sections of a given length and role out as a Hookpad paste.

The general version of melody_word_paste.py: no pattern filter, just "give me the
N-measure verses". Splits into parts because a single paste of 70 sections is too
much to look through at once.

Rules applied (the user's standing ones):
  - first instance per role only
  - no intros/outros/solos/interludes (melody_shared.role_of)
  - sliced STRICTLY from the section marker to the section end: no anacrusis
    lookback at all (the user, 2026-10-03: "let's just not worry about anacrusis
    at all"). --pickup restores corpus.section_phrase if it is ever wanted.
  - a note ringing past the section end is CLIPPED there, so a section cannot
    overlap the next one (13% of sections have one, by up to 8.75 beats)
  - sections with no melody entered are skipped — nothing to look at
  - variant files (-hooktab, -right, _dynamics, -90) collapse to the base song
  - bars counted from the notated barline; a pickup gets its own lead-in bar
    (melody_shared.place_at)

    themap_venv/python sections_paste.py --bars 10 --role verse --parts 2
    themap_venv/python sections_paste.py --bars 10 --role chorus --parts 4 --part 3
"""
import os, sys, json, argparse, collections
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from melody_shared import (role_of, place_at, key_entries, tempo_entries,
                           base_of, VARIANT, num)
from melody_bar_words import letter

OUT = os.path.expanduser('~/Desktop/shared_figures')

# NO air between sections: an 8-bar section gets 8 bars, back to back. The user,
# 2026-10-03: "you are giving these all 9 measures when they only need 8". Safe only
# because slicing is strict (no anacrusis) AND the last note is clipped at the section
# end -- 13% of sections have a note ringing past it, by up to 8.75 beats, which with
# no air would overlap the next section.
GAP = 0
def collect(nbars, role_want, pickup=False, need_chords=False):
    rows, seen = [], set()
    for name, d, nb in corpus.songs(need_chords=False):
        if nb != 4: continue
        notes = sorted([n for n in (d.get('notes') or []) if not n.get('isRest')],
                       key=lambda n: n['beat'])
        if not notes: continue
        chords = sorted(d.get('chords') or [], key=lambda c: c['beat'])
        used = set()
        for sec, b0, b1 in corpus.sections(d):
            role = role_of(sec)
            if role is None or role in used: continue
            end = min(b1, d.get('endBeat') or 10**9)
            if int((end-b0)//4) != nbars: continue
            used.add(role)
            if role_want and role != role_want: continue
            if pickup:
                inn, st, sp = corpus.section_phrase(notes, b0, end)
            else:
                # marker to end, nothing before and nothing after
                # the slot is exactly nbars bars; `end` can sit up to 3.75 beats
                # past it when (end-b0)//4 rounds down, and clipping to `end`
                # instead let a chord cross the NEXT section's marker.
                end = b0 + nbars*4
                inn, st, sp = [n for n in notes if b0 <= n['beat'] < end], b0, end
            if not inn: continue                   # no melody entered
            key = (base_of(name), role)
            if key in seen: continue               # one per song, not per variant
            seen.add(key)
            w = ''.join(letter([n for n in inn if b0+m*4 <= n['beat'] < b0+m*4+4])
                        for m in range(nbars))
            ch = [c for c in chords if st <= c['beat'] < sp and c.get('root')]
            if need_chords and not ch: continue
            rows.append((name, sec, role, w, inn, ch, b0, end, d))
    rows.sort(key=lambda r: r[0])
    return rows

def write(rows, nbars, path, bpm, keep_tonic=False):
    notes, chords, secs, at = [], [], [], 1      # first section starts at bar 1
    keys, tempos = [], []
    for name, sec, role, w, inn, ch, b0, end, d in rows:
        shift, lead = place_at(inn, at, b0)
        keys   += key_entries(d, b0, end, shift, keep_tonic)
        tempos += tempo_entries(d, b0, end, shift, bpm)
        secs.append({'beat': num(at), 'name': f"{w}  {name[:26]} {sec[:9]}"[:62]})
        for n in inn:
            dur = min(n['duration'], end - n['beat'])     # clip at the section end
            notes.append({'sd': str(n['sd']), 'octave': int(n.get('octave', 0)),
                          'beat': num(n['beat']+shift), 'duration': num(dur),
                          'isRest': False, 'recordingEndBeat': None})
        for c in ch:
            chords.append({'root': c['root'], 'beat': num(c['beat']+shift),
                           'duration': num(min(c.get('duration', 4), end - c['beat'])),
                           'type': int(c.get('type', 5)), 'inversion': 0,
                           'applied': c.get('applied', 0), 'adds': c.get('adds', []),
                           'omits': c.get('omits', []), 'alterations': c.get('alterations', []),
                           'suspensions': c.get('suspensions', []), 'substitutions': [],
                           'pedal': None, 'alternate': '', 'borrowed': c.get('borrowed') or '',
                           'isRest': False, 'recordingEndBeat': None})
        at += (lead+nbars+GAP)*4
    obj = {'version': 1, 'chords': chords, 'notes': notes,
           'keys': keys, 'tempos': tempos,
           'meters': [{'beat': 1, 'numBeats': 4, 'beatUnit': 1}],
           'breaks': [], 'sections': secs, 'endBeat': num(at), 'audioTracks': []}
    open(path, 'w').write(hp3.clipboard(obj))
    return int((at-1)/4), len(notes), len(chords)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bars', type=int, default=10)
    ap.add_argument('--role', default='verse')
    ap.add_argument('--parts', type=int, default=2)
    ap.add_argument('--part', type=int, help="only write this part (1-based)")
    ap.add_argument('--bpm', type=int, help="force one tempo; default is each song's own")
    ap.add_argument('--keep-tonic', action='store_true',
                    help="keep each song's real tonic instead of normalising to white notes")
    ap.add_argument('--max', type=int, help="stop after this many sections")
    ap.add_argument('--pickup', action='store_true', help="include the anacrusis")
    ap.add_argument('--with-chords', action='store_true', help="only sections that have chords")
    a = ap.parse_args()
    rows = collect(a.bars, a.role, a.pickup, a.with_chords)
    if a.max: rows = rows[:a.max]
    os.makedirs(OUT, exist_ok=True)
    n = len(rows); per = -(-n // a.parts)
    print(f"\n  {n} {a.bars}-measure {a.role} sections with a melody entered, "
          f"one per song -> {a.parts} part(s) of ~{per}\n")
    for i in range(a.parts):
        if a.part and i+1 != a.part: continue
        chunk = rows[i*per:(i+1)*per]
        if not chunk: continue
        p = os.path.join(OUT, f'{a.bars}bar_{a.role}_{i+1}of{a.parts}.txt')
        bars, nn, nc = write(chunk, a.bars, p, a.bpm, a.keep_tonic)
        nochord = sum(1 for r in chunk if not r[5])
        print(f"  part {i+1}: {len(chunk)} sections, {bars} bars, {nn} notes, "
              f"{nc} chords ({nochord} sections have none), {os.path.getsize(p)//1024}K")
        print(f"    {chunk[0][0][:28]} .. {chunk[-1][0][:28]}")
        print(f"    -> {p}")

if __name__ == '__main__':
    main()
