#!/usr/bin/env python3
"""
Hookpad Full Song Entry Script

Reads a Hookpad JSON file and enters chords + melody via Playwright.

Run:
  cd ~/Desktop && source midi_env/bin/activate && python glowinggardens_claude/hookpad_enter_song.py

Requirements:
  pip install playwright
  playwright install chromium
"""

import asyncio
import json
import sys
from playwright.async_api import async_playwright

# ============ CONFIGURATION ============

# Path to Hookpad JSON file
JSON_PATH = "/Users/robert/Desktop/hookpad_songs/hookpad_songs/kinks_lola_o_.json"

# Chord data (since the JSON has no chords, we provide them)
# Format: (beat, duration, roman_numeral, chord_type)
# chord_type: 'maj', 'min', '7', 'min7', 'dim', 'aug'
CHORD_DATA = [
    # Intro (1-16)
    (1, 16, 'I', 'maj'),

    # Verse I (17-52) - E A D E pattern
    (17, 4, 'I', 'maj'), (21, 4, 'IV', 'maj'), (25, 4, 'bVII', 'maj'), (29, 4, 'I', 'maj'),
    (33, 4, 'I', 'maj'), (37, 4, 'IV', 'maj'), (41, 4, 'bVII', 'maj'), (45, 4, 'I', 'maj'),
    (49, 4, 'I', 'maj'),

    # Bridge (53-60)
    (53, 8, 'I', 'maj'),

    # Verse II (61-96)
    (61, 4, 'I', 'maj'), (65, 4, 'IV', 'maj'), (69, 4, 'bVII', 'maj'), (73, 4, 'I', 'maj'),
    (77, 4, 'I', 'maj'), (81, 4, 'IV', 'maj'), (85, 4, 'bVII', 'maj'), (89, 4, 'I', 'maj'),
    (93, 4, 'I', 'maj'),

    # Bridge (97-104)
    (97, 8, 'I', 'maj'),

    # Chorus (105-120) - B F#m A B7
    (105, 4, 'V', 'maj'), (109, 4, 'ii', 'min'), (113, 4, 'IV', 'maj'), (117, 4, 'V', '7'),

    # Verse III (121-156)
    (121, 4, 'I', 'maj'), (125, 4, 'IV', 'maj'), (129, 4, 'bVII', 'maj'), (133, 4, 'I', 'maj'),
    (137, 4, 'I', 'maj'), (141, 4, 'IV', 'maj'), (145, 4, 'bVII', 'maj'), (149, 4, 'I', 'maj'),
    (153, 4, 'I', 'maj'),

    # Bridge (157-164)
    (157, 8, 'I', 'maj'),

    # Bridge section (165-184) - A C#m B
    (165, 4, 'IV', 'maj'), (169, 4, 'vi', 'min'), (173, 4, 'V', 'maj'),
    (177, 4, 'IV', 'maj'), (181, 4, 'vi', 'min'),

    # Verse IV (185-216)
    (185, 4, 'I', 'maj'), (189, 4, 'IV', 'maj'), (193, 4, 'bVII', 'maj'), (197, 4, 'I', 'maj'),
    (201, 4, 'I', 'maj'), (205, 4, 'IV', 'maj'), (209, 4, 'bVII', 'maj'), (213, 4, 'I', 'maj'),

    # Chorus (217-232)
    (217, 4, 'V', 'maj'), (221, 4, 'ii', 'min'), (225, 4, 'IV', 'maj'), (229, 4, 'V', '7'),

    # Verse V (233-260)
    (233, 4, 'I', 'maj'), (237, 4, 'IV', 'maj'), (241, 4, 'bVII', 'maj'), (245, 4, 'I', 'maj'),
    (249, 4, 'I', 'maj'), (253, 4, 'IV', 'maj'), (257, 4, 'bVII', 'maj'),

    # Outro (261+)
    (261, 16, 'I', 'maj'), (277, 16, 'I', 'maj'), (293, 16, 'I', 'maj'),
]

# Delay between actions (seconds)
ACTION_DELAY = 0.15
CHORD_DELAY = 0.25

# ============ HOOKPAD HELPERS ============

