"""Randomly sample N MIDIs from ~/Desktop/midi_files2, deep-analyze each, and output an HTML viewer.

Per-song analysis:
  - Tempo, key sig, time sig, duration (from header)
  - Tracks: name, instrument (GM program), note count, pitch range
  - Inferred key from pitch-class distribution
  - First 32 detected chord changes (from harmony tracks combined)
  - Melody track guess (narrow range + vocal register + moderate note count)
  - Quality score: POOR / OK / GOOD based on file integrity + content

Usage: analyze_midi_samples.py [N] [--seed SEED]
"""
import os, sys, csv, json, mido, random, collections, html
from datetime import datetime

DST = os.path.expanduser('~/Desktop/midi_files2')
CSV_IN = os.path.expanduser('~/Desktop/midi_files2.csv')
HTML_OUT = os.path.expanduser('~/Desktop/midi_samples.html')

N = 100
seed = None
args = sys.argv[1:]
if args and args[0].isdigit(): N = int(args[0]); args = args[1:]
if '--seed' in args: seed = int(args[args.index('--seed')+1])

GM = ['Piano','Bright Piano','EP Grand','Honky-tonk','EP1','EP2','Harpsi','Clav','Celesta','Glockenspiel','Music Box','Vibraphone','Marimba','Xylo','Tubular','Dulcimer','Drawbar Org','Perc Org','Rock Org','Church Org','Reed Org','Accordion','Harmonica','Tango Accordion','Nylon Guitar','Steel Guitar','Jazz Guitar','Clean Guitar','Muted Guitar','Overdriven','Distortion','Guitar Harm','Acoustic Bass','Electric Bass (finger)','Electric Bass (pick)','Fretless Bass','Slap Bass 1','Slap Bass 2','Synth Bass 1','Synth Bass 2','Violin','Viola','Cello','Contrabass','Tremolo Strings','Pizzicato','Harp','Timpani','Strings 1','Strings 2','SynthStr 1','SynthStr 2','Choir Aahs','Voice Oohs','Synth Voice','Orch Hit','Trumpet','Trombone','Tuba','Muted Trumpet','French Horn','Brass Section','SynthBr 1','SynthBr 2','Sop Sax','Alto Sax','Tenor Sax','Bari Sax','Oboe','English Horn','Bassoon','Clarinet','Piccolo','Flute','Recorder','Pan Flute','Blown Bottle','Shakuhachi','Whistle','Ocarina','Lead Square','Lead Saw','Lead Calliope','Lead Chiff','Lead Charang','Lead Voice','Lead 5th','Lead Bass+Lead','Pad NewAge','Pad Warm','Pad Poly','Pad Choir','Pad Bowed','Pad Metal','Pad Halo','Pad Sweep','FX Rain','FX Sndtrk','FX Crystal','FX Atm','FX Bright','FX Goblin','FX Echo','FX Sci','Sitar','Banjo','Shamisen','Koto','Kalimba','BagPipe','Fiddle','Shanai','TinkleBell','Agogo','SteelDrums','Woodblock','Taiko','MelodicTom','SynthDrum','RevCymbal','GFX','Breath','Seashore','BirdTweet','TelRing','Helicopter','Applause','Gunshot']
NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def track_notes(t):
    """Return [(start_tick, pitch, end_tick, channel)] for a single track."""
    out = []; abs_t = 0; starts = {}
    for msg in t:
        abs_t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            starts[msg.note] = abs_t
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in starts:
                out.append((starts.pop(msg.note), msg.note, abs_t))
    return out


