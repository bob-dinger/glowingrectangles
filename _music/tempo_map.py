"""Tempo map: every library song with audio, placed along the x-axis at its measured tempo.

    tempo_map.py        # writes ~/Desktop/music/tempo_map.html (rerun after more audio or pulse results)

Measured tempo = the whole-song beat fit (audio_work/tempo.json), unless the
song's strongest repeating pulse (audio_work/pulse.json) disagrees by more than
half/double: then the pulse wins and the song is marked "unsure". That rule got
31 of the user's 33 Beatles buckets right; the fit alone falls into the triplet
trap (2/3, 3/4 of the real tempo: Here Comes the Sun, Tomorrow Never Knows).

"Yours" = the bpm in the Guitar50-500 sheets of songs_to_learn_record_bpm.xlsx,
else the Hookpad file's tempo. The measured tempo is put in the same half/double
counting as yours, so a dot sits where you count the song. Dots are green when
the two agree (within 6 %), orange when only the measuring is unsure, red when
they disagree. Local page only (~/Desktop/music), like listen.html.
"""
import glob, json, os, re
import openpyxl

M = os.path.expanduser('~/Desktop/music')
A = f'{M}/audio_work'
OUT = f'{M}/tempo_map.html'
norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower().replace('&', 'and'))
tnorm = lambda t: norm(re.sub(r'^(the|a) ', '', re.sub(r'\(.*?\)|\[.*?\]', '', (t or '').lower().replace('’', "'")).strip()).replace("in'", 'ing'))
anorm = lambda a: norm(re.sub(r'^the ', '', (a or '').lower().strip()))
load = lambda f: json.load(open(f)) if os.path.exists(f) else {}
same = lambda a, b, tol=.04: min(abs(a * m / b - 1) for m in (.5, 1, 2)) < tol


def title_case(s):
    if any(c.isupper() for c in s): return s
    small = {'a', 'an', 'and', 'the', 'of', 'in', 'on', 'to', 'for', 'at', 'by', 'or'}
    return ' '.join(w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(s.split()))


