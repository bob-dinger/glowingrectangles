#!/usr/bin/env python3
"""
Generate one image per song-part from the PAO scenes, via the OpenAI image API.

Resume-safe: an existing file is skipped, so an interrupted run picks up where
it stopped. Defaults to a SMALL test batch — pass --all deliberately.

    export OPENAI_API_KEY=sk-...
    python3 pao_images.py --limit 4              # test the look first
    python3 pao_images.py --pools G50 --all

Style is fixed across every image on purpose: if the look drifts, you start
remembering pictures by style instead of by content and the system stops
working.
"""
import argparse, base64, json, os, random, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pao_pools as pp
import pao_options as po
import requests

STYLE = ("flat muted colour illustration, single clear subject, centred "
         "composition, plain simple background, soft even light, no text, "
         "no lettering, consistent series style")

# A wall of 30 identical-looking cards is harder to tell apart than a wall of
# 30 different ones — the whole point is that each picture is distinct enough
# to be a separate hook. Every style still has to enforce: ONE clear subject,
# centred, plain background, and no lettering (models render garbled
# pseudo-text, which is why captions are composited on afterwards).
COMMON = ("single clear subject, centred composition, plain uncluttered "
          "background, no text, no lettering, no words")
STYLES = {
 'flat':      f"flat muted colour illustration, soft even light, {COMMON}",
 'linocut':   f"bold linocut woodblock print, two ink colours on cream paper, "
              f"strong carved outlines, {COMMON}",
 'storybook': f"1960s children's picture-book illustration, gouache texture, "
              f"warm limited palette, gentle outlines, {COMMON}",
 'riso':      f"risograph print, two overlapping fluorescent inks, visible "
              f"grain and slight misregistration, {COMMON}",
 'chalk':     f"soft chalk pastel on dark charcoal paper, luminous dusty "
              f"colour, {COMMON}",
 'poster':    f"mid-century travel poster, simplified geometric shapes, flat "
              f"bold colour blocks, {COMMON}",
 'ukiyo':     f"ukiyo-e woodblock style, fine linework, flat washed colour, "
              f"pale sky background, {COMMON}",
 'papercut':  f"layered paper cut-out collage, visible paper edges and soft "
              f"drop shadows, {COMMON}",
}


def style_for(name, key=''):
    """Pick a style. A given song always gets the same one, so its cards look
    like a set, but the collection as a whole stays varied."""
    if name and name in STYLES: return STYLES[name]
    if name == 'mix' or not name:
        names = sorted(STYLES)
        return STYLES[names[abs(hash(key)) % len(names)]]
    return STYLES['flat']


def style_name(name, key=''):
    if name and name in STYLES: return name
    names = sorted(STYLES)
    return names[abs(hash(key)) % len(names)]

ENDPOINT = 'https://api.openai.com/v1/images/generations'


def api_key():
    k = os.environ.get('OPENAI_API_KEY')
    if k: return k.strip()
    for p in ('~/.config/openai/key', '~/.openai_key'):
        p = os.path.expanduser(p)
        if os.path.exists(p):
            return open(p).read().strip()
    sys.exit('No API key. Either:\n'
             '  export OPENAI_API_KEY=sk-...\n'
             '  or put it in ~/.config/openai/key')


