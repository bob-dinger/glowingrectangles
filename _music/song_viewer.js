// song_viewer.js — shared rendering + playback for any page that wants to display a Hookpad song.
//
// Usage:
//   const viewer = new SongViewer({
//     supabase: sb,          // supabase-js client
//     mainEl: '#main',       // container for the chord/melody visualization
//     headerEls: {           // optional: elements to update with song metadata
//       title: '#songTitle', artist: '#songArtist', meta: '#songMeta',
//     },
//     sectionListEl: '#sectionList',   // optional sidebar of sections (rendered after load)
//     transport: { playBtn, stopBtn, tempoInput },  // optional playback UI elements
//   });
//   await viewer.load('alan-jackson_gone-country_o');

(function () {
  'use strict';

  // ---------- Music theory helpers ----------
  const MAJOR_INT = [0, 2, 4, 5, 7, 9, 11];
  const MINOR_INT = [0, 2, 3, 5, 7, 8, 10];
  const NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const NOTES_FLAT  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
  const PC_NAMES = NOTES_SHARP;

  const MODE_QUALITIES = {
    'major':            ['M','m','m','M','M','m','d'],
    'minor':            ['m','d','M','m','m','M','M'],
    'dorian':           ['m','m','M','M','m','d','M'],
    'mixolydian':       ['M','m','d','M','m','m','M'],
    'lydian':           ['M','M','m','d','M','m','m'],
    'phrygian':         ['m','M','M','m','d','M','m'],
    'locrian':          ['d','M','m','m','M','M','m'],
    'harmonicMinor':    ['m','d','a','m','M','M','d'],
    'phrygianDominant': ['M','M','d','m','d','M','m'],
  };
  const MODE_INT = {
    'major':            [0,2,4,5,7,9,11],
    'minor':            [0,2,3,5,7,8,10],
    'dorian':           [0,2,3,5,7,9,10],
    'mixolydian':       [0,2,4,5,7,9,10],
    'lydian':           [0,2,4,6,7,9,11],
    'phrygian':         [0,1,3,5,7,8,10],
    'locrian':          [0,1,3,5,6,8,10],
    'harmonicMinor':    [0,2,3,5,7,8,11],
    'phrygianDominant': [0,1,4,5,7,8,10],
  };

  function tonicSemis(t) {
    let i = NOTES_SHARP.indexOf(t); if (i >= 0) return i;
    i = NOTES_FLAT.indexOf(t); return i >= 0 ? i : 0;
  }
  function stripAcc(s) {
    let acc = 0, rs = String(s || '');
    while (rs.length && (rs[0] === 'b' || rs[0] === '#')) { acc += rs[0] === 'b' ? -1 : 1; rs = rs.slice(1); }
    return { acc, rs };
  }
  function degToPc(rootStr, keyTonic, mode) {
    const { acc, rs } = stripAcc(rootStr);
    if (!/^\d+$/.test(rs)) return null;
    const deg = parseInt(rs);
    if (deg < 1 || deg > 7) return null;
    const intervals = MODE_INT[mode] || MODE_INT['major'];
    return (((tonicSemis(keyTonic) + intervals[deg-1] + acc) % 12) + 12) % 12;
  }
  function chordRootPc(c, keyTonic, keyScale) {
    // Accept a bare root string/number for callers that just want degree→pc lookup.
    if (typeof c !== 'object' || c === null) return degToPc(String(c), keyTonic, keyScale);
    // Applied chord: re-anchor to the applied target as new tonic (treated as major).
    if (c.applied) {
      const tgtPc = degToPc(String(c.applied), keyTonic, keyScale);
      if (tgtPc == null) return null;
      return degToPc(String(c.root), NOTES_SHARP[tgtPc], 'major');
    }
    const borrowed = typeof c.borrowed === 'string' ? c.borrowed : '';
    const mode = MODE_INT[borrowed] ? borrowed : keyScale;
    return degToPc(String(c.root), keyTonic, mode);
  }
  function noteMidi(n, keyTonic, keyScale) {
    const { acc, rs } = stripAcc(n.sd ?? '1');
    if (!/^\d+$/.test(rs)) return null;
    const deg = parseInt(rs);
    if (deg < 1 || deg > 7) return null;
    const intervals = keyScale === 'minor' ? MINOR_INT : MAJOR_INT;
    const octave = n.octave ?? 0;
    return (octave + 5) * 12 + tonicSemis(keyTonic) + intervals[deg-1] + acc;
  }
  function notePitchValue(n) {
    const { acc, rs } = stripAcc(n.sd ?? '1');
    if (!/^\d+$/.test(rs)) return null;
    const deg = parseInt(rs);
    if (deg < 1 || deg > 7) return null;
    return ((n.octave ?? 0) * 12) + MAJOR_INT[deg-1] + acc;
  }
  function chordMidiPitches(c, keyTonic, keyScale) {
    const pc = chordRootPc(c, keyTonic, keyScale);
    if (pc == null) return [];
    const root = 48 + pc;
    const { rs } = stripAcc(c.root);
    const deg = /^\d+$/.test(rs) ? parseInt(rs) : 1;
    const borrowed = typeof c.borrowed === 'string' ? c.borrowed : '';
    const typ = c.type;
    let intervals;
    if (c.applied) {
      intervals = [0, 4, 7, 10];
    } else {
      let q;
      if (typ === 'm' || typ === 'min') q = 'm';
      else {
        const mode = MODE_QUALITIES[borrowed] ? borrowed : keyScale;
        const qualities = MODE_QUALITIES[mode] || MODE_QUALITIES['major'];
        q = qualities[deg - 1];
      }
      if (q === 'M')      intervals = [0, 4, 7];
      else if (q === 'm') intervals = [0, 3, 7];
      else if (q === 'd') intervals = [0, 3, 6];
      else if (q === 'a') intervals = [0, 4, 8];
      else                intervals = [0, 4, 7];
      if (typ === '7' || typ === 7) intervals.push(q === 'd' ? 9 : 10);
    }
    return intervals.map(iv => root + iv);
  }
  function keyAtBeat(keys, beat) {
    if (!keys || !keys.length) return { tonic: 'C', scale: 'major' };
    let a = keys[0];
    for (const k of keys) if ((k.beat ?? 1) <= beat) a = k;
    return a;
  }

  // ---------- Build derived data structures from raw Hookpad JSON ----------
  function buildSongData(d) {
    const sections = d.sections || [];
    const chords = d.chords || [];
    const keys = d.keys?.length ? d.keys : [{ beat: 1, scale: 'major', tonic: 'C' }];
    const bpm = (d.tempos?.[0]?.bpm) ?? 120;
    const bpb = (d.meters?.[0]?.numBeats) ?? 4;
    const endBeat = d.endBeat || 0;
    const totalBars = endBeat ? Math.round(endBeat / bpb) : 8;

    const ai = d.activeMelodyIndex ?? 0;
    const notes = ai === 0 ? (d.notes || []) : ((d.inactiveNotes || [])[0] || []);

    const primary = keys[0];
    const keyStr = (primary.tonic || 'C') + (primary.scale === 'minor' ? 'm' : '');

    const chordBlocks = chords.filter(c => !c.isRest && c.beat != null).map(c => {
      const k = keyAtBeat(keys, c.beat);
      const tonic = k.tonic || 'C', scale = k.scale || 'major';
      const pc = chordRootPc(c, tonic, scale);
      const midi = chordMidiPitches(c, tonic, scale);
      const { acc } = stripAcc(c.root);
      const borrowedStr = typeof c.borrowed === 'string' ? c.borrowed : '';
      const isDiatonic = !c.applied && !borrowedStr && acc === 0;
      const deg = chordDeg(c);
      // Minor-key chords use the relative-major degree color (i=purple, III=red, etc.)
      const colorDeg = scale === 'minor' ? ((deg + 4) % 7) + 1 : deg;
      return {
        b: c.beat, d: c.duration ?? bpb, pc, midi,
        root: c.root, type: c.type, borrowed: borrowedStr,
        deg, colorDeg, isDiatonic,
        quality: chordQuality(c, scale),
        labelChord: chordLabelChord(c, tonic, scale),
        labelRoman: chordLabelRoman(c, scale),
      };
    });

    const noteBars = notes.filter(n => !n.isRest && n.beat != null).map(n => {
      const pitch = notePitchValue(n);
      if (pitch == null) return null;
      const k = keyAtBeat(keys, n.beat);
      const midi = noteMidi(n, k.tonic || 'C', k.scale || 'major');
      const pc = ((pitch % 12) + 12) % 12;
      return { b: n.beat, d: n.duration ?? 0.25, pitch, pc, sd: String(n.sd), midi };
    }).filter(Boolean);

    const sectionMarks = sections.map(s => ({ b: s.beat, name: s.name || '?' }));
    return { chordBlocks, noteBars, sectionMarks, bpm, bpb, totalBars, keyStr };
  }

  function chordTypeSuffix(t) {
    if (t === 7 || t === '7') return '7';
    if (t === 'm' || t === 'min') return '';
    if (typeof t === 'string' && t && t !== '5') return t;
    return '';
  }

  const ROMAN_UP = ['I','II','III','IV','V','VI','VII'];
  const ROMAN_LO = ['i','ii','iii','iv','v','vi','vii'];

  function chordDeg(c) {
    const { rs } = stripAcc(c.root);
    return /^\d+$/.test(rs) ? parseInt(rs) : 1;
  }
  function chordAccidental(c) {
    const { acc } = stripAcc(c.root);
    return acc > 0 ? '#'.repeat(acc) : acc < 0 ? 'b'.repeat(-acc) : '';
  }
  function chordQuality(c, keyScale) {
    if (c.applied) return 'M';
    const typ = c.type;
    if (typ === 'm' || typ === 'min') return 'm';
    const borrowed = typeof c.borrowed === 'string' ? c.borrowed : '';
    const mode = MODE_QUALITIES[borrowed] ? borrowed : keyScale;
    const qualities = MODE_QUALITIES[mode] || MODE_QUALITIES['major'];
    return qualities[chordDeg(c) - 1];
  }
  function chordLabelChord(c, keyTonic, keyScale) {
    const pc = chordRootPc(c, keyTonic, keyScale);
    if (pc == null) return '?';
    const q = chordQuality(c, keyScale);
    let name = NOTES_SHARP[pc];
    if (q === 'm')       name += 'm';
    else if (q === 'd')  name += 'dim';
    else if (q === 'a')  name += 'aug';
    if (c.type === 7 || c.type === '7') name += '7';
    if (c.applied) {
      const appPc = chordRootPc(String(c.applied), keyTonic, keyScale);
      if (appPc != null) name += '/' + NOTES_SHARP[appPc];
    }
    return name;
  }
  function chordLabelRoman(c, keyScale) {
    const deg = chordDeg(c);
    const acc = chordAccidental(c);
    const q = chordQuality(c, keyScale);
    let r = (q === 'M' || q === 'a') ? ROMAN_UP[deg-1] : ROMAN_LO[deg-1];
    let label = acc + r;
    if (c.type === 7 || c.type === '7') label += '7';
    if (q === 'd') label += '°';
    if (c.applied) label += '/' + ROMAN_UP[c.applied - 1];
    return label;
  }

  // ---------- Viewer class ----------
  class SongViewer {
    constructor(opts) {
      this.sb = opts.supabase;
      this.mainEl = typeof opts.mainEl === 'string' ? document.querySelector(opts.mainEl) : opts.mainEl;
      this.headerEls = {};
      for (const k of ['title', 'artist', 'meta']) {
        const el = opts.headerEls?.[k];
        if (!el) continue;
        this.headerEls[k] = typeof el === 'string' ? document.querySelector(el) : el;
      }
      this.sectionListEl = opts.sectionListEl
        ? (typeof opts.sectionListEl === 'string' ? document.querySelector(opts.sectionListEl) : opts.sectionListEl)
        : null;
      const t = opts.transport || {};
      this.transport = {
        playBtn: typeof t.playBtn === 'string' ? document.querySelector(t.playBtn) : t.playBtn,
        stopBtn: typeof t.stopBtn === 'string' ? document.querySelector(t.stopBtn) : t.stopBtn,
        tempoInput: typeof t.tempoInput === 'string' ? document.querySelector(t.tempoInput) : t.tempoInput,
        displaySelect: typeof t.displaySelect === 'string' ? document.querySelector(t.displaySelect) : t.displaySelect,
      };
      this.displayMode = (this.transport.displaySelect?.value) || 'chord';

      this.song = null;
      this.chordSynth = null;
      this.melodySynth = null;
      this.chordPart = null;
      this.melodyPart = null;
      this.playheadRaf = null;

      this._attachTransportHandlers();
      this._attachRowClickHandler();
      window.addEventListener('resize', () => this.render());
    }

    async load(slug) {
      this.stop();
      this.mainEl.innerHTML = '<div class="status">loading song…</div>';
      const { data, error } = await this.sb.schema('parcels').from('songs')
        .select('title,artist,key_tonic,key_scale,bpm,hookpad_json')
        .eq('slug', slug).limit(1);
      if (error) { this.mainEl.innerHTML = `<div class="status">error: ${error.message}</div>`; return; }
      const row = data?.[0];
      if (!row) { this.mainEl.innerHTML = `<div class="status">no song with slug <code>${slug}</code></div>`; return; }
      if (!row.hookpad_json) { this.mainEl.innerHTML = `<div class="status">song has no hookpad_json</div>`; return; }

      this.song = {
        title: row.title, artist: row.artist,
        raw: row.hookpad_json,
        derived: buildSongData(row.hookpad_json),
      };
      this._updateHeader();
      this.render();
    }

    _updateHeader() {
      if (!this.song) return;
      const { derived } = this.song;
      document.title = `${this.song.title} — ${this.song.artist}`;
      if (this.headerEls.title) this.headerEls.title.textContent = this.song.title;
      if (this.headerEls.artist) this.headerEls.artist.textContent = this.song.artist || '';
      if (this.headerEls.meta) this.headerEls.meta.innerHTML =
        `<b>${derived.keyStr}</b> · ${derived.bpm} BPM · ${derived.bpb}/4 · ${derived.totalBars} bars`;
      if (this.transport.tempoInput) this.transport.tempoInput.value = derived.bpm;
    }

    render() {
      if (!this.song) return;
      const { chordBlocks, noteBars, sectionMarks, bpb, totalBars } = this.song.derived;
      const BARS_PER_PAGE = 8;

      const SEC = sectionMarks.map((s, i) => {
        const nextBeat = sectionMarks[i+1] ? sectionMarks[i+1].b : (totalBars * bpb + 1);
        return Object.assign({}, s, { endBeat: nextBeat, bars: Math.round((nextBeat - s.b) / bpb) });
      }).filter(s => s.bars >= 1);

      const CHROME = 24 + 2 + 12 + 4 + 16;
      const viewportInner = this.mainEl.clientWidth - CHROME;
      const pxPerBar = viewportInner / BARS_PER_PAGE;
      const pxPerBeat = pxPerBar / bpb;

      const PC_BG = [
        'rgba(160, 30, 30, 0.20)', 'rgba(154, 56, 19, 0.15)',
        'rgba(179, 86, 16, 0.20)', 'rgba(164, 98, 14, 0.15)',
        'rgba(149,126, 12, 0.20)', 'rgba( 37,168, 56, 0.20)',
        'rgba( 48,154,108, 0.15)', 'rgba( 58,156,156, 0.20)',
        'rgba( 84, 89,165, 0.15)', 'rgba(110, 22,165, 0.20)',
        'rgba(135, 25,136, 0.15)', 'rgba(160, 27,107, 0.20)',
      ];

      let html = '';
      SEC.forEach((s, idx) => {
        const secNotes = noteBars.filter(n => n.b >= s.b && n.b < s.endBeat);
        let minP = Infinity, maxP = -Infinity;
        secNotes.forEach(n => { if (n.pitch < minP) minP = n.pitch; if (n.pitch > maxP) maxP = n.pitch; });
        if (!isFinite(minP)) { minP = 0; maxP = 12; }
        const pad = 1;
        const pitchTop = maxP + pad;
        const pitchBottom = minP - pad;
        const pitchRange = Math.max(3, pitchTop - pitchBottom);

        const MEL_H = 120, NOTE_H = 7;
        const slotH = (MEL_H - 4) / pitchRange;

        const rows = [];
        let rowStartBar = 0, remaining = s.bars;
        while (remaining > 0) {
          const rb = Math.min(BARS_PER_PAGE, remaining);
          rows.push({ startBar: rowStartBar, bars: rb });
          rowStartBar += rb;
          remaining -= rb;
        }

        const secChords = chordBlocks.filter(c => c.b >= s.b && c.b < s.endBeat);

        let rowsHtml = '';
        rows.forEach(row => {
          const rowStartBeat = s.b + row.startBar * bpb;
          const rowEndBeat = rowStartBeat + row.bars * bpb;
          const rowWidth = row.bars * pxPerBar;

          let ticks = '', labels = '';
          const rowBeats = row.bars * bpb;
          for (let k = 1; k <= rowBeats; k++) {
            const left = k * pxPerBeat;
            const isMeasure = (k % bpb === 0);
            ticks += `<div class="bar-tick ${isMeasure ? 'measure' : 'beat'}" style="left:${left}px"></div>`;
          }
          for (let m = 1; m <= row.bars; m++) {
            const absM = row.startBar + m;
            labels += `<div class="bar-label" style="left:${(m-1)*pxPerBar}px">m${absM}</div>`;
          }

          let stripes = '';
          for (let p = Math.ceil(pitchBottom); p <= Math.floor(pitchTop); p++) {
            const pc = ((p % 12) + 12) % 12;
            const yFromTop = ((pitchTop - p) / pitchRange) * (MEL_H - 4) + 2;
            stripes += `<div class="pitch-stripe" style="top:${yFromTop - slotH/2}px;height:${slotH}px;background:${PC_BG[pc]}"></div>`;
          }

          const rowNotes = secNotes.filter(n => n.b >= rowStartBeat && n.b < rowEndBeat);
          let prHtml = '';
          rowNotes.forEach(n => {
            const localBeat = n.b - rowStartBeat;
            const left = localBeat * pxPerBeat;
            const w = Math.max(3, n.d * pxPerBeat - 2);
            const yFromTop = ((pitchTop - n.pitch) / pitchRange) * (MEL_H - NOTE_H - 4) + 2;
            const cls = (n.pc != null) ? `pc-${n.pc}` : '';
            prHtml += `<div class="pr-note ${cls}" style="left:${left}px;top:${yFromTop}px;width:${w}px;height:${NOTE_H}px"
                             title="sd ${n.sd} at beat ${n.b}, dur ${n.d}"></div>`;
          });

          const rowChords = secChords.filter(c => c.b >= rowStartBeat && c.b < rowEndBeat);
          let chHtml = '';
          const mode = this.displayMode || 'chord';
          rowChords.forEach(c => {
            const local = c.b - rowStartBeat;
            const left = local * pxPerBeat;
            const remainingDur = (rowEndBeat - c.b);
            const dur = Math.min(c.d, remainingDur);
            const w = Math.max(8, dur * pxPerBeat - 1);
            const cls = c.isDiatonic && c.colorDeg >= 1 && c.colorDeg <= 7
              ? `deg-${c.colorDeg}`
              : (c.pc != null ? `pc-${c.pc}` : 'pc-unknown');
            const label = mode === 'roman' ? c.labelRoman : c.labelChord;
            chHtml += `<div class="chord-block ${cls}" style="left:${left}px;width:${w}px"
                             title="${c.labelChord} · ${c.labelRoman}">${label}</div>`;
          });

          rowsHtml += `<div class="canvas-row"
                data-start-beat="${rowStartBeat}" data-end-beat="${rowEndBeat}" data-px-per-beat="${pxPerBeat}"
                title="click to play from m${row.startBar + 1} of ${s.name}">
            <div class="section-canvas" style="width:${rowWidth}px;position:relative">
              <div class="melody-strip">${stripes}${ticks}${labels}${prHtml}</div>
              <div class="chord-strip">${ticks}${chHtml}</div>
            </div>
          </div>`;
        });

        html += `<div class="section-block" data-section-idx="${idx}" id="sec-${idx}">
          <div class="section-header">
            <span class="name">${s.name}</span>
            <span class="meta">${s.bars} bars · ${secChords.length} chord events · ${secNotes.length} notes</span>
          </div>
          <div class="section-body">${rowsHtml}</div>
        </div>`;
      });
      this.mainEl.innerHTML = html;

      if (this.sectionListEl) {
        this.sectionListEl.innerHTML = SEC.map((s, i) =>
          `<div class="section-item" data-idx="${i}">${s.name} <span class="bar">${s.bars}b</span></div>`
        ).join('');
        this.sectionListEl.onclick = e => {
          const item = e.target.closest('.section-item');
          if (!item) return;
          const idx = item.dataset.idx;
          const target = document.getElementById('sec-' + idx);
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          this.sectionListEl.querySelectorAll('.section-item.active').forEach(el => el.classList.remove('active'));
          item.classList.add('active');
        };
      }
    }

    // ---------- Playback ----------
    _midiToNoteName(m) {
      const oct = Math.floor(m / 12) - 1;
      return NOTES_SHARP[m % 12] + oct;
    }

    _buildParts() {
      if (this.chordPart) { this.chordPart.dispose(); this.chordPart = null; }
      if (this.melodyPart) { this.melodyPart.dispose(); this.melodyPart = null; }
      if (this.chordSynth) { this.chordSynth.dispose(); this.chordSynth = null; }
      if (this.melodySynth) { this.melodySynth.dispose(); this.melodySynth = null; }

      this.chordSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle' },
        envelope: { attack: 0.04, decay: 0.2, sustain: 0.4, release: 0.5 },
      }).toDestination();
      this.chordSynth.volume.value = -18;

      this.melodySynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle' },
        envelope: { attack: 0.02, decay: 0.1, sustain: 0.5, release: 0.3 },
      }).toDestination();
      this.melodySynth.volume.value = -6;

      const secPerBeat = 60 / Tone.Transport.bpm.value;
      const { chordBlocks, noteBars } = this.song.derived;

      const chordEvents = chordBlocks
        .filter(c => c.midi && c.midi.length && c.d > 0)
        .map(c => [(c.b - 1) * secPerBeat, {
          notes: c.midi.map(m => this._midiToNoteName(m)),
          dur: Math.max(0.1, c.d * secPerBeat * 0.95),
        }]);
      this.chordPart = new Tone.Part((time, ev) => {
        this.chordSynth.triggerAttackRelease(ev.notes, ev.dur, time);
      }, chordEvents);
      this.chordPart.start(0);

      const melodyEvents = noteBars
        .filter(n => n.midi != null && n.d > 0)
        .map(n => [(n.b - 1) * secPerBeat, {
          note: this._midiToNoteName(n.midi),
          dur: Math.max(0.05, n.d * secPerBeat * 0.95),
        }]);
      this.melodyPart = new Tone.Part((time, ev) => {
        this.melodySynth.triggerAttackRelease(ev.note, ev.dur, time);
      }, melodyEvents);
      this.melodyPart.start(0);
    }

    async startFromBeat(absoluteBeat) {
      if (!this.song) return;
      if (Tone.context.state !== 'running') await Tone.start();
      const bpm = parseInt(this.transport.tempoInput?.value, 10) || this.song.derived.bpm;
      Tone.Transport.bpm.value = bpm;
      Tone.Transport.stop();
      Tone.Transport.cancel(0);
      this._buildParts();
      const startSec = Math.max(0, (absoluteBeat - 1) * (60 / bpm));
      Tone.Transport.start(undefined, startSec);
      if (this.transport.playBtn) {
        this.transport.playBtn.classList.add('playing');
        this.transport.playBtn.textContent = '⏸ Pause';
      }
      this._startPlayheadAnimation();
    }

    stop() {
      Tone.Transport.stop();
      Tone.Transport.cancel(0);
      if (this.playheadRaf) cancelAnimationFrame(this.playheadRaf);
      this.playheadRaf = null;
      document.querySelectorAll('.playhead').forEach(el => el.remove());
      if (this.transport.playBtn) {
        this.transport.playBtn.classList.remove('playing');
        this.transport.playBtn.textContent = '▶ Play';
      }
    }

    _startPlayheadAnimation() {
      const tick = () => {
        const elapsedSec = Tone.Transport.seconds;
        const bpm = Tone.Transport.bpm.value;
        const curBeat = elapsedSec * (bpm / 60) + 1;
        document.querySelectorAll('.playhead').forEach(el => el.remove());
        const rowEls = this.mainEl.querySelectorAll('.canvas-row');
        for (const row of rowEls) {
          const rowStart = parseFloat(row.dataset.startBeat);
          const rowEnd = parseFloat(row.dataset.endBeat);
          const pxPerBeat = parseFloat(row.dataset.pxPerBeat);
          if (curBeat >= rowStart && curBeat < rowEnd) {
            const localBeat = curBeat - rowStart;
            const left = localBeat * pxPerBeat;
            const canvas = row.querySelector('.section-canvas');
            const ph = document.createElement('div');
            ph.className = 'playhead';
            ph.style.left = left + 'px';
            canvas.appendChild(ph);
            const rect = row.getBoundingClientRect();
            if (rect.top < 60 || rect.bottom > window.innerHeight - 20) {
              row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            break;
          }
        }
        if (Tone.Transport.state === 'started') this.playheadRaf = requestAnimationFrame(tick);
        else this.stop();
      };
      this.playheadRaf = requestAnimationFrame(tick);
    }

    _attachTransportHandlers() {
      const t = this.transport;
      if (t.playBtn) t.playBtn.onclick = () => {
        if (Tone.Transport.state === 'started') {
          Tone.Transport.pause();
          if (this.playheadRaf) cancelAnimationFrame(this.playheadRaf);
          t.playBtn.classList.remove('playing');
          t.playBtn.textContent = '▶ Play';
        } else this.startFromBeat(1);
      };
      if (t.stopBtn) t.stopBtn.onclick = () => this.stop();
      if (t.tempoInput) t.tempoInput.onchange = (e) => {
        if (!this.song) return;
        Tone.Transport.bpm.value = parseInt(e.target.value, 10) || this.song.derived.bpm;
        if (Tone.Transport.state === 'started') {
          const curSec = Tone.Transport.seconds;
          const curBeat = curSec * (Tone.Transport.bpm.value / 60) + 1;
          this.startFromBeat(curBeat);
        }
      };
      if (t.displaySelect) t.displaySelect.onchange = (e) => {
        this.displayMode = e.target.value;
        this.render();
      };
    }

    _attachRowClickHandler() {
      this.mainEl.addEventListener('click', (e) => {
        const row = e.target.closest('.canvas-row');
        if (!row) return;
        const rowStart = parseFloat(row.dataset.startBeat);
        if (!isNaN(rowStart)) this.startFromBeat(rowStart);
      });
    }
  }

  // ---------- Shared CSS ----------
  // Injects the chord/melody/playback styles. Pages can override anything via their own <style>.
  const SHARED_CSS = `
  .section-block { margin-bottom: 14px; background: #20203a; border: 1px solid #2a2a4a; border-radius: 6px; overflow: hidden; }
  .section-header { padding: 6px 12px; background: #16162a; border-bottom: 1px solid #2a2a4a; display: flex; gap: 12px; align-items: baseline; font-size: 12px; }
  .section-header .name { font-weight: 700; color: #e0e0e0; text-transform: capitalize; }
  .section-header .meta { color: #8a8ab0; font-size: 11px; }
  .section-body { padding: 6px; }
  .section-canvas { position: relative; }
  .canvas-row { margin-bottom: 8px; border: 2px solid #ffffff; border-radius: 4px; overflow: hidden; display: inline-block; vertical-align: top; cursor: pointer; }
  .canvas-row:hover { border-color: #6366f1; }
  .canvas-row:last-child { margin-bottom: 0; }
  .melody-strip { position: relative; height: 120px; overflow: hidden; background: #16162a; border-bottom: 1px solid #3a3a5a; }
  .chord-strip { position: relative; height: 36px; background: #14142a; border-top: 1px solid #ffffff; }
  .bar-tick { position: absolute; top: 0; bottom: 0; pointer-events: none; z-index: 2; }
  .bar-tick.measure { width: 2px; background: #ffffff; }
  .bar-tick.beat    { width: 1px; background: rgba(200, 200, 220, 0.28); }
  .bar-label { position: absolute; top: 2px; font-size: 9px; color: #44446a; padding-left: 3px; pointer-events: none; z-index: 2; }
  .pitch-stripe { position: absolute; left: 0; right: 0; pointer-events: none; z-index: 0; }
  .pr-note { position: absolute; height: 8px; border-radius: 1px; border: 1px solid #000; box-shadow: 0 0 0 1px rgba(255,255,255,0.15); z-index: 3; }
  .chord-block { position: absolute; bottom: 0; height: 36px; border-right: 2px solid #000; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #ffffff; font-size: 13px; text-shadow: 0 1px 0 rgba(0,0,0,0.85), 1px 0 0 rgba(0,0,0,0.6); overflow: hidden; }
  .playhead { position: absolute; top: 0; bottom: 0; width: 2px; background: #ffd700; pointer-events: none; z-index: 5; box-shadow: 0 0 4px rgba(255,215,0,0.7); }
  .pc-0  { background: #a01e1e; }
  .pc-1  { background: repeating-linear-gradient(135deg, #a01e1e 0 10px, #b35610 10px 20px); background-size: 28.28px 28.28px; }
  .pc-2  { background: #b35610; }
  .pc-3  { background: repeating-linear-gradient(135deg, #b35610 0 10px, #957e0c 10px 20px); background-size: 28.28px 28.28px; }
  .pc-4  { background: #957e0c; }
  .pc-5  { background: #25a838; }
  .pc-6  { background: repeating-linear-gradient(135deg, #25a838 0 10px, #3050d0 10px 20px); background-size: 28.28px 28.28px; }
  .pc-7  { background: #3050d0; }
  .pc-8  { background: repeating-linear-gradient(135deg, #3050d0 0 10px, #6e16a5 10px 20px); background-size: 28.28px 28.28px; }
  .pc-9  { background: #6e16a5; }
  .pc-10 { background: repeating-linear-gradient(135deg, #6e16a5 0 10px, #a01b6b 10px 20px); background-size: 28.28px 28.28px; }
  .pc-11 { background: #a01b6b; }
  .pc-unknown { background: #44446a; color: #b0b0cc; }
  /* Scale-degree colors (for chord blocks: I=red, ii=orange, iii=mustard, IV=green, V=teal, vi=purple, vii=magenta) */
  .deg-1 { background: #a01e1e; }
  .deg-2 { background: #b35610; }
  .deg-3 { background: #957e0c; }
  .deg-4 { background: #25a838; }
  .deg-5 { background: #3050d0; }
  .deg-6 { background: #6e16a5; }
  .deg-7 { background: #a01b6b; }
  .status { padding: 40px; text-align: center; color: #8a8ab0; font-size: 14px; }
  `;
  function injectSharedCss() {
    if (document.getElementById('song-viewer-css')) return;
    const style = document.createElement('style');
    style.id = 'song-viewer-css';
    style.textContent = SHARED_CSS;
    document.head.appendChild(style);
  }
  injectSharedCss();

  window.SongViewer = SongViewer;
})();
