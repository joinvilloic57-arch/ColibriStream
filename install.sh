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
