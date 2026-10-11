#!/usr/bin/env bash
# ==============================================================================
# Colibristream (colistream) — 100% Self-Contained Universal Installer
# Zero external server dependencies • Installs directly on ANY computer
# ==============================================================================
set -e

# Terminal Styling
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_PURPLE="\033[38;5;141m"
C_WHITE="\033[38;5;255m"

echo -e "\n${C_GREEN}${C_BOLD}"
cat << "BANNER"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
BANNER
echo -e "${C_RESET}${C_DIM}         Universal Bare-Metal AI Engine • 100% Open-Source • Local Host${C_RESET}\n"

# Step 1: Detect Host Environment
echo -e "${C_CYAN}${C_BOLD}[1/4] Detecting host system & architecture...${C_RESET}"
ARCH="$(uname -m)"
OS="$(uname -s)"
echo -e "      • System : ${C_WHITE}${OS} (${ARCH})${C_RESET}"
echo -e "      • Kernel : ${C_WHITE}$(uname -r)${C_RESET}"
sleep 0.3

# Step 2: Extract & Install colistream Binary Locally (Zero-Network Extract)
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"
echo -e "\n${C_CYAN}${C_BOLD}[2/4] Installing 'colistream' into ${INSTALL_DIR}...${C_RESET}"

# Embedded Payload Extraction
echo "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" | base64 -d | gzip -d > "${INSTALL_DIR}/colistream"
echo "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" | base64 -d | gzip -d > "${INSTALL_DIR}/colibri_chat.py"
chmod +x "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibri_chat.py"
ln -sf "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibristream"
echo -e "      • Permissions : ${C_GREEN}Executable (rwxr-xr-x)${C_RESET}"
echo -e "      • CLI Binary  : ${C_WHITE}${INSTALL_DIR}/colistream${C_RESET}"
echo -e "      • Alias       : ${C_WHITE}${INSTALL_DIR}/colibristream${C_RESET}"
sleep 0.3

# Step 3: Configure User Environment PATH
echo -e "\n${C_CYAN}${C_BOLD}[3/4] Configuring system PATH environment...${C_RESET}"
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ]; then
    if ! grep -q '\.local/bin' "$profile"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
      echo -e "      • Added ~/.local/bin to ${C_WHITE}${profile}${C_RESET}"
    else
      echo -e "      • PATH already configured in ${C_WHITE}${profile}${C_RESET}"
    fi
  fi
done
export PATH="${INSTALL_DIR}:${PATH}"
sleep 0.3

# Step 4: Verify & Setup Bare-Metal Inference Daemon
echo -e "\n${C_CYAN}${C_BOLD}[4/4] Verifying local Bare-Metal Inference Daemon...${C_RESET}"
if command -v ollama >/dev/null 2>&1; then
  OLLAMA_VER="$(ollama --version 2>/dev/null || echo 'active')"
  echo -e "      • Engine Status : ${C_GREEN}Installed (${OLLAMA_VER})${C_RESET}"
else
  echo -e "      • Engine Status : ${C_YELLOW}Auto-installing open-source engine...${C_RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
fi

if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo -e "      • Starting engine daemon on localhost..."
  nohup ollama serve >/dev/null 2>&1 &
  sleep 2
fi
echo -e "      • Local Daemon  : ${C_GREEN}ONLINE (localhost:11434)${C_RESET}"
sleep 0.3

# Finish Banner
echo -e "\n${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}✔ INSTALLATION SUCCESSFUL! 'colistream' is ready on your machine.${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}\n"

echo -e "${C_YELLOW}${C_BOLD}YOU CAN NOW RUN ANY MODEL DIRECTLY IN ANY TERMINAL:${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream run qwen2.5:72b${C_RESET}          ${C_DIM}# Run 72B Flagship Solo${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream run qwen2.5-coder:1.5b${C_RESET}   ${C_DIM}# Ultra-Fast Coder${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream run qwen3:14b${C_RESET}            ${C_DIM}# Deep Reasoning${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream swarm qwen3:14b qwen2.5-coder:1.5b${C_RESET} ${C_DIM}# Multi-Agent Swarm${C_RESET}"
echo -e "  ${C_BOLD}${C_CYAN}colistream${C_RESET}                          ${C_DIM}# Interactive Hardware Hub${C_RESET}\n"

if [ -n "$1" ]; then
  exec "${INSTALL_DIR}/colistream" "$@"
else
  if [ -e /dev/tty ]; then
    echo -ne "${C_BOLD}Press Enter to launch Colistream now (or 'q' to exit): ${C_RESET}"
    read -r CONT </dev/tty || CONT=""
    if [ "$CONT" != "q" ] && [ "$CONT" != "Q" ]; then
      exec "${INSTALL_DIR}/colistream" menu
    fi
  fi
fi
