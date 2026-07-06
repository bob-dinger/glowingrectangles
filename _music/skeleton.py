"""Melodic skeletons: the SKELETONER (real melody -> bones) and its inverse the
VARIER (bones -> N ornamented takes).  See memory music_skeleton_varier.

Model (validated across many hand-cleaned examples):
  A melody = RHYTHM cell + PITCH contour + PHRASE map + METRIC alignment.
  The skeleton preserves the identity = PALETTE (which degrees) + CHORDS + BEATS.
  Rhythm > pitch. The unit is the SYLLABLE ~= one note per beat.

Skeletoner: for each beat, take the note ONSETTING at/just-into it (prefer the
longer note over a grace flick); else the note SUSTAINING across it. Then merge
consecutive beats that trace to the SAME source note -> held notes stay held,
repeated onsets stay separate (never merge by pitch).
  - Exact on ON-BEAT tunes (YGTHYLA, Seashores: 100%). ~80% on syncopated ones
    (DLBIA) -> the off-beat notes are the curation residue; a melody has several
    valid competing skeletons, so this is a DRAFT to curate, not a truth.

Varier: keep the quarter skeleton, add a FEW eighths (subdivide-into-neighbour /
passing / re-articulate / pickup). Ornament budget is TEMPO-SCALED (fast bpm ->
fewer eighths): base = round(120/bpm * 3)  (=2 at 180 bpm).
"""
import os, json, random

# ---------------- Skeletoner ----------------
def skeletonize(notes, lo, hi):
    """notes: non-rest dicts {sd,octave,beat,duration}. Returns skeleton [{sd,octave,beat,duration}]."""
    beats = []
    for b in range(int(round(lo)), int(round(hi))):
        win = [n for n in notes if b - 0.05 <= n['beat'] < b + 0.4]
        if win:
            win.sort(key=lambda n: -n['duration'])
            beats.append((b, id(win[0]), win[0]))
        else:
            sus = [n for n in notes if n['beat'] < b < n['beat'] + n['duration']]
            beats.append((b, id(sus[-1]), sus[-1]) if sus else (b, None, None))
    out = []
    for b, sid, src in beats:
        if src is None:
            continue
        if out and out[-1]['_sid'] == sid:
            out[-1]['duration'] += 1
        else:
            out.append({'sd': str(src['sd']), 'octave': src['octave'], 'beat': b, 'duration': 1, '_sid': sid})
    for o in out:
        o.pop('_sid', None)
    return out

# ---------------- Simplifier (subtractive) ----------------
def _deg(sd):
    d = ''.join(c for c in str(sd) if c.isdigit())
    return int(d) if d else 0
def _pc(n):
    return (_deg(n['sd']), n['octave'])

def simplify(notes, short=0.75, passes=8):
    """SUBTRACTIVE reduction (real -> bones): delete EXCESS notes -- short ones
    whose pitch is already covered (a repeat of, or a neighbour returning to, a
    kept tone) -- and hand their time to the surviving note, so survivors keep
    their REAL durations (never grid-snapped). Iterates until stable.

    'Excess' per the user's rule = within the palette already + usually shorter.
    Keeps passing tones that ADVANCE a line (prev<this<next or prev>this>next)."""
    ns = [dict(n) for n in sorted(notes, key=lambda x: x['beat'])]
    for _ in range(passes):
        changed = False
        i = 1
        while i < len(ns):
            n, prev = ns[i], ns[i - 1]
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            dn, dp = _deg(n['sd']), _deg(prev['sd'])
            dx = _deg(nxt['sd']) if nxt else None
            passing = nxt and ((dp < dn < dx) or (dp > dn > dx))     # a real step in a line -> keep
            redundant = (_pc(n) == _pc(prev) or (nxt and _pc(n) == _pc(nxt))
                         or (nxt and _pc(prev) == _pc(nxt)))          # repeat / return-neighbour
            if n['duration'] <= short and redundant and not passing:
                prev['duration'] = round(prev['duration'] + n['duration'], 3)
                ns.pop(i)
                changed = True
                continue
            i += 1
        if not changed:
            break
    return ns

def simplify_rhythm(notes, grid=1.0):
    """RHYTHM axis (separate from melody): quantize survivor durations to the pulse
    and re-space, turning an irregular kept line into even beats. simplify() alone
    = 'keep the rhythm' bones (nowhere); simplify_rhythm(simplify()) = 'regularize
    the rhythm too' bones (neon moon). The user's two-axis view."""
    out = [dict(n) for n in notes]
    for n in out:
        n['duration'] = round(n['duration'] / grid) * grid or grid
    b = notes[0]['beat'] if notes else 1
    for n in out:
        n['beat'] = round(b, 3)
        b += n['duration']
    return out

