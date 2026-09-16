"""Scrape UG chord tabs for the guitar songs missing a local txt.

Reads ~/Desktop/guitar_missing_ug.csv, searches UG (logged in via ~/Desktop/.ug_auth.json),
picks a text-extractable CHORDS tab, extracts the rendered text + Key, saves to
~/Desktop/music/ug_tabs/<artist>_<title>.txt. Throttled + Cloudflare-challenge tolerant.
"""
import os, re, csv, time
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
OUT=os.path.expanduser('~/Desktop/music/ug_tabs'); os.makedirs(OUT,exist_ok=True)
AUTH=os.path.expanduser('~/Desktop/.ug_auth.json')
MISS=os.path.expanduser('~/Desktop/guitar_missing_ug.csv')
SUMMARY=os.path.expanduser('~/Desktop/ug_scrape_missing_summary.csv')
try:
    from playwright_stealth import Stealth; S=Stealth()
except Exception: S=None
from playwright.sync_api import sync_playwright

def blocked(t):
    l=t.lower(); return 'security verification' in l or 'just a moment' in l or 'verifies you are not a bot' in l
def fetch(pg,url,min_len=600):
    try: pg.goto(url,wait_until='domcontentloaded',timeout=30000)
    except Exception: return ''
    for _ in range(8):
        pg.wait_for_timeout(2500)
        t=pg.inner_text('body')
        if not blocked(t) and len(t)>min_len: return t
    return pg.inner_text('body')
def keyof(t):
    m=re.search(r'Key:\s*([A-G][#b]?m?)',t); return m.group(1) if m else None
def fname_from_url(u):
    m=re.search(r'/tab/([^/]+)/([^/]+?)-(?:chords|tabs|official|guitar-pro|ukulele|bass|drums)-\d+',u)
    if not m: return None
    return f"{m.group(1)}_{m.group(2)}"

rows=list(csv.DictReader(open(MISS)))
print(f'{len(rows)} songs to scrape',flush=True)
res=[]
ctxmgr = S.use_sync(sync_playwright()) if S else sync_playwright()
with ctxmgr as p:
    b=p.chromium.launch(headless=True)
    ctx=b.new_context(storage_state=AUTH,user_agent=UA,viewport={'width':1400,'height':1000})
    pg=ctx.new_page()
    for i,r in enumerate(rows,1):
        art=(r.get('artist') or '').strip(); tit=(r.get('title') or '').strip()
        q=f"{tit} {art}".replace(' ','%20')
        try:
            html=fetch(pg,'https://www.ultimate-guitar.com/search.php?search_type=title&value='+q,min_len=200)
            urls=re.findall(r'https://tabs\.ultimate-guitar\.com/tab/[^"\\\s]+',pg.content())
            seen=[]; [seen.append(u.split('?')[0]) for u in urls if u.split('?')[0] not in seen]
            chords=[u for u in seen if '-chords-' in u]
            target=(chords or [u for u in seen if '-tabs-' in u] or seen or [None])[0]
        except Exception as e:
            target=None
        if not target:
            print(f'[{i}/{len(rows)}] NO MATCH  {art} — {tit}',flush=True)
            res.append({'artist':art,'title':tit,'status':'no_match','url':'','key':'','chars':0}); time.sleep(3); continue
        txt=fetch(pg,target)
        fn=fname_from_url(target) or re.sub(r'[^a-z0-9_-]','-',f"{art}_{tit}".lower())
        if blocked(txt) or len(txt)<400:
            print(f'[{i}/{len(rows)}] BLOCKED/THIN  {art} — {tit}',flush=True)
            res.append({'artist':art,'title':tit,'status':'blocked','url':target,'key':'','chars':len(txt)}); time.sleep(4); continue
        open(os.path.join(OUT,fn+'.txt'),'w').write(txt)
        k=keyof(txt)
        print(f'[{i}/{len(rows)}] OK {fn}.txt  Key={k}  {len(txt)}b',flush=True)
        res.append({'artist':art,'title':tit,'status':'ok','url':target,'key':k or '','chars':len(txt)})
        time.sleep(3.5)   # throttle
    b.close()
with open(SUMMARY,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['artist','title','status','url','key','chars']); w.writeheader(); [w.writerow(x) for x in res]
ok=sum(1 for x in res if x['status']=='ok')
print(f'\nDONE: {ok}/{len(rows)} saved | summary -> {SUMMARY}',flush=True)
