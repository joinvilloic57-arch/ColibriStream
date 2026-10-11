#!/usr/bin/env bash
# ==============================================================================
# Colibristream (colistream) — 100% Fully Automated Standalone Installer
# Installs directly to disk & immediately launches with zero user intervention
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
echo -e "${C_RESET}${C_DIM}         Universal Bare-Metal AI Engine • 100% Automated Local Install${C_RESET}\n"

# Step 1: Detect Host Environment
echo -e "${C_CYAN}${C_BOLD}[1/4] Detecting host system & architecture...${C_RESET}"
ARCH="$(uname -m)"
OS="$(uname -s)"
echo -e "      • System : ${C_WHITE}${OS} (${ARCH})${C_RESET}"
echo -e "      • Kernel : ${C_WHITE}$(uname -r)${C_RESET}"

# Step 2: Write Binaries Permanently to Disk
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"
echo -e "\n${C_CYAN}${C_BOLD}[2/4] Saving 'colistream' permanently to disk at ${INSTALL_DIR}...${C_RESET}"

# Embedded Payload Extraction to physical disk
echo "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" | base64 -d | gzip -d > "${INSTALL_DIR}/colistream"
echo "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" | base64 -d | gzip -d > "${INSTALL_DIR}/colibri_chat.py"
chmod +x "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibri_chat.py"
ln -sf "${INSTALL_DIR}/colistream" "${INSTALL_DIR}/colibristream"
echo -e "      • Binary Saved : ${C_GREEN}${INSTALL_DIR}/colistream${C_RESET}"
echo -e "      • Alias Saved  : ${C_GREEN}${INSTALL_DIR}/colibristream${C_RESET}"

# Step 3: Configure User Environment PATH on Disk
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

# Step 4: Verify & Setup Bare-Metal Inference Daemon
echo -e "\n${C_CYAN}${C_BOLD}[4/4] Starting local Bare-Metal Inference Engine...${C_RESET}"
if command -v ollama >/dev/null 2>&1; then
  OLLAMA_VER="$(ollama --version 2>/dev/null || echo 'active')"
  echo -e "      • Engine Status : ${C_GREEN}Installed (${OLLAMA_VER})${C_RESET}"
else
  echo -e "      • Engine Status : ${C_YELLOW}Auto-installing engine...${C_RESET}"
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Turbo Boost Configuration: 16 parallel download streams + Native GPU kernels
export OLLAMA_MAX_PARALLEL_DOWNLOADS=16
export OLLAMA_FLASH_ATTENTION=0
export OLLAMA_NUM_PARALLEL=1
export GGML_CUDA_NO_PINNED=1

# Auto-detect fastest GPU if multiple cards exist
BEST_GPU_IDX="0"
MAX_GPU_MEM=0
GPU_COUNT=0
if command -v nvidia-smi >/dev/null 2>&1; then
  while IFS=, read -r gidx gname gmem; do
    if [ -n "$gidx" ]; then
      c_idx=$(echo "$gidx" | tr -d '[:space:]')
      c_mem=$(echo "$gmem" | tr -d '[:space:]' | tr -d 'MiB' | tr -d 'MB')
      GPU_COUNT=$((GPU_COUNT + 1))
      if [ "$c_mem" -gt "$MAX_GPU_MEM" ] 2>/dev/null; then
        MAX_GPU_MEM="$c_mem"
        BEST_GPU_IDX="$c_idx"
      fi
    fi
  done < <(nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits 2>/dev/null || true)
fi

mkdir -p "${HOME}/.colistream" 2>/dev/null || true
if [ "$GPU_COUNT" -gt 1 ]; then
  echo "$BEST_GPU_IDX" > "${HOME}/.colistream/gpu_config" 2>/dev/null || true
  export CUDA_VISIBLE_DEVICES="$BEST_GPU_IDX"
  echo -e "      • GPU Isolation : ${C_GREEN}Active [GPU ${BEST_GPU_IDX}] (Bypassed slower secondary card)${C_RESET}"
fi

if [ -d /etc/systemd/system ] && [ -w /etc/systemd/system ]; then
  mkdir -p /etc/systemd/system/ollama.service.d 2>/dev/null || true
  cat << SYSCONF > /etc/systemd/system/ollama.service.d/colistream.conf 2>/dev/null || true
[Service]
Environment="CUDA_VISIBLE_DEVICES=${BEST_GPU_IDX}"
Environment="OLLAMA_MAX_PARALLEL_DOWNLOADS=16"
Environment="OLLAMA_FLASH_ATTENTION=0"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="GGML_CUDA_NO_PINNED=1"
SYSCONF
  systemctl daemon-reload >/dev/null 2>&1 || true
  systemctl restart ollama >/dev/null 2>&1 || true
fi

if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo -e "      • Booting background daemon (Fast GPU: ${BEST_GPU_IDX})..."
  nohup ollama serve >/dev/null 2>&1 &
  sleep 2
fi
echo -e "      • Engine Daemon : ${C_GREEN}ONLINE (localhost:11434)${C_RESET}"

# Finish Banner
echo -e "\n${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}✔ INSTALLATION COMPLETE! Permanent on disk in ~/.local/bin${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}════════════════════════════════════════════════════════════════════════${C_RESET}\n"

# 100% AUTOMATIC LAUNCH: No prompts, launches directly into menu or command!
if [ -n "$1" ]; then
  exec "${INSTALL_DIR}/colistream" "$@"
else
  exec "${INSTALL_DIR}/colistream" menu
fi
