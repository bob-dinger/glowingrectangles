"""Extract structured musical data from any Guitar Pro file (.gp3/.gp4/.gp5/.gp/.gpx).

Output schema:
    {
      title, artist, tempo, key: {root: 0-11, mode: 'major'/'minor'},
      time_sig: (num, den),
      sections: [{measure: 1-indexed, name: str}],
      chord_progression: [{measure, beat (0-based within measure), duration_beats, name}],
      melody: [{measure, beat, pitch (midi), duration_beats}],
      n_measures: int,
    }
"""
import os, guitarpro

# Map pyguitarpro KeySignature names to (root pitch class, mode).
# Names look like "CMajor", "GMajor", "EMinor", "BMajorFlat" (Bb major), etc.
_KEY_NAME_MAP = {
    # Majors with sharps
    'CMajor': (0,'major'), 'GMajor': (7,'major'), 'DMajor': (2,'major'),
    'AMajor': (9,'major'), 'EMajor': (4,'major'), 'BMajor': (11,'major'),
    'FSharpMajor': (6,'major'), 'CSharpMajor': (1,'major'),
    # Majors with flats
    'FMajor': (5,'major'), 'BMajorFlat': (10,'major'), 'EMajorFlat': (3,'major'),
    'AMajorFlat': (8,'major'), 'DMajorFlat': (1,'major'), 'GMajorFlat': (6,'major'),
    'CMajorFlat': (11,'major'),
    # Minors with sharps
    'AMinor': (9,'minor'), 'EMinor': (4,'minor'), 'BMinor': (11,'minor'),
    'FSharpMinor': (6,'minor'), 'CSharpMinor': (1,'minor'),
    'GSharpMinor': (8,'minor'), 'DSharpMinor': (3,'minor'), 'ASharpMinor': (10,'minor'),
    # Minors with flats
    'DMinor': (2,'minor'), 'GMinor': (7,'minor'), 'CMinor': (0,'minor'),
    'FMinor': (5,'minor'), 'BMinorFlat': (10,'minor'), 'EMinorFlat': (3,'minor'),
    'AMinorFlat': (8,'minor'),
}


def _key_from_pyguitar(s):
    name = s.key.name if s.key else 'CMajor'
    return _KEY_NAME_MAP.get(name, (0, 'major'))


def _beats_per_measure(time_sig):
    """Convert a pyguitarpro TimeSignature to beats-per-measure in quarter-note units.
    A 6/8 = 3 quarter-note beats, 4/4 = 4 quarters, 3/4 = 3, 2/4 = 2."""
    num = time_sig.numerator
    den = time_sig.denominator.value
    return num * (4.0 / den)


def _beat_duration_quarters(beat):
    """Duration in quarter-note units. pyguitarpro Duration value is the inverse (4=quarter, 8=eighth)."""
    d = beat.duration
    base = 4.0 / d.value
    if d.isDotted: base *= 1.5
    # tuplet
    if d.tuplet and d.tuplet.enters > 0 and d.tuplet.times > 0:
        base *= d.tuplet.times / d.tuplet.enters
    return base