def analyze(path):
    try:
        m = mido.MidiFile(path)
    except Exception as e:
        return {'error': str(e)[:120]}
    ppq = m.ticks_per_beat
    tempo_bpm = None; ts = None; ks = None
    for tk in m.tracks:
        for msg in tk:
            if msg.type == 'set_tempo' and tempo_bpm is None:
                tempo_bpm = round(mido.tempo2bpm(msg.tempo), 1)
            if msg.type == 'time_signature' and ts is None:
                ts = f'{msg.numerator}/{msg.denominator}'
            if msg.type == 'key_signature' and ks is None:
                ks = msg.key
    # Per-track summary
    tracks = []
    all_harmony_notes = []
    for i, tk in enumerate(m.tracks):
        name = ''; program = None; channel = 0
        for msg in tk:
            if msg.type == 'track_name': name = msg.name
            if msg.type == 'program_change': program = msg.program; channel = msg.channel
        notes = track_notes(tk)
        if not notes: continue
        pitches = [p for _,p,_ in notes]
        pmin, pmax = min(pitches), max(pitches)
        median = sorted(pitches)[len(pitches)//2]
        is_drum = channel == 9 or (program is None and pmin < 50 and pmax < 60 and len(notes) > 100)
        instr = 'Drums' if is_drum else (GM[program] if program is not None else 'meta')
        tracks.append({'i': i, 'name': name, 'instrument': instr, 'notes': len(notes),
                       'pitch_min': pmin, 'pitch_max': pmax, 'median': median,
                       'range': pmax - pmin, 'is_drum': is_drum})
        if not is_drum:
            all_harmony_notes.append((i, notes))
    # Melody guess: track with narrowest pitch range + median in vocal register (55-80), not drum
    melody_candidates = [t for t in tracks
                        if not t['is_drum'] and t['range'] <= 28 and 50 <= t['median'] <= 84
                        and 30 <= t['notes'] <= 1500]
    melody = sorted(melody_candidates, key=lambda t: (t['range'], -t['notes']))[0] if melody_candidates else None

    # Inferred key from pitch distribution
    pcs = collections.Counter()
    for _, notes in all_harmony_notes:
        for _, p, _ in notes: pcs[p % 12] += 1
    inferred_key = None
    if pcs:
        # Krumhansl-like: find tonic that has best major-scale fit
        best = (None, -1)
        for tonic in range(12):
            scale = {(tonic+iv)%12 for iv in [0,2,4,5,7,9,11]}
            score = sum(pcs.get(pc, 0) for pc in scale) / max(sum(pcs.values()), 1)
            score += 0.05 * pcs.get(tonic, 0) / max(sum(pcs.values()), 1)
            if score > best[1]: best = (NAMES[tonic], score)
        inferred_key = best[0]

    # Chord progression from combined harmony tracks
    combined = []
    for _, notes in all_harmony_notes: combined.extend(notes)
    if combined:
        end_tick = max(e for _,_,e in combined)
        end_beat = end_tick // ppq
    else:
        end_beat = 0

    QUAL = {'':(0,4,7),'m':(0,3,7),'7':(0,4,7,10),'m7':(0,3,7,10),
            'dim':(0,3,6),'sus4':(0,5,7),'sus2':(0,2,7)}
    def identify(weights):
        if not weights: return None
        best = (None,-1)
        for r in range(12):
            for q, iv in QUAL.items():
                cps = {(r+x)%12 for x in iv}
                sc = sum(weights.get(p,0) for p in cps) + 0.5*weights.get(r,0)
                if len(iv)==3: sc *= 1.05
                if sc > best[1]: best = (NAMES[r]+q, sc)
        return best[0]
    progression = []
    last = None
    for beat in range(min(end_beat+1, 200)):  # cap at 200 beats for the summary
        t0, t1 = beat*ppq, (beat+1)*ppq
        w = collections.Counter()
        for s, p, e in combined:
            if s < t1 and e > t0:
                w[p%12] += (min(e,t1)-max(s,t0))/ppq
        c = identify(w) if w else None
        if c != last:
            progression.append((beat, c)); last = c
    # Trim to changes only (skip Nones consecutively)
    progression = [(b, c) for b, c in progression if c is not None][:32]

    # Quality score
    duration = round(m.length, 1) if m.length else 0
    flags = []
    if duration < 30: flags.append('short')
    if len(tracks) < 2: flags.append('few-tracks')
    if not melody: flags.append('no-melody')
    if not progression: flags.append('no-chords')
    if not tempo_bpm: flags.append('no-tempo')
    quality = 'GOOD' if not flags else ('OK' if len(flags) <= 1 else 'POOR')

    return {
        'tempo': tempo_bpm, 'time_sig': ts, 'key_sig': ks, 'inferred_key': inferred_key,
        'duration': duration, 'tracks': tracks, 'melody_track': melody['i'] if melody else None,
        'progression': progression, 'quality': quality, 'flags': flags,
        'ppq': ppq, 'end_beat': end_beat,
    }


def main():
    rng = random.Random(seed)
    rows = [r for r in csv.DictReader(open(CSV_IN)) if r.get('new_name') and not r.get('error')]
    print(f'catalog has {len(rows)} entries; sampling {N}')
    sample = rng.sample(rows, min(N, len(rows)))

    results = []
    for i, r in enumerate(sample, 1):
        path = os.path.join(DST, r['new_name'])
        if not os.path.exists(path): continue
        a = analyze(path)
        a['orig_name'] = r['orig_name']
        a['new_name'] = r['new_name']
        a['artist'] = r.get('artist','')
        a['title'] = r.get('title','')
        results.append(a)
        if i % 20 == 0: print(f'  [{i}/{N}]')

    # Build HTML
    n_good = sum(1 for r in results if r.get('quality') == 'GOOD')
    n_ok   = sum(1 for r in results if r.get('quality') == 'OK')
    n_poor = sum(1 for r in results if r.get('quality') == 'POOR')

    def color(q):
        return {'GOOD':'#25a838','OK':'#b35610','POOR':'#a01e1e'}.get(q, '#44446a')

    cards = []
    for r in results:
        if r.get('error'):
            cards.append(f'<div class="card poor"><div class="hdr"><b>{html.escape(r["new_name"])}</b> '
                         f'<span class="q" style="background:#a01e1e">PARSE ERROR</span></div>'
                         f'<div class="err">{html.escape(r["error"])}</div></div>')
            continue
        prog = ' → '.join(f'<span class="ch">{html.escape(c)}</span>' for _, c in r.get('progression', []))
        mel_idx = r.get('melody_track')
        tracks_html = ''.join(
            f'<tr><td>{t["i"]}</td><td>{html.escape(t["name"][:30])}</td>'
            f'<td>{html.escape(t["instrument"])}</td><td>{t["notes"]}</td>'
            f'<td>{t["pitch_min"]}-{t["pitch_max"]}</td>'
            f'<td>{"★" if t["i"] == mel_idx else ""}</td></tr>'
            for t in r.get('tracks', [])
        )
        flags_html = ' '.join(f'<span class="flag">{f}</span>' for f in r.get('flags', []))
        q = r.get('quality', 'POOR')
        cards.append(f'''<div class="card {q.lower()}">
            <div class="hdr">
                <b>{html.escape(r.get("artist","") + " — " + r.get("title",""))}</b>
                <span class="q" style="background:{color(q)}">{q}</span>
                <span class="meta">tempo {r.get('tempo') or '?'} · key {r.get('inferred_key') or r.get('key_sig') or '?'}
                · {r.get('time_sig') or '?'} · {r.get('duration', 0)}s · {r.get('end_beat', 0)} beats · {len(r.get('tracks',[]))} tracks</span>
                {flags_html}
            </div>
            <div class="prog">{prog}</div>
            <table class="tracks"><thead><tr><th>#</th><th>name</th><th>instrument</th><th>notes</th><th>pitch</th><th>mel?</th></tr></thead>
                <tbody>{tracks_html}</tbody></table>
            <div class="file">{html.escape(r["new_name"])}</div>
        </div>''')

    full = f'''<!doctype html><html><head><meta charset="utf-8"><title>MIDI samples ({N})</title>
<style>
* {{ box-sizing: border-box; }}
body {{ background:#1a1a2e; color:#e0e0e0; font-family: -apple-system, sans-serif; font-size: 12px; margin: 0; padding: 14px; }}
header {{ margin-bottom: 16px; }}
header h1 {{ font-size: 18px; margin: 0 0 4px; }}
header .stats {{ font-size: 12px; color:#8a8ab0; }}
.grid {{ display: grid; grid-template-columns: 1fr; gap: 10px; }}
.card {{ background:#20203a; border:1px solid #2a2a4a; border-radius: 6px; padding: 10px 14px; border-left: 4px solid #44446a; }}
.card.good {{ border-left-color: #25a838; }}
.card.ok   {{ border-left-color: #b35610; }}
.card.poor {{ border-left-color: #a01e1e; }}
.hdr {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }}
.hdr b {{ font-size: 14px; }}
.q {{ font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 10px; color: white; }}
.meta {{ color:#8a8ab0; font-size: 11px; }}
.flag {{ background:#a01e1e; color: white; font-size: 10px; padding: 1px 6px; border-radius: 8px; }}
.prog {{ font-family: monospace; font-size: 12px; color:#e0e0e0; margin: 8px 0; word-break: break-word; }}
.ch {{ background:#16162a; padding: 1px 6px; border-radius: 3px; margin: 0 2px; color: #ffd700; }}
table.tracks {{ width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 11px; }}
table.tracks th {{ text-align: left; color: #6a6a8a; padding: 3px 6px; border-bottom: 1px solid #2a2a4a; text-transform: uppercase; font-size: 10px; }}
table.tracks td {{ padding: 3px 6px; border-bottom: 1px solid rgba(42,42,74,0.4); }}
.file {{ font-family: monospace; color: #6a6a8a; font-size: 10px; margin-top: 4px; }}
.err {{ color: #f08585; font-family: monospace; font-size: 11px; }}
</style></head><body>
<header>
<h1>MIDI samples — {len(results)} random songs from midi_files2</h1>
<div class="stats">{n_good} GOOD · {n_ok} OK · {n_poor} POOR · catalog has {len(rows)} files · generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</header>
<div class="grid">{''.join(cards)}</div>
</body></html>'''
    open(HTML_OUT, 'w').write(full)
    print(f'\n{n_good} GOOD · {n_ok} OK · {n_poor} POOR')
    print(f'wrote → {HTML_OUT}')


if __name__ == '__main__':
    main()