def simplify_harmonic(notes, chords, fill=False, merge=False, dedupe=False, eps=0.05, measure=None, pick='downbeat'):
    """HARMONIC axis (the user's rule): ONE main note per chord/measure = the note
    SOUNDING AT the chord's downbeat -- its onset is at/just-before and it sustains
    ACROSS the downbeat, so a PUSHED/anticipated note counts, but a note that merely
    ENDS on the downbeat (a phrase tail) does not. If nothing sounds at the downbeat,
    take the first note onsetting after it. 'At least one note per measure, the first
    note of the measure, wherever it is.' Captures the section's essence; the tempo +
    chords + these main notes ARE the reduced score.

    dedupe=False anchors to every chord ENTRY (one per measure); True = real root
    changes only. fill=stretch each note to the next; merge=collapse repeats."""
    ns = sorted(notes, key=lambda n: n['beat'])
    if measure:                    # anchor to the BAR grid (one note per measure), not per chord
        start = min(c['beat'] for c in chords)
        end = max(n['beat'] + n['duration'] for n in ns)
        cbs, b = [], start
        while b < end - eps:
            cbs.append(round(b, 3)); b += measure
    elif dedupe:
        cbs, prev = [], None
        for c in sorted(chords, key=lambda c: c['beat']):
            ident = (c['root'], c.get('type'), c.get('applied', 0), str(c.get('borrowed') or ''))
            if ident != prev:
                cbs.append(c['beat'])
            prev = ident
    else:
        cbs = sorted(c['beat'] for c in chords)
    main = []
    for i, cb in enumerate(cbs):
        hi = cbs[i + 1] if i + 1 < len(cbs) else float('inf')
        if pick == 'longest':                                  # ARRIVAL: the bar's dominant long note
            region = [n for n in ns if cb - 0.5 <= n['beat'] < hi - 0.5]
            chosen = max(region, key=lambda n: n['duration']) if region else None
        else:                                                  # DOWNBEAT: note sounding at the downbeat
            sounding = [n for n in ns if n['beat'] <= cb + eps and cb < n['beat'] + n['duration'] - eps]
            if sounding:
                chosen = max(sounding, key=lambda n: n['beat'])
            else:
                after = [n for n in ns if cb - eps <= n['beat'] < hi]
                chosen = after[0] if after else None
        if chosen is not None:
            main.append({**{k: chosen[k] for k in ('sd', 'octave', 'beat', 'duration')}, '_cb': cb})
    if merge:
        out = []
        for n in main:
            if out and _pc(out[-1]) == _pc(n):
                out[-1]['duration'] = round(out[-1]['duration'] + n['duration'], 3)
            else:
                out.append(dict(n))
        main = out
    if fill:
        for i, n in enumerate(main):
            if i + 1 < len(main):
                n['duration'] = round(main[i + 1]['beat'] - n['beat'], 3)
    return main

# ---------------- Varier ----------------
def sd_step(sd, octave, up):
    d = int(''.join(c for c in str(sd) if c.isdigit())) + (1 if up else -1)
    if d > 7: d, octave = 1, octave + 1
    if d < 1: d, octave = 7, octave - 1
    return (str(d), octave)

def vary(skel, bpm=120, k=None, seed=0):
    """skel: list of (sd, octave, duration). Returns a varied list adding ~k eighth ornaments."""
    if k is None:
        k = max(1, round(120 / max(bpm, 1) * 3))
    rnd = random.Random(seed)
    cands = [i for i, (s, o, d) in enumerate(skel) if d >= 1 and i < len(skel) - 1]
    picks = set(rnd.sample(cands, min(k, len(cands)))) if cands else set()
    out = []
    for i, (sd, oct, dur) in enumerate(skel):
        if i in picks:
            kind = rnd.choice(['nbr', 'pass', 'rep', 'pickup'])
            if kind == 'nbr':
                nb = sd_step(sd, oct, rnd.random() < 0.5); out += [(sd, oct, 0.5), (nb[0], nb[1], 0.5)]
            elif kind == 'pass':
                nsd, noc, _ = skel[i + 1]
                up = (int(nsd) + (7 if noc > oct else 0)) > int(''.join(c for c in sd if c.isdigit()))
                mid = sd_step(sd, oct, up); out += [(sd, oct, 0.5), (mid[0], mid[1], 0.5)]
            elif kind == 'rep':
                out += [(sd, oct, 0.5), (sd, oct, 0.5)]
            else:
                gr = sd_step(sd, oct, False); out += [(gr[0], gr[1], 0.5), (sd, oct, 0.5)]
        else:
            out.append((sd, oct, dur))
    return out

# ---------------- Hookpad paste helpers ----------------
def note_obj(sd, octave, beat, duration):
    return {"sd": str(sd), "octave": octave, "beat": round(beat, 3), "duration": duration,
            "isRest": False, "recordingEndBeat": None}
