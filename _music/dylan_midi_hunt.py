"""Hunt Bob Dylan MIDIs across midis101 + bitmidi for a broad title list, so the
whole catalog can be imported into Hookpad to study his song structures.
Downloads one good full MIDI per song to ~/Desktop/dylan_midis/.
"""
import os, re, time, urllib.parse, requests
OUT = os.path.expanduser('~/Desktop/dylan_midis')
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'
S = requests.Session(); S.headers.update({'User-Agent': UA})
STOP = {'and', 'the', 'a', 'of', 'to', 'me', 'my', 'in', 'on', 'you', 'it', 'its', 'im'}

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def toks(t): return [w for w in re.findall(r'[a-z0-9]+', t.lower()) if w not in STOP and len(w) > 2]
def token_match(title, name):
    nn = norm(name).replace('rocknroll', 'rockandroll')
    tk = toks(title)
    return sum(1 for t in tk if t in nn) >= max(2, len(tk) - 1)

def candidates(title):
    dylan_first, rest = [], []
    try:
        r = S.get(f'https://midis101.com/search/{urllib.parse.quote(title)}', timeout=12)
        for mid, slug in re.findall(r'href="/free-midi/(\d+)-([^"]+)"', r.text):
            if norm(title) in norm(slug):
                u = f'https://midis101.com/download/{mid}-{slug}'
                (dylan_first if 'dylan' in norm(slug) else rest).append(u)
    except Exception: pass
    for q in ('dylan ' + title, title):
        try:
            j = S.get('https://bitmidi.com/api/midi/search', params={'q': q}, timeout=15).json()
            for x in j.get('result', {}).get('results', []):
                if x.get('downloadUrl') and token_match(title, x.get('name', '')):
                    u = 'https://bitmidi.com' + x['downloadUrl']
                    (dylan_first if 'dylan' in norm(x.get('name', '')) else rest).append(u)
        except Exception: pass
    return dylan_first + rest

def get(url, dest):
    try: r = S.get(url, timeout=20)
    except Exception: return False
    if r.status_code != 200 or r.content[:4] != b'MThd': return False
    open(dest, 'wb').write(r.content); return True

DYLAN = [
 "blowin in the wind","a hard rains a gonna fall","the times they are a changin","masters of war",
 "dont think twice its alright","girl from the north country","it aint me babe","mr tambourine man",
 "chimes of freedom","my back pages","all i really want to do","subterranean homesick blues",
 "maggies farm","its all over now baby blue","like a rolling stone","ballad of a thin man",
 "desolation row","highway 61 revisited","queen jane approximately","just like tom thumbs blues",
 "rainy day women","positively 4th street","visions of johanna","stuck inside of mobile","i want you",
 "just like a woman","most likely you go your way","sad eyed lady of the lowlands","all along the watchtower",
 "ill be your baby tonight","lay lady lay","i threw it all away","tangled up in blue","simple twist of fate",
 "youre a big girl now","idiot wind","youre gonna make me lonesome when you go","shelter from the storm",
 "buckets of rain","hurricane","isis","one more cup of coffee","oh sister","knockin on heavens door",
 "forever young","if not for you","i shall be released","the mighty quinn","man in the long black coat",
 "not dark yet","things have changed","make you feel my love","love minus zero","to ramona",
 "boots of spanish leather","she belongs to me","mama you been on my mind","its alright ma",
 "fourth time around","the lonesome death of hattie carroll","ballad of hollis brown","with god on our side",
 "when the ship comes in","political world","series of dreams","what was it you wanted",
]

def main():
    found = miss = 0
    for i, title in enumerate(DYLAN, 1):
        dest = os.path.join(OUT, norm(title) + '.mid')
        if os.path.exists(dest):
            found += 1; continue
        ok = False
        for url in candidates(title):
            if get(url, dest):
                ok = True; break
            time.sleep(1)
        print(f'  [{i}/{len(DYLAN)}] {title[:40]:40} {"ok" if ok else "-- not found"}')
        found += ok; miss += (not ok)
        time.sleep(1.5)
    print(f'\n{found}/{len(DYLAN)} Dylan MIDIs -> {OUT}')

if __name__ == '__main__':
    main()