def extract_pyguitarpro(path, vocal_track_hint=None):
    """Extract from .gp3/.gp4/.gp5 via pyguitarpro."""
    s = guitarpro.parse(path)
    key_root, key_mode = _key_from_pyguitar(s)
    first_ts = s.measureHeaders[0].timeSignature
    bpm = _beats_per_measure(first_ts)

    # Sections from markers
    sections = [{'measure': i+1, 'name': h.marker.title}
                for i, h in enumerate(s.measureHeaders) if h.marker]

    # Find best chord-bearing track (most chord-annotated beats among non-drum)
    def chord_count(t):
        if t.channel.channel == 9: return 0
        return sum(1 for m in t.measures for v in m.voices for b in v.beats
                   if b.effect and b.effect.chord)
    chord_track_idx = max(range(len(s.tracks)), key=lambda i: chord_count(s.tracks[i]))
    chord_track = s.tracks[chord_track_idx]

    # Walk chord track, build chord_progression
    chord_prog = []
    for mi, m in enumerate(chord_track.measures):
        # Beat-position counter within measure (in quarter-note units)
        for v in m.voices:
            beat_pos = 0.0
            for b in v.beats:
                dur = _beat_duration_quarters(b)
                if b.effect and b.effect.chord:
                    chord_prog.append({
                        'measure': mi + 1,
                        'beat': beat_pos,
                        'duration_beats': dur,
                        'name': b.effect.chord.name,
                    })
                beat_pos += dur

    # Find vocal/melody track: explicit vocal name first; otherwise score by monophony + vocal-register
    # narrow-range fit. Avoid "Play Along" / "Solo" / "Lead Guitar" backing tracks.
    def name_score(name):
        n = (name or '').lower()
        # Backing/secondary vocals: prefer lead over these
        if any(k in n for k in ['background','backing','harmony','choir','chorus vocal']):
            if any(k in n for k in ['vocal','voice','vox','sing']): return 40
        # Strong positive: explicit lead vocal markers
        if any(k in n for k in ['lead vocal','main vocal','lead vox','main vox']): return 120
        if any(k in n for k in ['vocal','voice','vox','sing']): return 100
        if 'melody' in n: return 80
        # Penalties: backing tracks and full-arrangement tracks
        if any(k in n for k in ['play along','playalong','play-along']): return -50
        if 'solo' in n and 'guitar' not in n: return 20
        if any(k in n for k in ['rhythm','strum','chord','comp']): return -30
        if 'bass' in n and 'guitar' not in n: return -100
        if 'drum' in n: return -100
        return 0

    def track_pitches(t):
        out = []
        for m in t.measures:
            for v in m.voices:
                for b in v.beats:
                    for n in b.notes:
                        if 0 <= n.string - 1 < len(t.strings):
                            out.append(t.strings[n.string-1].value + n.value)
        return out

    def melody_score(t):
        """Higher = more melody-like. Combines: vocal-register-ness, monophony, narrow range, note density."""
        if t.channel.channel == 9: return -1000   # drums
        pitches = track_pitches(t)
        if not pitches: return -1000
        # Range check: melody usually spans 12-24 semitones; reject wide multi-instrument tracks
        lo, hi = min(pitches), max(pitches)
        rng = hi - lo
        # Monophony
        mono = poly = 0
        for m in t.measures:
            for v in m.voices:
                for b in v.beats:
                    if not b.notes: continue
                    if len(b.notes) == 1: mono += 1
                    else: poly += 1
        if mono + poly == 0: return -1000
        mono_pct = mono / (mono + poly)
        # In vocal range (C4-C6 = 60-84): % of notes
        in_range = sum(1 for p in pitches if 55 <= p <= 84) / len(pitches)
        # Penalties
        range_penalty = max(0, rng - 28) * 2   # range > 2 octaves is suspect
        # Avoid bass-only tracks (max pitch too low)
        if hi < 55: return -500
        # Boost: narrow + monophonic + in vocal range
        score = (mono_pct * 50) + (in_range * 50) - range_penalty
        # Add name-based adjustments
        score += name_score(t.name)
        # Note density: penalize too-sparse tracks (solos < 50 notes)
        if len(pitches) < 50: score -= 20
        return score

    vocal_idx = None
    if vocal_track_hint is not None:
        vocal_idx = vocal_track_hint
    else:
        scores = [(i, melody_score(t), t.name) for i, t in enumerate(s.tracks)]
        scores.sort(key=lambda x: x[1], reverse=True)
        vocal_idx = scores[0][0]

    # Extract melody from vocal track
    melody = []
    vt = s.tracks[vocal_idx]
    for mi, m in enumerate(vt.measures):
        for v in m.voices:
            beat_pos = 0.0
            for b in v.beats:
                dur = _beat_duration_quarters(b)
                if b.notes:
                    # Pick highest pitch (top note of any chord stack)
                    pitches = []
                    for n in b.notes:
                        if n.string - 1 < len(vt.strings):
                            pitches.append(vt.strings[n.string-1].value + n.value)
                    if pitches:
                        melody.append({
                            'measure': mi + 1, 'beat': beat_pos,
                            'duration_beats': dur, 'pitch': max(pitches),
                        })
                beat_pos += dur

    # Per-measure time signatures (so paste-builder knows beats per measure for each measure)
    measure_ts = [(h.timeSignature.numerator, h.timeSignature.denominator.value) for h in s.measureHeaders]
    return {
        'title': s.title or '', 'artist': s.artist or '',
        'tempo': float(s.tempo) if s.tempo else 120.0,
        'key': {'root': key_root, 'mode': key_mode},
        'time_sig': measure_ts[0] if measure_ts else (4, 4),
        'measure_ts': measure_ts,
        'sections': sections,
        'chord_progression': chord_prog,
        'melody': melody,
        'n_measures': len(s.measureHeaders),
        'chord_track_name': chord_track.name,
        'vocal_track_name': s.tracks[vocal_idx].name,
    }