def safe(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-')[:48]


def scene_for(seq, rng):
    out = []
    for i in range(0, len(seq), 4):
        grp = seq[i:i+4]
        # applied dominants normalise to `@<semitone>`, which is not one of
        # the nine images; nine_of reads them by pitch class
        picks = []
        for s, c in enumerate(grp):
            k = pp.nine_of(c) if c is not None else None
            picks.append((k or c, '???' if not k
                          else rng.choice(po.W[k][po.ROLES[s]])))
        out.append(po.sentence(picks))
    return ', then '.join(out)


def collect(pools, seed):
    rng = random.Random(seed)
    pm = json.load(open(pp.POOLS))
    idx = pp.build_index()
    rows, seen_global, used_names = [], set(), set()
    for slug in sorted(s for s, p in pm.items() if p in pools):
        path = pp.find(slug, idx)
        if not path: continue
        tonic, scale, secs = pp.sections_of(path)
        band, _, title = pp.strip_tags(slug).partition('_')
        # One image per DISTINCT progression in a song. A file with three
        # sections all named "chorus" on the same loop needs one picture,
        # not three — and if the verse shares the chorus's progression,
        # that is worth knowing rather than drawing twice.
        byprog = {}
        for part, seq in secs:
            if any(x is None for x in seq):      # skip unmapped chords
                continue
            key = '-'.join(seq)
            byprog.setdefault(key, []).append(part)
        for key, parts in byprog.items():
            seq = key.split('-')
            # the same song can appear under several pool_map slugs (tag
            # variants), so dedupe on band+title+progression, not per file
            gk = (band, title, key)
            if gk in seen_global: continue
            seen_global.add(gk)
            label = '+'.join(sorted(set(parts), key=parts.index))
            nm = f'{safe(band)}__{safe(title)}__{safe(label)}.png'
            if nm in used_names:                      # never silently overwrite
                k = 2
                while f'{nm[:-4]}-{k}.png' in used_names: k += 1
                nm = f'{nm[:-4]}-{k}.png'
            used_names.add(nm)
            rows.append(dict(
                band=band.replace('-', ' ').title(),
                song=title.replace('-', ' ').title(),
                part=label, prog=key,
                scene=scene_for(seq, rng),
                nchords=len(seq), name=nm))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pools', default='G50')
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop/pao-images'))
    ap.add_argument('--model', default='gpt-image-1')
    ap.add_argument('--size', default='1024x1024')
    ap.add_argument('--limit', type=int, default=4)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--min-chords', type=int, default=3,
                    help='a one- or two-chord scene is not a picture')
    ap.add_argument('--max-chords', type=int, default=4,
                    help='skip progressions too long to be one image')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    allrows = collect(set(a.pools.split(',')), a.seed)
    rows = [r for r in allrows
            if a.min_chords <= r['nchords'] <= a.max_chords]
    skipped = len(allrows) - len(rows)
    os.makedirs(a.out, exist_ok=True)
    pending = [r for r in rows if not os.path.exists(os.path.join(a.out, r['name']))]
    done = len(rows) - len(pending)
    todo = pending if a.all else pending[:a.limit]
    held = len(pending) - len(todo)

    print(f'{len(allrows)} distinct progressions in {a.pools}; '
          f'{len(rows)} drawable ({a.min_chords}-{a.max_chords} chords), '
          f'{skipped} outside that range')
    print(f'  {done} already on disk | {len(todo)} to generate'
          + (f' | {held} held back by --limit (use --all)' if held else ''))
    if a.dry_run:
        for r in todo:
            print(f"\n  {r['name']}\n    {r['prog']}\n    {r['scene']}")
        return
    if not todo:
        print('nothing to do'); return

    key = api_key()
    hdr = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    ok = fail = 0
    for i, r in enumerate(todo, 1):
        prompt = f"{r['scene']}. {STYLE}."
        print(f"  [{i}/{len(todo)}] {r['name']}", flush=True)
        print(f"        {r['scene']}", flush=True)
        body = {'model': a.model, 'prompt': prompt, 'size': a.size, 'n': 1}
        try:
            resp = requests.post(ENDPOINT, headers=hdr, json=body, timeout=180)
            if resp.status_code != 200:
                print(f'        API {resp.status_code}: {resp.text[:200]}', flush=True)
                fail += 1
                # bail immediately on anything retrying cannot fix: a bad
                # key, or an unfunded account. Only a real rate-limit is worth
                # waiting out.
                if resp.status_code in (401, 403): break
                if resp.status_code == 429 and 'insufficient_quota' in resp.text:
                    print('        -> no credits on the API account; stopping.',
                          flush=True)
                    break
                time.sleep(3); continue
            d = resp.json()['data'][0]
            raw = (base64.b64decode(d['b64_json']) if 'b64_json' in d
                   else requests.get(d['url'], timeout=120).content)
            open(os.path.join(a.out, r['name']), 'wb').write(raw)
            ok += 1
        except Exception as e:
            print(f'        ERROR {e}', flush=True); fail += 1
        time.sleep(1.2)

    print(f'\nwrote {ok}, failed {fail} -> {a.out}')


if __name__ == '__main__':
    main()
