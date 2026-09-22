#!/usr/bin/env python3
"""Copy the iCloud Hookpad screenshots into a folder per guitar pool.

COPIES. The originals stay in the hookpad folder exactly where they are --
every image ends up in two places, which is the point.

Matching is image basename -> pool_map slug. Two traps, both hit before:
  * strip ONE trailing digit from the image name, not a greedy run: a greedy
    strip ate the 69 out of "summer of 69".
  * pool slugs STACK their tags -- abba_fernando_ly_o, aerosmith_dream-on_o_c_ly,
    america_sister-golden-hair_ly_o-63a2de -- so strip until stable, or 259 of
    567 images look unmatched when only 95 really are.
"""
import json, os, re, glob, shutil, collections, sys

D = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/hookpad')
HERE = os.path.dirname(os.path.abspath(__file__))
DRY = '--go' not in sys.argv

def norm(s):
    s = s.lower(); s = re.sub(r"[''`]", '', s); s = re.sub(r'\band\b', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)

def debase(slug):
    prev = None
    while prev != slug:
        prev = slug
        slug = re.sub(r'-[0-9a-f]{6}$', '', slug)
        slug = re.sub(r'_(o|c|ly|j|s|m|r|x)$', '', slug)
    return slug

pool = json.load(open(os.path.join(HERE, 'pool_map.json')))
P = {}
for slug, g in pool.items():
    P.setdefault(norm(debase(slug)), g)

plan = collections.defaultdict(list)
unmatched = []
for p in sorted(glob.glob(f"{D}/*.png")):
    g = P.get(norm(re.sub(r'\d$', '', os.path.basename(p)[:-4])))
    (plan[g] if g else unmatched).append(p) if g else unmatched.append(p)

copied = skipped = 0
for g, files in sorted(plan.items(), key=lambda kv: int(kv[0][1:])):
    folder = os.path.join(D, '_' + g[1:])          # G50 -> _50
    if not DRY:
        os.makedirs(folder, exist_ok=True)
    for src in files:
        dst = os.path.join(folder, os.path.basename(src))
        if os.path.exists(dst):
            skipped += 1; continue
        if not DRY:
            shutil.copy2(src, dst)
        copied += 1
    print(f"  {'_'+g[1:]:<8}{len(files):>4} images")

print(f"\n  {'WOULD COPY' if DRY else 'copied'} {copied}, already there {skipped}, "
      f"unmatched (left where they are) {len(unmatched)}")
if DRY: print("  dry run — pass --go to actually copy")
