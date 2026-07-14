"""Key-changes browser. Groups every genuine modulation in the library by TYPE
(parallel flip, relative minor/major, up-a-whole-step, up-a-minor-third, to V, ...)
and lists the songs that make that move. Sidebar = move types ranked by count,
panel = songs (with the specific from->to, full path, returns-home flag, UG/HP links).

Writes _music/key-changes.html.
"""
import os, re, json, psycopg2
from collections import defaultdict
from urllib.parse import quote_plus
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,
    'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
PCN=['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B']
def kname(pc,mode): return PCN[pc]+('m' if mode=='minor' else '')
def norm(s): return re.sub(r'[^a-z0-9]','',(s or '').lower())

def collapse(ks):
    out=[]
    for k in ks:
        pc=PC.get(k.get('tonic'),-1)
        if pc<0: continue
        s=(pc,'minor' if k.get('scale')=='minor' else 'major')
        if not out or out[-1]!=s: out.append(s)
    return out

# move classification -> (key, human label, rank-order)
def classify(a,b):
    dp=(b[0]-a[0])%12; same=a[1]==b[1]
    if not same:
        if dp==0: return ('parallel','parallel flip (same tonic, major↔minor)')
        if a[1]=='major' and dp==9: return ('rel_min','to the relative minor')
        if a[1]=='minor' and dp==3: return ('rel_maj','to the relative major')
        return ('flip_'+str(dp), f'mode change + {dp} semitones')
    m={1:('up_half','up a half step'),2:('up_whole','up a whole step'),
       3:('up_m3','up a minor third (♭III mediant)'),4:('up_M3','up a major third'),
       5:('to_IV','to IV (down a fifth)'),6:('tritone','tritone'),
       7:('to_V','to V (up a fifth)'),8:('down_M3','down a major third'),
       9:('down_m3','down a minor third'),10:('down_whole','down a whole step'),
       11:('down_half','down a half step')}
    return m.get(dp,('other_'+str(dp), f'+{dp} semitones'))

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor()
    cur.execute("select artist,title,hookpad_json,ug_url,hookpad_url from parcels.songs where has_chords and hookpad_json is not null")
    rows=cur.fetchall(); c.close()

    # dedupe by (artist, base-title) keeping the longest journey
    best={}
    for a,t,hj,ug,hp in rows:
        if not t: continue
        seq=collapse(hj.get('keys') or [])
        if len(seq)<2: continue
        base=re.sub(r'-(hooktab|simple|C|150|right|wrong|mixolydian)$','',t.strip(),flags=re.I)
        k=(norm(a),norm(base))
        if k not in best or len(seq)>len(best[k][2]):
            ug2=(ug or '').strip() or ('https://www.ultimate-guitar.com/search.php?search_type=title&value='+quote_plus(f"{a or ''} {base}".strip()))
            best[k]=(a or '', base, seq, ug2, (hp or '').strip())

    groups=defaultdict(list); labels={}
    for a,base,seq,ug,hp in best.values():
        path=' → '.join(kname(*s) for s in seq)
        home = seq[0]==seq[-1]
        seen=set()
        for i in range(len(seq)-1):
            gk,lab=classify(seq[i],seq[i+1]); labels[gk]=lab
            if gk in seen: continue
            seen.add(gk)
            move=f"{kname(*seq[i])} → {kname(*seq[i+1])}"
            groups[gk].append({'a':a,'t':base,'move':move,'path':path,'home':home,'ug':ug,'hp':hp})

    types=[]
    for gk,songs in groups.items():
        songs.sort(key=lambda s:(s['a'].lower(),s['t'].lower()))
        types.append({'key':gk,'label':labels[gk],'n':len(songs),'songs':songs})
    types.sort(key=lambda x:-x['n'])
    data={'types':types,'total':len(best)}
    out=os.path.join(os.path.dirname(__file__),'key-changes.html')
    open(out,'w').write(PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False)))
    print(f"wrote {out}  |  {len(best)} key-changing songs, {len(types)} move types")

PAGE=r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Key Changes</title>
<style>
  html,body{margin:0;height:100vh;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333;background:#fff}
  #wrap{display:flex;height:100vh}
  #side{width:320px;flex:0 0 320px;border-right:1px solid #eee;overflow-y:auto}
  #side h1{font-size:16px;margin:14px 16px 4px}
  #side .sub{font-size:12px;color:#999;margin:0 16px 10px}
  .trow{display:flex;justify-content:space-between;align-items:center;padding:9px 16px;cursor:pointer;border-bottom:1px solid #f4f4f7;font-size:13px}
  .trow:hover{background:#f8f8fc}
  .trow.on{background:#2a2a44;color:#fff}
  .trow .ct{font-weight:700;color:#aaa;font-size:12px}
  .trow.on .ct{color:#cfd}
  #main{flex:1;overflow-y:auto;padding:18px 22px}
  #hd{font-size:18px;font-weight:700;margin-bottom:2px}
  #sub2{color:#888;font-size:13px;margin-bottom:12px}
  table{border-collapse:collapse;width:100%}
  td,th{text-align:left;padding:5px 10px;border-bottom:1px solid #eee;font-size:13px}
  th{color:#999;font-size:11px;text-transform:uppercase}
  .move{font-weight:700;color:#4060c0;white-space:nowrap}
  .path{color:#777;font-size:12px}
  .home{color:#2a9d5a;font-weight:700}
  .lk{font-size:10px;font-weight:700;text-decoration:none;border-radius:4px;padding:2px 6px;margin-right:4px;color:#fff}
  .lk.ug{background:#c8600f}.lk.hp{background:#5090f0}.lk.off{background:#eee;color:#bbb}
</style></head><body>
<div id="wrap">
  <div id="side"><h1>Key Changes</h1><div class="sub" id="sub"></div><div id="list"></div></div>
  <div id="main"><div id="hd"></div><div id="sub2"></div><div id="body"></div></div>
</div>
<script>
const D=__DATA__;
const L=document.getElementById('list');
document.getElementById('sub').textContent=`${D.total} songs that change key`;
D.types.forEach((t,i)=>{const r=document.createElement('div');r.className='trow';r.dataset.i=i;
  r.innerHTML=`<span>${t.label}</span><span class=ct>${t.n}</span>`;r.onclick=()=>sel(i);L.appendChild(r);});
function sel(i){document.querySelectorAll('.trow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
  const t=D.types[i];document.getElementById('hd').textContent=t.label;
  document.getElementById('sub2').textContent=`${t.n} song${t.n>1?'s':''}`;
  let h='<table><tr><th>Artist</th><th>Song</th><th>Move</th><th>Full path</th><th>Links</th></tr>';
  t.songs.forEach(o=>{
    const ug=o.ug?`<a class="lk ug" href="${o.ug}" target="_blank" rel="noopener">UG</a>`:`<span class="lk ug off">UG</span>`;
    const hp=o.hp?`<a class="lk hp" href="${o.hp}" target="_blank" rel="noopener">HP</a>`:`<span class="lk hp off">HP</span>`;
    h+=`<tr><td>${o.a}</td><td>${o.t}</td><td class=move>${o.move}</td><td class=path>${o.path}${o.home?' <span class=home>↺ home</span>':''}</td><td style="white-space:nowrap">${ug}${hp}</td></tr>`;});
  document.getElementById('body').innerHTML=h+'</table>';}
sel(0);
</script></body></html>
"""

if __name__=='__main__':
    main()
