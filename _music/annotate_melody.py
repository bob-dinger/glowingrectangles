"""Auto-annotate a song's melody into parcels.melodies (variation-grammar columns).

For each vocal section: segment phrases by inter-onset gap, label them (A/B/A2...),
compute palette (core/reach/stretch), cadence (final note melodic + vs-chord), and
GUESS transforms (echo/trim/clip/tag/merge/lift/drop). Upserts one row per (slug, section).

Usage:
    python annotate_melody.py --slug <slug> [--dry-run]
    python annotate_melody.py --title "1979" [--dry-run]

The guesses are meant to be corrected by hand — this is a fast first pass, not truth.
"""
import os, re, json, argparse
from difflib import SequenceMatcher
from dotenv import load_dotenv
load_dotenv('/Users/robert/Desktop/themap/themap_claude/.env')
import psycopg2

GAP = 1.5          # beats of silence (end->next onset) that mark a phrase break
SUNG = ('verse', 'chorus', 'bridge', 'pre', 'refrain')
INSTR = ('solo', 'instrument', 'intro', 'outro', 'interlude', 'break', 'pre-verse', 'half')
is_sung = lambda n: any(k in n for k in SUNG) and not any(k in n for k in INSTR)

LYR_MARK = {'verse': {'v','v1','v2','vc'}, 'chorus': {'c','ch'}, 'pre': {'pc','pv','p'},
            'pre-chorus': {'pc','pv','p'}, 'bridge': {'b'}, 'refrain': {'r'}}
def lyric_blocks(blob):
    out=[]; parts=re.split(r'(\[[A-Za-z0-9]{1,4}\])', blob or ''); curm=None
    for p in parts:
        m=re.fullmatch(r'\[([A-Za-z0-9]{1,4})\]', p)
        if m: curm=m.group(1).lower(); continue
        if curm and p.strip(): out.append((curm, p.strip())); curm=None
    return out
def section_lyric(blocks, section):
    want = LYR_MARK.get(section, set())
    return next((t for mk, t in blocks if mk in want), None)

def conn():
    return psycopg2.connect(host=os.environ['DB_HOST'], dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
                            password=os.environ['DB_PASSWORD'], port=os.environ.get('DB_PORT', 5432), connect_timeout=10)

def sd_deg(s):                                              # base degree, ignoring #/b
    m = re.match(r'[#b]?(\d)', str(s)); return int(m.group(1)) if m else 0
def sd_alt(s): return str(s)[:1] in ('#', 'b')              # is it chromatic?
def dia(sd, octv): return octv * 7 + (sd_deg(sd) - 1)       # diatonic index, tonic=0
def lbl(sd, octv):
    s = str(sd); return s if octv == 0 else (f"↓{s}" if octv < 0 else f"↑{s}")

# ---------- phrase segmentation ----------
def segment(notes):
    """notes = non-rest melody notes in a section, sorted by beat -> list of phrases."""
    notes = sorted(notes, key=lambda n: n['beat'])
    phrases, cur = [], []
    for i, n in enumerate(notes):
        if cur:
            gap = n['beat'] - (cur[-1]['beat'] + cur[-1]['duration'])
            if gap >= GAP:
                phrases.append(cur); cur = []
        cur.append(n)
    if cur: phrases.append(cur)
    return phrases

def pitchseq(ph): return [(str(n['sd']), n['octave']) for n in ph]
def durseq(ph):   return [n['duration'] for n in ph]

def parse_pattern(patt):
    """'8-2222-ABAB' -> (lengths=[2,2,2,2], labels=['A','B','A2','B2']). None if unparseable."""
    if not patt: return None
    parts = patt.split(',')[0].strip().split('-')
    if len(parts) < 2 or not parts[1].isdigit(): return None
    lengths = [int(ch) for ch in parts[1]]
    labels = None
    if len(parts) >= 3 and re.fullmatch(r'[A-Z]+', parts[2] or ''):
        raw = list(parts[2]); counts = {}; labels = []
        for ch in raw:
            counts[ch] = counts.get(ch, 0) + 1
            labels.append(ch if counts[ch] == 1 else f"{ch}{counts[ch]}")
        if len(labels) != len(lengths): labels = None
    return lengths, labels

def segment_by_bars(notes, start, bpb, lengths):
    """Split notes into phrases of the given bar-lengths starting at beat `start`."""
    notes = sorted(notes, key=lambda n: n['beat']); phrases = []; cursor = start
    for L in lengths:
        end = cursor + L * bpb
        phrases.append([n for n in notes if cursor <= n['beat'] < end]); cursor = end
    return [p for p in phrases if p]

# ---------- labeling ----------
def label_phrases(phrases):
    """Assign A/B/... with variant suffixes (A, A2, A3) by similarity."""
    reps = []          # (letter, pitchseq)
    labels = []
    letters = 'ABCDEFGH'
    counts = {}
    for ph in phrases:
        ps = pitchseq(ph)
        match = None
        for li, (letter, rp) in enumerate(reps):
            if SequenceMatcher(None, [str(x) for x in ps], [str(x) for x in rp]).ratio() >= 0.6:
                match = letter; break
        if match is None:
            match = letters[len(set(r[0] for r in reps))]
            reps.append((match, ps))
        counts[match] = counts.get(match, 0) + 1
        labels.append(match if counts[match] == 1 else f"{match}{counts[match]}")
    return labels

