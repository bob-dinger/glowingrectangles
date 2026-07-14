"""Key-map page (built, to embed song data). Home key at center, every modulation
destination around it, each labeled with the move type AND how many library songs
make that move; click a destination to list those songs. Pick the home key to
re-spell the destinations. Writes _music/key-map.html.
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

def classify(a,b):
    dp=(b[0]-a[0])%12; same=a[1]==b[1]
    if not same:
        if dp==0: return 'parallel'
        if a[1]=='major' and dp==9: return 'relative'
        if a[1]=='minor' and dp==3: return 'relative'
        return None
    return {1:'up_half',2:'up_whole',3:'up_m3',4:'up_M3',5:'to_IV',6:'tritone',
            7:'to_V',8:'down_M3',9:'down_m3',10:'down_whole',11:'down_half'}.get(dp)

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor()
    cur.execute("select artist,title,hookpad_json,ug_url,hookpad_url from parcels.songs where has_chords and hookpad_json is not null")
    rows=cur.fetchall(); c.close()
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
    moves=defaultdict(list)
    for a,base,seq,ug,hp in best.values():
        path=' → '.join(kname(*s) for s in seq)
        home=seq[0]==seq[-1]; seen=set()
        for i in range(len(seq)-1):
            mv=classify(seq[i],seq[i+1])
            if not mv or mv in seen: continue
            seen.add(mv)
            moves[mv].append({'a':a,'t':base,'move':f"{kname(*seq[i])} → {kname(*seq[i+1])}",'path':path,'home':home,'ug':ug,'hp':hp})
    data={mv:{'n':len(s),'songs':sorted(s,key=lambda x:(x['a'].lower(),x['t'].lower()))} for mv,s in moves.items()}
    out=os.path.join(os.path.dirname(__file__),'key-map.html')
    open(out,'w').write(PAGE.replace('__DATA__', json.dumps(data, ensure_ascii=False)))
    summ=', '.join('{}={}'.format(k,v['n']) for k,v in sorted(data.items(),key=lambda x:-x[1]['n']))
    print(f"wrote {out}  |  moves: {summ}")

PAGE=r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Key Map</title>
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:#fbfbfd;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333}
  #viz{width:100vw;height:100vh}
  .edge{fill:none;stroke-width:2px;opacity:.5}
  .elab{font-size:11px;font-weight:600;pointer-events:none}
  .node{cursor:pointer}
  .node:hover circle{stroke:#222;stroke-width:3px}
  .node text{font-weight:700;pointer-events:none}
  .node.on circle{stroke:#222;stroke-width:3.5px}
  .cnt{font-size:11px;font-weight:700;fill:#555;pointer-events:none}
  #panel{position:fixed;top:16px;left:18px;max-width:240px}
  #panel h1{font-size:17px;margin:0 0 6px}
  #panel p{font-size:12px;line-height:1.45;color:#666;margin:4px 0}
  select{width:100%;padding:5px;font-size:13px;border:1px solid #ccd;border-radius:6px;margin-bottom:6px}
  .legend{margin-top:8px;font-size:12px}
  .legend .row{display:flex;align-items:center;gap:7px;margin:2px 0}
  .sw{width:13px;height:13px;border-radius:50%;flex:0 0 auto}
  #songs{position:fixed;top:0;right:0;width:340px;height:100vh;background:#fff;border-left:1px solid #eee;box-shadow:-2px 0 12px rgba(0,0,0,.05);overflow-y:auto;transform:translateX(100%);transition:transform .25s}
  #songs.open{transform:none}
  #songs h2{font-size:15px;margin:16px 16px 2px}
  #songs .s2{font-size:12px;color:#888;margin:0 16px 8px}
  #songs table{border-collapse:collapse;width:100%}
  #songs td,#songs th{text-align:left;padding:4px 10px;border-bottom:1px solid #f0f0f0;font-size:12px}
  #songs th{color:#999;font-size:10px;text-transform:uppercase}
  .move{font-weight:700;color:#4060c0;white-space:nowrap}
  .home{color:#2a9d5a;font-weight:700}
  .lk{font-size:9px;font-weight:700;text-decoration:none;border-radius:4px;padding:1px 5px;margin-right:3px;color:#fff}
  .lk.ug{background:#c8600f}.lk.hp{background:#5090f0}.lk.off{background:#eee;color:#bbb}
  #close{position:absolute;top:12px;right:14px;cursor:pointer;font-size:20px;color:#aaa;border:none;background:none}
</style></head><body>
<div id="panel">
  <h1>Key Map</h1>
  <select id="home"></select>
  <p>Every key you could modulate to, around the home key. Numbers = how many library songs make that move. <b>Click a move</b> to list them.</p>
  <div class="legend" id="legend"></div>
</div>
<div id="songs"><button id="close">×</button><h2 id="sh"></h2><div class="s2" id="ss"></div><div id="sbody"></div></div>
<div id="viz"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
const MOVES=__DATA__;
const PCN=['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B'];
const kname=(pc,mode)=>PCN[((pc%12)+12)%12]+(mode==='minor'?'m':'');
const CAT={parallel:'#7a7a8c',relative:'#7040b0',fifth:'#5090f0',step:'#3aa85f',m3:'#f0a040',M3:'#e8c828',tritone:'#e84545'};
const DESTS=[
  {mv:'parallel', dp:0, flip:true,  cat:'parallel', lab:'parallel',       ang:0,    r:.5},
  {mv:'relative', dp:'rel', flip:true, cat:'relative', lab:'relative',    ang:28,   r:.8},
  {mv:'to_V',   dp:7, flip:false, cat:'fifth',    lab:'to V',            ang:60,   r:.85},
  {mv:'up_whole',dp:2,flip:false, cat:'step',     lab:'up whole-step',   ang:88,   r:1.1},
  {mv:'up_m3',  dp:3, flip:false, cat:'m3',       lab:'up m3 (♭III)',    ang:116,  r:1.02},
  {mv:'up_M3',  dp:4, flip:false, cat:'M3',       lab:'up M3',           ang:143,  r:1.15},
  {mv:'up_half',dp:1, flip:false, cat:'step',     lab:'up ½-step',       ang:167,  r:1.3},
  {mv:'tritone',dp:6, flip:false, cat:'tritone',  lab:'tritone',         ang:180,  r:1.4},
  {mv:'down_half',dp:11,flip:false,cat:'step',    lab:'down ½-step',     ang:-167, r:1.3},
  {mv:'down_M3',dp:8, flip:false, cat:'M3',       lab:'down M3',         ang:-143, r:1.15},
  {mv:'down_m3',dp:9, flip:false, cat:'m3',       lab:'down m3',         ang:-116, r:1.02},
  {mv:'down_whole',dp:10,flip:false,cat:'step',   lab:'down whole-step', ang:-88,  r:1.1},
  {mv:'to_IV',  dp:5, flip:false, cat:'fifth',    lab:'to IV',           ang:-60,  r:.85},
];
const relDp=mode=>mode==='major'?9:3;

let home={pc:0,mode:'major'};
const W=window.innerWidth,H=window.innerHeight;
const TOP=40,BOT=90;                                    // bottom margin
const CX=W/2, CY=(TOP+(H-BOT))/2;
const RAD=Math.min(W/2-60,(Math.min(CY-TOP,(H-BOT)-CY))/1.42);
const svg=d3.select('#viz').append('svg').attr('width',W).attr('height',H);
const defs=svg.append('defs');
defs.append('marker').attr('id','arw').attr('viewBox','0 -5 10 10').attr('refX',20).attr('refY',0)
  .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto').append('path').attr('d','M0,-5L10,0L0,5').attr('fill','#bbb');
const g=svg.append('g');

// home dropdown
const homeOpts=[];
for(const m of ['major','minor']) for(let pc=0;pc<12;pc++) homeOpts.push({pc,mode:m,name:kname(pc,m)});
d3.select('#home').selectAll('option').data(homeOpts).join('option').attr('value',(d,i)=>i).text(d=>d.name+' major'.replace('major',d.mode));
d3.select('#home').on('change',function(){home=homeOpts[+this.value];draw();});
d3.select('#legend').selectAll('div').data(Object.entries(CAT)).join('div').attr('class','row')
  .html(d=>`<span class="sw" style="background:${d[1]}"></span>${d[0]}`);

function dests(){
  return DESTS.map(d=>{
    const dp=d.dp==='rel'?relDp(home.mode):d.dp;
    const pc=(home.pc+dp)%12, mode=d.flip?(home.mode==='major'?'minor':'major'):home.mode;
    const a=d.ang*Math.PI/180, n=(MOVES[d.mv]||{}).n||0;
    return {...d,pc,mode,n,x:CX+RAD*d.r*Math.sin(a),y:CY-RAD*d.r*Math.cos(a)};
  });
}
let active=null;
function draw(){
  const ds=dests(), homeN={pc:home.pc,mode:home.mode,x:CX,y:CY,home:true};
  const ed=g.selectAll('.edge').data(ds,d=>d.mv);
  ed.join(e=>e.append('path').attr('class','edge').attr('marker-end','url(#arw)'))
    .transition().duration(400).attr('stroke',d=>CAT[d.cat]).attr('d',d=>`M${CX},${CY} L${d.x},${d.y}`);
  const el=g.selectAll('.elab').data(ds,d=>d.mv);
  el.join(e=>e.append('text').attr('class','elab').attr('text-anchor','middle'))
    .attr('fill',d=>d3.color(CAT[d.cat]).darker(.4))
    .transition().duration(400).attr('x',d=>CX+(d.x-CX)*0.52).attr('y',d=>CY+(d.y-CY)*0.52-3).text(d=>d.lab);
  const all=[homeN,...ds];
  const nd=g.selectAll('.node').data(all,d=>d.home?'HOME':d.mv);
  const en=nd.enter().append('g').on('click',(e,d)=>{if(!d.home){active=d.mv;showSongs(d);}});
  en.append('circle'); en.append('text').attr('class','lbl'); en.append('text').attr('class','cnt');
  const m=en.merge(nd);
  m.attr('class',d=>'node'+(d.home?' home':'')+(d.mv===active?' on':''));
  m.transition().duration(400).attr('transform',d=>`translate(${d.x},${d.y})`);
  m.select('circle').attr('r',d=>d.home?32:22)
    .attr('fill',d=>d.home?'#2a2a44':(d.mode==='minor'?d3.color(CAT[d.cat]).brighter(1.15):CAT[d.cat]))
    .attr('stroke',d=>d.home?'#000':d3.color(CAT[d.cat]).darker(.6)).attr('stroke-width',1.6);
  m.select('.lbl').attr('text-anchor','middle').attr('dy','0.34em')
    .style('font-size',d=>d.home?'18px':'14px').attr('fill',d=>(d.home||d.mode!=='minor')?'#fff':'#333')
    .text(d=>kname(d.pc,d.mode));
  m.select('.cnt').attr('text-anchor','middle').attr('dy','2.9em').text(d=>d.home?'':(d.n||0));
  nd.exit().remove();
}
function showSongs(d){
  draw();
  const data=MOVES[d.mv]||{n:0,songs:[]};
  d3.select('#sh').text(d.lab+'  →  '+kname(d.pc,d.mode));
  d3.select('#ss').text(`${data.n} song${data.n===1?'':'s'} make this move (any key)`);
  let h='<table><tr><th>Artist</th><th>Song</th><th>Move</th><th>Path</th><th></th></tr>';
  (data.songs||[]).forEach(o=>{
    const ug=o.ug?`<a class="lk ug" href="${o.ug}" target="_blank">UG</a>`:`<span class="lk ug off">UG</span>`;
    const hp=o.hp?`<a class="lk hp" href="${o.hp}" target="_blank">HP</a>`:`<span class="lk hp off">HP</span>`;
    h+=`<tr><td>${o.a}</td><td>${o.t}</td><td class=move>${o.move}</td><td style="color:#888">${o.path}${o.home?' <span class=home>↺</span>':''}</td><td style="white-space:nowrap">${ug}${hp}</td></tr>`;});
  d3.select('#sbody').html(h+'</table>');
  d3.select('#songs').classed('open',true);
}
d3.select('#close').on('click',()=>{d3.select('#songs').classed('open',false);active=null;draw();});
draw();
</script></body></html>
"""

if __name__=='__main__':
    main()
