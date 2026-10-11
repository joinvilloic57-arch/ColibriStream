#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Web Preview Launcher
# Opens or serves the Phase 1 landing page locally
# ==============================================================================

set -e
PORT=${1:-3000}
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================="
echo "  Colibristream Web Gateway is running!"
echo "  Open this link in your browser: http://localhost:${PORT}"
echo "========================================================="

# Try to open in GUI browser if desktop environment is active (silently ignore if headless)
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
  if command -v xdg-open >/dev/null 2>&1; then
    (sleep 1 && xdg-open "http://localhost:${PORT}" >/dev/null 2>&1) &
  fi
fi

python3 -m http.server "${PORT}" --directory "${DIR}"
