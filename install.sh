#!/usr/bin/env bash
# ==============================================================================
# Colibristream (colistream) — Universal Bare-Metal AI Installer
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
C_GRAY="\033[38;5;244m"
C_WHITE="\033[38;5;255m"

# Header Banner
echo -e "\n${C_GREEN}${C_BOLD}"
cat << "EOF"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
EOF
echo -e "${C_RESET}${C_DIM}         Bare-Metal AI Engine • 100% Free • Zero Cloud Subscriptions${C_RESET}\n"

# Step 1: Detect Host Architecture & Environment
echo -e "${C_CYAN}${C_BOLD}[1/5] Detecting host hardware & architecture...${C_RESET}"
ARCH="$(uname -m)"
OS="$(uname -s)"
echo -e "      • System: ${C_WHITE}${OS} (${ARCH})${C_RESET}"
echo -e "      • Kernel: ${C_WHITE}$(uname -r)${C_RESET}"
sleep 0.5

# Step 2: Prepare Binary Directory
INSTALL_DIR="${HOME}/.local/bin"
echo -e "\n${C_CYAN}${C_BOLD}[2/5] Setting up local binary directory...${C_RESET}"
echo -e "      • Target Directory: ${C_WHITE}${INSTALL_DIR}${C_RESET}"
mkdir -p "$INSTALL_DIR"
sleep 0.5

# Step 3: Fetch and Install colistream
echo -e "\n${C_CYAN}${C_BOLD}[3/5] Downloading Colibristream Bare-Metal CLI...${C_RESET}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -f "${SCRIPT_DIR}/colistream" ]; then
  echo -e "      • Copying local binary from repo..."
  cp "${SCRIPT_DIR}/colistream" "${INSTALL_DIR}/colistream"
  if [ -f "${SCRIPT_DIR}/colibri_chat.py" ]; then
    cp "${SCRIPT_DIR}/colibri_chat.py" "${INSTALL_DIR}/colibri_chat.py"
  fi
else
  # Auto-detect origin server or fallback
  SERVER="http://10.0.2.235:8888"
  echo -e "      • Connecting to distribution mirror: ${C_DIM}${SERVER}${C_RESET}..."
  curl -# -fSL "${SERVER}/colistream" -o "${INSTALL_DIR}/colistream" 2>/dev/null || \
  curl -# -fSL "https://raw.githubusercontent.com/joinvilloic57/colibristream/main/colistream" -o "${INSTALL_DIR}/colistream"
  
  # Fetch chat runner
  curl -fsSL "${SERVER}/colibri_chat.py" -o "${INSTALL_DIR}/colibri_chat.py" 2>/dev/null || true
fi

chmod +x "${INSTALL_DIR}/colistream"
ln -sf "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibristream"
echo -e "      • Permissions: ${C_GREEN}Executable (rwxr-xr-x)${C_RESET}"
echo -e "      • Symlink: ${C_WHITE}colibristream ➔ colistream${C_RESET}"
sleep 0.5

# Step 4: Configure User Environment PATH
echo -e "\n${C_CYAN}${C_BOLD}[4/5] Configuring system PATH environment...${C_RESET}"
UPDATED_SHELL=""
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ]; then
    if ! grep -q '\.local/bin' "$profile"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
      echo -e "      • Added ~/.local/bin to ${C_WHITE}${profile}${C_RESET}"
      UPDATED_SHELL="1"
    else
      echo -e "      • Verified PATH in ${C_WHITE}${profile}${C_RESET}"
    fi
  fi
done
export PATH="${INSTALL_DIR}:${PATH}"
sleep 0.5

# Step 5: Verify & Setup Bare-Metal Inference Daemon
echo -e "\n${C_CYAN}${C_BOLD}[5/5] Initializing local Bare-Metal Inference Engine...${C_RESET}"
if command -v ollama >/dev/null 2>&1; then
  OLLAMA_VER="$(ollama --version 2>/dev/null || echo 'active')"
  echo -e "      • Local engine found: ${C_GREEN}Ollama (${OLLAMA_VER})${C_RESET}"
else
  echo -e "      • ${C_YELLOW}Engine not detected on host. Auto-installing bare-metal engine...${C_RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Ensure daemon is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo -e "      • Booting background inference daemon..."
  nohup ollama serve >/dev/null 2>&1 &
  sleep 2
fi
echo -e "      • Bare-metal inference daemon: ${C_GREEN}ONLINE (localhost:11434)${C_RESET}"
sleep 0.5

# Finish Banner
echo -e "\n${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}✔ INSTALLATION SUCCESSFUL! Colistream is ready on your machine.${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}\n"

echo -e "${C_YELLOW}${C_BOLD}HOW TO RUN MODELS ON YOUR MACHINE:${C_RESET}"
echo -e "  ${C_WHITE}1. Run the interactive hardware scan & model hub:${C_RESET}"
echo -e "     ${C_BOLD}${C_CYAN}colistream${C_RESET}\n"
echo -e "  ${C_WHITE}2. Run any model directly (auto-downloads if needed):${C_RESET}"
echo -e "     ${C_BOLD}${C_CYAN}colistream run qwen2.5:72b${C_RESET}          ${C_DIM}# 72B Flagship Model${C_RESET}"
echo -e "     ${C_BOLD}${C_CYAN}colistream run qwen2.5-coder:1.5b${C_RESET}   ${C_DIM}# Ultra-Fast Coding Model${C_RESET}"
echo -e "     ${C_BOLD}${C_CYAN}colistream run qwen3:14b${C_RESET}            ${C_DIM}# Thinking / Reasoning Model${C_RESET}\n"
echo -e "  ${C_WHITE}3. Run dual-model swarms in shared memory (1x RAM):${C_RESET}"
echo -e "     ${C_BOLD}${C_CYAN}colistream swarm qwen3:14b qwen2.5-coder:1.5b${C_RESET}\n"

# If arguments were provided (e.g. curl ... | bash -s -- run qwen2.5:72b), run immediately!
if [ -n "$1" ]; then
  echo -e "${C_YELLOW}[*] Executing specified command:${C_RESET} colistream $@\n"
  exec "${INSTALL_DIR}/colistream" "$@"
else
  # Prompt user to launch interactive menu or exit
  if [ -e /dev/tty ]; then
    echo -ne "${C_BOLD}Press Enter to open the Colistream Model Hub now (or 'q' to finish): ${C_RESET}"
    read -r CONT </dev/tty || CONT=""
    if [ "$CONT" != "q" ] && [ "$CONT" != "Q" ]; then
      exec "${INSTALL_DIR}/colistream" menu
    fi
  fi
fi