def _gp7_pitch_step(step, accidental):
    """Convert GPIF KeyNote step + accidental to pitch class 0-11."""
    base = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}.get(step, 0)
    if accidental == 'Sharp': base = (base + 1) % 12
    elif accidental == 'Flat': base = (base - 1) % 12
    elif accidental == 'DoubleSharp': base = (base + 2) % 12
    elif accidental == 'DoubleFlat': base = (base - 2) % 12
    return base


def _chord_name_from_gpif(chord_el):
    """Build a chord-name string from a GPIF <Chord> element's KeyNote/BassNote/Degree children."""
    import re
    kn = chord_el.find('KeyNote')
    if kn is None: return None
    root = kn.get('step', '')
    acc = kn.get('accidental', '')
    if acc == 'Sharp': root += '#'
    elif acc == 'Flat': root += 'b'

    # Walk <Degree> children to infer quality + extensions
    # Each Degree has interval (Third, Fifth, Seventh, Ninth, ...) and alteration (Major, Minor, Perfect, Diminished, Augmented).
    quality = 'major'
    extensions = []
    alterations = []
    has_3 = has_5 = False
    is_omit_3 = False
    for deg in chord_el.findall('Degree'):
        iv = deg.get('interval', '')
        alt = deg.get('alteration', '')
        omitted = deg.get('omitted', 'false') == 'true'
        if iv == 'Third':
            has_3 = True
            if alt == 'Minor': quality = 'minor'
            elif alt == 'Diminished': quality = 'minor'   # treat as minor for our purposes
            if omitted: is_omit_3 = True
        elif iv == 'Fifth':
            has_5 = True
            if alt == 'Diminished': alterations.append('b5')
            elif alt == 'Augmented': alterations.append('#5')
        elif iv == 'Seventh':
            if alt == 'Major': extensions.append('M7')
            elif alt == 'Minor': extensions.append('7')
            elif alt == 'Diminished': extensions.append('b7')   # rare
        elif iv == 'Ninth':
            extensions.append('9' if alt != 'Flat' else 'b9')
        elif iv == 'Eleventh':
            extensions.append('11' if alt != 'Sharp' else '#11')
        elif iv == 'Thirteenth':
            extensions.append('13')
        elif iv == 'Sixth':
            extensions.append('6')

    name = root
    if not has_3 and has_5:
        name += '5'   # power chord
    else:
        if quality == 'minor': name += 'm'
        for ext in extensions:
            if ext == 'M7': name += 'maj7'
            else: name += ext
        for alt in alterations: name += alt

    bn = chord_el.find('BassNote')
    if bn is not None:
        bs = bn.get('step', ''); ba = bn.get('accidental', '')
        if bs and bs != root.rstrip('#b'):
            bass = bs
            if ba == 'Sharp': bass += '#'
            elif ba == 'Flat': bass += 'b'
            name += '/' + bass
    return name


