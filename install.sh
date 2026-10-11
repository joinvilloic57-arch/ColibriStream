#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Universal Open-Source Installer
# Works on ANY Linux / macOS / WSL machine with zero setup.
# Usage: curl -fsSL https://get.colibristream.run | bash
# ==============================================================================

set -e

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_DIM="\033[2m"

echo -e "${C_GREEN}${C_BOLD}"
cat << "EOF"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
EOF
echo -e "${C_RESET}${C_DIM}         Universal Open-Source Bare-Metal AI Installer${C_RESET}\n"

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"

echo -e "${C_CYAN}[1/3] Installing Colibristream binary to ${INSTALL_DIR}...${C_RESET}"

# If running from cloned repo, copy local colibri; otherwise download from repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -f "${SCRIPT_DIR}/colibri" ]; then
  cp "${SCRIPT_DIR}/colibri" "${INSTALL_DIR}/colibri"
  if [ -f "${SCRIPT_DIR}/colibri_chat.py" ]; then
    cp "${SCRIPT_DIR}/colibri_chat.py" "${INSTALL_DIR}/colibri_chat.py"
  fi
else
  # Fetch latest release from source repository
  REPO_RAW="https://raw.githubusercontent.com/joinvilloic57/colibristream/main"
  curl -fsSL "${REPO_RAW}/colibri" -o "${INSTALL_DIR}/colibri" 2>/dev/null || \
  curl -fsSL "http://10.0.2.235:8888/colibri" -o "${INSTALL_DIR}/colibri"
fi

chmod +x "${INSTALL_DIR}/colibri"
ln -sf "${INSTALL_DIR}/colibri" "${INSTALL_DIR}/colibristream"

echo -e "${C_CYAN}[2/3] Configuring system PATH environment...${C_RESET}"
# Ensure ~/.local/bin is in PATH across all shell profiles
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ] && ! grep -q '\.local/bin' "$profile"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
  fi
done
export PATH="${INSTALL_DIR}:${PATH}"

echo -e "${C_CYAN}[3/3] Checking bare-metal inference daemon...${C_RESET}"
if ! command -v ollama >/dev/null 2>&1; then
  echo -e "${C_YELLOW}[!] Local inference engine not detected. Auto-installing bare-metal engine...${C_RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
fi

echo -e "\n${C_GREEN}${C_BOLD}✔ Installation Complete!${C_RESET}"
echo -e "${C_DIM}Colibristream is installed and available globally as 'colibri'.${C_RESET}\n"

# Launch immediately into hardware scan and model hub
exec "${INSTALL_DIR}/colibri" menu
