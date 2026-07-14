"""Key-journey visualizer. For every song that genuinely changes key (Hookpad
`keys` markers, collapsed + scale-normalized), emit its tonal path and render a
D3 page: the home key sits at the center of a family-space, the keys it visits
are placed by their relationship to home (parallel = on top of home, relative /
IV / V = close, distant keys further out), and the journey animates out and back.

Writes _music/key-journeys.html.
"""
import os, json, psycopg2
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,
    'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def collapse(ks):
    out=[]
    for k in ks:
        pc=PC.get(k.get('tonic'),-1)
        if pc<0: continue
        s=[pc, 'minor' if k.get('scale')=='minor' else 'major']
        if not out or out[-1]!=s: out.append(s)
    return out

def main():
    c=psycopg2.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],port=os.environ.get('DB_PORT',5432))
    cur=c.cursor()
    cur.execute("select artist,title,hookpad_json from parcels.songs where has_chords and hookpad_json is not null")
    rows=cur.fetchall(); c.close()
    songs=[]
    for a,t,hj in rows:
        if t and t.lower().endswith(('-hooktab','-simple')): continue
        seq=collapse(hj.get('keys') or [])
        if len(seq)<2: continue
        songs.append({'a':a or '','t':t,'seq':seq})
    # dedupe by (artist,title) keeping the longest journey
    best={}
    for s in songs:
        k=(s['a'].lower(),s['t'].lower())
        if k not in best or len(s['seq'])>len(best[k]['seq']): best[k]=s
    songs=sorted(best.values(), key=lambda s:(s['a'].lower(),s['t'].lower()))
    out=os.path.join(os.path.dirname(__file__),'key-journeys.html')
    open(out,'w').write(PAGE.replace('__DATA__', json.dumps(songs)))
    print(f'wrote {out}  |  {len(songs)} key-changing songs')

