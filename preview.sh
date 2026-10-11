#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Web Preview Launcher
# Opens or serves the Phase 1 landing page locally
# ==============================================================================

set -e
PORT=${1:-3000}
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "---------------------------------------------------------"
echo "  Starting Colibristream Web Gateway on port ${PORT}..."
echo "  URL: http://localhost:${PORT}"
echo "---------------------------------------------------------"

if command -v xdg-open >/dev/null 2>&1; then
  (sleep 1 && xdg-open "http://localhost:${PORT}") &
fi

python3 -m http.server "${PORT}" --directory "${DIR}"