def base(label): return re.match(r'[A-Z]', label).group()

# ---------- transform guessing ----------
def guess(P, Q):
    """Guess ops turning phrase P into Q (both note-dict lists). Returns (ops, summary)."""
    pp, qp = pitchseq(P), pitchseq(Q)
    pd, qd = durseq(P), durseq(Q)
    if pp == qp and pd == qd: return (["echo"], "identical")
    if pp == qp and pd != qd:                       # same pitches, only rhythm changed
        sp, sq = sum(pd), sum(qd)
        if sq > sp * 1.1: return (["augment"], "same pitches, rhythm stretched")
        if sq < sp * 0.9: return (["compress"], "same pitches, rhythm compressed")
        return (["rhythm-vary"], "same pitches, internal rhythm changed")
    ops = []
    # longest common prefix / suffix on pitch
    lcp = 0
    while lcp < min(len(pp), len(qp)) and pp[lcp] == qp[lcp]: lcp += 1
    lcs = 0
    while lcs < min(len(pp), len(qp)) and pp[-1-lcs] == qp[-1-lcs]: lcs += 1
    # merge: collapsing consecutive same-pitch notes of P yields Q's pitches
    merged = []
    for x in pp:
        if not merged or merged[-1] != x: merged.append(x)
    if merged == qp and len(qp) < len(pp): ops.append("merge")
    # length-based front/back edits
    if len(qp) < len(pp):
        if lcp >= len(qp): ops.append(f"trim:tail(-{len(pp)-len(qp)})")     # front held, tail dropped
        elif lcs >= len(qp): ops.append(f"clip:head(-{len(pp)-len(qp)})")   # back held, head dropped
    elif len(qp) > len(pp):
        if lcp >= len(pp): ops.append(f"tag:tail(+{len(qp)-len(pp)})")
        elif lcs >= len(pp): ops.append(f"tag:head(+{len(qp)-len(pp)})")
    # final-note lift/drop (same length, only last pitch differs)
    if len(pp) == len(qp) and pp[:-1] == qp[:-1] and pp[-1] != qp[-1]:
        d = dia(*qp[-1]) - dia(*pp[-1])
        ops.append("lift:final" if d > 0 else "drop:final")
    if not ops: ops.append("varied")
    summary = f"len {len(pp)}->{len(qp)}, shared front {lcp}, shared back {lcs}"
    return (ops, summary)

# ---------- palette ----------
def palette(notes):
    from collections import Counter
    dur = Counter()
    for n in notes: dur[str(n['sd'])] += n['duration']
    total = sum(dur.values()) or 1
    ranked = sorted(dur.items(), key=lambda x: -x[1])
    core = [k for k, v in ranked if v/total >= 0.15]
    reach = [k for k, v in ranked if v/total < 0.15]
    idx = [dia(n['sd'], n['octave']) for n in notes]
    return {"degrees": sorted(dur, key=lambda s: (sd_deg(s), s)), "core": core, "reach": reach,
            "stretch": f"{max(idx)-min(idx)+1} steps"}

# ---------- cadence ----------
def chord_at(chords, beat):
    for c in chords:
        if c['beat'] <= beat < c['beat'] + c['duration']: return c
    return None

def cadence(ph, chords):
    n = ph[-1]; deg = sd_deg(n['sd']); alt = sd_alt(n['sd'])
    oc = "closed" if (deg in (1, 3) and not alt) else "open"
    c = chord_at(chords, n['beat'])
    vs = "(no chord)"
    if c:
        r = c['root']; iv = (deg - r) % 7
        role = {0: "root", 2: "3rd", 4: "5th"}.get(iv)
        vs = f"{role} of {r} (chord tone)" if (role and not alt) else f"NCT over {r}"
    return {"note": lbl(n['sd'], n['octave']), "oc": oc, "vs_chord": vs}

