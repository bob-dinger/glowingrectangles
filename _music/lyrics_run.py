"""The bulk lyrics run: write lyrics_fill.py's fills and cleans into the Hookpad songs.

    lyrics_run.py --limit 10      # the first 10 not yet done
    lyrics_run.py                 # everything left (resumes from the log)
    lyrics_run.py --only clean    # or --only fill

Per song: GET the live copy (never the local file, so edits since the last sync
survive), back it up to ~/Desktop/music/superseded/lyrics1116/, skip it unless it
is private (lyrics are copyrighted), fill or clean it, PATCH it back, and update
the local copy in hookpad_songs_full. A fill is written only when at least half of
the lyric lines inside the charted melody were placed (MIN_FIT); the rest are
logged as 'weak' for a later look. Tokens come from hookpad_token.grab() (the
saved login) and are refreshed on a 401. ~10 s per song; log in
~/Desktop/music/lyrics_run.json, one entry per song.
"""
import argparse, json, os, sys, time
import lyrics_fill as L
import corpus as C
import hookpad_token
import hp3
from hookpad_upload_variants import call, json_data, API
from hashids import Hashids

M = os.path.expanduser('~/Desktop/music')
BACK = f'{M}/superseded/lyrics1116'
LOG = f'{M}/lyrics_run.json'
PACE = 5.0
MIN_FIT = .5
HASH = Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')


class Tok:
    def __init__(self):
        self.t = hookpad_token.read_saved(); self.at = 0
    def refresh(self):
        t = hookpad_token.grab()
        if not t: sys.exit('could not get a token from the saved login: stopping')
        self.t = t; self.at = time.time()
        open(os.path.expanduser('~/.hookpad_token'), 'w').write(t); os.chmod(os.path.expanduser('~/.hookpad_token'), 0o600)
    def req(self, method, url, **kw):
        if time.time() - self.at > 45 * 60: self.refresh()
        r = call(method, url, self.t, **kw)
        if r.status_code == 401:
            self.refresh(); r = call(method, url, self.t, **kw)
        if r.status_code == 429: sys.exit('429 from Hookpad after backoff: stopping')
        return r


def song_ids(tok):
    allsongs, page = [], 1
    while True:
        r = tok.req('GET', f'{API}/songs/h?per-page=100&page={page}')
        r.raise_for_status(); data = r.json()
        allsongs += data
        if len(data) < 100: break
        page += 1; time.sleep(3)
    # Hookpad names were lowercased; local files keep old case. Two songs under one
    # name = a Hookpad 3 save beside its original: the newest is the live one.
    return {s['song'].replace('/', '_').lower(): s['ID']
            for s in hp3.newest_per_name(allsongs, key=lambda s: s['song'].replace('/', '_').lower())}


def plan(only):
    idx = L.lyric_index()
    todo = []
    if only in (None, 'fill'):
        for name, d, j, rb in L.targets(idx):
            todo.append(('fill', name, j, rb))
    if only in (None, 'clean'):
        for name, d, nb in C.songs(need_chords=False):
            if L.has_lyrics(d) and L.clean(json.loads(json.dumps(d)))[1]:
                todo.append(('clean', name, None, None))
    return todo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--only', choices=['fill', 'clean'])
    a = ap.parse_args()
    os.makedirs(BACK, exist_ok=True)
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    todo = [x for x in plan(a.only) if x[1] not in log]
    if a.limit: todo = todo[:a.limit]
    print(f'{len(todo)} songs to do ({sum(x[0] == "fill" for x in todo)} fill, {sum(x[0] == "clean" for x in todo)} clean); {len(log)} done before', flush=True)
    tok = Tok(); tok.refresh()
    ids = song_ids(tok)
    t0 = time.time()
    for i, (kind, name, j, rb) in enumerate(todo, 1):
        rec = {'kind': kind, 'at': time.strftime('%Y-%m-%d %H:%M')}
        sid = ids.get(name.lower())
        if not sid:
            rec['status'] = 'no id'
        else:
            r = tok.req('GET', f'{API}/songs/{HASH.encode(sid)}?fields=ID,jsonData,isPrivate')
            if r.status_code != 200:
                rec['status'] = f'get {r.status_code}'
            else:
                g = r.json(); raw = g.get('jsonData')
                if not raw:
                    rec['status'] = 'empty'
                elif str(g.get('isPrivate')) not in ('1', 'True', 'true'):
                    rec['status'] = 'public, skipped'
                else:
                    d = hp3.to_hp2(json.loads(raw))     # a Hookpad 3 song is read in the old shape
                    open(f'{BACK}/{name}.json', 'w').write(raw)
                    out = None
                    if kind == 'fill':
                        if L.has_lyrics(d):
                            rec['status'] = 'has lyrics now'
                        else:
                            f, err = L.fill(d, j, rb)
                            if err: rec['status'] = err
                            else:
                                inside = max(f['fit']['inside'], 1)
                                rec.update(lines=f['lines'], inside=f['fit']['inside'], written=f['fitted'])
                                if f['fitted'] / inside < MIN_FIT: rec['status'] = 'weak'
                                else:
                                    secs, texts = L.section_texts(d, f['notes'], f['tok'], f['starts'])
                                    out = L.apply(d, secs, texts)
                    else:
                        out, n = L.clean(d)
                        if not n: rec['status'] = 'nothing to clean'; out = None
                    if out is not None:
                        p = tok.req('PATCH', f'{API}/songs/{sid}', json={'jsonData': hp3.payload_for(raw, out) or json_data(out)})
                        rec['status'] = 'written' if p.status_code == 200 else f'patch {p.status_code}'
                        if p.status_code == 200:
                            json.dump(out, open(f'{M}/hookpad_songs_full/{name}.json', 'w'), ensure_ascii=False)
        log[name] = rec
        json.dump(log, open(LOG, 'w'), indent=0)
        if i % 10 == 0 or i == len(todo):
            el = time.time() - t0
            st = {}
            for v in log.values(): st[v['status']] = st.get(v['status'], 0) + 1
            print(f'[{i}/{len(todo)}] {el / 60:.0f} min, ~{(len(todo) - i) * el / i / 60:.0f} left  ' +
                  '  '.join(f'{k}:{v}' for k, v in sorted(st.items())), flush=True)
        time.sleep(PACE)


if __name__ == '__main__':
    main()
