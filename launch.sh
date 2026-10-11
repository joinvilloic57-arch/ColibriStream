#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Bare-Metal CLI Launcher
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -z "$DIR" ] || [ ! -f "${DIR}/colibri" ]; then
  if [ -f "./colibri" ]; then
    DIR="$PWD"
  elif [ -f "/home/tech/Projects/collibri/colibri" ]; then
    DIR="/home/tech/Projects/collibri"
  else
    DIR="${HOME}/.colibri"
    mkdir -p "$DIR"
    curl -fsSL "http://10.0.2.235:8888/colibri" -o "${DIR}/colibri" 2>/dev/null || true
    curl -fsSL "http://10.0.2.235:8888/colibri_chat.py" -o "${DIR}/colibri_chat.py" 2>/dev/null || true
    chmod +x "${DIR}/colibri" "${DIR}/colibri_chat.py" 2>/dev/null || true
  fi
fi

chmod +x "${DIR}/colibri" "${DIR}/colibri_chat.py" 2>/dev/null || true
exec bash "${DIR}/colibri" menu "$@"
