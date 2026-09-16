"""Fill chords into a chordless Hookpad song from HookTheory's TheoryTab data
(pulled live via the public Meilisearch API — see hooktheory_search.py).

HookTheory docs give per-section absolute chords (`chordAbs`, 'qq'-separated) + key,
so this reuses the exact same fit-to-Hookpad-section-length pipeline as ug_fill.py.
Melody is NOT in the search index, so this is chords-only.

Usage:
    hooktheory_fill.py "artist" "title"        # prototype one -> paste .txt
"""
import os, sys, re, json
import hooktheory_search as hts
from pollack_fill import load_hookpad, build_paste, fit, role, _db, NOTE_PC

OUT = os.path.expanduser('~/Desktop/pollack_pastes')

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def _artist_key(s): return re.sub(r'^the', '', hts._norm_artist(s))   # drop leading "the"

def reduce_period(seq):
    """HookTheory lists a chord per melody-region, so a 4-chord loop shows up as
    'Ab Bbm Fm Db Ab Bbm Fm Db ...'. Collapse to the smallest repeating period."""
    if not seq: return seq
    n = len(seq)
    for p in range(1, n):
        if all(seq[i] == seq[i - p] for i in range(p, n)):
            return seq[:p]
    return seq

def song_sections(artist, title):
    """-> (key_tonic, key_scale, [(role, section_name, [chord_names])]) from HookTheory."""
    hits = hts.search(f'{title} {artist}', limit=1000)
    na, nt = _artist_key(artist), norm(title)
    secs, key = [], None
    for h in hits:
        if _artist_key(h.get('artist', '')) != na or norm(h.get('song', '')) != nt:
            continue
        key = key or h.get('key', 'C major')
        chords = reduce_period([c for c in re.split(r'qq|\s+', h.get('chordAbs', '')) if c])
        if chords:
            secs.append((role(h.get('section', '')), h.get('section', ''), chords))
    kt, ks = (key.split()[0], (key.split()[1] if len(key.split()) > 1 else 'major')) if key else ('C', 'major')
    return kt, ks, secs

def assign(hp_sections, ht_secs):
    """Role-match each Hookpad section to a HookTheory section's progression; fit to bars."""
    role_prog = {}
    for r, name, seq in ht_secs:
        role_prog.setdefault(r, seq)
    def fallback():
        for pref in ['verse', 'chorus', 'refrain', 'intro']:
            if pref in role_prog: return role_prog[pref]
        return ht_secs[0][2] if ht_secs else []
    fill, report, matched = {}, [], 0
    for i, s in enumerate(hp_sections):
        if s['bars'] == 0: continue
        r = role(s['name'])
        prog = role_prog.get(r); fb = prog is None
        if fb: prog = fallback()
        fitted, _ = fit([[c] for c in prog], s['bars'])
        if not fb: matched += 1
        fill[i] = fitted
        report.append({'section': s['name'], 'bars': s['bars'], 'prog': len(prog), 'fallback': fb})
    filled = sum(1 for s in hp_sections if s['bars'] > 0)
    return fill, report, (matched / filled if filled else 0)

def run_one(cur, artist, title, write=True, verbose=True):
    kt, ks, ht = song_sections(artist, title)
    if not ht:
        if verbose: print(f"  ! HookTheory has no data for {artist} - {title}")
        return None
    hp = load_hookpad(cur, title, artist_like=f'%{artist}%')
    if not hp:
        hp = load_hookpad(cur, title, artist_like='%')          # any artist fallback
    if not hp:
        if verbose: print(f"  ! no chordless Hookpad song matching {title!r}")
        return None
    fill, report, cov = assign(hp['sections'], ht)
    obj = build_paste(hp, fill, NOTE_PC.get(kt, 0), ks)
    if verbose:
        print(f"\n=== {artist} - {title}  [HT {kt} {ks} -> Hookpad {hp['key_tonic']} {hp['key_scale']}]"
              f"  match={cov:.0%}  chords={len(obj['chords'])} ===")
        print(f"  HookTheory sections: {', '.join(n for _,n,_ in ht)}")
        for r in report:
            tag = '~fallback' if r['fallback'] else f"prog{r['prog']}->{r['bars']}bars"
            print(f"   {r['section'][:16]:16} {r['bars']:>2}bars  {tag}")
    if write:
        os.makedirs(OUT, exist_ok=True)
        json.dump(obj, open(os.path.join(OUT, 'htchords_' + norm(title) + '.txt'), 'w'), separators=(',', ':'))
    return cov

if __name__ == '__main__':
    con = _db(); cur = con.cursor()
    artist = sys.argv[1] if len(sys.argv) > 1 else 'Radiohead'
    title = sys.argv[2] if len(sys.argv) > 2 else 'Creep'
    run_one(cur, artist, title)
