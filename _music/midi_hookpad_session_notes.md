# MIDI & Hookpad Session Notes
**Date:** February 2, 2026

## What We Accomplished

### 1. MIDI Workflow Established
- **Goal:** Create MIDI with code, hear it, edit in a DAW, export back to MIDI
- **Solution:** Python → .mid files → REAPER (free $60 DAW that actually exports MIDI) → back to Python
- **Key insight:** MIDI is just data. Treat it that way.

### 2. Tools Installed

```bash
# yt-dlp - download videos from YouTube
brew install yt-dlp

# ffmpeg - video/audio processing
brew install ffmpeg

# VLC - plays everything
brew install --cask vlc

# Python virtual environment with MIDI + Playwright tools
cd ~/Desktop
python3 -m venv midi_env
source midi_env/bin/activate
pip install mido playwright
playwright install chromium
```

### 3. MIDI Parsing Works
Your `music_stuff.zip` contains ~7,600 files:
- 1,172 vocal melodies
- Organized by measure length (2, 4, 8, 16 measures)
- Songs from Beatles, Nirvana, Pixies, Weezer, etc.

Parse any MIDI file:
```python
import mido
mid = mido.MidiFile('yourfile.mid')
for track in mid.tracks:
    for msg in track:
        print(msg)
```

### 4. Hookpad Automation Built
**File:** `~/Desktop/hookpad_enter_notes.py`

**How it works:**
- Opens Playwright's Chromium browser
- Navigates to Hookpad
- Clicks chord buttons (I, ii, iii, IV, V, vi, vii)
- Double-clicks melody area to activate note entry
- Presses 1-7 keys for scale degrees

**Run it:**
```bash
cd ~/Desktop && source midi_env/bin/activate && python hookpad_enter_notes.py
```

**Customize by editing:**
```python
CHORDS = ['I', 'V', 'vi', 'IV']  # The famous pop progression
MELODY = ['5', '3', '5', '6', '5', '4', '3', '2', '1', '3', '5', '3']
```

### 5. Hookpad UI Selectors Discovered
| Element | Selector |
|---------|----------|
| Chord buttons | `.div-chord-button:has-text("I")` |
| Note entry | Double-click in melody area, then press 1-7 |
| Duration | `h`, `j`, `k`, `l`, `;` keys |

### 6. Video Clipping Works
```bash
# Download from YouTube
yt-dlp "https://youtube.com/watch?v=VIDEO_ID"

# Clip a section (start at 2:29, end at 2:34.75)
ffmpeg -i input.mkv -ss 2:29 -to 2:34.75 -c copy output.mkv
```

## Key Files on Desktop
- `hookpad_enter_notes.py` - Hookpad automation script
- `midi_env/` - Python virtual environment with all tools
- `music_stuff.zip` - Your MIDI collection
- `midi_export.MID` - Test export from REAPER

## Brave Profile Info
- "adam" profile = Profile 3
- Located at: `~/Library/Application Support/BraveSoftware/Brave-Browser/Profile 3`
- CDP connection to Brave was flaky; Playwright's Chromium works better

## Next Steps (when ready)
1. Parse MIDI files → extract chords/melody → auto-generate Hookpad input
2. Build web-based MIDI tools (Tone.js for playback)
3. Analyze your 1000+ songs for patterns

## Commands to Rebuild Environment
```bash
# If starting fresh
cd ~/Desktop
python3 -m venv midi_env
source midi_env/bin/activate
pip install mido midiutil playwright
playwright install chromium
```

## VST/Sound Info
- **Free instruments:** Spitfire LABS, Vital, VSCO 2 Community Edition
- **SoundFonts:** GeneralUser GS, FluidR3
- **Web playback:** Tone.js + @tonejs/midi
