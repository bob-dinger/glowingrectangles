import os,json,re,time,requests
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2
def slug(s):
    s=(s or '').lower().replace('&','and')
    s=re.sub(r"[.'’]","",s); s=re.sub(r"[^a-z0-9]+","-",s).strip('-'); return s
def exists(u):
    try:
        r=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=15,allow_redirects=True)
        return r.status_code
    except Exception: return 0
c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432)); cur=c.cursor()
cur.execute(r"""select title,artist,slug from parcels.songs where hookpad_json is not null
  and coalesce(jsonb_array_length(hookpad_json->'chords'),0)=0
  and slug not like 'beatles_%' and slug not like 'mine\_%' order by lower(artist),lower(title)""")
songs=cur.fetchall(); c.close()
res={}; found=0; errs=0
for i,(title,artist,sg) in enumerate(songs,1):
    a=slug(artist); t=slug(title); cands=[f"{a}/{t}"]
    cands.append((f"the-{a}/{t}") if not a.startswith('the-') else f"{a[4:]}/{t}")
    hit=None
    for cand in cands:
        u=f"https://www.hooktheory.com/theorytab/view/{cand}"
        code=exists(u); time.sleep(0.5)
        if code==200: hit=u; break
        if code in (403,429): errs+=1
    if hit: found+=1
    res[sg]={'found':bool(hit),'url':hit or ''}
    if i%50==0:
        print(f"{i}/{len(songs)} checked, {found} in theorytab, {errs} blocks",flush=True)
        json.dump(res,open('/tmp/theorytab_results.json','w'))
        if errs>20: print("too many blocks, stopping");break
json.dump(res,open('/tmp/theorytab_results.json','w'))
print(f"DONE: {found}/{len(songs)} no-chord songs are in TheoryTab")