PAGE=r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Key Journeys</title>
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:#fbfbfd;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333}
  #viz{width:100vw;height:100vh}
  #panel{position:fixed;top:16px;left:18px;width:270px}
  #panel h1{font-size:17px;margin:0 0 6px}
  select{width:100%;padding:6px;font-size:13px;border:1px solid #ccd;border-radius:6px;background:#fff}
  #meta{font-size:12px;color:#666;margin:8px 0;line-height:1.5;min-height:34px}
  button{margin-top:6px;padding:6px 14px;font-size:13px;font-weight:600;border:1px solid #2a2a44;background:#2a2a44;color:#fff;border-radius:6px;cursor:pointer}
  .home circle{stroke:#2a2a44;stroke-width:3px}
  .knode text{font-weight:700;pointer-events:none}
  .edge{fill:none;stroke-width:2px;opacity:.55}
  .edgelbl{font-size:10px;fill:#888;font-weight:600}
  .token{fill:#ffd23f;stroke:#c89000;stroke-width:2px}
  .legend{margin-top:12px;font-size:11px;color:#777;line-height:1.6}
</style>
</head>
<body>
<div id="panel">
  <h1>Key Journeys</h1>
  <select id="pick"></select>
  <div id="meta"></div>
  <button id="play">▶ replay journey</button>
  <div class="legend">
    Home key at center. Each key the song visits is placed by its relationship to home —
    <b>parallel</b> flip sits on top of home, <b>relative / IV / V</b> nearby, distant keys further out.
    Major = solid, minor = pale. Watch it venture out and (often) return home.
  </div>
</div>
<div id="viz"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
const SONGS=__DATA__;
const PCN=['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B'];
const kname=k=>PCN[k[0]]+(k[1]==='minor'?'m':'');
function fifths(home,pc){let f=(((pc-home)*7)%12+12)%12; return f>6?f-12:f;}
// relationship of key b relative to home a -> label + radius factor
function rel(a,b){
  const dp=((b[0]-a[0])%12+12)%12, same=a[1]===b[1];
  if(dp===0&&!same) return {t:'parallel',r:0.42};
  if(a[1]==='major'&&b[1]==='minor'&&dp===9) return {t:'relative minor',r:0.72};
  if(a[1]==='minor'&&b[1]==='major'&&dp===3) return {t:'relative major',r:0.72};
  const f=Math.abs(fifths(a[0],b[0]));
  const names={7:'up ½',2:'up whole',10:'down whole',3:'up m3',9:'down m3',4:'up M3',8:'down M3',5:'to IV',6:'tritone'};
  let lab=names[dp]|| (same?('+'+dp):('flip +'+dp));
  if(dp===7&&same) lab='to V'; if(dp===5&&same) lab='to IV';
  return {t:lab, r: 0.7 + Math.min(f,6)*0.16};
}
// color a key by its home-relative role (degree color of its tonic in home's major)
const DEGCOL={0:'#e84545',7:'#5090f0',5:'#50c878',2:'#f0a040',9:'#7040b0',4:'#e8c828',11:'#e070b0'};
function keyColor(home,k){const dp=((k[0]-home[0])%12+12)%12; return DEGCOL[dp]||'#9aa';}

const W=window.innerWidth,H=window.innerHeight,CX=W/2,CY=H/2,RAD=Math.min(W,H)/2-110;
const svg=d3.select('#viz').append('svg').attr('width',W).attr('height',H);
const g=svg.append('g');

// build dropdown
const pick=d3.select('#pick');
pick.selectAll('option').data(SONGS).join('option')
  .attr('value',(d,i)=>i).text(d=>`${d.a} — ${d.t}  (${d.seq.map(kname).join('→')})`);

let cur=null;
function layout(song){
  const home=song.seq[0];
  // unique keys -> position
  const pos=new Map();
  pos.set(kname(home),{k:home,x:CX,y:CY,home:true});
  song.seq.forEach(k=>{
    const nm=kname(k); if(pos.has(nm))return;
    const r=rel(home,k), f=fifths(home,k[0]);
    const ang=(f*30)*Math.PI/180;                 // 0 = straight up; V right, IV left
    const rr=RAD*r.r + (k[1]==='minor'?0:0);
    pos.set(nm,{k, x:CX+rr*Math.sin(ang), y:CY-rr*Math.cos(ang), home:false, rel:r.t});
  });
  return {home,pos};
}

function draw(song){
  g.selectAll('*').remove();
  const {home,pos}=layout(song);
  const nodes=[...pos.values()];
  // edges follow the sequence
  const edges=[];
  for(let i=0;i<song.seq.length-1;i++){
    const A=pos.get(kname(song.seq[i])), B=pos.get(kname(song.seq[i+1]));
    if(A&&B&&(A.x!==B.x||A.y!==B.y)) edges.push({A,B,rel:rel(home,song.seq[i+1]).t});
  }
  // draw edges (curved)
  g.selectAll('.edge').data(edges).join('path').attr('class','edge')
    .attr('stroke',d=>keyColor(home,d.B.k))
    .attr('d',d=>{const mx=(d.A.x+d.B.x)/2,my=(d.A.y+d.B.y)/2-30;return `M${d.A.x},${d.A.y} Q${mx},${my} ${d.B.x},${d.B.y}`;})
    .attr('marker-end','url(#arw)');
  // edge labels (unique rel per edge)
  g.selectAll('.edgelbl').data(edges).join('text').attr('class','edgelbl')
    .attr('x',d=>(d.A.x+d.B.x)/2).attr('y',d=>(d.A.y+d.B.y)/2-34).attr('text-anchor','middle').text(d=>d.rel);
  // nodes
  const nd=g.selectAll('.knode').data(nodes).join('g').attr('class',d=>'knode'+(d.home?' home':''))
    .attr('transform',d=>`translate(${d.x},${d.y})`);
  nd.append('circle').attr('r',d=>d.home?30:20)
    .attr('fill',d=>d.k[1]==='minor'?d3.color(keyColor(home,d.k)).brighter(1.1):keyColor(home,d.k))
    .attr('stroke',d=>d3.color(keyColor(home,d.k)).darker(.6)).attr('stroke-width',1.5);
  nd.append('text').attr('text-anchor','middle').attr('dy','0.34em')
    .style('font-size',d=>d.home?'16px':'13px')
    .attr('fill',d=>d.k[1]==='minor'?'#333':'#fff').text(d=>kname(d.k));
  // arrow marker
  const defs=svg.select('defs').empty()?svg.append('defs'):svg.select('defs');
  defs.selectAll('#arw').data([0]).join('marker').attr('id','arw').attr('viewBox','0 -5 10 10')
    .attr('refX',22).attr('refY',0).attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
    .append('path').attr('d','M0,-5L10,0L0,5').attr('fill','#bbb');
  return {home,pos};
}

function animate(song,pos){
  g.selectAll('.token').remove();
  const pts=song.seq.map(k=>pos.get(kname(k)));
  const tok=g.append('circle').attr('class','token').attr('r',9).attr('cx',pts[0].x).attr('cy',pts[0].y);
  let i=0;
  function step(){
    if(i>=pts.length-1) return;
    const A=pts[i],B=pts[i+1]; i++;
    tok.transition().duration(750).ease(d3.easeCubicInOut).attr('cx',B.x).attr('cy',B.y).on('end',step);
  }
  step();
}

function show(idx){
  cur=SONGS[idx];
  const {pos}=draw(cur);
  const home=kname(cur.seq[0]), end=kname(cur.seq[cur.seq.length-1]);
  d3.select('#meta').html(`<b>${cur.seq.map(kname).join(' → ')}</b><br>${cur.seq.length-1} moves · ${home===end?'returns home ✔':'ends on '+end}`);
  animate(cur,pos);
}
pick.on('change',()=>show(+pick.node().value));
d3.select('#play').on('click',()=>{if(cur){const {pos}=draw(cur);animate(cur,pos);}});
// default: pick something juicy if present, else first
const def=SONGS.findIndex(s=>/comfortably numb|pretty woman|norwegian/i.test(s.t));
pick.node().value=def>=0?def:0; show(def>=0?def:0);
</script>
</body>
</html>
"""

if __name__=='__main__':
    main()
