"""Parse the GPIF XML format used by Guitar Pro 6 (.gpx) and Guitar Pro 7+ (.gp).

Both formats use the same internal XML schema (`Content/score.gpif`). The difference is
container: .gp is a plain ZIP, .gpx uses BCFZ-compressed GPX virtual filesystem.

Public API:
    parse_gpif(xml_bytes_or_path) -> dict
        Returns {title, artist, tempo, key, time_sig, n_measures, sections, tracks}
"""
import xml.etree.ElementTree as ET


def _text(el, path, default=None):
    if el is None: return default
    found = el.find(path)
    return found.text if found is not None and found.text is not None else default


def parse_gpif(src):
    """src = bytes (XML content) or path to file."""
    if isinstance(src, (bytes, bytearray)):
        root = ET.fromstring(src)
    else:
        root = ET.parse(src).getroot()

    score = root.find('Score')
    title = _text(score, 'Title', '')
    artist = _text(score, 'Artist', '')
    album = _text(score, 'Album', '')

    # MasterTrack/Automations holds tempo automations. First tempo automation is typically the song tempo.
    mt = root.find('MasterTrack')
    tempo = None
    if mt is not None:
        autos = mt.find('Automations')
        if autos is not None:
            for auto in autos.findall('Automation'):
                if _text(auto, 'Type') == 'Tempo':
                    val = _text(auto, 'Value')   # e.g. "120 2" (BPM and unit)
                    if val:
                        try: tempo = float(val.split()[0])
                        except: pass
                        break

    # MasterBars: ordered list of bars in the song
    mbars = root.find('MasterBars')
    n_measures = len(mbars) if mbars is not None else 0

    # Sections: a master bar can have a <Section><Letter>A</Letter><Text>Verse</Text></Section>
    sections = []
    if mbars is not None:
        for i, mb in enumerate(mbars):
            sec = mb.find('Section')
            if sec is not None:
                letter = _text(sec, 'Letter', '')
                text = _text(sec, 'Text', '')
                label = text or letter or ''
                sections.append((i + 1, label.strip()))

    # Key (sharps/flats) and time sig from first MasterBar
    key = None
    time_sig = None
    if mbars is not None and len(mbars):
        first = mbars[0]
        k = first.find('Key')
        if k is not None:
            acc = _text(k, 'AccidentalCount', '0')
            mode = _text(k, 'Mode', 'Major')
            try: key = f'{int(acc):+d}{mode[0]}'   # e.g. "+2M" = D major, "-3M" = Eb major
            except: pass
        t = first.find('Time')
        if t is not None and t.text:
            time_sig = t.text.strip()

    # Tracks: just collect names + a rough note count
    tracks = []
    tracks_el = root.find('Tracks')
    if tracks_el is not None:
        for tr in tracks_el.findall('Track'):
            tracks.append({
                'name': _text(tr, 'Name', '') or '',
                'short_name': _text(tr, 'ShortName', '') or '',
            })

    return {
        'title': title, 'artist': artist, 'album': album,
        'tempo': tempo, 'key': key, 'time_sig': time_sig,
        'n_measures': n_measures,
        'sections': sections,
        'tracks': tracks,
    }


def parse_gp_zip(path):
    """.gp (GP7+) is a plain ZIP containing Content/score.gpif."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        xml = z.read('Content/score.gpif')
    return parse_gpif(xml)


if __name__ == '__main__':
    import sys, json
    if len(sys.argv) < 2: print('usage: gp_xml_parser.py <file.gp|.gpif>'); sys.exit(1)
    p = sys.argv[1]
    if p.endswith('.gp') or p.endswith('.gp7'):
        result = parse_gp_zip(p)
    else:
        result = parse_gpif(p)
    print(json.dumps(result, indent=2, default=str))
