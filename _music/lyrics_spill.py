"""Which mis-aligned sections are boundary SPILL, and what move fixes them.

A sung phrase does not always stop where the section marker does — "oh I believe in
yesterday" starts in verse 1 and finishes after verse 2 has begun, so its tail is
typed into the next section's box. That leaves a matched pair of errors: section i
short of its note count, section i+1 carrying syllables that belong to i.

This does not guess. For every adjacent pair it SIMULATES the move — take the first
line of i+1 and append it to i (or push i's last line down) — and keeps the move only
if the combined error against the note counts actually drops. So every row it reports
is a fix that has been tested arithmetically.

    themap_venv/python lyrics_spill.py               # how much of the mess is spill
    themap_venv/python lyrics_spill.py --song yesterday
"""
import os, sys, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corpus
from parse_lyrics import parse_song

def err(pairs):
    return sum(abs(s - n) for s, n in pairs)

def find_moves(rows):
    """[(direction, from_section, to_section, line_text, gain)] — tested moves only."""
    live = [r for r in rows if r['notes']]
    out = []
    for i in range(len(live) - 1):
        a, b = live[i], live[i+1]
        base = err([(a['syllables'], a['notes']), (b['syllables'], b['notes'])])
        # pull b's first line up into a
        if len(b['lines']) > 1:
            k = len(b['lines'][0]['syllables'])
            after = err([(a['syllables']+k, a['notes']), (b['syllables']-k, b['notes'])])
            if after < base:
                out.append(('up', b['name'], a['name'],
                            ' '.join(b['lines'][0]['syllables']), base - after))
                continue
        # push a's last line down into b
        if len(a['lines']) > 1:
            k = len(a['lines'][-1]['syllables'])
            after = err([(a['syllables']-k, a['notes']), (b['syllables']+k, b['notes'])])
            if after < base:
                out.append(('down', a['name'], b['name'],
                            ' '.join(a['lines'][-1]['syllables']), base - after))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--song'); a = ap.parse_args()
    songs = moves = 0; gained = 0; tot_off = 0; examples = []
    for name, d, nb in corpus.songs(need_chords=False):
        if a.song and a.song.lower() not in name.lower(): continue
        rows, flags = parse_song(d)
        live = [r for r in rows if r['notes']]
        if len(live) < 2: continue
        off = [r for r in live if abs(r['syllables']-r['notes'])/max(r['notes'],1) > .25]
        tot_off += len(off)
        ms = find_moves(rows)
        if ms:
            songs += 1; moves += len(ms); gained += sum(m[4] for m in ms)
            examples.append((sum(m[4] for m in ms), name, ms))
        if a.song:
            print(f"\n{name}")
            for r in live:
                print(f"   {r['name'][:14]:14} {r['syllables']:4} syll / {r['notes']:4} notes")
            for d_, frm, to, text, gain in ms:
                arrow = 'move UP  ' if d_ == 'up' else 'move DOWN'
                print(f"   {arrow} from {frm[:12]:12} to {to[:12]:12} gain {gain:3}  \"{text[:48]}\"")
    if a.song: return
    print(f"  songs with at least one tested spill fix : {songs}")
    print(f"  total moves that reduce the error        : {moves}")
    print(f"  syllables of error they remove           : {gained:,}")
    print(f"  sections currently off by more than 25%  : {tot_off}")
    print(f"\n  biggest wins")
    for g, name, ms in sorted(examples, reverse=True)[:12]:
        print(f"   gain {g:4}  {len(ms)} move(s)  {name[:44]}")

if __name__ == '__main__':
    main()
