#!/usr/bin/env bash
# ==============================================================================
# ObsidianCore (obsidiancore) — 1-Line Universal Installer for ANY Computer
# Usage: curl -fsSL https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh | bash
# ==============================================================================
set -e

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_DIM="\033[2m"

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"

echo -e "\n${C_GREEN}${C_BOLD}Installing ObsidianCore onto your computer...${C_RESET}"

# Download standalone installer from GitHub repository
exec curl -fsSL "https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh" | bash -s -- "$@"