def extract_gpif(path):
    """Extract from .gp or .gpx via GPIF XML."""
    import xml.etree.ElementTree as ET, zipfile
    if path.endswith('.gp') or path.endswith('.gp7'):
        with zipfile.ZipFile(path) as z: xml = z.read('Content/score.gpif')
    else:
        from gpx_unpack import extract_score_gpif
        xml = extract_score_gpif(path)
    root = ET.fromstring(xml)

    score = root.find('Score')
    title = (score.findtext('Title') or '') if score is not None else ''
    artist = (score.findtext('Artist') or '') if score is not None else ''

    # Tempo from first Tempo automation
    tempo = 120.0
    mt = root.find('MasterTrack')
    if mt is not None:
        autos = mt.find('Automations')
        if autos is not None:
            for a in autos.findall('Automation'):
                if (a.findtext('Type') or '') == 'Tempo':
                    v = a.findtext('Value') or ''
                    if v:
                        try: tempo = float(v.split()[0]); break
                        except: pass

    # MasterBars: order, time signatures, key sig, section markers
    mbars = root.find('MasterBars').findall('MasterBar') if root.find('MasterBars') is not None else []
    n_measures = len(mbars)
    sections = []
    measure_ts = []   # parallel list of (num, den) per measure
    measure_starts = [1.0]   # 1-indexed global beat each measure starts at
    cur_beat = 1.0
    key_root = 0; key_mode = 'major'

    for i, mb in enumerate(mbars):
        # Section
        sec = mb.find('Section')
        if sec is not None:
            text = (sec.findtext('Text') or sec.findtext('Letter') or '').strip()
            if text:
                sections.append({'measure': i + 1, 'name': text})
        # Time signature (default 4/4 if absent)
        t = mb.findtext('Time') or '4/4'
        try: num, den = (int(x) for x in t.split('/'))
        except: num, den = 4, 4
        measure_ts.append((num, den))
        # Key (from first measure only)
        if i == 0:
            k = mb.find('Key')
            if k is not None:
                # AccidentalCount is signed: positive=sharps, negative=flats
                try: acc = int(k.findtext('AccidentalCount') or '0')
                except: acc = 0
                mode = k.findtext('Mode') or 'Major'
                key_mode = 'minor' if mode.lower() == 'minor' else 'major'
                # Convert sharps/flats count to tonic pitch class for major mode
                sharps_to_major = {0:0, 1:7, 2:2, 3:9, 4:4, 5:11, 6:6, 7:1}
                flats_to_major  = {0:0, 1:5, 2:10, 3:3, 4:8, 5:1, 6:6, 7:11}
                if acc >= 0: key_root = sharps_to_major.get(acc, 0)
                else: key_root = flats_to_major.get(-acc, 0)
                if key_mode == 'minor':
                    # Relative minor = tonic - 3 semitones (vi of major)
                    key_root = (key_root - 3) % 12
        # Advance global beat for next measure
        beats_in_measure = num * (4.0 / den)
        cur_beat += beats_in_measure
        measure_starts.append(cur_beat)

    # Build chord progression by walking Bars→Voices→Beats and looking for inline <Chord>
    # GPIF organizes data as flat collections with cross-references by id/ref.
    bars_el = root.find('Bars'); voices_el = root.find('Voices')
    beats_el = root.find('Beats'); rhythms_el = root.find('Rhythms')
    bars_by_id = {b.get('id'): b for b in (bars_el if bars_el is not None else []) if b.get('id')}
    voices_by_id = {v.get('id'): v for v in (voices_el if voices_el is not None else []) if v.get('id')}
    beats_by_id = {b.get('id'): b for b in (beats_el if beats_el is not None else []) if b.get('id')}
    rhythms_by_id = {r.get('id'): r for r in (rhythms_el if rhythms_el is not None else []) if r.get('id')}

    def rhythm_quarters(rhythm_el):
        """Convert a Rhythm element to quarter-note duration."""
        if rhythm_el is None: return 1.0
        nv = (rhythm_el.findtext('NoteValue') or 'Quarter')
        val_map = {'Whole':4.0,'Half':2.0,'Quarter':1.0,'Eighth':0.5,'16th':0.25,'32nd':0.125,'64th':0.0625}
        base = val_map.get(nv, 1.0)
        # Augmentation dots
        aug = rhythm_el.find('AugmentationDot')
        if aug is not None:
            try: dots = int(aug.get('count', '0')); base *= sum(0.5**i for i in range(dots+1))
            except: pass
        return base

    # Build chord-name library per track. Each track has <Items><Item id="N" name="A#5"><Chord>...</Chord></Item></Items>.
    # When a beat says <Chord>N</Chord>, look up the name in the track's library.
    tracks_el = root.find('Tracks')
    n_tracks = len(tracks_el.findall('Track')) if tracks_el is not None else 0
    chord_libs = {}   # track_idx -> {item_id_str: name}
    for ti, tr in enumerate(tracks_el.findall('Track') if tracks_el is not None else []):
        lib = {}
        for item in tr.findall('.//Items/Item'):
            iid = item.get('id'); name = item.get('name')
            if iid is not None and name and item.find('Chord') is not None:
                lib[iid] = name
        chord_libs[ti] = lib

    # MasterBars list "Bars" attribute: space-separated bar IDs (one per track)
    # Pick the bar belonging to the track with the most chord-annotated beats.
    track_chord_counts = [0] * n_tracks
    for mb in mbars:
        bar_ids = (mb.findtext('Bars') or '').split()
        for ti, bid in enumerate(bar_ids):
            if ti >= n_tracks: break
            bar = bars_by_id.get(bid)
            if bar is None: continue
            voice_refs = (bar.findtext('Voices') or '').split()
            for vid in voice_refs:
                if vid == '-1': continue
                voice = voices_by_id.get(vid)
                if voice is None: continue
                beat_refs = (voice.findtext('Beats') or '').split()
                for bid_b in beat_refs:
                    beat = beats_by_id.get(bid_b)
                    if beat is not None and beat.find('Chord') is not None:
                        track_chord_counts[ti] += 1
    chord_track_idx = track_chord_counts.index(max(track_chord_counts)) if track_chord_counts else 0

    chord_prog = []
    for mi, mb in enumerate(mbars):
        bar_ids = (mb.findtext('Bars') or '').split()
        if chord_track_idx >= len(bar_ids): continue
        bar = bars_by_id.get(bar_ids[chord_track_idx])
        if bar is None: continue
        voice_refs = (bar.findtext('Voices') or '').split()
        for vid in voice_refs:
            if vid == '-1': continue
            voice = voices_by_id.get(vid)
            if voice is None: continue
            beat_refs = (voice.findtext('Beats') or '').split()
            beat_pos = 0.0
            for bid_b in beat_refs:
                beat = beats_by_id.get(bid_b)
                if beat is None: continue
                rhythm_ref = beat.find('Rhythm')
                rhythm = rhythms_by_id.get(rhythm_ref.get('ref')) if rhythm_ref is not None else None
                dur = rhythm_quarters(rhythm)
                ch_el = beat.find('Chord')
                if ch_el is not None:
                    # Two forms: either <Chord>N</Chord> (index ref) or <Chord><KeyNote.../></Chord> (inline)
                    name = None
                    if ch_el.text and ch_el.text.strip():
                        name = chord_libs.get(chord_track_idx, {}).get(ch_el.text.strip())
                    if not name and ch_el.find('KeyNote') is not None:
                        name = _chord_name_from_gpif(ch_el)
                    if name:
                        chord_prog.append({
                            'measure': mi + 1, 'beat': beat_pos,
                            'duration_beats': dur, 'name': name,
                        })
                beat_pos += dur

    # ===== Melody extraction =====
    # Build Note lookup + each track's tuning (pitch values per string index).
    notes_el = root.find('Notes')
    notes_by_id = {n.get('id'): n for n in (notes_el if notes_el is not None else []) if n.get('id')}

    def _track_tuning(track_el):
        """Return list of MIDI pitches (one per string), or None if no tuning."""
        for prop in track_el.findall('.//Property'):
            if prop.get('name') == 'Tuning':
                pitches = prop.find('Pitches')
                if pitches is not None and pitches.text:
                    try: return [int(x) for x in pitches.text.split()]
                    except: pass
        return None

    def _note_pitch(note_el, tuning):
        """Return MIDI pitch of a Note, or None if can't compute.
        Two encodings: (a) guitar tab via String+Fret+tuning, (b) concert pitch via Tone(step 0-11)+Octave."""
        string_idx = fret = tone = octave = None
        for prop in note_el.findall('.//Property'):
            n = prop.get('name')
            if n == 'String':
                try: string_idx = int(prop.findtext('String'))
                except: pass
            elif n == 'Fret':
                try: fret = int(prop.findtext('Fret'))
                except: pass
            elif n == 'Tone':
                try: tone = int(prop.findtext('Step'))
                except: pass
            elif n == 'Octave':
                try: octave = int(prop.findtext('Number'))
                except: pass
        if tone is not None and octave is not None:
            return tone + (octave + 1) * 12   # C4 = MIDI 60
        if string_idx is not None and fret is not None and tuning is not None:
            if 0 <= string_idx < len(tuning):
                return tuning[string_idx] + fret
        return None

    # Pick vocal/melody track using same scoring as the pyguitarpro path: name + monophony +
    # in-range fit. Walk each track's beats to compute these stats.
    tracks_list = tracks_el.findall('Track') if tracks_el is not None else []

    def _gpif_name_score(name):
        n = (name or '').lower()
        if any(k in n for k in ['background','backing','harmony','choir','chorus vocal']):
            if any(k in n for k in ['vocal','voice','vox','sing']): return 40
        if any(k in n for k in ['lead vocal','main vocal','lead vox','main vox']): return 120
        if any(k in n for k in ['vocal','voice','vox','sing']): return 100
        if 'melody' in n: return 80
        if any(k in n for k in ['play along','playalong','play-along']): return -50
        if 'solo' in n and 'guitar' not in n: return 20
        if any(k in n for k in ['rhythm','strum','chord','comp']): return -30
        if 'bass' in n and 'guitar' not in n: return -100
        if 'drum' in n: return -100
        return 0

    def _gpif_track_stats(ti, tr):
        """Walk all beats in this track, return list of pitches + monophony ratio."""
        tuning = _track_tuning(tr)
        pitches = []; mono = poly = 0
        for mb in mbars:
            bar_ids = (mb.findtext('Bars') or '').split()
            if ti >= len(bar_ids): continue
            bar = bars_by_id.get(bar_ids[ti])
            if bar is None: continue
            for vid in (bar.findtext('Voices') or '').split():
                if vid == '-1': continue
                voice = voices_by_id.get(vid)
                if voice is None: continue
                for bid_b in (voice.findtext('Beats') or '').split():
                    beat = beats_by_id.get(bid_b)
                    if beat is None: continue
                    nrefs = (beat.findtext('Notes') or '').split()
                    if not nrefs: continue
                    if len(nrefs) == 1: mono += 1
                    else: poly += 1
                    for nid in nrefs:
                        nn = notes_by_id.get(nid)
                        if nn is None: continue
                        p = _note_pitch(nn, tuning)
                        if p is not None: pitches.append(p)
        return pitches, mono, poly

    def _gpif_melody_score(ti, tr):
        # Drum-track detection: tuning of all zeros
        tn = _track_tuning(tr)
        if tn and not any(p > 0 for p in tn): return -1000
        pitches, mono, poly = _gpif_track_stats(ti, tr)
        if not pitches or mono + poly == 0: return -1000
        lo, hi = min(pitches), max(pitches)
        if hi < 55: return -500
        mono_pct = mono / (mono + poly)
        in_range = sum(1 for p in pitches if 55 <= p <= 84) / len(pitches)
        rng = hi - lo
        range_penalty = max(0, rng - 28) * 2
        score = (mono_pct * 50) + (in_range * 50) - range_penalty
        score += _gpif_name_score(tr.findtext('Name') or '')
        if len(pitches) < 50: score -= 20
        return score

    if tracks_list:
        scores = [(ti, _gpif_melody_score(ti, tr)) for ti, tr in enumerate(tracks_list)]
        scores.sort(key=lambda x: x[1], reverse=True)
        vocal_idx = scores[0][0]
    else:
        vocal_idx = 0

    vocal_track = tracks_list[vocal_idx] if vocal_idx < len(tracks_list) else None
    vocal_tuning = _track_tuning(vocal_track) if vocal_track is not None else None
    vocal_track_name = vocal_track.findtext('Name') if vocal_track is not None else ''

    melody = []
    if vocal_track is not None:
        for mi, mb in enumerate(mbars):
            bar_ids = (mb.findtext('Bars') or '').split()
            if vocal_idx >= len(bar_ids): continue
            bar = bars_by_id.get(bar_ids[vocal_idx])
            if bar is None: continue
            voice_refs = (bar.findtext('Voices') or '').split()
            for vid in voice_refs:
                if vid == '-1': continue
                voice = voices_by_id.get(vid)
                if voice is None: continue
                beat_refs = (voice.findtext('Beats') or '').split()
                beat_pos = 0.0
                for bid_b in beat_refs:
                    beat = beats_by_id.get(bid_b)
                    if beat is None: continue
                    rhythm_ref = beat.find('Rhythm')
                    rhythm = rhythms_by_id.get(rhythm_ref.get('ref')) if rhythm_ref is not None else None
                    dur = rhythm_quarters(rhythm)
                    note_refs = beat.findtext('Notes')
                    if note_refs:
                        pitches = []
                        for nid in note_refs.split():
                            n = notes_by_id.get(nid)
                            if n is None: continue
                            p = _note_pitch(n, vocal_tuning)
                            if p is not None: pitches.append(p)
                        if pitches:
                            melody.append({
                                'measure': mi + 1, 'beat': beat_pos,
                                'duration_beats': dur, 'pitch': max(pitches),
                            })
                    beat_pos += dur

    return {
        'title': title, 'artist': artist,
        'tempo': tempo,
        'key': {'root': key_root, 'mode': key_mode},
        'time_sig': measure_ts[0] if measure_ts else (4, 4),
        'measure_ts': measure_ts,
        'sections': sections,
        'chord_progression': chord_prog,
        'melody': melody,
        'n_measures': n_measures,
        'chord_track_name': '(track index ' + str(chord_track_idx) + ')',
        'vocal_track_name': vocal_track_name or '(none)',
    }


