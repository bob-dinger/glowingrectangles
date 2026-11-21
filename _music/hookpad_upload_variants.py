#!/usr/bin/env python3
"""
Create the double/half-time variants (tempo_variant_pastes.jobs) straight in
the Hookpad library, instead of pasting 221 songs by hand.

    themap_venv/python hookpad_upload_variants.py --only oasis_wonderwall-170   # one song
    themap_venv/python hookpad_upload_variants.py --all --throttle 20           # the rest

It does what Hookpad's own "Save as" does (found in the app bundle):
    POST /v1/songs  {song: name, jsonData: <song JSON + fp>, cloudBackupsEnabled}
fp = SHA-1 of the compact JSON, the same checksum as the clipboard paste.
Then PATCH /v1/songs/{ID} {isPrivate: 1}, because every song in the library is
private and a plain POST may not be; then GET it back and check the notes and
tempo arrived. Each created song is logged to ~/Desktop/tempo_pastes/uploaded.json
(name, ID, slug), and a name already logged or already in the library is skipped,
so a rerun never makes duplicates.
"""
import argparse, hashlib, json, os, sys, time
import requests
from hashids import Hashids
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hookpad_token
import tempo_variant_pastes as T

API = 'https://api.hooktheory.com/v1'
LEDGER = os.path.expanduser('~/Desktop/tempo_pastes/uploaded.json')
HASH = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11,
               alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')


def js(o):
    return json.dumps(o, separators=(',', ':'), ensure_ascii=False)


def json_data(o):
    return js({**o, 'fp': hashlib.sha1(js(o).encode('utf-8')).hexdigest()})


def call(method, url, tok, **kw):
    if method == 'PATCH' and 'jsonData' in (kw.get('json') or {}):
        # our scripts write the Hookpad 2 shape; a song Hookpad 3 saved gets it
        # converted onto its live copy (hp3.from_hp2), keeping its instruments and tabs
        import hp3
        g = call('GET', url.split('?')[0] + '?fields=jsonData', tok)
        if g.status_code >= 300:
            raise RuntimeError(f'{url}: could not read the live song first ({g.status_code})')
        live = g.json().get('jsonData')
        if live and hp3.is_hp3(json.loads(live)):
            jd = kw['json']['jsonData']
            new = hp3.payload_for(live, json.loads(jd) if isinstance(jd, str) else jd)
            kw = {**kw, 'json': {**kw['json'], 'jsonData': new}}
            print('    (Hookpad 3 song: written in its format)')
    for wait in (0, 60, 180):
        if wait:
            print(f'    429, waiting {wait}s'); time.sleep(wait)
        for attempt in range(3):            # a timeout is retried; every call here is safe to repeat
            try:
                r = requests.request(method, url, headers={'authorization': f'Bearer {tok}'}, timeout=60, **kw)
                break
            except requests.exceptions.RequestException as e:
                if attempt == 2: raise
                print(f'    {type(e).__name__}, retrying in 20s'); time.sleep(20)
        if r.status_code != 429:
            return r
    return r


HP3_BASE = os.path.expanduser('~/Desktop/music/hookpad_songs_hp3/bob dylan_tangled up in blue.json')


def upload(tok, name, o, hp3_base=None):
    """Create a private song. hp3_base (a raw Hookpad 3 song, or True for HP3_BASE)
    makes it a Hookpad 3 song: o is laid onto that song's instruments and mixer
    (hp3.from_hp2), so the user's saves in Hookpad 3 update it in place, no copy."""
    if hp3_base:
        import hp3
        base = json.load(open(HP3_BASE)) if hp3_base is True else hp3_base
        jd = json.dumps(hp3.from_hp2({k: v for k, v in o.items() if k != 'fp'}, base), separators=(',', ':'), ensure_ascii=False)
    else:
        jd = json_data(o)
    r = call('POST', f'{API}/songs', tok, json={'song': name, 'jsonData': jd, 'cloudBackupsEnabled': True})
    if r.status_code >= 300:
        return None, f'POST {r.status_code}: {r.text[:300]}'
    resp = r.json()
    sid = resp.get('ID') or resp.get('id')
    if not sid:
        return None, f'POST ok but no ID in {str(resp)[:300]}'
    time.sleep(1)
    p = call('PATCH', f'{API}/songs/{sid}', tok, json={'isPrivate': 1})
    priv = p.status_code < 300
    time.sleep(1)
    slug = HASH.encode(int(sid))
    g = call('GET', f'{API}/songs/{slug}?fields=ID,song,jsonData,isPrivate', tok)
    got = g.json() if g.status_code < 300 else {}
    jd = got.get('jsonData')
    jd = json.loads(jd) if isinstance(jd, str) else (jd or {})
    import hp3
    jd = hp3.to_hp2(jd)
    ok = (len(jd.get('notes') or []) == len(o.get('notes') or [])
          and len(jd.get('chords') or []) == len(o.get('chords') or [])
          and (jd.get('tempos') or [{}])[0].get('bpm') == o['tempos'][0]['bpm'])
    return dict(name=name, ID=sid, slug=slug, private=str(got.get('isPrivate')) if got else priv,
                verified=ok, url=f'https://hookpad.hooktheory.com/?idOfUserSong={slug}'), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', action='append', help='variant name(s) to upload')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--throttle', type=float, default=20)
    ap.add_argument('--skip-fine', action='store_true', help='leave out halved songs that now have notes finer than a 16th')
    a = ap.parse_args()
    if not (a.only or a.all): ap.error('--only NAME or --all')

    tok = hookpad_token.read_saved()
    if not tok or call('GET', f'{API}/songs/h?per-page=1&page=1', tok).status_code == 401:
        print('token expired, fetching a fresh one')
        tok = hookpad_token.grab()
        if not tok: sys.exit('no token: the saved Hookpad login has expired, run setup_hookpad_auth.py')
        with open(hookpad_token.OUT, 'w') as f: f.write(tok + '\n')
        os.chmod(hookpad_token.OUT, 0o600)

    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else []
    done = {x['name'].lower() for x in ledger}
    jobs, _ = T.jobs()
    todo = [j for j in jobs if (a.all or j[1] in a.only) and j[1].lower() not in done]
    if a.skip_fine:
        todo = [j for j in todo if not (j[3] < 1 and T.off_grid(T.full_json(json.load(open(j[2])), j[3])))]
    print(f'{len(todo)} to create')
    for i, (sub, name, path, F, listed, hp) in enumerate(todo):
        if i: time.sleep(a.throttle)
        o = T.full_json(json.load(open(path)), F)
        rec, err = upload(tok, name, o)
        if err and 'POST 401' in err:
            # tokens last about an hour; a long batch outlives one
            print('    token expired, fetching a fresh one')
            tok = hookpad_token.grab()
            if tok:
                with open(hookpad_token.OUT, 'w') as f: f.write(tok + '\n')
                os.chmod(hookpad_token.OUT, 0o600)
                rec, err = upload(tok, name, o)
        if err:
            print(f'  FAIL {name}: {err}');
            if 'POST 401' in err or 'POST 403' in err: break
            continue
        rec.update(sub=sub, factor=F, from_bpm=hp)
        ledger.append(rec); json.dump(ledger, open(LEDGER, 'w'), indent=1)
        print(f'  [{i + 1}/{len(todo)}] {name}  ID {rec["ID"]}  private={rec["private"]}  verified={rec["verified"]}')


if __name__ == '__main__':
    main()
