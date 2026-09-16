"""Build song.html — generic single-song viewer that takes ?slug= and renders from Supabase.
Shared rendering/playback live in song_viewer.js so all pages stay in sync."""
import os, sys
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_KEY', '')


def build(out_path):
    html = TEMPLATE.replace('__SUPABASE_URL__', SUPABASE_URL).replace('__SUPABASE_ANON_KEY__', SUPABASE_ANON_KEY)
    open(out_path, 'w').write(html)
    print(f'wrote {out_path}')


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<title>song viewer</title>
<style>
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, sans-serif; font-size: 13px; }
.layout { display: flex; height: 100vh; }
.sidebar { width: 240px; min-width: 240px; background: #16162a; border-right: 1px solid #2a2a4a; display: flex; flex-direction: column; padding: 16px; overflow: hidden; }
.sidebar h1 { font-size: 18px; margin: 0 0 4px; color: #e0e0e0; font-weight: 700; }
.sidebar .artist { font-size: 12px; color: #8a8ab0; margin-bottom: 12px; }
.sidebar .meta { font-size: 11px; color: #b0b0cc; margin-bottom: 16px; }
.sidebar .meta b { color: #e0e0e0; }
.sidebar h2 { font-size: 11px; color: #6a6a8a; text-transform: uppercase; letter-spacing: 1px; margin: 12px 0 6px; }
.transport { display: flex; gap: 6px; margin-bottom: 12px; }
.transport button { flex: 1; background: #2a2a4a; color: #e0e0e0; border: 1px solid #3a3a5a; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; }
.transport button:hover { background: #3a3a5a; }
.transport button.playing { background: #6e16a5; border-color: #8e26c5; }
.transport .tempo-input { width: 50px; background: #16162a; color: #e0e0e0; border: 1px solid #3a3a5a; border-radius: 4px; padding: 4px; text-align: center; font-size: 12px; }
.transport label { font-size: 11px; color: #8a8ab0; display: flex; align-items: center; gap: 4px; }
.section-list { overflow-y: auto; flex: 1; }
.section-item { padding: 6px 10px; cursor: pointer; font-size: 12px; border-left: 3px solid transparent; border-radius: 0 3px 3px 0; }
.section-item:hover { background: #20203a; }
.section-item.active { background: #20203a; border-left-color: #6366f1; color: #e0e0e0; }
.section-item .bar { color: #6a6a8a; font-size: 10px; margin-left: 6px; }
.main { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 12px; }
</style>
</head><body>
<div class="layout">
  <div class="sidebar">
    <h1 id="songTitle">…</h1>
    <div class="artist" id="songArtist"></div>
    <div class="meta" id="songMeta"></div>
    <div class="transport">
      <button id="playBtn">▶ Play</button>
      <button id="stopBtn">■ Stop</button>
      <label>BPM <input type="number" id="tempoInput" class="tempo-input" min="40" max="240"></label>
      <label style="margin-top:6px">show
        <select id="displaySelect" class="tempo-input" style="width:auto">
          <option value="chord">chord names</option>
          <option value="roman">roman</option>
        </select>
      </label>
    </div>
    <h2>sections</h2>
    <div class="section-list" id="sectionList"></div>
  </div>
  <div class="main" id="main"><div class="status">loading…</div></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="https://cdn.jsdelivr.net/npm/tone@14.7.77/build/Tone.js"></script>
<script src="song_viewer.js"></script>
<script>
const sb = window.supabase.createClient('__SUPABASE_URL__', '__SUPABASE_ANON_KEY__');
const viewer = new SongViewer({
  supabase: sb,
  mainEl: '#main',
  headerEls: { title: '#songTitle', artist: '#songArtist', meta: '#songMeta' },
  sectionListEl: '#sectionList',
  transport: { playBtn: '#playBtn', stopBtn: '#stopBtn', tempoInput: '#tempoInput', displaySelect: '#displaySelect' },
});
const slug = new URLSearchParams(window.location.search).get('slug');
if (!slug) {
  document.getElementById('main').innerHTML = '<div class="status">no <code>?slug=</code> in URL.<br>try <code>song.html?slug=beatles_blackbird</code></div>';
} else {
  viewer.load(slug);
}
</script>
</body></html>
"""


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'song.html')
    build(out_path)