# ---------- main ----------
def annotate(slug, dry=False):
    c = conn(); cur = c.cursor()
    cur.execute("select hookpad_json from parcels.songs where slug=%s", (slug,))
    row = cur.fetchone()
    if not row or not row[0]:
        print(f"no hookpad_json for {slug}"); c.close(); return
    d = row[0]
    lblocks = lyric_blocks((((d.get('lyrics') or {}).get('values') or ['']) or [''])[0])
    beats_per_bar = (d.get('meters') or [{}])[0].get('numBeats', 4)
    allnotes = [n for n in d.get('notes', []) if not n.get('isRest')]
    chords = d.get('chords', [])
    secs = d.get('sections') or []
    endBeat = d.get('endBeat') or (max((n['beat'] for n in d.get('notes', [])), default=0) + 4)
    spans = []
    for i, s in enumerate(secs):
        e = secs[i+1]['beat'] if i+1 < len(secs) else endBeat
        spans.append((s['name'].lower(), s['beat'], e))

    # first populated instance per vocal section base
    seen = {}
    for name, b, e in spans:
        if not is_sung(name): continue
        key = next((k for k in SUNG if k in name), name)
        ns = [n for n in allnotes if b <= n['beat'] < e]
        if ns and key not in seen: seen[key] = (name, b, e, ns)

    results = []
    for key, (name, b, e, ns) in seen.items():
        cur.execute("select patterns from parcels.melodies where slug=%s and section=%s limit 1", (slug, key))
        pr = cur.fetchone()
        manual = pr[0] if pr else None
        parsed = parse_pattern(manual)
        conformed = False
        if parsed:                                   # use YOUR architecture to segment
            lengths, plabels = parsed
            phrases = segment_by_bars(ns, b, beats_per_bar, lengths)
            if plabels and len(plabels) == len(phrases):
                labels = plabels; conformed = True
            else:
                labels = label_phrases(phrases)
        else:                                        # no manual pattern -> gap-based guess
            phrases = segment(ns); labels = label_phrases(phrases)
        if not phrases:                              # segmentation produced nothing usable
            phrases = segment(ns); labels = label_phrases(phrases); conformed = False
        pal = palette(ns)
        phrase_notes, cad = {}, {}
        for ph, lab in zip(phrases, labels):
            phrase_notes[lab] = [[n['sd'], n['octave'], n['duration']] for n in ph]
            cad[lab] = cadence(ph, chords)
        # transforms: each variant vs the FIRST occurrence of its letter (the prototype)
        trans = []
        first_of = {}
        for i, lab in enumerate(labels):
            bl = base(lab)
            if bl not in first_of:
                first_of[bl] = i
            else:
                ops, summ = guess(phrases[first_of[bl]], phrases[i])
                trans.append({"from": labels[first_of[bl]], "to": lab, "ops": ops, "summary": summ})
        # patterns string: if we conformed to your manual pattern, echo it (keeps them in sync)
        if conformed:
            patt = manual
        else:
            secbars = round((e - b) / beats_per_bar)
            pbars = ''.join(str(max(1, round((ph[-1]['beat']+ph[-1]['duration']-ph[0]['beat'])/beats_per_bar))) for ph in phrases)
            patt = f"{secbars}-{pbars}-{''.join(base(l) for l in labels)}"
        lyr = section_lyric(lblocks, key)
        results.append((key, patt, phrase_notes, pal, cad, trans, len(phrases), lyr))

    # report
    for key, patt, pn, pal, cad, trans, nph, lyr in results:
        print(f"\n### {slug}  /  {key}   pattern={patt}   ({nph} phrases)")
        print(f"   palette: core {pal['core']} reach {pal['reach']} stretch {pal['stretch']}")
        for lab, cd in cad.items():
            print(f"   {lab:<4} cadence {cd['note']:<4} {cd['oc']:<7} {cd['vs_chord']}")
        for t in trans:
            print(f"   {t['from']}->{t['to']}: {', '.join(t['ops'])}   [{t['summary']}]")

    if dry:
        print("\n(dry run — nothing written)"); c.close(); return
    cur.execute("alter table parcels.melodies add column if not exists patterns_auto text")
    cur.execute("alter table parcels.melodies add column if not exists lyrics text")
    for key, patt, pn, pal, cad, trans, nph, lyr in results:
        cur.execute("select id, patterns from parcels.melodies where slug=%s and section=%s limit 1", (slug, key))
        ex = cur.fetchone()
        # patterns = human-only; auto ALWAYS goes to patterns_auto (never clobber the human column)
        if ex:
            if ex[1] and ex[1] != patt:
                print(f"   ⚠ {key}: your patterns '{ex[1]}' != auto '{patt}' — kept yours, auto saved separately")
            cur.execute("update parcels.melodies set phrases=%s,palette=%s,cadence=%s,transforms=%s,patterns_auto=%s,lyrics=coalesce(%s,lyrics),updated_at=now() where id=%s",
                        (json.dumps(pn), json.dumps(pal), json.dumps(cad), json.dumps(trans), patt, lyr, ex[0]))
        else:
            cur.execute("insert into parcels.melodies (slug,section,patterns_auto,phrases,palette,cadence,transforms,lyrics) values (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (slug, key, patt, json.dumps(pn), json.dumps(pal), json.dumps(cad), json.dumps(trans), lyr))
    c.commit(); c.close()
    print(f"\nupserted {len(results)} section rows for {slug}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--slug'); ap.add_argument('--title'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    slug = a.slug
    if not slug and a.title:
        c = conn(); cur = c.cursor()
        cur.execute("select slug from parcels.songs where title ilike %s and hookpad_json is not null order by length(coalesce(hookpad_json->>'notes','')) desc limit 1", (a.title,))
        r = cur.fetchone(); slug = r[0] if r else None
        print(f"resolved title '{a.title}' -> {slug}")
    if not slug: print("need --slug or --title"); raise SystemExit(1)
    annotate(slug, dry=a.dry_run)