def copy_chord(ch, beat):
    return {"root": ch.get('root', 1), "beat": round(beat, 3), "duration": ch.get('duration', 4),
            "type": ch.get('type', 5), "inversion": ch.get('inversion', 0), "applied": ch.get('applied', 0),
            "adds": ch.get('adds') or [], "omits": ch.get('omits') or [], "alterations": ch.get('alterations') or [],
            "suspensions": ch.get('suspensions') or [], "substitutions": ch.get('substitutions') or [],
            "pedal": ch.get('pedal'), "alternate": ch.get('alternate') or "", "borrowed": ch.get('borrowed') or "",
            "isRest": False, "recordingEndBeat": None}
def plain_chord(root, beat, dur):
    return copy_chord({"root": root, "duration": dur}, beat)

def write_paste(notes, chords, sections, endbeat, path):
    paste = {"notes": notes, "chords": chords, "sections": sections, "endBeat": round(endbeat),
             "audioTracks": [], "version": 1}
    open(os.path.expanduser(path), 'w').write(json.dumps(paste, separators=(',', ':')))
    return path

def _db():
    from dotenv import load_dotenv; load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
    import psycopg2
    return psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                            password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432))

def draft_compare_paste(sections, path='~/Desktop/skeleton_test.txt'):
    """sections: list of (slug, section_name). Emits real->skeleton blocks with real chords."""
    c = _db(); cur = c.cursor(); NOTES = []; CHORDS = []; SECS = []; cursor = 1.0
    for i, (slug, secname) in enumerate(sections, 1):
        cur.execute("select title,hookpad_json->'notes',hookpad_json->'chords',hookpad_json->'sections',hookpad_json->'meters' from parcels.songs where slug=%s", (slug,))
        r = cur.fetchone()
        if not r: continue
        tit, notes, chords, secs, meters = r
        nb = (meters or [{}])[0].get('numBeats', 4); eb = max((n['beat'] for n in notes), default=0) + nb
        seg = None
        for k, s in enumerate(secs):
            if secname in s['name'].lower():
                e = secs[k+1]['beat'] if k+1 < len(secs) else eb
                ns = sorted([n for n in notes if not n.get('isRest') and s['beat'] <= n['beat'] < e], key=lambda n: n['beat'])
                if ns: seg, b0, e0 = ns, s['beat'], e; break
        if not seg: continue
        realend = max(n['beat']+n['duration'] for n in seg)
        skel = skeletonize(seg, b0, realend + 1)
        secch = [ch for ch in (chords or []) if b0 <= ch['beat'] < e0]
        name = f"{i}. {tit[:16]} {secname}"
        for blk, block in [(" real", seg), (" skel", [{'sd': s['sd'], 'octave': s['octave'], 'beat': s['beat'], 'duration': s['duration']} for s in skel])]:
            SECS.append({"beat": round(cursor), "name": name + blk})
            for n in block: NOTES.append(note_obj(n['sd'], n['octave'], cursor + (n['beat'] - b0), n['duration']))
            for ch in secch: CHORDS.append(copy_chord(ch, cursor + (ch['beat'] - b0)))
            span = int(max((n['beat']+n['duration'] for n in block), default=b0) - b0 + nb); span -= span % nb
            cursor += max(span, nb)
        cursor += nb
    c.close()
    return write_paste(NOTES, CHORDS, SECS, cursor, path)

def vary_paste(skel, chords, bpm, n=3, path='~/Desktop/varier_test.txt'):
    """skel: list of (sd,octave,duration). chords: list of (root,duration). Emits skeleton + n variations."""
    base = max(1, round(120 / max(bpm, 1) * 3))
    variants = [("skeleton", skel)] + [(f"var {j+1}", vary(skel, bpm, base + j, seed=3 + 6*j)) for j in range(n)]
    NOTES = []; CHORDS = []; SECS = []; cursor = 1; bar = sum(d for _, d in chords)
    for name, sk in variants:
        t = cursor
        for sd, oct, dur in sk: NOTES.append(note_obj(sd, oct, t, dur)); t += dur
        ct = cursor
        for root, d in chords: CHORDS.append(plain_chord(root, ct, d)); ct += d
        SECS.append({"beat": cursor, "name": name}); cursor += bar
    return write_paste(NOTES, CHORDS, SECS, cursor, path)

if __name__ == '__main__':
    # default demo: the 10-section comparison
    print(draft_compare_paste([
        ("smashing-pumpkins_1979", "verse"), ("shawn-colvin_sunny-came-home", "verse"),
        ("brooks-and-dunn_neon-moon_o", "chorus"), ("switchfoot_meant-to-live_o", "verse"),
        ("fastball_fire-escape", "verse"), ("rod-stewart_maggie-may", "verse"),
        ("clint-black_nothin-but-the-taillights_o", "verse"), ("merle-haggard_seashores-of-old-mexico", "verse"),
        ("natalie-merchant_wonder_o_c_ly", "chorus"), ("oasis_don-t-look-back-in-anger", "verse"),
    ]))
