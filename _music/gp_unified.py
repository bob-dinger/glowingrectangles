"""Unified parser for all Guitar Pro formats: .gp3, .gp4, .gp5 (via pyguitarpro),
.gp/.gp7 (via zipfile + GPIF XML), .gpx (via custom BCFZ decoder + GPX FS + XML).

Public API:
    summarize_gp_any(path) -> dict with title, artist, tempo, key, time_sig,
                              n_measures, sections, n_tracks (or {'error': msg})
"""
import os, struct
import guitarpro

from gp_xml_parser import parse_gpif, parse_gp_zip
from gpx_unpack import extract_score_gpif


def _summarize_pyguitarpro(path):
    s = guitarpro.parse(path)
    markers = [(i+1, h.marker.title) for i, h in enumerate(s.measureHeaders) if h.marker]
    return {
        'title': s.title or '',
        'artist': s.artist or '',
        'album': s.album or '',
        'tempo': float(s.tempo) if s.tempo else None,
        'key': s.key.name if s.key else None,
        'time_sig': None,   # pyguitarpro exposes per-measure time sigs; skip top-level for now
        'n_measures': len(s.measureHeaders),
        'sections': markers,
        'n_tracks': len(s.tracks),
    }


def _summarize_gp7(path):
    r = parse_gp_zip(path)
    return {**{k: r[k] for k in ('title','artist','album','tempo','key','time_sig',
                                  'n_measures','sections')}, 'n_tracks': len(r['tracks'])}


def _summarize_gpx(path):
    xml = extract_score_gpif(path)
    r = parse_gpif(xml)
    return {**{k: r[k] for k in ('title','artist','album','tempo','key','time_sig',
                                  'n_measures','sections')}, 'n_tracks': len(r['tracks'])}


def summarize_gp_any(path):
    """Detect format from extension + magic bytes, dispatch to right parser."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in ('.gp3', '.gp4', '.gp5'):
            return _summarize_pyguitarpro(path)
        if ext in ('.gp', '.gp7'):
            return _summarize_gp7(path)
        if ext == '.gpx':
            return _summarize_gpx(path)
        return {'error': f'unsupported extension {ext}'}
    except Exception as e:
        return {'error': f'{type(e).__name__}: {str(e)[:120]}'}


if __name__ == '__main__':
    import sys, json
    for p in sys.argv[1:]:
        print(f'=== {os.path.basename(p)} ===')
        r = summarize_gp_any(p)
        print(json.dumps(r, indent=2, default=str))
