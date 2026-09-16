"""Walk ~/Desktop/midi_files, parse each MIDI's metadata, copy with normalized {artist}_{title}.mid name
to ~/Desktop/midi_files2 (originals left intact), and write ~/Desktop/midi_files2.csv catalog."""
import os, csv, shutil, re, mido

SRC = os.path.expanduser('~/Desktop/midi_files')
DST = os.path.expanduser('~/Desktop/midi_files2')
CSV_OUT = os.path.expanduser('~/Desktop/midi_files2.csv')
os.makedirs(DST, exist_ok=True)


def kebab(s):
    s = (s or '').lower().strip()
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-_')
    return s


def parse_name(fname):
    """Split filename into (artist, title). Prefers '-' as the artist-title separator,
    falling back to '_' only when no '-' exists. '_' inside an artist or title is treated
    as a word separator (becomes a space)."""
    base = os.path.splitext(fname)[0].lstrip('_').strip()
    # Strip trailing -ID (4+ digits, after - or _)
    base = re.sub(r'[-_]\d{4,}$', '', base)
    # Prefer '-' as the splitter (most reliable)
    if '-' in base:
        artist, _, title = base.partition('-')
    elif '_' in base:
        # No '-': use first '_' as artist|title split (less reliable)
        artist, _, title = base.partition('_')
    else:
        artist, title = '', base
    # Underscores → spaces (word separator inside artist/title)
    return artist.replace('_', ' ').strip().lower(), title.replace('_', ' ').strip().lower()


def get_metadata(path):
    try:
        m = mido.MidiFile(path)
        tempo = ts = ks = None
        notes = 0
        for tk in m.tracks:
            for msg in tk:
                if msg.type == 'set_tempo' and tempo is None:
                    tempo = round(mido.tempo2bpm(msg.tempo), 1)
                if msg.type == 'time_signature' and ts is None:
                    ts = f'{msg.numerator}/{msg.denominator}'
                if msg.type == 'key_signature' and ks is None:
                    ks = msg.key
                if msg.type == 'note_on' and msg.velocity > 0:
                    notes += 1
        try: dur = round(m.length, 1)
        except Exception: dur = None
        return {'tempo': tempo, 'time_sig': ts, 'key_sig': ks,
                'duration_sec': dur, 'tracks': len(m.tracks), 'notes': notes}
    except Exception as e:
        return {'error': str(e)[:80]}


rows = []
for root, dirs, files in os.walk(SRC):
    folder = os.path.relpath(root, SRC).replace(os.sep, '/') if root != SRC else ''
    for f in sorted(files):
        if not f.lower().endswith(('.mid', '.midi')):
            continue
        src_path = os.path.join(root, f)
        artist, title = parse_name(f)
        # Fall back to folder name as artist if filename has none
        if not artist and folder and folder != '.':
            artist = folder.split('/')[0].lower()
        # Build target filename
        ka, kt = kebab(artist), kebab(title)
        new_base = f'{ka}_{kt}' if ka else (kt or 'unknown')
        new_name = new_base + '.mid'
        dst_path = os.path.join(DST, new_name)
        # Handle name collisions
        if os.path.exists(dst_path):
            i = 2
            while os.path.exists(os.path.join(DST, f'{new_base}_{i}.mid')):
                i += 1
            new_name = f'{new_base}_{i}.mid'
            dst_path = os.path.join(DST, new_name)
        # Copy (best-effort)
        try:
            shutil.copy2(src_path, dst_path)
        except Exception as e:
            rows.append({'orig_folder': folder, 'orig_name': f, 'error': f'copy: {e}'}); continue
        # Metadata
        meta = get_metadata(src_path)
        rows.append({'orig_folder': folder, 'orig_name': f, 'new_name': new_name,
                     'artist': artist, 'title': title, **meta})

fields = ['orig_folder', 'orig_name', 'new_name', 'artist', 'title',
          'tempo', 'time_sig', 'key_sig', 'duration_sec', 'tracks', 'notes', 'error']
with open(CSV_OUT, 'w', newline='') as fp:
    w = csv.DictWriter(fp, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in fields})

n_ok = sum(1 for r in rows if not r.get('error'))
print(f'processed {len(rows)} files ({n_ok} ok, {len(rows)-n_ok} errors)')
print(f'copied to {DST}')
print(f'catalog → {CSV_OUT}')
