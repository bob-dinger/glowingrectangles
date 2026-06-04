"""Build quiz-facts.html: free-text quiz on tempo, key, and section measure-counts.

Pool = Beatles-Study + Guitar 50 + Guitar 100 + Guitar 150 (slugs pulled from those HTML pages).
Each card includes the bpm, key, and {section_name: bar_count} map for that song.
"""
import os, re, json
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
from supabase import create_client

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ['Beatles-Study.html', 'Guitar50.html', 'Guitar100.html', 'Guitar150.html']
OUT = os.path.join(HERE, 'quiz-facts.html')


def slugs_from_page(fn):
    html = open(os.path.join(HERE, fn)).read()
    m = re.search(r'const SONGS\s*=\s*(\[.*?\]);', html, flags=re.DOTALL)
    if not m:
        return []
    return [(s['slug'], s.get('title',''), s.get('artist',''))
            for s in json.loads(m.group(1)) if s.get('slug')]


def section_bar_counts(d):
    sections = d.get('sections') or []
    bpb = ((d.get('meters') or [{}])[0].get('numBeats')) or 4
    end_beat = d.get('endBeat') or 0
    sorted_secs = sorted(sections, key=lambda s: s.get('beat', 0))
    out = []
    for i, s in enumerate(sorted_secs):
        name = (s.get('name') or '').strip()
        if not name or name.lower() == 'section':
            continue
        start = s.get('beat', 0)
        end = sorted_secs[i+1]['beat'] if i+1 < len(sorted_secs) else end_beat
        bars = round((end - start) / bpb)
        if bars < 1:
            continue
        out.append({'name': name, 'bars': bars})
    return out


