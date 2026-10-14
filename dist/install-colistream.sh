#!/usr/bin/env bash
# ==============================================================================
# ObsidianCore (legacy colistream alias) — 1-Line Universal Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh | bash
# ==============================================================================
set -e

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[38;5;48m"

echo -e "\n${C_GREEN}${C_BOLD}Installing ObsidianCore (colistream alias) onto your computer...${C_RESET}"

# Download standalone installer from GitHub repository
exec curl -fsSL "https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh" | bash -s -- "$@"
