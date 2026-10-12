#!/usr/bin/env bash
# ==============================================================================
# Colibristream (colistream) — 1-Line Universal Installer for ANY Computer
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

echo -e "\n${C_GREEN}${C_BOLD}Installing colistream onto your computer...${C_RESET}"

# Download standalone installer from GitHub repository
exec curl -fsSL "https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh" | bash -s -- "$@"

chmod +x "${INSTALL_DIR}/colistream"
ln -sf "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibristream"

# Add to ~/.bashrc and current session PATH
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ] && ! grep -q '\.local/bin' "$profile"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
  fi
done
export PATH="${INSTALL_DIR}:${PATH}"

# Ensure backend daemon
if ! command -v ollama >/dev/null 2>&1; then
  echo -e "${C_CYAN}[*] Setting up local bare-metal engine...${C_RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
fi

echo -e "\n${C_GREEN}${C_BOLD}✔ Success! 'colistream' is now permanently installed.${C_RESET}"
echo -e "${C_YELLOW}You can now run any model anytime:${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream run qwen2.5:72b${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream run qwen2.5-coder:1.5b${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream${C_RESET} (interactive menu)\n"

# If arguments were passed, run them immediately!
if [ -n "$1" ]; then
  exec "${INSTALL_DIR}/colistream" "$@"
fi
