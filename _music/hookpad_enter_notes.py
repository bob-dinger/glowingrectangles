#!/usr/bin/env python3
"""
Hookpad Note Entry Script

Run:
  cd ~/Desktop && source midi_env/bin/activate && python hookpad_enter_notes.py
"""

import asyncio
from playwright.async_api import async_playwright

# ============ CUSTOMIZE YOUR MUSIC HERE ============

# Chord progression (use: I, ii, iii, IV, V, vi, vii, rest)
CHORDS = ['I', 'V', 'vi', 'IV']

# Melody notes (use: 1-7 for scale degrees)
MELODY = ['5', '3', '5', '6', '5', '4', '3', '2', '1', '3', '5', '3']

# Note duration in seconds between notes (lower = faster)
NOTE_DELAY = 0.2

# How long to keep browser open (seconds)
KEEP_OPEN = 120

# ===================================================

async def enter_notes():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})
        page.set_default_timeout(60000)

        print("Opening Hookpad...")
        await page.goto("https://hookpad.hooktheory.com/", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Start blank project
        print("Starting blank project...")
        try:
            await page.click('text=Blank Project', timeout=10000)
            await asyncio.sleep(2)
        except:
            print("No modal found, continuing...")

        # Add chords
        print(f"Adding chords: {' - '.join(CHORDS)}")
        for chord in CHORDS:
            await page.click(f'.div-chord-button:has-text("{chord}")')
            await asyncio.sleep(0.3)

        # Activate note entry
        print("Activating note entry...")
        await page.mouse.dblclick(120, 390)
        await asyncio.sleep(0.5)

        # Add melody notes
        print(f"Adding melody: {' '.join(MELODY)}")
        for note in MELODY:
            await page.keyboard.press(note)
            await asyncio.sleep(NOTE_DELAY)

        print(f"\nDone! Browser stays open for {KEEP_OPEN} seconds.")
        print("Press Play to hear it!")
        print("Sign in via 'Sign In' button in top right to save.")

        await asyncio.sleep(KEEP_OPEN)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(enter_notes())