def build():
    sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    pool = {}
    for fn in PAGES:
        for slug, title, artist in slugs_from_page(fn):
            pool.setdefault(slug, {'title': title, 'artist': artist, 'pages': set()})['pages'].add(fn.replace('.html',''))
    slugs = list(pool.keys())
    print(f"pool: {len(slugs)} unique slugs across {PAGES}")

    cards = []
    for i in range(0, len(slugs), 100):
        chunk = slugs[i:i+100]
        rows = (sb.schema('parcels').table('songs')
                .select('slug,artist,title,bpm,hookpad_json')
                .in_('slug', chunk).execute().data)
        for r in rows:
            if not r.get('hookpad_json'):
                continue
            d = r['hookpad_json']
            bpm = (d.get('tempos') or [{}])[0].get('bpm')
            keys = d.get('keys') or []
            if not keys or bpm is None:
                continue
            k = keys[0]
            sects = section_bar_counts(d)
            meta = pool.get(r['slug'], {})
            cards.append({
                'slug': r['slug'],
                'title': meta.get('title') or r.get('title') or '',
                'artist': meta.get('artist') or r.get('artist') or '',
                'pages': sorted(meta.get('pages', set())),
                'bpm': int(round(bpm)),
                'tonic': k.get('tonic') or 'C',
                'scale': k.get('scale') or 'major',
                'sections': sects,
            })
    cards.sort(key=lambda c: (c['artist'].lower(), c['title'].lower()))
    print(f"  → {len(cards)} cards with full data")

    data_json = json.dumps(cards, separators=(',', ':'), ensure_ascii=False)
    html = TEMPLATE.replace('__DATA__', data_json)
    open(OUT, 'w').write(html)
    print(f"wrote {OUT}")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Quiz — Tempo / Key / Measures</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#16162a; color:#e0e0e0; margin:0; padding:0; height:100vh; overflow:hidden; display:flex; flex-direction:column; }
  header { padding:14px 24px; background:#20203a; border-bottom:1px solid #2a2a4a; display:flex; gap:24px; align-items:center; flex-wrap:wrap; }
  header h1 { font-size:18px; margin:0; font-weight:600; }
  .score { font-size:14px; color:#8a8ab0; }
  .score .num { color:#e0e0e0; font-weight:700; }
  .filters { display:flex; gap:6px; flex-wrap:wrap; }
  .filters button, .filters label { padding:4px 10px; background:#2a2a4a; border:1px solid #44446a; color:#e0e0e0; border-radius:4px; font-size:12px; cursor:pointer; display:inline-flex; align-items:center; gap:4px; }
  .filters button.active, .filters input:checked + span { background:#6366f1; border-color:#6366f1; }
  .filters input { display:none; }

  main { flex:1; display:flex; align-items:center; justify-content:center; padding:24px; }
  .card { background:#20203a; border:1px solid #2a2a4a; border-radius:12px; padding:36px 44px; min-width:420px; max-width:640px; text-align:center; }
  .pool-badge { font-size:11px; color:#8a8ab0; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; }
  .song { font-size:28px; font-weight:600; margin-bottom:4px; }
  .artist { font-size:16px; color:#8a8ab0; margin-bottom:32px; }
  .question { font-size:20px; margin-bottom:18px; line-height:1.4; }
  .question .hl { color:#a5b4fc; font-weight:600; }
  .reveal-area { margin-top:24px; min-height:120px; display:flex; flex-direction:column; justify-content:center; align-items:center; }
  .reveal-btn { background:#2a2a4a; border:2px dashed #44446a; color:#a5b4fc; padding:24px 40px; font-size:18px; border-radius:8px; cursor:pointer; font-family:inherit; min-width:280px; }
  .reveal-btn:hover { background:#33335a; border-color:#6366f1; }
  .answer { font-size:42px; font-weight:700; color:#a5b4fc; margin-bottom:8px; line-height:1.1; }
  .scorer { display:flex; gap:10px; margin-top:18px; }
  button.primary { background:#6366f1; color:#fff; border:none; padding:10px 20px; font-size:14px; border-radius:6px; cursor:pointer; font-weight:600; font-family:inherit; }
  button.primary:hover { background:#5258e8; }
  button.got    { background:#16a34a; color:#fff; border:none; padding:12px 28px; font-size:15px; border-radius:6px; cursor:pointer; font-weight:700; font-family:inherit; }
  button.got:hover    { background:#15803d; }
  button.missed { background:#dc2626; color:#fff; border:none; padding:12px 28px; font-size:15px; border-radius:6px; cursor:pointer; font-weight:700; font-family:inherit; }
  button.missed:hover { background:#b91c1c; }
  .next-hint { margin-top:12px; font-size:12px; color:#8a8ab0; }
  kbd { background:#16162a; border:1px solid #44446a; padding:1px 6px; border-radius:3px; font-family:monospace; font-size:11px; }
  .empty { color:#8a8ab0; font-size:14px; }
</style>
</head>
<body>
<header>
  <h1>Quiz — Tempo · Key · Measures</h1>
  <div class="score">Score: <span class="num" id="correct">0</span> / <span class="num" id="total">0</span> <span id="streak"></span></div>
  <div class="filters" id="qfilters">
    <span style="font-size:11px;color:#8a8ab0;">QUESTIONS:</span>
    <label><input type="checkbox" value="tempo" checked><span>tempo</span></label>
    <label><input type="checkbox" value="key" checked><span>key</span></label>
    <label><input type="checkbox" value="measures" checked><span>measures</span></label>
  </div>
  <div class="filters" id="pfilters">
    <span style="font-size:11px;color:#8a8ab0;">POOL:</span>
    <label><input type="checkbox" value="Beatles-Study" checked><span>Beatles</span></label>
    <label><input type="checkbox" value="Guitar50" checked><span>G50</span></label>
    <label><input type="checkbox" value="Guitar100" checked><span>G100</span></label>
    <label><input type="checkbox" value="Guitar150" checked><span>G150</span></label>
  </div>
  <button class="primary" id="skipBtn" style="margin-left:auto">Skip ⏭</button>
</header>
<main id="main"></main>

<script>
const SONGS = __DATA__;

function pickSongsAndQuestion() {
  const qTypes = [...document.querySelectorAll('#qfilters input:checked')].map(i=>i.value);
  const pools = [...document.querySelectorAll('#pfilters input:checked')].map(i=>i.value);
  if (!qTypes.length || !pools.length) return null;
  const eligible = SONGS.filter(s => s.pages.some(p => pools.includes(p)));
  if (!eligible.length) return null;
  for (let attempt = 0; attempt < 50; attempt++) {
    const s = eligible[Math.floor(Math.random()*eligible.length)];
    const qt = qTypes[Math.floor(Math.random()*qTypes.length)];
    if (qt === 'measures' && !s.sections.length) continue;
    return { song: s, qType: qt };
  }
  return null;
}

let state = { correct: 0, total: 0, current: null, revealed: false };

function render() {
  const main = document.getElementById('main');
  if (!state.current) {
    const c = pickSongsAndQuestion();
    if (!c) { main.innerHTML = '<div class="empty">No songs match your filters.</div>'; return; }
    if (c.qType === 'measures') {
      c.section = c.song.sections[Math.floor(Math.random()*c.song.sections.length)];
    }
    state.current = c;
    state.revealed = false;
  }
  const {song, qType, section, revealed} = {...state.current, revealed: state.revealed};
  let questionHtml;
  if (qType === 'tempo') questionHtml = `What's the <span class="hl">tempo</span> (BPM)?`;
  else if (qType === 'key') questionHtml = `What's the <span class="hl">key</span>?`;
  else questionHtml = `How many <span class="hl">measures</span> is the <span class="hl">${section.name}</span>?`;

  let answerStr;
  if (qType === 'tempo') answerStr = `${song.bpm} BPM`;
  else if (qType === 'key') answerStr = `${song.tonic}${song.scale === 'minor' ? ' minor' : ''}`;
  else answerStr = `${section.bars} measures`;

  const revealHtml = revealed
    ? `<div class="answer">${answerStr}</div>
       <div class="scorer">
         <button class="missed" id="missedBtn">Missed ✗</button>
         <button class="got" id="gotBtn">Got it ✓</button>
       </div>
       <div class="next-hint"><kbd>J</kbd> missed · <kbd>K</kbd> got it</div>`
    : `<button class="reveal-btn" id="revealBtn">Reveal answer</button>
       <div class="next-hint"><kbd>Space</kbd> reveal · <kbd>→</kbd> skip</div>`;

  main.innerHTML = `
    <div class="card">
      <div class="pool-badge">${song.pages.join(' · ')}</div>
      <div class="song">${song.title}</div>
      <div class="artist">${song.artist}</div>
      <div class="question">${questionHtml}</div>
      <div class="reveal-area">${revealHtml}</div>
    </div>
  `;
  if (!revealed) document.getElementById('revealBtn').addEventListener('click', reveal);
  else {
    document.getElementById('gotBtn').addEventListener('click', () => score(true));
    document.getElementById('missedBtn').addEventListener('click', () => score(false));
  }
}

function reveal() {
  state.revealed = true;
  render();
}
function score(got) {
  state.total += 1;
  if (got) state.correct += 1;
  document.getElementById('correct').textContent = state.correct;
  document.getElementById('total').textContent = state.total;
  nextQuestion();
}
function nextQuestion() {
  state.current = null;
  render();
}

document.getElementById('skipBtn').addEventListener('click', nextQuestion);
document.querySelectorAll('#qfilters input, #pfilters input').forEach(el => {
  el.addEventListener('change', () => { state.current = null; render(); });
});
window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  if (!state.revealed && (e.key === ' ' || e.key === 'Enter')) { e.preventDefault(); reveal(); }
  else if (state.revealed && (e.key === 'k' || e.key === 'K' || e.key === 'Enter')) { e.preventDefault(); score(true); }
  else if (state.revealed && (e.key === 'j' || e.key === 'J')) { e.preventDefault(); score(false); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); nextQuestion(); }
});
render();
</script>
</body>
</html>
"""


if __name__ == '__main__':
    build()
