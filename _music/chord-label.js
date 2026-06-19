// Canonical Hookpad chord → Roman-numeral labeler. Mirrors _music/chord_label.py.
// Hookpad fields (compact): c.r (root 1-7), c.t (type), c.app (applied), c.bor (borrowed),
//   c.sus (suspensions[]), c.adds, c.omits, c.alterations.
//
// Exposes a global `chordLabel(c, scale)` function. HTML pages should:
//   <script src="chord-label.js"></script>
//   <script>function romanLabel(c, scale) { return chordLabel(c, scale); }</script>
//
// Keep this file in sync with _music/chord_label.py.

(function () {
  const NUM = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'];
  const MIN_TO_MAJ = {1: 6, 2: 7, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5};
  const MAJ_INT = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11};
  const MIN_INT = {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10};

  function addExt(base, c, t) {
    if (t === 7) base += '7';
    else if (t === 9 || t === 11 || t === 13) base += String(t);
    const sus = c.sus || c.suspensions || [];
    for (const s of sus) base += 'sus' + String(s);
    const adds = c.adds || [];
    for (const a of adds) base += 'add' + String(a);
    const om = c.omits || [];
    const hasSus = sus.length > 0;
    const hasAdds = adds.length > 0;
    if (om.indexOf(3) >= 0 && !hasSus && !hasAdds) {
      base += '5';
    } else if (om.indexOf(3) >= 0) {
      base += '(no3)';
    }
    if (om.indexOf(5) >= 0) base += '(no5)';
    const alts = c.alterations || [];
    for (const a of alts) base += String(a);
    return base;
  }

  function chordLabel(c, scale) {
    scale = scale || 'major';
    // Hookpad's compact fields use c.r, c.t, c.app, c.bor; long form uses c.root, etc.
    let r = c.r != null ? c.r : c.root;
    if (!r || r < 1 || r > 7) return '?';
    let applied = (c.app != null ? c.app : c.applied) || 0;
    let tRaw = c.t != null ? c.t : (c.type != null ? c.type : 5);
    let t = parseInt(tRaw, 10);
    if (isNaN(t)) t = 5;
    let bor = c.bor != null ? c.bor : c.borrowed;
    const origScale = scale;

    // Minor → relative-major shift
    if (scale === 'minor') {
      if (applied > 0) {
        applied = MIN_TO_MAJ[applied];
      } else {
        r = MIN_TO_MAJ[r];
      }
      scale = 'major';
    }

    // bVII (root=7 + minor/mixolydian borrow + no applied) → IV/IV
    if (r === 7 && (bor === 'minor' || bor === 'mixolydian') && applied === 0) {
      r = 4;
      applied = 4;
      bor = null;
    }

    if (applied > 0) {
      const y_pc = MAJ_INT[applied];
      const root_intervals = (origScale === 'minor') ? MIN_INT : MAJ_INT;
      const chord_pc = ((y_pc + root_intervals[r]) % 12 + 12) % 12;

      // Diatonic major position (I/IV/V) → simple Roman
      for (const d of [1, 4, 5]) {
        if (MAJ_INT[d] === chord_pc) {
          return addExt(NUM[d - 1], c, t);
        }
      }
      // bVII case → IV/IV
      if (chord_pc === 10) {
        return addExt('IV', c, t) + '/IV';
      }
      // Try V/Z form
      const v_target_pc = ((chord_pc - 7) % 12 + 12) % 12;
      let v_z_deg = null;
      for (const d of [1, 2, 3, 4, 5, 6, 7]) {
        if (MAJ_INT[d] === v_target_pc) {
          v_z_deg = d;
          break;
        }
      }
      if (v_z_deg !== null) {
        const x = addExt('V', c, t);
        let y = NUM[v_z_deg - 1];
        if (v_z_deg === 2 || v_z_deg === 3 || v_z_deg === 6) y = y.toLowerCase();
        return x + '/' + y;
      }
      // Fallback: original X/Y
      let x = NUM[r - 1];
      if ((r === 2 || r === 3 || r === 6) && t !== 7) x = x.toLowerCase();
      x = addExt(x, c, t);
      let y = NUM[applied - 1];
      if (applied === 2 || applied === 3 || applied === 6) y = y.toLowerCase();
      return x + '/' + y;
    }

    // Diatonic / borrowed
    let base = NUM[r - 1];
    if (!bor) {
      if (r === 2 || r === 3 || r === 6) base = base.toLowerCase();
    }
    if (bor === 'minor' && (r === 3 || r === 6 || r === 7)) base = 'b' + base;
    else if (bor === 'mixolydian' && r === 7) base = 'b' + base;

    if (t === 7) {
      if ((r === 1 || r === 4) && !bor) base += 'maj7';
      else base += '7';
    } else if (t === 9 || t === 11 || t === 13) {
      base += String(t);
    }

    const sus = c.sus || c.suspensions || [];
    for (const s of sus) base += 'sus' + String(s);
    const adds = c.adds || [];
    for (const a of adds) base += 'add' + String(a);
    const om = c.omits || [];
    if (om.indexOf(3) >= 0 && sus.length === 0 && adds.length === 0) {
      base += '5';
    } else if (om.indexOf(3) >= 0) {
      base += '(no3)';
    }
    if (om.indexOf(5) >= 0) base += '(no5)';
    const alts = c.alterations || [];
    for (const a of alts) base += String(a);
    return base;
  }

  // Expose globally
  window.chordLabel = chordLabel;
})();
