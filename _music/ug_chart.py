"""Preview the UG-tab side of the fusion: parse each song's UG tab into
sections + chord sequences + inferred key. Shows what the 'chart' half gives us
before we fuse in MIDI timing.
"""
import os, re, glob, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from parse_ug import parse_tab, infer_key

NOISE={'the','a','of'}
def toks(s):
    s=re.sub(r'\.txt$','',s,flags=re.I); s=re.sub(r'[_\-\s]+',' ',s.lower()); s=re.sub(r"[^a-z0-9 ]",'',s)
    return [t for t in s.split() if t and t not in NOISE and not t.isdigit()]
UG=glob.glob(os.path.expanduser('~/Desktop/music/ug_tabs/*.txt'))
UGIDX=[(p, ''.join(toks(os.path.basename(p))), set(toks(os.path.basename(p)))) for p in UG]
def find_ug(artist,title):
    at=set(toks(artist or '')); asq=''.join(toks(artist or '')); tsq=''.join(toks(title or ''))
    if len(tsq)<4: return None
    cands=[p for p,sq,tk in UGIDX if tsq in sq and (asq[:5] in sq or (at & tk)) and 'verse' not in os.path.basename(p).lower() and 'chorus' not in os.path.basename(p).lower()]
    return min(cands,key=lambda p:len(os.path.basename(p))) if cands else (UGIDX and next((p for p,sq,tk in UGIDX if tsq in sq and (asq[:5] in sq or at&tk)),None))

def chart(path):
    meta, secs = parse_tab(open(path, encoding='utf-8', errors='replace').read())
    key = infer_key(secs)
    out=[]
    for s in secs:
        chords=[]
        for kind,pl in s.get('events',[]):
            if kind=='chord_line':
                for cn,_ in pl:
                    if not chords or chords[-1]!=cn: chords.append(cn)
        if chords: out.append((s.get('name') or '(section)', chords))
    return key, out

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor(); cur.execute("select artist,title from parcels.songs where not has_chords and has_melody and in_hookpad and artist is not null")
    rows=cur.fetchall(); c.close()
    targets=['september','mrs robinson','pinball wizard','celebration','mustang sally',
             'the cave','lullaby','wont get fooled','my generation','september']
    seen=set()
    for tg in targets:
        row=next((r for r in rows if tg in (r[1] or '').lower()),None)
        if not row or row[1] in seen: continue
        seen.add(row[1])
        p=find_ug(*row)
        if not p: print(f'\n### {row[0]} - {row[1]}: NO UG TAB'); continue
        key,secs=chart(p)
        print(f'\n### {row[0]} - {row[1]}   [key {key[0]} {key[1]}]  ({os.path.basename(p)})')
        # dedupe consecutive identical sections
        prev=None
        for name,ch in secs[:10]:
            line=f'{name}: {" ".join(ch[:14])}'
            if line!=prev: print(f'  {line}')
            prev=line

if __name__=='__main__':
    main()
