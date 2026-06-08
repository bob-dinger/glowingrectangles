#!/bin/bash
# Launch an isolated Brave instance with:
#   - CDP debugging port (so fill_hookpad_tabs.py can connect)
#   - Its own user-data-dir at ~/BraveHookpadDebug (won't disturb your regular Brave)
#   - N tabs pre-opened to Hookpad
#
# First run: sign into Hookpad once in any of the tabs. Auth persists across launches.
# Subsequent runs: just run this; the isolated profile remembers everything.
#
# Usage:
#   bash launch_hookpad_debug.sh              # default 25 tabs
#   bash launch_hookpad_debug.sh 10           # 10 tabs

N=${1:-25}
USER_DATA_DIR="$HOME/BraveHookpadDebug"
DEBUG_PORT=9222

# Build N hookpad URLs
URLS=()
for ((i=1; i<=N; i++)); do
  URLS+=("https://hookpad.hooktheory.com")
done

# Use the binary directly so --user-data-dir is honored on macOS
BRAVE_BIN="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
if [[ ! -x "$BRAVE_BIN" ]]; then
  echo "Brave binary not found at: $BRAVE_BIN"
  exit 1
fi

echo "launching isolated Brave with $N tabs..."
echo "  user-data-dir: $USER_DATA_DIR"
echo "  debug port:    $DEBUG_PORT"
mkdir -p "$USER_DATA_DIR"

"$BRAVE_BIN" \
  --remote-debugging-port=$DEBUG_PORT \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run --no-default-browser-check \
  "${URLS[@]}" \
  >/dev/null 2>&1 &

echo "PID $!"
echo ""
echo "If this is your first launch: sign into Hookpad in any one tab (others share auth)."
echo "Then run:  python _music/fill_hookpad_tabs.py 'song one' 'song two' ..."
