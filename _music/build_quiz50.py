"""Build quiz50.html — structural-fingerprint quiz over Guitar 50.

For each song, displays:
  - tempo + key/scale
  - each section: name, bar count, full chord progression with | between measures
  - title/artist hidden, click to reveal
Shuffles order on load; "Shuffle" button to re-randomize.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client
from build_study_list_page import resolve_slug
from rebuild_studied_songs import USER_LIST

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quiz50.html')

QUAL = {'major':['M','m','m','M','M','m','d'],'minor':['m','d','M','m','m','M','M'],
        'dorian':['m','m','M','M','m','d','M'],'mixolydian':['M','m','d','M','m','m','M'],
        'lydian':['M','M','m','d','M','m','m'],'phrygian':['m','M','M','m','d','M','m'],
        'locrian':['d','M','m','m','M','M','m'],'harmonicMinor':['m','d','a','m','M','M','d']}
ROMAN_UP = ['I','II','III','IV','V','VI','VII']
ROMAN_LO = ['i','ii','iii','iv','v','vi','vii']


def chord_label(c, key_scale='major'):
    root = str(c.get('root',''))
    acc, rs = '', root
    while rs and rs[0] in 'b#':
        acc += rs[0]; rs = rs[1:]
    if not rs.isdigit(): return '?'
    deg = int(rs)
    typ = c.get('type','')
    borrowed = c.get('borrowed','') if isinstance(c.get('borrowed'), str) else ''
    if c.get('applied'): q = 'M'
    elif typ in ('m', 'min'): q = 'm'
    else:
        mode = borrowed if borrowed in QUAL else key_scale
        q = QUAL.get(mode, QUAL['major'])[deg-1]
    r = ROMAN_UP[deg-1] if q in ('M', 'a') else ROMAN_LO[deg-1]
    label = acc + r
    if typ in ('7', 7): label += '7'
    if q == 'd': label += '°'
    if c.get('applied'): label += f"/{ROMAN_UP[c['applied']-1]}"
    return label


def section_str(start, n_bars, section_chords, bpb, key_scale):
    measures = [[] for _ in range(n_bars)]
    for c in section_chords:
        idx = int((c['beat'] - start) / bpb)
        if 0 <= idx < n_bars:
            measures[idx].append(chord_label(c, key_scale))
    out, last = [], None
    for m in measures:
        if m:
            out.append(' '.join(m)); last = m[-1]
        else:
            out.append(last if last else '—')
    return ' | '.join(out)


def build():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    cards = []
    for title, artist in USER_LIST:
        slug = resolve_slug(title, artist)
        if not slug:
            continue
        r = sb.schema('parcels').table('songs').select('hookpad_json').eq('slug', slug).limit(1).execute()
        if not r.data or not r.data[0]['hookpad_json']:
            continue
        d = r.data[0]['hookpad_json']
        bpm = (d.get('tempos') or [{}])[0].get('bpm') or '?'
        bpb = (d.get('meters') or [{}])[0].get('numBeats') or 4
        key_scale = (d.get('keys') or [{}])[0].get('scale', 'major')
        sections = d.get('sections', [])
        chords = d.get('chords', [])
        end_beat = d.get('endBeat', 999999)

        sec_rows = []
        for i, s in enumerate(sections):
            nb = sections[i+1]['beat'] if i+1 < len(sections) else end_beat
            bars = round((nb - s['beat']) / bpb)
            if bars < 1: continue
            sec_ch = [c for c in chords if s['beat'] <= c.get('beat', 0) < nb and not c.get('isRest')]
            if not sec_ch:
                continue  # drop empty sections
            prog = section_str(s['beat'], bars, sec_ch, bpb, key_scale)
            sec_rows.append({'name': s.get('name', '?'), 'bars': bars, 'prog': prog})

        if not sec_rows:
            continue

        cards.append({
            'title': title, 'artist': artist, 'slug': slug,
            'bpm': bpm, 'scale': key_scale, 'sections': sec_rows,
        })

    data_json = json.dumps(cards, separators=(',', ':'))
    html = TEMPLATE.replace('__CARDS__', data_json).replace('__COUNT__', str(len(cards)))
    open(OUT, 'w').write(html)
    print(f'wrote {OUT}  ({len(cards)} cards)')


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Guitar 50 — structural quiz</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }
header {
  position: sticky; top: 0; background: #0f0f1f; padding: 10px 18px; border-bottom: 1px solid #2a2a4a;
  display: flex; align-items: center; gap: 14px; z-index: 10;
}
header h1 { margin: 0; font-size: 16px; font-weight: 700; }
header .meta { font-size: 12px; color: #8a8ab0; }
header button {
  background: #2a2a4a; color: #e0e0e0; border: 1px solid #3a3a5a;
  padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;
}
header button:hover { background: #3a3a5a; }
header .score { margin-left: auto; font-size: 12px; color: #b0b0cc; }
header .score b { color: #e0e0e0; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 12px; padding: 14px; }
.card {
  background: #20203a; border: 1px solid #2a2a4a; border-radius: 6px;
  padding: 12px 14px; cursor: pointer; transition: border-color 0.15s, background 0.15s;
}
.card:hover { border-color: #6366f1; background: #25254a; }
.card .header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
  font-size: 11px; color: #8a8ab0; text-transform: uppercase; letter-spacing: 1px;
}
.card .header .num { background: #16162a; padding: 2px 8px; border-radius: 10px; color: #e0e0e0; font-weight: 700; }
.card .header .bpm { color: #b0b0cc; }
.card .header .scale { color: #6e16a5; font-weight: 700; }

.sections { font-family: 'SF Mono', Menlo, monospace; font-size: 12px; line-height: 1.5; }
.sec-row { display: flex; gap: 10px; padding: 3px 0; }
.sec-row .sec-name {
  flex: 0 0 90px; color: #b0b0cc; font-weight: 600; text-transform: capitalize;
}
.sec-row .sec-bars { flex: 0 0 30px; color: #6a6a8a; text-align: right; }
.sec-row .sec-prog { flex: 1; color: #e0e0e0; word-break: break-word; }
.sec-row .sec-prog .pipe { color: #ffd700; font-weight: 900; padding: 0 6px; }

.answer {
  margin-top: 10px; padding-top: 8px; border-top: 1px dashed #3a3a5a;
  display: none; font-size: 13px;
}
.answer .title { font-weight: 700; color: #fff; font-size: 14px; }
.answer .artist { color: #8a8ab0; font-size: 12px; }
.answer .actions { display: flex; gap: 6px; margin-top: 6px; }
.answer .actions button {
  background: transparent; border: 1px solid #3a3a5a; color: #b0b0cc;
  padding: 3px 10px; border-radius: 3px; cursor: pointer; font-size: 11px;
}
.answer .actions button.got    { border-color: #25a838; color: #5bd470; }
.answer .actions button.missed { border-color: #a01e1e; color: #f08585; }
.answer .actions button:hover  { background: #2a2a4a; }
.answer .actions a {
  margin-left: auto; color: #6366f1; font-size: 11px; text-decoration: none;
}
.answer .actions a:hover { text-decoration: underline; }
.card.revealed .answer { display: block; }
.card.got    { border-color: #25a838; }
.card.missed { border-color: #a01e1e; }

.hint { padding: 6px 14px 0; color: #6a6a8a; font-size: 11px; }
</style>
</head><body>
<header>
  <h1>Guitar 50 — structural quiz</h1>
  <span class="meta">__COUNT__ songs</span>
  <button id="shuffleBtn">↻ Shuffle</button>
  <button id="revealAllBtn">Reveal all</button>
  <button id="resetBtn">Reset scores</button>
  <span class="score">score: <b id="scoreGot">0</b> got · <b id="scoreMissed">0</b> missed · <b id="scoreLeft">__COUNT__</b> open</span>
</header>
<div class="hint">click a card to reveal the answer. mark "got" or "missed".</div>
<div class="grid" id="grid"></div>

<script>
const CARDS = __CARDS__;

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

let order = shuffle(CARDS);
const state = {}; // slug → 'got' | 'missed' | undefined

function fmtProg(p) {
  return p.split(' | ').map(m => `<span>${m}</span>`).join('<span class="pipe">|</span>');
}

function render() {
  const grid = document.getElementById('grid');
  grid.innerHTML = order.map((c, i) => {
    const s = state[c.slug] || '';
    return `<div class="card ${s}" data-slug="${c.slug}">
      <div class="header">
        <span class="num">${i+1}</span>
        <span class="bpm">tempo ${c.bpm}</span>
        <span class="scale">${c.scale}</span>
      </div>
      <div class="sections">
        ${c.sections.map(sec => `
          <div class="sec-row">
            <div class="sec-name">${sec.name}</div>
            <div class="sec-bars">${sec.bars}b</div>
            <div class="sec-prog">${fmtProg(sec.prog)}</div>
          </div>`).join('')}
      </div>
      <div class="answer">
        <div class="title">${c.title}</div>
        <div class="artist">${c.artist}</div>
        <div class="actions">
          <button class="got"    data-mark="got">got it</button>
          <button class="missed" data-mark="missed">missed</button>
          <a href="song.html?slug=${c.slug}" target="_blank">open viewer →</a>
        </div>
      </div>
    </div>`;
  }).join('');
  updateScore();
}

function updateScore() {
  const got = Object.values(state).filter(v => v === 'got').length;
  const missed = Object.values(state).filter(v => v === 'missed').length;
  document.getElementById('scoreGot').textContent = got;
  document.getElementById('scoreMissed').textContent = missed;
  document.getElementById('scoreLeft').textContent = order.length - got - missed;
}

document.getElementById('grid').addEventListener('click', e => {
  const markBtn = e.target.closest('button[data-mark]');
  const card = e.target.closest('.card');
  if (!card) return;
  const slug = card.dataset.slug;
  if (markBtn) {
    const mark = markBtn.dataset.mark;
    state[slug] = mark;
    card.classList.remove('got','missed');
    card.classList.add(mark);
    updateScore();
    e.stopPropagation();
    return;
  }
  card.classList.toggle('revealed');
});

document.getElementById('shuffleBtn').onclick = () => { order = shuffle(CARDS); render(); };
document.getElementById('revealAllBtn').onclick = () =>
  document.querySelectorAll('.card').forEach(c => c.classList.add('revealed'));
document.getElementById('resetBtn').onclick = () => {
  for (const k of Object.keys(state)) delete state[k];
  document.querySelectorAll('.card').forEach(c => { c.classList.remove('got','missed','revealed'); });
  updateScore();
};

render();
</script>
</body></html>
"""


if __name__ == '__main__':
    build()
