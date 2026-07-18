"""Per-SECTION core-set browser. For every section of every song, weight chords by
duration, keep those >=10% (the CORE), drop the rest as tags. Group sections by
their 4-chord core set. Emit a sidebar+panel HTML page (site: _music/chord-sets.html).
"""
import os, re, json, html, psycopg2
from urllib.parse import quote_plus
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from chord_label import chord_label

CUTOFF = 0.10
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def coretok(t):
    if '°' in t:   # secondary leading-tone dim (vii°7 / vii°7/iii) — keep whole token
        m = re.match(r'^(vii°7?(?:/[b#]*[ivxIVX]+)?)', t); return m.group(1) if m else t
    m = re.match(r'^([b#]*[ivxIVX]+(?:/[b#]*[ivxIVX]+)?)', t); return m.group(1) if m else t

NUM={'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7}; MAJ={1:0,2:2,3:4,4:5,5:7,6:9,7:11}
PCN=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
def _plain(t):
    m=re.match(r'^([b#]*)([ivxIVX]+)$',t)
    if not m: return None
    acc=sum(-1 if x=='b' else 1 for x in m.group(1)); deg=NUM.get(m.group(2).lower())
    if not deg: return None
    q='dim' if (m.group(2).lower()=='vii' and m.group(2).islower()) else ('maj' if m.group(2).isupper() else 'min')
    return (MAJ[deg]+acc)%12, q
def toC(t):
    if '°' in t:   # secondary leading-tone dim → letter of the leading tone below the target
        tgt = t.split('/', 1)[1] if '/' in t else 'I'
        rp = _plain(tgt)
        base_pc = rp[0] if rp else 0
        return PCN[(base_pc - 1) % 12] + 'dim'
    if '/' in t:
        l,r=t.split('/',1); rp=_plain(r); m=re.match(r'^([b#]*)([ivxIVX]+)$',l)
        if rp and m:
            acc=sum(-1 if x=='b' else 1 for x in m.group(1)); d=NUM.get(m.group(2).lower())
            if d: return PCN[(rp[0]+MAJ[d]+acc)%12]
        return t
    p=_plain(t)
    if not p: return t
    return PCN[p[0]]+('m' if p[1]=='min' else 'dim' if p[1]=='dim' else '')
def cpc(c):
    b=c.replace('dim','').rstrip('m'); return PCN.index(b) if b in PCN else 99

# names we've assigned
DEG2ROM={1:'I',2:'ii',3:'iii',4:'IV',5:'V',6:'vi',7:'vii'}
def _basetok(tok):   # strip 7/maj7/6/sus/add… -> bare roman with accidentals, matches page tokens
    m=re.match(r'^([b#]*)([ivxIVX]+)',tok); return (m.group(1)+m.group(2)) if m else None
# match a chord SET (unordered) against every named unit — a set of chords can power several
# named progressions (I/IV/V/vi = Axis + Let It Be + Stand By Me + …). Include ordered loops too.
NAMED=defaultdict(list)
for e in json.load(open(os.path.join(os.path.dirname(__file__),'chord_sets.json')))['entries']:
    if e.get('degrees'):
        toks=[DEG2ROM[d] for d in e['degrees'] if d in DEG2ROM]
    elif e.get('roman'):
        toks=[_basetok(t) for t in e['roman'].split()]
    else:
        toks=[]
    toks=[t for t in toks if t]
    if toks: NAMED[frozenset(toks)].append(e['name'])

def section_cores(hj):
    """yield (core_frozenset, roman_share_map, section_name) per section."""
    scale=(hj.get('keys') or [{}])[0].get('scale','major'); scale=scale if scale in ('major','minor') else 'major'
    secs=sorted(hj.get('sections') or [], key=lambda s:s.get('beat',0))
    if not secs: secs=[{'beat':0,'name':'(whole)'}]
    end=hj.get('endBeat',10**9)
    bounds=[(secs[i]['beat'], secs[i+1]['beat'] if i+1<len(secs) else end+1, secs[i].get('name','')) for i in range(len(secs))]
    for b0,b1,nm in bounds:
        tot=defaultdict(float)
        for c in hj.get('chords') or []:
            if c.get('root') and 1<=c['root']<=7 and b0<=c.get('beat',0)<b1:
                tot[coretok(chord_label(c,scale))]+=c.get('duration',1)
        s=sum(tot.values())
        if s<=0: continue
        share={k:v/s for k,v in tot.items()}
        core=frozenset(k for k,v in share.items() if v>=CUTOFF)
        if core: yield core, share, nm

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor(); cur.execute("select artist,title,hookpad_json,ug_url,hookpad_url from parcels.songs where has_chords and hookpad_json is not null")
    rows=cur.fetchall(); c.close()
    sets=defaultdict(list); seen=set()
    for artist,title,hj,ug_url,hp_url in rows:
        if not title or title.lower().endswith(('-hooktab','-simple')): continue
        # UG: stored url if present, else a title search; HP: stored url only (needs the hashid)
        ug=(ug_url or '').strip() or ('https://www.ultimate-guitar.com/search.php?search_type=title&value='
                                      + quote_plus(f"{artist or ''} {title}".strip()))
        hp=(hp_url or '').strip()
        for core,share,secname in section_cores(hj):
            if len(core)<2: continue
            key=(norm((artist or '')+title), core)
            if key in seen: continue
            seen.add(key)
            tags=sorted((toC(k) for k,v in share.items() if v<CUTOFF), key=cpc)
            sets[core].append({'a':artist or '','t':title,'sec':secname,'tags':tags,'ug':ug,'hp':hp})
    # build serializable, grouped by size, ranked within
    data={'2':[],'3':[],'4':[],'5':[],'6+':[]}
    for core,songs in sorted(sets.items(), key=lambda kv:-len(kv[1])):
        chords=sorted((toC(t) for t in core), key=cpc)
        roman=' '.join(sorted(core,key=lambda x:(len(x),x)))
        bucket=str(len(core)) if len(core)<=5 else '6+'
        names=list(dict.fromkeys(NAMED.get(core,[])))   # dedupe, keep order
        data[bucket].append({'chords':chords,'roman':roman,'name':(names[0] if names else ''),'names':names,
                     'n':len(songs),'songs':sorted(songs,key=lambda s:(s['a'].lower(),s['t'].lower()))})
    out=os.path.join(os.path.dirname(__file__),'chord-sets.html')
    open(out,'w').write(PAGE.replace('__DATA__', json.dumps(data)))
    print('wrote {}  |  {} sets'.format(out, '  '.join(f'{k}:{len(v)}' for k,v in data.items())))

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><title>Chord Sets · 4-chord</title>
<style>
*{box-sizing:border-box} body{margin:0;font:14px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a2e;background:#f4f4f8}
#wrap{display:flex;height:100vh}
#side{width:300px;flex:none;overflow-y:auto;border-right:1px solid #ddd;background:#fff}
#side h1{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:#888;padding:14px 16px 6px;margin:0}
.tog{display:flex;gap:6px;padding:10px 16px;border-bottom:1px solid #eee;position:sticky;top:0;background:#fff;z-index:2}
.tog button{flex:1;padding:7px 0;border:1px solid #ccd;background:#f6f6fb;border-radius:7px;cursor:pointer;font-weight:600;color:#556}
.tog button.on{background:#2a2a44;color:#fff;border-color:#2a2a44}
.setrow{padding:8px 14px;cursor:pointer;border-bottom:1px solid #f0f0f4;display:flex;justify-content:space-between;align-items:center;gap:8px}
.setrow:hover{background:#eef}.setrow.on{background:#2a2a44}
.setrow .nm{font-size:11px;color:#8a2be2;margin-left:4px}.setrow.on .nm{color:#ffd}
.setrow .ct{font-size:11px;color:#aaa;flex:none}.setrow.on .ct{color:#dde}
#main{flex:1;overflow-y:auto;padding:24px 32px}
#hd .meta{color:#888;margin:10px 0 2px}#hd .name{color:#8a2be2;font-size:20px;font-weight:600;margin-top:8px}
.chip{display:inline-block;border-radius:6px;color:#fff;font-weight:700;text-shadow:0 1px 2px rgba(0,0,0,.5);
  padding:2px 9px;margin-right:4px}
.setrow .chip{font-size:12px;padding:1px 7px}
#hd .chip{font-size:30px;padding:6px 18px;border-radius:9px;margin-right:8px}
table{border-collapse:collapse;width:100%;margin-top:14px}
td,th{text-align:left;padding:5px 10px;border-bottom:1px solid #eee}th{color:#999;font-size:11px;text-transform:uppercase}
.tag{font-size:11px;color:#c60;background:#fff3e0;border-radius:4px;padding:1px 5px;margin-left:3px}
.lk{font-size:10px;font-weight:700;text-decoration:none;border-radius:4px;padding:2px 6px;margin-right:4px;display:inline-block}
.lk.ug{color:#fff;background:#c8600f}.lk.hp{color:#fff;background:#5090f0}
.lk.off{background:#eee;color:#bbb;pointer-events:none}
</style></head><body><div id=wrap>
<div id=side><div class=tog><button data-sz=2>2</button><button data-sz=3>3</button><button data-sz=4 class=on>4</button><button data-sz=5>5</button><button data-sz="6+">6+</button></div><div id=list></div></div>
<div id=main><div id=hd></div><div id=body></div></div></div>
<script>
const D=__DATA__;
let SZ='4';
// canonical chord colors (from chord-viz.html), by ROOT pitch class
const PCCOL={0:'#e84545',2:'#f0a040',4:'#e8c828',5:'#50c878',7:'#5090f0',9:'#7040b0',11:'#e070b0'};
const NOTEPC={C:0,'C#':1,Db:1,D:2,'D#':3,Eb:3,E:4,F:5,'F#':6,Gb:6,G:7,'G#':8,Ab:8,A:9,'A#':10,Bb:10,B:11};
// near-diatonic borrowed chords get their own dedicated color (distinct from the diatonic chord on the same pc)
const SPECIAL={'D':'#c8600f','E':'#b89000'};   // secondary doms: V/V=dark orange, V/vi=dark yellow (vs Dm/Em diatonic)
function chBg(c){if(SPECIAL[c]!==undefined)return SPECIAL[c];
  const m=c.match(/^([A-G][#b]?)/);const pc=m?NOTEPC[m[1]]:0;
  if(PCCOL[pc]!==undefined)return PCCOL[pc];                     // diatonic root = solid
  return `linear-gradient(135deg,${PCCOL[(pc+11)%12]} 0 50%,${PCCOL[(pc+1)%12]} 50%)`;} // chromatic = diagonal stripe
function chip(c){return `<span class=chip style="background:${chBg(c)}">${c}</span>`;}
const L=document.getElementById('list');
function build(){L.innerHTML='';
 D[SZ].forEach((s,i)=>{const r=document.createElement('div');r.className='setrow';r.dataset.i=i;
  const extra=(s.names&&s.names.length>1)?` +${s.names.length-1}`:'';
  r.innerHTML=`<span>${s.chords.map(chip).join('')}${s.name?`<span class=nm>${s.name}${extra}</span>`:''}</span><span class=ct>${s.n}</span>`;
  r.onclick=()=>sel(i);L.appendChild(r);});}
function load(sz){SZ=sz;document.querySelectorAll('.tog button').forEach(b=>b.classList.toggle('on',b.dataset.sz===sz));build();sel(0);}
document.querySelectorAll('.tog button').forEach(b=>b.onclick=()=>load(b.dataset.sz));
function sel(i){document.querySelectorAll('.setrow').forEach(e=>e.classList.toggle('on',+e.dataset.i===i));
 const s=D[SZ][i];document.getElementById('hd').innerHTML=
  `<div>${s.chords.map(chip).join('')}</div>`+
  ((s.names&&s.names.length)?`<div class=name>${s.names.join('  ·  ')}</div>`:'')+
  `<div class=meta>${s.roman} · ${s.n} sections</div>`;
 let h='<table><tr><th>Artist</th><th>Song</th><th>Section</th><th>Links</th><th>tags</th></tr>';
 s.songs.forEach(o=>{
  const ug=o.ug?`<a class="lk ug" href="${o.ug}" target="_blank" rel="noopener">UG</a>`:`<span class="lk ug off">UG</span>`;
  const hp=o.hp?`<a class="lk hp" href="${o.hp}" target="_blank" rel="noopener">HP</a>`:`<span class="lk hp off">HP</span>`;
  h+=`<tr><td>${o.a}</td><td>${o.t}</td><td>${o.sec||''}</td><td style="white-space:nowrap">${ug}${hp}</td><td>${(o.tags||[]).map(t=>`<span class=tag>${t}</span>`).join('')}</td></tr>`});
 document.getElementById('body').innerHTML=h+'</table>';}
load('4');
</script></body></html>"""

if __name__ == '__main__':
    main()
