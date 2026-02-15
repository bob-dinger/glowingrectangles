#!/usr/bin/env python3
"""
Hookpad Server - receives chord progressions and enters them via Playwright

Run:
  cd ~/Desktop/glowinggardens_claude/_music && python hookpad_server.py

Then click the "H" button on fire-escape-mashup.html
"""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright
import threading

# Chord name to Hookpad button mapping (in G major)
# G=I, Am=ii, Bm=iii, C=IV, D=V, Em=vi
CHORD_TO_DEGREE = {
    'G': 1, 'Am': 2, 'Bm': 3, 'C': 4, 'D': 5, 'Em': 6
}

class HookpadHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/hookpad':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            print(f"\n{'='*50}")
            print("Received chord progression:")
            for i, phrase in enumerate(data['phrases']):
                print(f"  Phrase {i+1}: {' → '.join(phrase['chords'])}")
            print(f"Key: {data['key']}, Tempo: {data['tempo']}")
            print('='*50)

            # Run Playwright in a separate thread
            thread = threading.Thread(target=lambda: asyncio.run(enter_hookpad(data)))
            thread.start()

            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging


async def enter_hookpad(data):
    """Enter chords into Hookpad via Playwright"""
    async with async_playwright() as p:
        print("\nLaunching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})
        page.set_default_timeout(60000)

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

        # Change key to G major
        print("Setting key to G major...")
        try:
            # Click the key display (usually shows "C" at top)
            await page.click('.key-display', timeout=5000)
            await asyncio.sleep(0.5)
            # Click G in the key picker
            await page.click('text=G', timeout=3000)
            await asyncio.sleep(0.5)
            # Close picker if needed (click elsewhere or press escape)
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"  Could not change key: {e}")
            print("  Continuing in C major...")

        # Roman numeral buttons in Hookpad
        DEGREE_BUTTONS = {
            1: 'I', 2: 'ii', 3: 'iii', 4: 'IV', 5: 'V', 6: 'vi', 7: 'vii°'
        }

        async def click_duration_row(label_text):
            """Click a duration row by its label text (e.g., '1', '2', '4', '1/2')"""
            try:
                # Find the label div with exact text, then click its parent row's SVG
                selector = f'.width-25.text-align-right:text-is("{label_text}")'
                label = await page.query_selector(selector)
                if label:
                    # Click the sibling SVG (the clickable bar)
                    parent = await label.evaluate_handle('el => el.parentElement')
                    svg = await parent.query_selector('svg')
                    if svg:
                        await svg.click()
                        await asyncio.sleep(0.15)
                        return True
                # Fallback: try clicking the row containing this text
                row_selector = f'.flex.flex-align-items-center:has(.width-25:text-is("{label_text}"))'
                await page.click(row_selector, timeout=1000)
                await asyncio.sleep(0.15)
                return True
            except Exception as e:
                print(f"      Could not click duration '{label_text}': {e}")
                return False

        async def set_duration(beats):
            """Set the duration by decomposing into 4, 2, 1, 1/2, 1/4 clicks"""
            # Double the duration (Hookpad uses half-beat units)
            beats = beats * 2
            print(f"    Setting duration to {beats} beats (doubled)...")

            # Decompose beats into components: 4, 2, 1, 0.5, 0.25
            remaining = beats
            components = []

            if remaining >= 4:
                count = int(remaining // 4)
                for _ in range(count):
                    components.append('4')
                remaining -= count * 4

            if remaining >= 2:
                count = int(remaining // 2)
                for _ in range(count):
                    components.append('2')
                remaining -= count * 2

            if remaining >= 1:
                count = int(remaining // 1)
                for _ in range(count):
                    components.append('1')
                remaining -= count * 1

            if remaining >= 0.5:
                components.append('1/2')
                remaining -= 0.5

            if remaining >= 0.25:
                components.append('1/4')
                remaining -= 0.25

            # If nothing, default to 1 beat
            if not components:
                components = ['1']

            print(f"      Decomposed into: {' + '.join(components)}")

            # Click first component (sets base duration)
            await click_duration_row(components[0])

            # Click Add then each additional component
            for comp in components[1:]:
                await asyncio.sleep(0.1)
                await click_duration_row('Add')
                await asyncio.sleep(0.1)
                await click_duration_row(comp)

        # Enter chords for each phrase
        print("\nEntering chords with durations...")
        total_entered = 0

        for phrase_idx, phrase in enumerate(data['phrases']):
            chords = phrase['chords']
            rhythm = phrase['rhythm']

            for chord_idx, chord in enumerate(chords):
                degree = CHORD_TO_DEGREE.get(chord, 1)
                button_text = DEGREE_BUTTONS[degree]
                duration = rhythm[chord_idx] if chord_idx < len(rhythm) else 2

                try:
                    # Set duration first
                    await set_duration(duration)

                    # Click the chord button
                    selector = f'.div-chord-button:has-text("{button_text}")'
                    await page.click(selector, timeout=3000)
                    total_entered += 1
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"  Could not enter {chord} ({button_text}): {e}")

            print(f"  Phrase {phrase_idx + 1}: {' → '.join(chords)} ✓")

        print(f"\nTotal chords entered: {total_entered}")
        print("\n" + "="*50)
        print("DONE! Browser stays open.")
        print("- Press SPACE to play in Hookpad")
        print("- Sign in to save your work")
        print("="*50)

        # Keep browser open
        try:
            await page.wait_for_timeout(300000)  # 5 minutes
        except:
            pass

        await browser.close()


def run_server():
    port = 5111
    server = HTTPServer(('localhost', port), HookpadHandler)
    print(f"""
╔══════════════════════════════════════════════════╗
║         HOOKPAD SERVER RUNNING                   ║
║                                                  ║
║  Listening on: http://localhost:{port}            ║
║                                                  ║
║  Click the green "H" button on                   ║
║  fire-escape-mashup.html to send chords          ║
║                                                  ║
║  Press Ctrl+C to stop                            ║
╚══════════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


if __name__ == "__main__":
    run_server()
