"""Fill chords into a chordless Hookpad song from an Ultimate-Guitar chord tab.

Same invariant as pollack_fill.py: Hookpad section lengths are ground truth; the
UG progression for each section is fit INTO the exact bar count (1 chord/bar,
looped/truncated to fill). Chords are converted via the UG tab's own key so the
scale-degree function is preserved regardless of the Hookpad key.

Usage:
    python3 ug_fill.py "roll over beethoven"          # prototype one
    python3 ug_fill.py --all                            # all covers we have tabs for
"""
import os, sys, re, glob, json
from parse_ug import parse_tab, infer_key
from pollack_fill import (load_hookpad, build_paste, role, fit, _db, NOTE_PC, slugify)

UG_DIR = os.path.expanduser('~/Desktop/music/ug_tabs')
OUT = os.path.expanduser('~/Desktop/pollack_pastes')

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def find_tab(title):
    n = norm(title)
    for p in glob.glob(UG_DIR + '/beatles_*.txt'):
        if n in norm(os.path.basename(p)): return p
    return None

def ug_progressions(text):
    """-> (key_tonic, key_scale, [(role, section_name, [chord_names])]) with
    consecutive duplicate chords collapsed to the underlying progression."""
    meta, secs = parse_tab(text)
    kt = meta.get('key'); ks = meta.get('scale', 'major')
    if not kt:
        kt, ks = infer_key(secs)
    out = []
    for s in secs:
        seq = []
        for kind, payload in s['events']:
            if kind == 'chord_line':
                for cname, _col in payload:
                    if not seq or seq[-1] != cname:
                        seq.append(cname)
        if seq:
            out.append((role(s['name']), s['name'], seq))
    return kt, ks, out

def assign(hp_sections, ug_secs):
    """Role-match each Hookpad section to a UG section's progression; fit to bars.
    Returns (fill dict, report, coverage)."""
    role_prog = {}                     # role -> [chords]  (first occurrence wins)
    for r, name, seq in ug_secs:
        role_prog.setdefault(r, seq)

    def fallback():
        for pref in ['verse', 'chorus', 'refrain']:
            if pref in role_prog: return role_prog[pref]
        return ug_secs[0][2] if ug_secs else []

    fill, report, matched = {}, [], 0
    for i, s in enumerate(hp_sections):
        if s['bars'] == 0: continue
        r = role(s['name'])
        prog = role_prog.get(r)
        used_fb = prog is None
        if used_fb: prog = fallback()
        bars = [[c] for c in prog]                 # 1 chord per bar
        fitted, _ = fit(bars, s['bars'])           # loop/truncate to exact length
        if not used_fb: matched += 1
        fill[i] = fitted
        report.append({'section': s['name'], 'bars': s['bars'],
                       'prog': len(prog), 'fallback': used_fb})
    filled = sum(1 for s in hp_sections if s['bars'] > 0)
    return fill, report, (matched / filled if filled else 0)

def run_one(cur, title, write=True, verbose=True):
    tab = find_tab(title)
    if not tab:
        print(f"  ! no UG tab for {title}"); return None
    hp = load_hookpad(cur, title)
    if not hp:
        print(f"  ! no hookpad song for {title}"); return None
    kt, ks, ug = ug_progressions(open(tab, encoding='utf-8', errors='replace').read())
    key_root = NOTE_PC.get(kt, 0)
    fill, report, cov = assign(hp['sections'], ug)
    obj = build_paste(hp, fill, key_root, ks)         # convert via UG key
    if verbose:
        print(f"\n=== {title}  [UG key {kt} {ks} -> Hookpad {hp['key_tonic']} {hp['key_scale']}]"
              f"  match={cov:.0%}  chords={len(obj['chords'])} ===")
        for r in report:
            tag = '~fallback' if r['fallback'] else f"prog{r['prog']}->{r['bars']}bars"
            print(f"   {r['section'][:16]:16} {r['bars']:>2}bars  {tag}")
    if write:
        os.makedirs(OUT, exist_ok=True)
        json.dump(obj, open(os.path.join(OUT, 'ugchords_' + norm(title) + '.txt'), 'w'),
                  separators=(',', ':'))
    return cov

COVERS = ["a taste of honey", "act naturally", "baby its you", "bad boy",
    "devil in her heart", "dizzy miss lizzy", "everybody's trying to be my baby",
    "honey don't", "kansas city", "long tall sally", "matchbox", "money",
    "please mister postman", "rock and roll music", "roll over beethoven",
    "slow down", "words of love", "you really got a hold on me"]

if __name__ == '__main__':
    con = _db(); cur = con.cursor()
    if sys.argv[1:2] == ['--all']:
        res = []
        for t in COVERS:
            cov = run_one(cur, t, write=True, verbose=False)
            res.append((cov if cov is not None else -1, t))
        res.sort(reverse=True)
        print(f"\n{'COV':>5}  song")
        for cov, t in res:
            print(f"{cov:>5.0%}  {t}" if cov >= 0 else f"  n/a  {t}")
    else:
        run_one(cur, ' '.join(sys.argv[1:]) or 'roll over beethoven')