def extract(path):
    """Top-level extractor. Dispatches by extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.gp3', '.gp4', '.gp5'):
        return extract_pyguitarpro(path)
    if ext in ('.gp', '.gp7', '.gpx'):
        return extract_gpif(path)
    raise NotImplementedError(f'{ext} not yet supported in gp_extract')


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2: print('usage: gp_extract.py <file>'); sys.exit(1)
    r = extract(sys.argv[1])
    print(f"{r['title']} / {r['artist']}")
    print(f"  tempo={r['tempo']}, key={r['key']}, ts={r['time_sig']}, measures={r['n_measures']}")
    print(f"  sections ({len(r['sections'])}):")
    for s in r['sections'][:15]:
        print(f"    m{s['measure']:3d}: {s['name']}")
    print(f"  chord_progression: {len(r['chord_progression'])} (track: {r['chord_track_name']})")
    for c in r['chord_progression'][:10]:
        print(f"    m{c['measure']:3d} beat {c['beat']:.1f}: {c['name']} ({c['duration_beats']:.1f}q)")
    print(f"  melody: {len(r['melody'])} notes (track: {r['vocal_track_name']})")
    for n in r['melody'][:10]:
        print(f"    m{n['measure']:3d} beat {n['beat']:.1f}: midi {n['pitch']} ({n['duration_beats']:.1f}q)")