# Map chord names to Hookpad button text
CHORD_BUTTONS = {
    'I': 'I',
    'ii': 'ii',
    'iii': 'iii',
    'IV': 'IV',
    'V': 'V',
    'vi': 'vi',
    'vii': 'vii°',
    'bVII': 'VII',  # borrowed chord - need special handling
}

# Duration to beats mapping (Hookpad uses these keys)
# In Hookpad: default is usually 4 beats (whole note in their UI)
# Keys: probably need to explore, but let's start simple

async def enter_song():
    async with async_playwright() as p:
        print("=" * 50)
        print("HOOKPAD SONG ENTRY SCRIPT")
        print("=" * 50)

        # Load JSON for melody
        print(f"\nLoading: {JSON_PATH}")
        with open(JSON_PATH, encoding='utf-8-sig') as f:
            data = json.load(f)

        melody_notes = data.get('notes', [])
        print(f"Melody notes to enter: {len(melody_notes)}")
        print(f"Chords to enter: {len(CHORD_DATA)}")

        # Launch browser
        print("\nLaunching browser...")
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})
        page.set_default_timeout(60000)

        # Open Hookpad
        print("Opening Hookpad...")
        await page.goto("https://hookpad.hooktheory.com/", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Start blank project
        print("Starting blank project...")
        try:
            await page.click('text=Blank Project', timeout=10000)
            await asyncio.sleep(2)
        except:
            print("  No modal found, continuing...")

        # ============ ENTER CHORDS ============
        print("\n--- ENTERING CHORDS ---")

        # For now, just enter the chord progression simply
        # Hookpad adds chords sequentially when you click buttons

        entered = 0
        for beat, duration, roman, ctype in CHORD_DATA:
            # Find the button text
            button_text = CHORD_BUTTONS.get(roman, roman)

            # Handle borrowed chords (bVII) differently
            if roman == 'bVII':
                # For borrowed bVII, we might need to use the secondary chord menu
                # For now, let's just use VII and note it
                button_text = 'VII'

            try:
                # Click the chord button
                selector = f'.div-chord-button:has-text("{button_text}")'
                await page.click(selector, timeout=2000)
                entered += 1

                # Handle minor chords - need to click modifier
                if ctype == 'min' and roman not in ['ii', 'iii', 'vi']:
                    # Major chords that need to be made minor
                    pass  # ii, iii, vi are already minor

                # Handle 7th chords
                if ctype == '7':
                    # Try to add 7th - might need keyboard shortcut
                    pass

                await asyncio.sleep(CHORD_DELAY)

                if entered % 10 == 0:
                    print(f"  Entered {entered} chords...")

            except Exception as e:
                print(f"  Could not enter chord {roman}: {e}")

        print(f"  Total chords entered: {entered}")

        # ============ ENTER MELODY ============
        print("\n--- ENTERING MELODY ---")
        print("Double-clicking to enter melody mode...")

        # Click in the melody area to activate note entry
        # The melody area is typically in the upper portion of the editor
        await page.mouse.click(200, 300)
        await asyncio.sleep(0.3)
        await page.mouse.dblclick(200, 300)
        await asyncio.sleep(0.5)

        entered = 0
        for note in melody_notes[:100]:  # Start with first 100 notes as test
            sd = note.get('sd', '1')
            is_rest = note.get('isRest', False)

            if is_rest:
                # Press 0 or space for rest
                await page.keyboard.press('0')
            else:
                # Convert scale degree to key press
                # Hookpad uses 1-7, with modifiers for accidentals
                key = sd.replace('b', '').replace('#', '')  # Get base number
                if key.isdigit():
                    await page.keyboard.press(key)
                    entered += 1

            await asyncio.sleep(ACTION_DELAY)

            if entered % 50 == 0 and entered > 0:
                print(f"  Entered {entered} notes...")

        print(f"  Total melody notes entered: {entered}")

        # ============ DONE ============
        print("\n" + "=" * 50)
        print("DONE! Browser will stay open.")
        print("- Press SPACE to play")
        print("- Sign in to save your work")
        print("- Close browser window when finished")
        print("=" * 50)

        # Keep browser open
        try:
            await page.wait_for_timeout(300000)  # 5 minutes
        except:
            pass

        await browser.close()

if __name__ == "__main__":
    asyncio.run(enter_song())
