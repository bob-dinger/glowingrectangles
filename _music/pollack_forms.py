"""Song-level structure for every Beatles song Pollack wrote up: just the section sequence.

Reads the full `Form:` block out of each note's HTML — NOT _index.json, whose `form`
field is truncated at the first line break (Please Please Me stores as
"Intro | Verse | Verse | Bridge |", losing "| Verse | Outro").
"""
import os, re, json, html, argparse
from collections import Counter

NOTES = os.path.expanduser('~/Desktop/music/pollack_beatles_notes')

def fullform(path):
    t = open(path, errors='ignore').read()
    t = re.sub(r'<[^>]+>', ' ', t); t = html.unescape(t); t = re.sub(r'[ \t]+', ' ', t)
    m = re.search(r'Form:(.*?)(?:CD:|Recorded:|UK-release)', t, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None

def parts(form):
    """Pollack's form line -> ['intro','verse','verse','bridge','verse','outro']"""
    out = []
    for tok in form.split('|'):
        tok = re.sub(r'\(.*?\)', '', tok).strip().lower()
        if not tok: continue
        tok = re.sub(r'\s+', ' ', tok)
        out.append(tok)
    return out

def kind(tok):
    """collapse Pollack's wording to a bare section type"""
    for k, v in (('intro', 'intro'), ('outro', 'outro'), ('coda', 'outro'), ('verse', 'verse'),
                 ('bridge', 'bridge'), ('middle', 'bridge'), ('refrain', 'refrain'),
                 ('chorus', 'chorus'), ('solo', 'solo'), ('instrumental', 'solo'),
                 ('break', 'solo'), ('connector', 'link'), ('link', 'link'), ('transition', 'link')):
        if k in tok: return v
    return tok

def load():
    idx = json.load(open(os.path.join(NOTES, '_index.json')))
    rows = []
    for slug, v in idx.items():
        if not isinstance(v, dict) or not v.get('title'): continue
        p = os.path.join(NOTES, slug + '.html')
        if not os.path.exists(p): continue
        f = fullform(p)
        if not f: continue
        raw = parts(f)
        rows.append({'slug': slug, 'title': v['title'], 'key': v.get('key', ''),
                     'meter': v.get('meter', ''), 'form_raw': f,
                     'sections': raw, 'kinds': [kind(t) for t in raw]})
    return sorted(rows, key=lambda r: r['title'].lower())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bare', action='store_true', help='collapse to section types only')
    ap.add_argument('--tally', action='store_true', help='group songs by identical structure')
    ap.add_argument('--json', help='write to this path')
    a = ap.parse_args()
    rows = load()
    if a.tally:
        g = Counter(', '.join(r['kinds']) for r in rows)
        by = {}
        for r in rows: by.setdefault(', '.join(r['kinds']), []).append(r['title'])
        for form, n in g.most_common():
            print(f'\n{n:>3}  {form}')
            for t in sorted(by[form]): print(f'          {t}')
    else:
        for r in rows:
            seq = r['kinds'] if a.bare else r['sections']
            print(f"{r['title'][:38]:<40} {', '.join(seq)}")
    print(f'\n{len(rows)} songs')
    if a.json:
        json.dump(rows, open(a.json, 'w'), indent=1)
        print(f'wrote {a.json}')

if __name__ == '__main__':
    main()