def sheet_bpms():
    """{(title, artist[:5]): (bpm, sheet)} from the Guitar lists"""
    wb = openpyxl.load_workbook(f'{M}/songs_to_learn_record_bpm.xlsx', read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        if not ws.title.lower().replace(' ', '').startswith('guitar'): continue
        rows = list(ws.iter_rows(values_only=True))
        h = [str(x or '').lower() for x in rows[0]]
        if 'bpm' not in h: continue
        ti = h.index('title') if 'title' in h else h.index('song')
        ar = h.index('artist') if 'artist' in h else h.index('band')
        b = h.index('bpm')
        for r in rows[1:]:
            try: v = float(r[b])
            except (TypeError, ValueError): continue
            if r[ti] and r[ar] and 40 <= v <= 260:
                out.setdefault((tnorm(str(r[ti])), anorm(str(r[ar]))[:5]), (v, ws.title))
    return out


def hookpad_bpms():
    out = {}
    for f in glob.glob(f'{M}/hookpad_songs_full/*.json'):
        n = os.path.basename(f)[:-5]
        if '_' not in n: continue
        a, t = n.split('_', 1)
        try: v = json.load(open(f))['tempos'][0]['bpm']
        except Exception: continue
        out[(tnorm(t), anorm(a)[:5])] = v
    return out


def main():
    T, P = load(f'{A}/tempo.json'), load(f'{A}/pulse.json')
    sheet, hp = sheet_bpms(), hookpad_bpms()
    rows, seen = [], set()
    for f in ('fixes_manifest.json', 'pilot_manifest.json', 'batch1_manifest.json', 'library_manifest.json'):
        for r in (load(f'{A}/youtube/{f}') or []):
            p = r.get('file')
            if not p or p in seen or r.get('src') == 'extra' or not os.path.exists(p): continue
            seen.add(p)
            t = T.get(p) or {}
            if not t.get('bpm'): continue
            fit = t['bpm']
            pk = P.get(p); pulse = pk[0][0] if isinstance(pk, list) and pk else None
            unsure = bool(pulse) and not same(fit, pulse)
            m = pulse if unsure else fit
            key = (tnorm(r['title']), anorm(r['artist'])[:5])
            mine, src = None, None
            if key in sheet: mine, src = sheet[key][0], sheet[key][1]
            elif key in hp: mine, src = hp[key], 'Hookpad'
            if mine:
                m = min((m * k for k in (.5, 1, 2)), key=lambda x: abs(x - mine))
                d = m / mine
                status = 'ok' if abs(d - 1) <= .06 else 'ratio' if min(abs(d - x) for x in (1.5, 2 / 3, 4 / 3, .75)) < .04 else 'off'
            else:
                while m > 200: m /= 2
                while m < 55: m *= 2
                status = 'none'
            rows.append(dict(t=title_case(r['title']), a=title_case(r['artist']), m=round(m, 1), y=mine and round(mine), src=src,
                             st=status, u=unsure, fit=round(fit, 1), pulse=pulse, dr=t.get('drift_ms'), f=os.path.relpath(p, M)))
    n = {k: sum(r['st'] == k for r in rows) for k in ('ok', 'ratio', 'off', 'none')}
    page = PAGE.replace('__DATA__', json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
    open(OUT, 'w').write(page)
    print(f'{len(rows)} songs -> file://{OUT}', n, sum(r['u'] for r in rows), 'unsure', sum(1 for r in rows if r['pulse']), 'with pulse')


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tempo Map</title>
<style>
:root{--bg:#faf8f4;--fg:#1d1b18;--mut:#7a746b;--line:#e3ddd2;--card:#fff;--ok:#2e8b57;--un:#d48a1c;--off:#c8372d;--none:#a39d93;--hl:#1f5fbf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17161a;--fg:#ece8e1;--mut:#9a948b;--line:#2c2a30;--card:#201f24;--ok:#4fbf80;--un:#f0a83c;--off:#f0645a;--none:#6d6a72;--hl:#6aa3ff}}
:root[data-theme="dark"]{--bg:#17161a;--fg:#ece8e1;--mut:#9a948b;--line:#2c2a30;--card:#201f24;--ok:#4fbf80;--un:#f0a83c;--off:#f0645a;--none:#6d6a72;--hl:#6aa3ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;height:100vh;display:flex;flex-direction:column}
header{display:flex;gap:14px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:17px;margin:0 8px 0 0}
.chip{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:14px;padding:3px 10px;cursor:pointer;font-size:13px}
.chip.on{background:var(--fg);color:var(--bg)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:-1px}
input{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:4px 8px;width:180px}
main{flex:1;display:flex;min-height:0}
#plot{flex:1;min-width:0;position:relative}
svg{width:100%;height:100%;display:block}
aside{width:330px;border-left:1px solid var(--line);padding:12px 14px;overflow:auto}
aside h2{font-size:15px;margin:0 0 6px}
.row{padding:4px 0;border-bottom:1px solid var(--line);cursor:pointer}
.row small{color:var(--mut)}
.mut{color:var(--mut)}
audio{width:100%;margin:8px 0}
.legend span{margin-right:10px;font-size:13px}
@media (max-width:760px){main{flex-direction:column}aside{width:auto;border-left:0;border-top:1px solid var(--line);max-height:45vh}}
</style></head><body>
<header>
  <h1>Tempo map</h1>
  <span class="legend"><span><i class="dot" style="background:var(--ok)"></i>agrees with yours</span><span><i class="dot" style="background:var(--un)"></i>measuring unsure</span><span><i class="dot" style="background:var(--off)"></i>disagrees</span><span><i class="dot" style="background:var(--none)"></i>no tempo of yours</span></span>
  <span id="f"></span>
  <input id="q" placeholder="search song or artist">
  <span class="mut" id="cnt"></span>
</header>
<main><div id="plot"><svg id="svg"></svg></div>
<aside id="side"><h2>How to read it</h2><p class="mut">Each dot is a song, placed at its measured tempo (in the same half/double counting as yours). Click a dot for the song, or a column label for everything in that 10-bpm bucket. Red and orange dots are the ones to tap along to.</p></aside></main>
<script>
const D=__DATA__;
const COL={ok:'var(--ok)',ratio:'var(--off)',off:'var(--off)',none:'var(--none)'};
const FILTERS=[['all','All'],['check','To check'],['off','Disagree'],['ok','Agree']];
let filt='all',q='';
const fEl=document.getElementById('f');
FILTERS.forEach(([k,l])=>{const b=document.createElement('span');b.className='chip'+(k==filt?' on':'');b.textContent=l;b.onclick=()=>{filt=k;[...fEl.children].forEach(c=>c.classList.remove('on'));b.classList.add('on');draw()};fEl.appendChild(b)});
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase();draw()};
const color=r=>r.st==='ok'&&r.u?'var(--un)':COL[r.st];
const keep=r=>filt==='all'||(filt==='ok'&&r.st==='ok'&&!r.u)||(filt==='off'&&(r.st==='off'||r.st==='ratio'))||(filt==='check'&&(r.st==='off'||r.st==='ratio'||r.u));
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function side(html){document.getElementById('side').innerHTML=html}
function why(r){
  if(r.st==='none')return 'No tempo of yours to compare.';
  const d=r.m/r.y;
  let s=r.st==='ok'?'Agrees with yours.':r.st==='ratio'?`Off by ${Math.abs(d-1.5)<.05||Math.abs(d-2/3)<.05?'3:2':'4:3'}: the triplet-type trap, on one side or the other.`:'Disagrees.';
  if(r.u)s+=` The two methods disagreed (beat fit ${r.fit}, pulse ${r.pulse}); the pulse is used.`;
  return s}
function show(r){side(`<h2>${esc(r.t)}</h2><div class="mut">${esc(r.a)}</div>
<p><b>Measured:</b> ${r.m} bpm<br><b>Yours:</b> ${r.y?r.y+' bpm <span class="mut">('+esc(r.src)+')</span>':'—'}</p>
<p>${why(r)}</p><p class="mut">beat fit ${r.fit} · pulse ${r.pulse??'—'} · beat wobble ${r.dr??'—'} ms</p>
<audio controls src="${encodeURI(r.f)}"></audio>`)}
function bucket(b){
  const rs=D.filter(r=>keep(r)&&Math.round(r.m/10)*10===b).sort((x,y)=>x.m-y.m);
  side(`<h2>${b} bpm bucket</h2><div class="mut">${rs.length} songs (${b-5}–${b+5})</div>`+rs.map((r,i)=>`<div class="row" data-i="${D.indexOf(r)}"><i class="dot" style="background:${color(r)}"></i>${esc(r.t)} <small>${esc(r.a)} · ${r.m}${r.y&&r.st!=='ok'?' · yours '+r.y:''}</small></div>`).join(''));
  document.querySelectorAll('.row').forEach(e=>e.onclick=()=>show(D[+e.dataset.i]))}
function draw(){
  const svg=document.getElementById('svg'),W=svg.clientWidth,H=svg.clientHeight;
  const x0=50,x1=230,L=34,R=12,T=14,B=46,R0=3.6;
  const X=v=>L+(v-x0)/(x1-x0)*(W-L-R);
  const rs=D.filter(keep);
  const hit=r=>q&&(r.t+' '+r.a).toLowerCase().includes(q);
  const bins={};rs.forEach(r=>{const k=Math.round(r.m/2)*2;(bins[k]=bins[k]||[]).push(r)});
  const maxn=Math.max(1,...Object.values(bins).map(b=>b.length));
  const step=Math.min(R0*2+1,(H-T-B)/maxn);
  let s='';
  for(let v=60;v<=220;v+=10){const x=X(v);s+=`<line x1="${x}" x2="${x}" y1="${T}" y2="${H-B}" stroke="var(--line)"/><text x="${x}" y="${H-B+18}" text-anchor="middle" font-size="12" fill="var(--fg)" style="cursor:pointer" data-b="${v}">${v}</text>`}
  s+=`<text x="${(L+W-R)/2}" y="${H-6}" text-anchor="middle" font-size="12" fill="var(--mut)">tempo (bpm), your counting · click a number for that bucket</text>`;
  Object.entries(bins).forEach(([k,b])=>{b.sort((p,q2)=>(p.st==='ok')-(q2.st==='ok'));b.forEach((r,j)=>{
    const cx=X(+k),cy=H-B-6-j*step,h=hit(r);
    s+=`<circle cx="${cx}" cy="${cy}" r="${h?R0+2:Math.min(R0,step/2)}" fill="${color(r)}" ${h?'stroke="var(--hl)" stroke-width="2"':''} opacity="${q&&!h?0.25:0.95}" data-i="${D.indexOf(r)}" style="cursor:pointer"><title>${esc(r.t)} — ${esc(r.a)}: ${r.m}${r.y?' (yours '+r.y+')':''}</title></circle>`})});
  svg.innerHTML=s;
  svg.querySelectorAll('circle').forEach(c=>c.onclick=()=>show(D[+c.dataset.i]));
  svg.querySelectorAll('text[data-b]').forEach(t=>t.onclick=()=>bucket(+t.dataset.b));
  const n=rs.length,hits=q?rs.filter(hit).length:null;
  document.getElementById('cnt').textContent=`${n} songs`+(hits!==null?` · ${hits} match`:'');
}
addEventListener('resize',draw);draw();
</script></body></html>'''

if __name__ == '__main__':
    main()
