#!/usr/bin/env python3
"""
A double- or half-time Hookpad paste for every song whose tempo can be heard
two ways, so the song can sit in both tempo playlists.

    themap_venv/python tempo_variant_pastes.py      # -> ~/Desktop/tempo_pastes/{guitar,beatles}/

Which songs: listed tempo (bpm_10) outside 100-140, or Hookpad's own tempo
outside it. Inside that band nobody counts a song two ways.

Which way: from the tempo the Hookpad file is ACTUALLY at, since the paste
re-frames that file. Under 100 -> double; over 140 -> halve; a file already at
100-140 moves toward the listed tempo (listed 70, file at 140 -> halve).

Name: the file's own name + "-" + the new tempo to the nearest ten (the
playlist it joins), e.g. oasis_wonderwall-170. The bpm inside is exact (172).
Songs that already have that variant in the library are skipped.

Lyrics are copied unchanged: they attach to notes in order, not to beats.
Inactive voices are left out.
"""
import copy, json, os, re, sys
import hp3   # pastes both Hookpads accept (no version, real fp)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_tempo_map as M
import build_pool_quiz as Q
from double_song import double, num

OUT = os.path.expanduser('~/Desktop/tempo_pastes')

# the tempo-map rows drop the resolved file; keep it, keyed by the Hookpad link
# the rows do carry
PATHS = {}
_card_for = Q.card_for
def card_for(r, files, library, catalog):
    c = _card_for(r, files, library, catalog)
    if c is not None:
        PATHS[c['hookpad']] = Q.resolve(r[0], r[1], files)
    return c
Q.card_for = card_for


def file_bpm(d):
    t = d.get('tempos') or []
    return float(t[0]['bpm']) if t and t[0].get('bpm') else None


def factor(listed, hp):
    if hp < 100: return 2
    if hp > 140: return .5
    if listed < 100: return .5
    if listed > 140: return 2
    return None


def off_grid(new):
    """notes the halving pushed below a 16th (beats not on a quarter-beat or triplet grid)"""
    bad = 0
    for n in new['notes']:
        for x in (n['beat'] - 1, n['duration']):
            if abs(x * 4 - round(x * 4)) > 1e-6 and abs(x * 3 - round(x * 3)) > 1e-6:
                bad += 1; break
    return bad


def sb(b, F): return num((float(b) - 1) * F + 1)


def full_json(d, F):
    """the whole saved song (what Hookpad's own Save sends), re-framed by F.
    Every beat coordinate scales, tempo scales the same way, everything else
    (lyrics, bands' instruments, settings) is kept as it was."""
    o = copy.deepcopy(d)
    o.pop('fp', None)
    def scale(xs, dur=True):
        for x in xs or []:
            if 'beat' in x: x['beat'] = sb(x['beat'], F)
            if dur and 'duration' in x and x['duration'] is not None: x['duration'] = num(x['duration'] * F)
            if 'recordingEndBeat' in x: x['recordingEndBeat'] = None
    scale(o.get('chords')); scale(o.get('notes'))
    for v in o.get('inactiveNotes') or []: scale(v)
    for k in ('keys', 'meters', 'breaks', 'sections', 'bands', 'keyFrames'): scale(o.get(k), dur=False)
    scale(o.get('tempos'), dur=False)
    for t in o.get('tempos') or []: t['bpm'] = num(t['bpm'] * F)
    if o.get('loopGui'): scale([o['loopGui']])
    o['cursor'] = {'beat': 1, 'location': (o.get('cursor') or {}).get('location', 'cursor-note-staff')}
    o['endBeat'] = sb(o.get('endBeat', 1), F)
    # audio would need cloning on the server; a re-framed copy has no use for it
    o['audioTracks'], o['externalAudioFiles'] = [], []
    if isinstance(o.get('lyrics'), dict): o['lyrics']['isOpen'] = o['lyrics']['isFocused'] = False
    return o


def jobs():
    """(sub, name, source path, factor, listed bpm_10, file bpm) per song to re-frame,
    plus skip notes"""
    library = {s.get('song', '').lower() for s in Q.context()[1]}
    out, skips = [], []
    for sub, rows in (('guitar', M.collect()), ('beatles', M.beatles_rows()[0])):
        for r in rows:
            path = PATHS.get(r['hookpad']) if r['hookpad'] else None
            if not path: skips.append(('no file', sub, r['title'])); continue
            d = json.load(open(path))
            hp = file_bpm(d)
            listed = r['bpm10'] if isinstance(r['bpm10'], (int, float)) else None
            if hp is None or listed is None: continue
            if 100 <= listed <= 140 and 100 <= hp <= 140: continue
            F = factor(listed, hp)
            if F is None: continue
            name = f'{os.path.splitext(os.path.basename(path))[0]}-{int(round(hp * F / 10) * 10)}'
            if name.lower() in library: skips.append(('have it', sub, name)); continue
            out.append((sub, name, path, F, listed, hp))
    return out, skips


def main():
    library = {s.get('song', '').lower() for s in Q.context()[1]}
    groups = [('guitar', M.collect()), ('beatles', M.beatles_rows()[0])]
    report = []
    for sub, rows in groups:
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        for r in rows:
            path = PATHS.get(r['hookpad']) if r['hookpad'] else None
            if not path: report.append(('no file', sub, r['title'])); continue
            d = json.load(open(path))
            hp = file_bpm(d)
            listed = r['bpm10'] if isinstance(r['bpm10'], (int, float)) else None
            if hp is None or listed is None: continue
            if 100 <= listed <= 140 and 100 <= hp <= 140: continue
            F = factor(listed, hp)
            if F is None: continue
            base = os.path.splitext(os.path.basename(path))[0]
            tag = int(round(hp * F / 10) * 10)
            name = f'{base}-{tag}'
            if name.lower() in library:
                report.append(('have it', sub, name)); continue
            new = double(d, F)
            if d.get('lyrics', {}).get('values'):
                new['lyrics'] = {'isOpen': False, 'isFocused': False, 'values': d['lyrics']['values']}
            open(os.path.join(OUT, sub, name + '.txt'), 'w').write(hp3.clipboard(new))
            report.append(('wrote', sub, name, hp, new['tempos'][0]['bpm'], off_grid(new)))
    return report


if __name__ == '__main__':
    rep = main()
    wrote = [x for x in rep if x[0] == 'wrote']
    for sub in ('guitar', 'beatles'):
        w = [x for x in wrote if x[1] == sub]
        print(f'{sub}: {len(w)} pastes  (doubled {sum(x[4] > x[3] for x in w)}, halved {sum(x[4] < x[3] for x in w)})')
    print('already in the library:', [x[2] for x in rep if x[0] == 'have it'])
    print('no Hookpad file:', [x[2] for x in rep if x[0] == 'no file'])
    fine = [x for x in wrote if x[5]]
    print(f'{len(fine)} halved songs now have notes finer than a 16th:', [(x[2], x[5]) for x in fine])
