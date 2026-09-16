"""For covers whose melody track came out wrong, download SEVERAL candidate MIDIs
(all midis101 matches), score each one's best melody track, and keep the source
whose melody line is a named vocal/lead with a sensible note count. Writes the
winner's isolated melody MIDI to the cover-melodies folder.
"""
import os, re, sys, time, urllib.parse, requests
import mido
from midi_melody_extract import score_track, monophony_ratio
from beatles_cover_melody_midis import meta_track, OUT

os.makedirs(OUT, exist_ok=True)
CAND = os.path.expanduser('~/Desktop/_midi_candidates')
os.makedirs(CAND, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA})

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

STOP = {'and', 'the', 'a', 'of', 'to', 'me', 'my', 'in'}
def tokens(title):
    return [w for w in re.findall(r'[a-z0-9]+', title.lower()) if w not in STOP and len(w) > 2]

def token_match(title, name):
    """Most significant title words present in the candidate name (n<->and safe)."""
    nn = norm(name).replace('rocknroll', 'rockandroll')
    toks = tokens(title)
    hit = sum(1 for t in toks if t in nn)
    return hit >= max(2, len(toks) - 1)

def candidates(title):
    """(url, label) from midis101 + bitmidi."""
    out = []
    try:
        r = S.get(f'https://midis101.com/search/{urllib.parse.quote(title+" beatles")}', timeout=12)
        for mid, slug in re.findall(r'href="/free-midi/(\d+)-([^"]+)"', r.text):
            if norm(title) in norm(slug):
                out.append((f'https://midis101.com/download/{mid}-{slug}', slug));
    except Exception: pass
    try:
        j = S.get('https://bitmidi.com/api/midi/search', params={'q': 'beatles ' + title}, timeout=15).json()
        for x in j.get('result', {}).get('results', []):
            if x.get('downloadUrl') and token_match(title, x.get('name', '')):
                out.append(('https://bitmidi.com' + x['downloadUrl'], x['name']))
    except Exception: pass
    return out[:8]

def download(url, dest):
    try: r = S.get(url, timeout=20)
    except Exception: return False
    if r.status_code != 200 or r.content[:4] != b'MThd': return False
    open(dest, 'wb').write(r.content); return True

def evaluate(path):
    """Return the best melody track's (score, name, notes, mono, named) or None."""
    try: mid = mido.MidiFile(path)
    except Exception: return None
    tpb = mid.ticks_per_beat
    scored = [score_track(tr, tpb) for tr in mid.tracks]
    best = max(range(len(scored)), key=lambda i: scored[i][0])
    sc, notes = scored[best]
    if sc < 0 or not notes: return None
    name = ' '.join(m.name for m in mid.tracks[best] if m.type == 'track_name') or '(unnamed)'
    named = any(k in name.lower() for k in ('vocal', 'melody', 'lead', 'voice', 'sing'))
    return {'path': path, 'best': best, 'score': sc, 'name': name,
            'notes': len(notes), 'mono': monophony_ratio(notes), 'named': named}

def quality(c):
    # prefer: named vocal/lead, note count in a real melody range, high monophony
    good_len = 70 <= c['notes'] <= 450
    return (c['named'], good_len, round(c['mono'], 2), c['score'])

def main(songs):
    for title in songs:
        cands = []
        seen = set()
        for i, (url, label) in enumerate(candidates(title)):
            dest = os.path.join(CAND, f'{norm(title)}_{i}.mid')
            if download(url, dest):
                key = os.path.getsize(dest)
                if key in seen:      # skip byte-identical dupes
                    continue
                seen.add(key)
                ev = evaluate(dest)
                if ev: ev['slug'] = label; cands.append(ev)
            time.sleep(1.5)
        if not cands:
            print(f'{title:30} — no usable candidates'); continue
        cands.sort(key=quality, reverse=True)
        w = cands[0]
        print(f'\n{title}')
        for c in cands:
            tag = ' <-- picked' if c is w else ''
            print(f'   {c["name"][:22]:22} notes={c["notes"]:>4} mono={c["mono"]:.0%} named={c["named"]}{tag}')
        # write winner
        mid = mido.MidiFile(w['path']); new = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
        new.tracks.append(meta_track(mid)); new.tracks.append(mid.tracks[w['best']])
        new.save(os.path.join(OUT, norm(title) + '_melody.mid'))
        print(f'   -> wrote {norm(title)}_melody.mid')

if __name__ == '__main__':
    songs = sys.argv[1:] or ["rock and roll music", "words of love", "please mister postman", "long tall sally"]
    main(songs)
