"""Upload the chord perms library's all-in-one pastes as Hookpad 3 songs, one per riff folder.

    perms_to_hookpad.py --dry                    # list what would go up, build each locally
    perms_to_hookpad.py --token-file ~/.hookpad_token_alt [--throttle 20] [--only roar]

Reads ~/Desktop/perms/chord/<k>/<folder>/all-<N>.txt (built by build_perm_pastes.py),
lays the paste onto a whole saved project (tempo_variant_pastes.full_json of
mine_choruses) and POSTs it private in the Hookpad 3 format. Named
perms-chords_<folder>-<N>, after the first one the user made by hand
(perms-chords_malibu-mrJones-360). Songs whose name is already in the account
are skipped, so a re-run only fills gaps.

2026-11-23: the perms go to the user's OTHER Hookpad account (user 255248); its
token lives in ~/.hookpad_token_alt, never in ~/.hookpad_token.
"""
import argparse, glob, json, os, time
import template_8 as T
from tempo_variant_pastes import full_json

ROOT = os.path.expanduser('~/Desktop/perms/chord')
# already in the account under the name the user gave it by hand
SKIP = {'perms-chords_14-18-14-18_ABCD_malibu,mrjones-360'}   # = perms-chords_malibu-mrJones-360
KEEP = ('notes', 'chords', 'keys', 'tempos', 'meters', 'sections', 'breaks', 'endBeat')


def items():
    for f in sorted(glob.glob(f'{ROOT}/[0-9]/*/all-*.txt')):
        folder = os.path.basename(os.path.dirname(f))
        n = os.path.basename(f)[4:-4]
        yield f'perms-chords_{folder}-{n}', f


def song(path):
    p = json.load(open(path))
    o = full_json(json.load(open(f'{T.D}/mine_choruses.json')), 1)
    o.update({k: p[k] for k in KEEP if k in p})
    o['notes'] = p.get('notes') or []
    o['inactiveNotes'] = [[] for _ in o.get('inactiveNotes') or [[]]]
    if not o.get('breaks'):
        o['breaks'] = [{'beat': s['beat']} for s in o['sections'][1:]]
    if isinstance(o.get('lyrics'), dict):
        o['lyrics']['values'] = ['' for _ in o['lyrics'].get('values') or []]
        o['lyrics']['sectionLyrics'] = [{'sectionName': s['name'], 'lyrics': ['', '', '', '']} for s in o['sections']]
    return o


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--token-file', default='~/.hookpad_token_alt')
    ap.add_argument('--throttle', type=float, default=20)
    ap.add_argument('--only', help='substring of the song name')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    todo = [(n, f) for n, f in items() if not a.only or a.only.lower() in n.lower()]
    if a.dry:
        for n, f in todo:
            o = song(f)
            print(f"{len(o['sections']):4d} sections {len(o['chords']):5d} chords {o['tempos'][0]['bpm']:4} bpm  {n}")
        raise SystemExit
    from hookpad_upload_variants import upload, call, API
    tok = open(os.path.expanduser(a.token_file)).read().strip()
    have = {s['song'].lower() for s in call('GET', f'{API}/songs/h?per-page=100&page=1', tok).json()}
    for i, (n, f) in enumerate(todo):
        if n in SKIP or n.lower() in have or n.lower().replace(',', '-') in have:
            print('have  ', n); continue
        time.sleep(a.throttle if i else 3)
        r, err = upload(tok, n, song(f), hp3_base=True)
        print(err or f"{'ok    ' if r['verified'] else 'CHECK '}{n}  {r['url']}", flush=True)
        if err and '401' in err:
            raise SystemExit('token expired: paste a new one into ' + a.token_file)
