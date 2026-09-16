"""Build hookpad_images/beatles2/ — one folder per Beatles recording session (the 12 UK
studio albums), each containing a subfolder per song for dropping Hookpad screenshots into.

Full canonical UK album tracklists + non-album singles/B-sides folded into their era.
Reports which songs are already in the user's Hookpad library (from beatles_proj.json) vs
still to screenshot. Safe to re-run: rebuilds the empty scaffolding, never touches images
that already exist in a folder (rmtree only runs on a fully-empty tree — see KEEP_IMAGES).

  <venv>/bin/python build_beatles2_folders.py
"""
import re, os, shutil, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(HERE), 'hookpad_images', 'beatles2')
# real Hookpad library = the fresh API export (~246 beatles JSONs); NOT the stale proj map
HOOKPAD_DIR = os.path.expanduser('~/Desktop/music/hookpad_songs_full')

# ---- songs already in Hookpad, normalised to folder-name style ----
def norm(fn):
    s = os.path.basename(fn)[:-5] if fn.endswith('.json') else fn
    s = s[8:] if s.lower().startswith('beatles_') else s
    s = s.lower().strip().strip('_').strip()
    s = re.sub(r'-(mixolydian|right|double|completed|simple|hooktab|c|150|wrong)$', '', s)
    s = re.sub(r'-[0-9a-f]{6}$', '', s)
    s = re.sub(r'(_ly)?(_o)?(_completed)?_?$', '', s)
    s = re.sub(r'-1$', '', s); s = re.sub(r'2$', '', s)
    s = s.replace('!', '').replace('?', '').replace('.', '').replace(',', '').replace("'", '')
    toks = s.replace('-', ' ').split(); out = []
    for t in toks:
        if t in {'s', 't', 'm', 've', 're', 'd', 'll'} and out: out[-1] += t
        else: out.append(t)
    s = ' '.join(out)
    alias = {'dr robert': 'doctor robert', 'benefit of mr kite': 'being for the benefit of mr kite',
             'all ive got to do': 'all ive gotta do', 'obladioblada': 'ob-la-di ob-la-da',
             'ob la di ob la da': 'ob-la-di ob-la-da', 'sgt pepper': 'sgt peppers lonely hearts club band',
             'sgt peppers': 'sgt peppers lonely hearts club band'}
    return alias.get(s, s)

HAVE = set(norm(f) for f in glob.glob(os.path.join(HOOKPAD_DIR, 'beatles*.json')))

# ---- canonical UK studio-album tracklists (folder-name style) ----
ALBUMS = {
 1: ("Please Please Me", ["i saw her standing there","misery","anna","chains","boys","ask me why",
    "please please me","love me do","ps i love you","baby its you","do you want to know a secret",
    "a taste of honey","theres a place","twist and shout"]),
 2: ("With The Beatles", ["it wont be long","all ive gotta do","all my loving","dont bother me",
    "little child","till there was you","please mister postman","roll over beethoven","hold me tight",
    "you really got a hold on me","i wanna be your man","devil in her heart","not a second time","money"]),
 3: ("A Hard Days Night", ["a hard days night","i should have known better","if i fell",
    "im happy just to dance with you","and i love her","tell me why","cant buy me love","any time at all",
    "ill cry instead","things we said today","when i get home","you cant do that","ill be back"]),
 4: ("Beatles For Sale", ["no reply","im a loser","babys in black","rock and roll music","ill follow the sun",
    "mr moonlight","kansas city hey hey hey hey","eight days a week","words of love","honey dont",
    "every little thing","i dont want to spoil the party","what youre doing","everybodys trying to be my baby"]),
 5: ("Help", ["help","the night before","youve got to hide your love away","i need you","another girl",
    "youre going to lose that girl","ticket to ride","act naturally","its only love","you like me too much",
    "tell me what you see","ive just seen a face","yesterday","dizzy miss lizzy"]),
 6: ("Rubber Soul", ["drive my car","norwegian wood","you wont see me","nowhere man","think for yourself",
    "the word","michelle","what goes on","girl","im looking through you","in my life","wait",
    "if i needed someone","run for your life"]),
 7: ("Revolver", ["taxman","eleanor rigby","im only sleeping","love you to","here there and everywhere",
    "yellow submarine","she said she said","good day sunshine","and your bird can sing","for no one",
    "doctor robert","i want to tell you","got to get you into my life","tomorrow never knows"]),
 8: ("Sgt Peppers", ["sgt peppers lonely hearts club band","with a little help from my friends",
    "lucy in the sky with diamonds","getting better","fixing a hole","shes leaving home",
    "being for the benefit of mr kite","within you without you","when im sixty four","lovely rita",
    "good morning good morning","sgt peppers reprise","a day in the life"]),
 9: ("Magical Mystery Tour", ["magical mystery tour","the fool on the hill","flying","blue jay way",
    "your mother should know","i am the walrus","hello goodbye","strawberry fields forever","penny lane",
    "baby youre a rich man","all you need is love"]),
 10: ("White Album", ["back in the ussr","dear prudence","glass onion","ob-la-di ob-la-da","wild honey pie",
    "the continuing story of bungalow bill","while my guitar gently weeps","happiness is a warm gun",
    "martha my dear","im so tired","blackbird","piggies","rocky raccoon","dont pass me by",
    "why dont we do it in the road","i will","julia","birthday","yer blues","mother natures son",
    "everybodys got something to hide except me and my monkey","sexy sadie","helter skelter","long long long",
    "revolution 1","honey pie","savoy truffle","cry baby cry","revolution 9","good night"]),
 11: ("Let It Be", ["two of us","dig a pony","across the universe","i me mine","dig it","let it be",
    "maggie mae","ive got a feeling","one after 909","the long and winding road","for you blue","get back"]),
 12: ("Abbey Road", ["come together","something","maxwells silver hammer","oh darling","octopuss garden",
    "i want you shes so heavy","here comes the sun","because","you never give me your money","sun king",
    "mean mr mustard","polythene pam","she came in through the bathroom window","golden slumbers",
    "carry that weight","the end","her majesty"]),
}

# ---- non-album singles / B-sides, folded into their recording-era album ----
SINGLES = {
 1: ["from me to you","thank you girl"],
 2: ["she loves you","ill get you","i want to hold your hand","this boy"],
 4: ["i feel fine","shes a woman"],
 5: ["yes it is","im down"],
 6: ["day tripper","we can work it out"],
 7: ["paperback writer","rain"],
 10: ["lady madonna","the inner light","hey jude","revolution","dont let me down"],
 11: ["you know my name look up the number"],
 12: ["the ballad of john and yoko","old brown shoe"],
}

def song_folders(num):
    """(folder_name, match_name) pairs: album tracks numbered by position, singles unnumbered."""
    pairs = [(f"{i:02d}_{t}", t) for i, t in enumerate(ALBUMS[num][1], 1)]
    pairs += [(t, t) for t in SINGLES.get(num, [])]   # singles: no track number
    return pairs

def main():
    # only wipe if the tree has no image files (protect any screenshots already dropped in)
    if os.path.isdir(ROOT):
        imgs = any(f.lower().endswith(('.png','.jpg','.jpeg'))
                   for _,_,fs in os.walk(ROOT) for f in fs)
        if imgs:
            print("beatles2 already contains images — adding missing folders only, not wiping.")
        else:
            shutil.rmtree(ROOT)

    tot = have = 0
    for num in sorted(ALBUMS):
        name = ALBUMS[num][0]; folder = f"{num:02d} {name}"
        pairs = song_folders(num)
        for fname, mname in pairs:
            os.makedirs(os.path.join(ROOT, folder, fname), exist_ok=True)
        h = sum(1 for _, mname in pairs if mname in HAVE)
        s = len(SINGLES.get(num, []))
        tot += len(pairs); have += h
        note = f" (+{s} single{'s' if s != 1 else ''})" if s else ""
        print(f"{folder:26} {len(pairs):>2} songs{note:14} · have {h:>2} · need {len(pairs)-h:>2}")
    print(f"\nTOTAL {tot} songs · in Hookpad {have} · to screenshot {tot-have}")
    print(f"Root: {ROOT}")

if __name__ == '__main__':
    main()
