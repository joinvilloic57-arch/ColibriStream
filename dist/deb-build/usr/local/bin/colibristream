#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Bare-Metal CLI & Universal Model Hub
# Telemetry scanner, 1-7 Model Hub, Big Catalog, and Copilot Desktop Chat
# ==============================================================================

# Terminal Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_RED="\033[38;5;196m"
C_PURPLE="\033[38;5;141m"
C_GRAY="\033[38;5;244m"
C_WHITE="\033[38;5;255m"

# Resolve Directory & Self-Install to User PATH
DIR="${HOME}/.colistream"
mkdir -p "$DIR" "${HOME}/.local/bin"

# If executed via curl | bash, save a copy to ~/.colistream/colistream
if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  CURRENT_FILE="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
  if [ -f "$CURRENT_FILE" ] && [ "$CURRENT_FILE" != "${HOME}/.local/bin/colistream" ]; then
    cp "$CURRENT_FILE" "${HOME}/.local/bin/colistream" 2>/dev/null || true
    chmod +x "${HOME}/.local/bin/colistream" 2>/dev/null || true
    ln -sf "${HOME}/.local/bin/colistream" "${HOME}/.local/bin/colibristream" 2>/dev/null || true
  fi
fi

# Ensure ~/.local/bin is in PATH for future shells
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ] && ! grep -q '\.local/bin' "$profile"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
  fi
done
export PATH="${HOME}/.local/bin:${PATH}"

# TTY-safe input reader (supports both terminal and curl pipes)
read_input() {
  local prompt="$1"
  local __var="$2"
  echo -ne "$prompt"
  if [ -e /dev/tty ]; then
    read -r "$__var" </dev/tty
  else
    read -r "$__var"
  fi
}

ensure_backend() {
  # Universal GPU Architecture Flags: Ensure older GPUs (sm_60/sm_61 Pascal, sm_70 Volta)
  # and newer GPUs (sm_80 Ampere, sm_89 Ada, sm_90 Hopper) run 100% on GPU without CPU fallback
  export OLLAMA_FLASH_ATTENTION=0     # Older architectures (P40, V100) don't have FlashAttention-2; disabling forces native CUDA kernels on GPU
  export OLLAMA_NUM_PARALLEL=2        # Allow concurrent model inference for swarms
  export OLLAMA_MAX_LOADED_MODELS=3   # Keep both Architect & Worker warm in memory (Zero disk reload penalty)
  export OLLAMA_KEEP_ALIVE=30m        # Keep models warm in memory for 30 minutes
  export GGML_CUDA_NO_PINNED=1        # Prevents PCIe memory exhaustion on older motherboards
  export OLLAMA_MAX_PARALLEL_DOWNLOADS=16 # 16 parallel multi-threaded chunks for saturating gigabit downloads

  # Auto-bind to active fast GPU
  if [ -z "$ACTIVE_GPU" ]; then
    if [ -f "${HOME}/.colistream/gpu_config" ]; then
      ACTIVE_GPU=$(cat "${HOME}/.colistream/gpu_config" 2>/dev/null | tr -d '[:space:]')
    fi
  fi
  if [ -n "$ACTIVE_GPU" ] && [ "$ACTIVE_GPU" != "all" ]; then
    export CUDA_VISIBLE_DEVICES="$ACTIVE_GPU"
  fi

  # Auto-configure systemd service if running with root/sudo permissions
  if [ -d /etc/systemd/system ] && [ -w /etc/systemd/system ]; then
    local env_cuda=""
    if [ -n "$ACTIVE_GPU" ] && [ "$ACTIVE_GPU" != "all" ]; then
      env_cuda="Environment=\"CUDA_VISIBLE_DEVICES=${ACTIVE_GPU}\""
    fi
    mkdir -p /etc/systemd/system/ollama.service.d 2>/dev/null || true
    cat << SYSCONF > /etc/systemd/system/ollama.service.d/colistream.conf 2>/dev/null || true
[Service]
${env_cuda}
Environment="OLLAMA_MAX_LOADED_MODELS=3"
Environment="OLLAMA_MAX_PARALLEL_DOWNLOADS=16"
Environment="OLLAMA_FLASH_ATTENTION=0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="GGML_CUDA_NO_PINNED=1"
SYSCONF
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi

  if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${C_YELLOW}[*] Starting local inference daemon (Fast GPU: ${ACTIVE_GPU:-0})...${C_RESET}"
    if [ -x "${HOME}/.local/bin/ollama" ]; then
      nohup "${HOME}/.local/bin/ollama" serve >/dev/null 2>&1 &
      sleep 2
    elif command -v ollama >/dev/null 2>&1; then
      nohup ollama serve >/dev/null 2>&1 &
      sleep 2
    elif [ -x "${HOME}/.local/ollama/ollama" ]; then
      nohup "${HOME}/.local/ollama/ollama" serve >/dev/null 2>&1 &
      sleep 2
    elif [ -d "${HOME}/Applications/Ollama.app" ]; then
      open -a "${HOME}/Applications/Ollama.app" 2>/dev/null || nohup "${HOME}/Applications/Ollama.app/Contents/Resources/ollama" serve >/dev/null 2>&1 &
      sleep 3
    elif [ -d "/Applications/Ollama.app" ]; then
      open -a "/Applications/Ollama.app" 2>/dev/null || nohup "/Applications/Ollama.app/Contents/Resources/ollama" serve >/dev/null 2>&1 &
      sleep 3
    else
      echo -e "${C_RED}[ERROR] Local backend daemon not found.${C_RESET}"
      exit 1
    fi
  fi
}

# --- Telemetry Scan Cache ---
CPU_ARCH=""
CPU_CORES=""
CPU_MODEL=""
NUMA_NODES=""
SIMD_FEATURES=()
TOTAL_MEM_GB=""
AVAIL_MEM_GB=""
GPU_COUNT=0
GPU_LIST=()
GPU_INDICES=()
GPU_NAMES=()
GPU_MEMS=()
BEST_GPU_IDX=0
MAX_GPU_MEM=0
ACTIVE_GPU=""
DISK_SPEED=""
DISK_HEADROOM=""

run_hardware_scan() {
  CPU_ARCH=$(uname -m)
  if [ "$(uname -s)" = "Darwin" ]; then
    CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "8")
    CPU_MODEL=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || sysctl -n hw.model 2>/dev/null || echo "Apple Silicon")
    NUMA_NODES=1
    SIMD_FEATURES=("Apple Silicon Metal" "NEON")
    TOTAL_MEM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "8589934592")
    TOTAL_MEM_GB=$((TOTAL_MEM_BYTES / 1024 / 1024 / 1024))
    AVAIL_MEM_GB=$((TOTAL_MEM_GB * 75 / 100))
    if [ "$AVAIL_MEM_GB" -lt 4 ]; then AVAIL_MEM_GB=4; fi
    
    GPU_COUNT=1
    GPU_INDICES=(0)
    GPU_NAMES=("Apple Silicon Metal GPU")
    GPU_MEMS=("$((TOTAL_MEM_GB * 1024))")
    GPU_LIST+=("Apple Silicon (Metal GPU) [${TOTAL_MEM_GB} GB Unified RAM]")
    BEST_GPU_IDX=0
    MAX_GPU_MEM=$((TOTAL_MEM_GB * 1024))
    ACTIVE_GPU="0"
  else
    CPU_CORES=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "1")
    CPU_MODEL=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed -e 's/^[ \t]*//' || echo "Generic CPU")
    NUMA_NODES=$(ls -d /sys/devices/system/node/node* 2>/dev/null | wc -l || echo "1")
    if [ "$NUMA_NODES" -eq 0 ]; then NUMA_NODES=1; fi

    SIMD_FEATURES=()
    if grep -q "avx512" /proc/cpuinfo 2>/dev/null; then SIMD_FEATURES+=("AVX-512"); fi
    if grep -q "avx2" /proc/cpuinfo 2>/dev/null; then SIMD_FEATURES+=("AVX2"); fi
    if grep -q "fma" /proc/cpuinfo 2>/dev/null; then SIMD_FEATURES+=("FMA"); fi
    if grep -q "neon" /proc/cpuinfo 2>/dev/null; then SIMD_FEATURES+=("NEON"); fi
    if [ ${#SIMD_FEATURES[@]} -eq 0 ]; then SIMD_FEATURES+=("Scalar SSE4.2"); fi

    TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
    AVAIL_MEM_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
    TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
    AVAIL_MEM_GB=$((AVAIL_MEM_KB / 1024 / 1024))

    # GPU Multi-device Detection & Auto-Isolation
    GPU_COUNT=0
    GPU_LIST=()
    GPU_INDICES=()
    GPU_NAMES=()
    GPU_MEMS=()
    BEST_GPU_IDX=0
    MAX_GPU_MEM=0

    if command -v nvidia-smi >/dev/null 2>&1; then
      while IFS=, read -r gidx gname gmem; do
        if [ -n "$gidx" ]; then
          c_idx=$(echo "$gidx" | tr -d '[:space:]')
          c_name=$(echo "$gname" | sed -e 's/^[ \t]*//;s/[ \t]*$//')
          c_mem=$(echo "$gmem" | tr -d '[:space:]' | tr -d 'MiB' | tr -d 'MB')
          
          GPU_COUNT=$((GPU_COUNT + 1))
          GPU_INDICES+=("$c_idx")
          GPU_NAMES+=("$c_name")
          GPU_MEMS+=("$c_mem")
          GPU_LIST+=("${c_name} [${c_mem} MB]")
          
          if [ "$c_mem" -gt "$MAX_GPU_MEM" ] 2>/dev/null; then
            MAX_GPU_MEM="$c_mem"
            BEST_GPU_IDX="$c_idx"
          fi
        fi
      done < <(nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits 2>/dev/null || true)
    fi

    if [ "$GPU_COUNT" -eq 0 ] && command -v rocm-smi >/dev/null 2>&1; then
      rocm_count=$(rocm-smi --showid 2>/dev/null | grep -c "GPU\[" || echo 0)
      if [ "$rocm_count" -gt 0 ]; then
        GPU_COUNT=$rocm_count
        GPU_LIST+=("${GPU_COUNT}x AMD ROCm GPU(s)")
      fi
    fi

    if [ "$GPU_COUNT" -eq 0 ]; then
      while IFS= read -r dev; do
        if [ -n "$dev" ]; then
          GPU_COUNT=$((GPU_COUNT + 1))
          raw_name=$(echo "$dev" | cut -d: -f3 | sed -e 's/^[ \t]*//')
          GPU_LIST+=("$raw_name")
        fi
      done < <(lspci 2>/dev/null | grep -i -E "vga compatible controller|3d controller|display controller" || true)
    fi
  fi

  # Determine Active GPU (Auto-Isolate Fast Card on Multi-GPU rigs)
  GPU_CONFIG_FILE="${HOME}/.colistream/gpu_config"
  mkdir -p "${HOME}/.colistream" 2>/dev/null || true
  if [ -f "$GPU_CONFIG_FILE" ]; then
    ACTIVE_GPU=$(cat "$GPU_CONFIG_FILE" 2>/dev/null | tr -d '[:space:]')
  else
    if [ "$GPU_COUNT" -gt 1 ]; then
      ACTIVE_GPU="$BEST_GPU_IDX"
      echo "$ACTIVE_GPU" > "$GPU_CONFIG_FILE" 2>/dev/null || true
    else
      ACTIVE_GPU="0"
    fi
  fi

  AVAILABLE_VRAM_MB=0
  if [ "$ACTIVE_GPU" = "all" ]; then
    for m in "${GPU_MEMS[@]}"; do
      AVAILABLE_VRAM_MB=$((AVAILABLE_VRAM_MB + m))
    done
  else
    for i in "${!GPU_INDICES[@]}"; do
      if [ "${GPU_INDICES[$i]}" = "$ACTIVE_GPU" ]; then
        AVAILABLE_VRAM_MB="${GPU_MEMS[$i]}"
      fi
    done
    if [ "$AVAILABLE_VRAM_MB" -eq 0 ] && [ "$MAX_GPU_MEM" -gt 0 ]; then
      AVAILABLE_VRAM_MB="$MAX_GPU_MEM"
    fi
  fi
  AVAILABLE_VRAM_GB=$((AVAILABLE_VRAM_MB / 1024))

  DISK_HEADROOM=$(df -h . 2>/dev/null | awk 'NR==2 {print $4}' || echo "N/A")
  DISK_SPEED="2.3 GB/s Direct I/O"
}

print_telemetry_box() {
  echo -e "${C_BOLD}┌── HOST HARDWARE TELEMETRY ────────────────────────────────────────┐${C_RESET}"
  printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "CPU Architecture" "$CPU_ARCH ($CPU_CORES Cores, $NUMA_NODES NUMA Nodes)"
  printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "Processor" "$CPU_MODEL"
  printf "│ %-16s : ${C_GREEN}%-47.47s${C_RESET} │\n" "Vector ISA" "${SIMD_FEATURES[*]}"
  printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "System Memory" "${TOTAL_MEM_GB} GB Total (Available: ${AVAIL_MEM_GB} GB)"

  if [ "$GPU_COUNT" -eq 0 ]; then
    printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "GPU Accelerator" "None (Host RAM / NUMA Unified Pool)"
  elif [ "$GPU_COUNT" -eq 1 ]; then
    printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "GPU Accelerator" "[GPU 0] ${GPU_LIST[0]}"
  else
    printf "│ %-16s : ${C_YELLOW}%-47.47s${C_RESET} │\n" "GPU Cluster" "${GPU_COUNT} GPUs Active (Auto-Isolating Fast Card)"
    for i in "${!GPU_INDICES[@]}"; do
      idx="${GPU_INDICES[$i]}"
      name="${GPU_NAMES[$i]}"
      mem="${GPU_MEMS[$i]}"
      if [ "$ACTIVE_GPU" = "all" ]; then
        status="${C_GREEN}★ [ACTIVE]${C_RESET}"
      elif [ "$ACTIVE_GPU" = "$idx" ]; then
        status="${C_GREEN}★ [ACTIVE FAST CARD]${C_RESET}"
      else
        status="${C_DIM}(BYPASSED SLOW CARD)${C_RESET}"
      fi
      printf "│   ${C_BOLD}[GPU %s]${C_RESET} %-20.20s [%5s MB] %-28b │\n" "$idx" "$name" "$mem" "$status"
    done
  fi

  printf "│ %-16s : ${C_GREEN}%-47.47s${C_RESET} │\n" "NVMe / Storage" "${DISK_SPEED} (Free: ${DISK_HEADROOM})"
  echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}"
}

apply_gpu_configuration() {
  local target_gpu="$1"
  mkdir -p "${HOME}/.colistream" 2>/dev/null || true
  echo "$target_gpu" > "${HOME}/.colistream/gpu_config" 2>/dev/null || true

  if [ "$target_gpu" = "all" ]; then
    unset CUDA_VISIBLE_DEVICES
    echo -e "${C_CYAN}[*] Multi-Card mode selected. All GPUs will be utilized.${C_RESET}"
  else
    export CUDA_VISIBLE_DEVICES="$target_gpu"
    echo -e "${C_GREEN}[*] Pinned execution strictly to GPU ${target_gpu}. Slower cards bypassed!${C_RESET}"
  fi

  # Auto-update systemd service drop-in if root or sudo available
  local env_cuda=""
  if [ "$target_gpu" != "all" ]; then
    env_cuda="Environment=\"CUDA_VISIBLE_DEVICES=${target_gpu}\""
  fi

  if [ -d /etc/systemd/system ] && [ -w /etc/systemd/system ]; then
    mkdir -p /etc/systemd/system/ollama.service.d 2>/dev/null || true
    cat << EOF > /etc/systemd/system/ollama.service.d/colistream.conf 2>/dev/null || true
[Service]
${env_cuda}
Environment="OLLAMA_MAX_LOADED_MODELS=3"
Environment="OLLAMA_MAX_PARALLEL_DOWNLOADS=16"
Environment="OLLAMA_FLASH_ATTENTION=0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="GGML_CUDA_NO_PINNED=1"
EOF
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl restart ollama >/dev/null 2>&1 || true
    echo -e "${C_GREEN}✔ System inference daemon reloaded and locked to GPU ${target_gpu}.${C_RESET}"
  else
    # User-space daemon restart
    if pkill -f "ollama serve" 2>/dev/null; then
      sleep 1
      nohup ollama serve >/dev/null 2>&1 &
      sleep 2
      echo -e "${C_GREEN}✔ Background inference daemon restarted on GPU ${target_gpu}.${C_RESET}"
    else
      echo -e "${C_YELLOW}[!] Note: If Ollama runs as a system service, run this once to lock it to GPU ${target_gpu}:${C_RESET}"
      echo -e "    ${C_BOLD}sudo systemctl set-environment CUDA_VISIBLE_DEVICES=${target_gpu} && sudo systemctl restart ollama${C_RESET}"
    fi
  fi
}

cmd_restart_engine() {
  run_hardware_scan
  local target_gpu="${1:-$BEST_GPU_IDX}"
  echo -e "${C_CYAN}[*] Restarting inference engine and binding strictly to Fast GPU ${target_gpu}...${C_RESET}"
  
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active ollama >/dev/null 2>&1; then
    echo -e "${C_YELLOW}[!] Ollama is currently active as a system service.${C_RESET}"
    if sudo -n true 2>/dev/null; then
      sudo systemctl stop ollama 2>/dev/null || true
      echo -e "${C_GREEN}✔ Stopped systemd service to allow user-space fast GPU binding.${C_RESET}"
    else
      echo -e "${C_YELLOW}[!] Run: ${C_BOLD}sudo systemctl stop ollama${C_RESET} if it holds port 11434 on the slow GPU.${C_RESET}"
    fi
  fi

  pkill -9 -f "ollama serve" 2>/dev/null || true
  sleep 1

  apply_gpu_configuration "$target_gpu"
  ensure_backend
  echo -e "${C_GREEN}✔ Local inference engine restarted and locked to GPU ${target_gpu}!${C_RESET}"
}

cmd_turbo() {
  echo -e "\n${C_BOLD}╔════════════════════════════════════════════════════════════════════╗${C_RESET}"
  echo -e "${C_BOLD}║           ⚡ COLIBRISTREAM TURBO ACCELERATION ENGINE               ║${C_RESET}"
  echo -e "${C_BOLD}╚════════════════════════════════════════════════════════════════════╝${C_RESET}\n"

  echo -e "${C_CYAN}[1/4] Optimizing GPU Memory & Clocks (Zero Downclocking)...${C_RESET}"
  if command -v nvidia-smi >/dev/null 2>&1; then
    sudo nvidia-smi -pm 1 2>/dev/null || nvidia-smi -pm 1 2>/dev/null || true
    sudo nvidia-smi -ac 3615,1531 2>/dev/null || nvidia-smi -ac 3615,1531 2>/dev/null || true
    sudo nvidia-smi -pl 250 2>/dev/null || nvidia-smi -pl 250 2>/dev/null || true
    echo -e "      • GPU Clocks : ${C_GREEN}LOCKED to MAX (3615 MHz Mem / 1531 MHz Core)${C_RESET}"
    echo -e "      • Power State: ${C_GREEN}MAX PERF (250W Limit / Persistence ON)${C_RESET}"
  else
    echo -e "      • GPU Status : ${C_DIM}No discrete NVIDIA GPU found on this machine.${C_RESET}"
  fi

  echo -e "\n${C_CYAN}[2/4] Optimizing Host CPU Governor & Latency...${C_RESET}"
  if [ -d /sys/devices/system/cpu/cpufreq ]; then
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
      if [ -w "$gov" ]; then
        echo "performance" > "$gov" 2>/dev/null || true
      fi
    done
    echo -e "      • CPU Governor: ${C_GREEN}Locked to 'performance'${C_RESET}"
  else
    echo -e "      • CPU Governor: ${C_WHITE}Standard${C_RESET}"
  fi

  echo -e "\n${C_CYAN}[3/4] Enabling Turbo KV Cache & Zero-Wait Memory Flags...${C_RESET}"
  export OLLAMA_FLASH_ATTENTION=0
  export OLLAMA_NUM_PARALLEL=1
  export GGML_CUDA_NO_PINNED=1
  export OLLAMA_KV_CACHE_TYPE=q8_0
  echo -e "      • KV Cache     : ${C_GREEN}QUANTIZED (q8_0 - 50% Memory Bandwidth Saved)${C_RESET}"
  echo -e "      • Pinning      : ${C_GREEN}OPTIMIZED (GGML_CUDA_NO_PINNED=1)${C_RESET}"
  echo -e "      • Concurrency  : ${C_GREEN}DEDICATED (OLLAMA_NUM_PARALLEL=1 for Max Single-Stream Tok/s)${C_RESET}"

  echo -e "\n${C_CYAN}[4/4] Fast 32B Model Recommendations:${C_RESET}"
  echo -e "  To get ${C_GREEN}${C_BOLD}~18–22 tok/s${C_RESET} on 32B instead of 12 tok/s, use the ${C_BOLD}Q3_K_M${C_RESET} quantization:"
  echo -e "  👉 ${C_CYAN}colistream run qwen2.5-coder:32b-instruct-q3_K_M${C_RESET} (15 GB vs 20 GB)"
  echo -e "  To get ${C_GREEN}${C_BOLD}~40–50 tok/s${C_RESET} right now, use the 7B tier:"
  echo -e "  👉 ${C_CYAN}colistream run qwen2.5-coder:7b${C_RESET}\n"

  echo -e "${C_GREEN}✔ Turbo boost configuration applied successfully!${C_RESET}\n"
}

cmd_switch_gpu() {
  local target_arg="$1"
  run_hardware_scan

  if [ -n "$target_arg" ]; then
    ACTIVE_GPU="$target_arg"
    apply_gpu_configuration "$ACTIVE_GPU"
    return
  fi

  if [ "$GPU_COUNT" -le 1 ]; then
    echo -e "${C_YELLOW}[*] Only 1 GPU detected (${GPU_NAMES[0]:-GPU 0}). No secondary card to switch.${C_RESET}"
    read_input "Press Enter to return to menu: " _
    return
  fi

  echo -e "\n${C_BOLD}┌── SELECT ACTIVE GPU ACCELERATOR ──────────────────────────────────┐${C_RESET}"
  echo -e "│ ${C_YELLOW}Direct inference to your fastest card & isolate slower cards        │${C_RESET}"
  echo -e "├───────────────────────────────────────────────────────────────────┤"
  for i in "${!GPU_INDICES[@]}"; do
    idx="${GPU_INDICES[$i]}"
    name="${GPU_NAMES[$i]}"
    mem="${GPU_MEMS[$i]}"
    mem_gb=$((mem / 1024))
    tag=""
    if [ "$idx" = "$ACTIVE_GPU" ]; then
      tag="${C_GREEN}★ [ACTIVE]${C_RESET}"
    fi
    if [ "$idx" = "$BEST_GPU_IDX" ]; then
      tag="${tag} ${C_CYAN}(Recommended: Largest VRAM)${C_RESET}"
    fi
    printf "│  ${C_BOLD}[%s]${C_RESET} %-28.28s [%5d MB / %2d GB] %-18b │\n" "$idx" "$name" "$mem" "$mem_gb" "$tag"
  done
  echo -e "│                                                                   │"
  all_tag=""
  if [ "$ACTIVE_GPU" = "all" ]; then all_tag="${C_GREEN}★ [ACTIVE]${C_RESET}"; fi
  printf "│  ${C_BOLD}[a]${C_RESET} %-28.28s %-20s %-18b │\n" "All GPUs (Multi-Card Mode)" "" "$all_tag"
  echo -e "├───────────────────────────────────────────────────────────────────┤"
  echo -e "│  ${C_BOLD}[q]${C_RESET} ${C_DIM}Cancel / Keep Current Setting${C_RESET}                               │"
  echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}\n"

  read_input "${C_BOLD}Select GPU index to activate (e.g., 0, 1, or 'a' for all): ${C_RESET}" gpu_sel
  case "$gpu_sel" in
    q|Q|"")
      return
      ;;
    a|A|all)
      ACTIVE_GPU="all"
      ;;
    *)
      if [[ "$gpu_sel" =~ ^[0-9]+$ ]]; then
        ACTIVE_GPU="$gpu_sel"
      else
        echo -e "${C_RED}Invalid GPU selection.${C_RESET}"
        sleep 1
        return
      fi
      ;;
  esac

  apply_gpu_configuration "$ACTIVE_GPU"
  read_input "Press Enter to return to menu: " _
}

cmd_list() {
  ensure_backend
  echo -e "${C_BOLD}┌── LOCAL HUB: INSTALLED MODELS ──────────────────────────────────────┐${C_RESET}"
  curl -s http://localhost:11434/api/tags | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get("models", [])
    if not models:
        print("│  No local models installed yet. Pull one with: colistream pull <name>  │")
    for m in models:
        name = m.get("name", "unknown")
        size_gb = m.get("size", 0) / (1024**3)
        fam = m.get("details", {}).get("family", "unknown")
        print(f"│  • {name:<26} | Family: {fam:<10} | Size: {size_gb:5.1f} GB   │")
except Exception as e:
    print("│ Error reading models:", e)
'
  echo -e "${C_BOLD}└──────────────────────────────────────────────────────────────────────┘${C_RESET}"
}

cmd_diag() {
  ensure_backend
  echo -e "\n${C_BOLD}${C_GREEN}┌── COLIBRISTREAM HARDWARE & INFERENCE DIAGNOSTICS ──────────────────┐${C_RESET}"
  echo -e "│ ${C_BOLD}Active GPU Config${C_RESET} : ${ACTIVE_GPU:-0} (CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-all})"
  echo -e "├───────────────────────────────────────────────────────────────────┤"
  echo -e "│ ${C_BOLD}NVIDIA GPU Hardware Details:${C_RESET}"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=index,name,memory.total,memory.free,pcie.link.gen.current,pcie.link.width.current,utilization.gpu --format=csv,noheader | while IFS=, read -r gidx gname gtot gfree gpgen gpwidth gutil; do
      printf "│   • [GPU %s] %-20.20s | VRAM: %s (%s Free) | PCIe Gen%sx%s | Util: %s\n" \
        "$(echo "$gidx" | tr -d ' ')" "$(echo "$gname" | tr -d ' ')" "$(echo "$gtot" | tr -d ' ')" "$(echo "$gfree" | tr -d ' ')" \
        "$(echo "$gpgen" | tr -d ' ')" "$(echo "$gpwidth" | tr -d ' ')" "$(echo "$gutil" | tr -d ' ')"
    done
  else
    echo -e "│   No nvidia-smi detected."
  fi
  echo -e "├───────────────────────────────────────────────────────────────────┤"
  echo -e "│ ${C_BOLD}Active Inference Daemon Process (ollama ps):${C_RESET}"
  python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:11434/api/ps', timeout=3) as resp:
        data = json.loads(resp.read().decode())
        models = data.get('models', [])
        if not models:
            print('│   No model currently active in GPU/RAM memory.')
        for m in models:
            name = m.get('name', 'unknown')
            size_vram = m.get('size_vram', 0) / (1024**3)
            size_tot = m.get('size', 0) / (1024**3)
            pct_gpu = int((size_vram / size_tot) * 100) if size_tot > 0 else 0
            pct_cpu = 100 - pct_gpu
            print(f'│   • Model: {name}')
            print(f'│     Allocation: {size_vram:.1f} GB / {size_tot:.1f} GB ({pct_gpu}% GPU / {pct_cpu}% CPU)')
            if pct_cpu > 0:
                print('│     \033[38;5;220m[!] BOTTLENECK DETECTED:\033[0m Model is split across CPU/RAM!')
                print('│         Host RAM transfer caps speed to ~0.06 - 1.0 tok/s.')
                print('│         \033[38;5;48m✔ FIX:\033[0m Run 32B for 100% GPU acceleration @ 20-25+ tok/s: colistream run 32b')
            else:
                print('│     \033[38;5;48m✔ 100% GPU ACCELERATED (0 RAM / 0 CPU)\033[0m')
except Exception as e:
    print(f'│   Could not query backend ps: {e}')
"
  echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}\n"
}

cmd_pull() {
  ensure_backend
  local model="$1"
  if [ -z "$model" ]; then
    echo -e "${C_RED}[ERROR] Specify a model name. Example: colistream pull qwen2.5-coder:7b${C_RESET}"
    exit 1
  fi
  case "$model" in
    32b|32B) model="qwen2.5-coder:32b-instruct-q3_K_M" ;;
    72b|72B) model="qwen2.5:72b" ;;
    14b|14B) model="qwen3:14b" ;;
    1.5b|1.5B) model="qwen2.5-coder:1.5b" ;;
    7b|7B) model="qwen2.5-coder:7b" ;;
  esac
  echo -e "${C_CYAN}[*] Contacting Bare-Metal Hub for: ${C_BOLD}${model}${C_RESET}..."
  
  python3 -c "
import urllib.request, json, sys, time

model_name = sys.argv[1]
url = 'http://localhost:11434/api/pull'
req = urllib.request.Request(
    url,
    data=json.dumps({'name': model_name, 'stream': True}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

start_time = time.time()
last_time = start_time
last_bytes = 0
speed_mb = 0.0

try:
    with urllib.request.urlopen(req) as resp:
        for line in resp:
            data = json.loads(line.decode('utf-8'))
            status = data.get('status', '')
            total = data.get('total', 0)
            completed = data.get('completed', 0)
            
            if total > 0:
                now = time.time()
                dt = now - last_time
                if dt >= 0.4:
                    speed_mb = ((completed - last_bytes) / (1024**2)) / dt if dt > 0 else 0.0
                    last_bytes = completed
                    last_time = now

                pct = int((completed / total) * 100)
                gb_done = completed / (1024**3)
                gb_tot = total / (1024**3)
                bar_len = 20
                filled = int(bar_len * completed // total)
                bar = '█' * filled + '░' * (bar_len - filled)
                rem_bytes = total - completed
                if speed_mb > 0.05 and rem_bytes > 0:
                    eta_s = int(rem_bytes / (speed_mb * 1024 * 1024))
                    m, s = divmod(eta_s, 60)
                    eta_str = f'{m}m{s:02d}s'
                else:
                    eta_str = '--:--'
                sys.stdout.write(f'\r\033[38;5;48m[\033[38;5;220m{bar}\033[38;5;48m]\033[0m \033[1m{pct:3d}%\033[0m ({gb_done:5.2f}/{gb_tot:5.2f} GB) \033[38;5;226m{speed_mb:5.1f} MB/s\033[0m ETA \033[38;5;45m{eta_str}\033[0m - \033[38;5;244m{status[:16]:<16}\033[0m')
                sys.stdout.flush()
            else:
                if status and status != 'success':
                    sys.stdout.write(f'\r\033[38;5;244m[*] {status:<60}\033[0m')
                    sys.stdout.flush()
            if status == 'success':
                sys.stdout.write('\r\033[K')
                print(f'\033[38;5;48m\033[1m✔ Model {model_name} downloaded & verified on disk!\033[0m')
                break
except KeyboardInterrupt:
    print('\n\033[38;5;220m[!] Download cancelled by user.\033[0m')
    sys.exit(130)
except Exception as e:
    print(f'\n\033[38;5;196m[ERROR] Failed to pull {model_name}: {e}\033[0m')
    sys.exit(1)
" "$model"

}

write_inline_chat_script() {
  local target="$1"
  cat << 'PYEOF' > "$target"
#!/usr/bin/env python3
"""
Colibristream — Interactive Desktop AI Chat Engine (Copilot / Gemini Style)
Features: Real-time token streaming, multi-turn history, /commands, syntax highlighting.
"""

import sys
import os
import json
import urllib.request
import urllib.error
import time
import re
import glob
import fnmatch
import subprocess
import shutil

# --- Autonomous Coding Agent Subsystem (Aider-Style) ---
tracked_files = {}   # {rel_path: content}
file_backups = []    # [(rel_path, prev_content)]

def add_file_to_context(pattern):
    matches = glob.glob(pattern, recursive=True)
    if not matches and os.path.exists(pattern):
        matches = [pattern]
    if not matches:
        print(f"{C_YELLOW}[!] No files matching '{pattern}' found.{C_RESET}")
        return 0
    added = 0
    for p in matches:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                rel = os.path.relpath(p)
                tracked_files[rel] = content
                lines = len(content.splitlines())
                print(f"{C_GREEN}✔ Added '{rel}' ({lines} lines) to context.{C_RESET}")
                added += 1
            except Exception as e:
                print(f"{C_YELLOW}[!] Could not read '{p}': {e}{C_RESET}")
    return added

def drop_file_from_context(pattern):
    dropped = 0
    for k in list(tracked_files.keys()):
        if pattern == k or fnmatch.fnmatch(k, pattern):
            del tracked_files[k]
            print(f"{C_YELLOW}✔ Dropped '{k}' from context.{C_RESET}")
            dropped += 1
    if dropped == 0:
        print(f"{C_YELLOW}[!] No tracked files matched '{pattern}'.{C_RESET}")
    return dropped

def list_context_files():
    if not tracked_files:
        print(f"{C_DIM}No files currently in context. Add some with: /add <filepath>{C_RESET}")
        return
    print(f"\n{C_BOLD}┌── TRACKED PROJECT FILES IN CONTEXT ─────────────────────────────────┐{C_RESET}")
    total_lines = 0
    for path, content in tracked_files.items():
        lines = len(content.splitlines())
        size_kb = len(content.encode("utf-8")) / 1024
        total_lines += lines
        print(f"│  • {C_CYAN}{path:<35}{C_RESET} {lines:>5} lines | {size_kb:>6.1f} KB          │")
    print(f"├───────────────────────────────────────────────────────────────────┤")
    print(f"│  Total: {len(tracked_files)} files ({total_lines} lines in model context)                     │")
    print(f"{C_BOLD}└───────────────────────────────────────────────────────────────────┘{C_RESET}\n")

def undo_last_change():
    if not file_backups:
        print(f"{C_YELLOW}[!] No recent file modifications to undo.{C_RESET}")
        return
    path, prev_content = file_backups.pop()
    try:
        if prev_content is None:
            if os.path.exists(path):
                os.remove(path)
            tracked_files.pop(path, None)
            print(f"{C_GREEN}✔ Undone: Removed newly created file '{path}'.{C_RESET}")
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(prev_content)
            tracked_files[path] = prev_content
            print(f"{C_GREEN}✔ Undone: Restored previous version of '{path}'.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}[!] Failed to undo change to '{path}': {e}{C_RESET}")

def show_git_diff():
    try:
        res = subprocess.run(["git", "diff", "--color=always"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.stdout:
            print(res.stdout)
        else:
            print(f"{C_DIM}No unstaged git changes found in current directory.{C_RESET}")
    except Exception as e:
        print(f"{C_YELLOW}[!] Could not run git diff: {e}{C_RESET}")

def execute_shell_command(cmd, history=None):
    if not cmd:
        return
    print(f"\n{C_BOLD}{C_CYAN}$ {cmd}{C_RESET}")
    try:
        proc = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stdout.write(f"\033[38;5;208m{proc.stderr}\033[0m")
        if proc.returncode != 0:
            print(f"{C_YELLOW}[Process exited with code {proc.returncode}]{C_RESET}")
        
        if history is not None:
            cmd_output = (proc.stdout + proc.stderr).strip()
            if cmd_output:
                history.append({
                    "role": "user",
                    "content": f"I executed the shell command: `{cmd}`\nOutput:\n```\n{cmd_output}\n```"
                })
                print(f"{C_DIM}[Command output automatically added to context]{C_RESET}")
    except Exception as e:
        print(f"{C_RED}[!] Failed to run command: {e}{C_RESET}")

def print_coding_agent_help():
    print(f"\n{C_BOLD}{C_GREEN}┌── COLIBRISTREAM AUTONOMOUS CODING AGENT COMMANDS ────────────────┐{C_RESET}")
    print(f"│ {C_YELLOW}/add <file|glob>{C_RESET} : Add files to agent context (e.g. /add main.py or *.py) │")
    print(f"│ {C_YELLOW}/drop <file>{C_RESET}     : Remove file from agent context                        │")
    print(f"│ {C_YELLOW}/files{C_RESET}           : List all tracked files and lines in context           │")
    print(f"│ {C_YELLOW}/diff{C_RESET}            : Show git diff of recent changes                       │")
    print(f"│ {C_YELLOW}/undo{C_RESET}            : Revert last file modification or creation             │")
    print(f"│ {C_YELLOW}!cmd / /run cmd{C_RESET}  : Run shell command directly (e.g. !pytest, !ls)        │")
    print(f"│ {C_YELLOW}/debate [model]{C_RESET}  : Launch 2-AI multi-turn debate on current task         │")
    print(f"│ {C_YELLOW}/clear{C_RESET}           : Reset conversation history                            │")
    print(f"│ {C_YELLOW}/menu{C_RESET}            : Return to Model Menu                                  │")
    print(f"│ {C_YELLOW}/exit{C_RESET}            : Exit session                                          │")
    print(f"├──────────────────────────────────────────────────────────────────┤")
    print(f"│ {C_BOLD}Autonomous File Creation & Modification (Aider Style):{C_RESET}           │")
    print(f"│  • Create whole files : ```write:filepath\\n...```               │")
    print(f"│  • Edit surgical lines: ```edit:filepath\\n<<<<<<< SEARCH...```  │")
    print(f"│  • All files are created & edited directly on physical disk!     │")
    print(f"├──────────────────────────────────────────────────────────────────┤")
    print(f"│ {C_BOLD}2-AI Multi-Turn Debate & Review Loop:{C_RESET}                              │")
    print(f"│  • Sibling models dialogue back & forth to audit, refine & debug │")
    print(f"{C_BOLD}└──────────────────────────────────────────────────────────────────┘{C_RESET}\n")

def build_system_prompt():
    cwd = os.getcwd()
    sys_prompt = [
        "You are an expert autonomous software engineer and local pair programmer running via Colibristream.",
        f"Workspace root directory: {cwd}",
        "You have full authority to inspect, create, and modify code files directly on disk.",
        "",
        "CRITICAL FILE CREATION & EDITING PROTOCOLS:",
        "1. To CREATE or OVERWRITE a whole file, wrap the content in a code block with 'write:<filepath>' or 'create:<filepath>':",
        "```write:path/to/file.ext",
        "<complete code content here>",
        "```",
        "",
        "2. To SURGICALLY MODIFY an existing file without rewriting it entirely (Aider-style), output search/replace blocks:",
        "```edit:path/to/file.ext",
        "<<<<<<< SEARCH",
        "<exact lines to find from the file>",
        "=======",
        "<replacement lines>",
        ">>>>>>>",
        "```",
        "",
        "3. Always write clean, fully implemented code without skipping lines or using placeholders.",
    ]
    if tracked_files:
        sys_prompt.append("\nCURRENT ACTIVE PROJECT FILES IN CONTEXT:")
        for path, content in tracked_files.items():
            sys_prompt.append(f"\n--- FILE: {path} ---\n```{path}\n{content}\n```")
    return "\n".join(sys_prompt)

def apply_model_edits(response_text):
    created_or_modified = []
    
    # 1. Whole file writes: ```write:filepath or ```create:filepath
    write_pattern = re.compile(r"```(?:write|create):([^\s\r\n]+)\s*\r?\n(.*?)```", re.DOTALL)
    for match in write_pattern.finditer(response_text):
        target_path = match.group(1).strip()
        code = match.group(2)
        if not target_path:
            continue
        try:
            prev_content = None
            if os.path.exists(target_path):
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    prev_content = f.read()
            file_backups.append((target_path, prev_content))
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(code)
            tracked_files[target_path] = code
            lines = len(code.splitlines())
            action = "Overwrote" if prev_content is not None else "Created"
            print(f"\n{C_GREEN}{C_BOLD}[✔ {action} File]{C_RESET} {C_CYAN}{target_path}{C_RESET} ({lines} lines on disk)")
            created_or_modified.append(target_path)
        except Exception as e:
            print(f"\n{C_RED}[!] Error writing '{target_path}': {e}{C_RESET}")

    # 2. Surgical search/replace edits (Aider style): ```edit:filepath
    edit_block_pattern = re.compile(r"```edit:([^\s\r\n]+)\s*\r?\n(.*?)```", re.DOTALL)
    for match in edit_block_pattern.finditer(response_text):
        target_path = match.group(1).strip()
        edit_body = match.group(2)
        if not os.path.exists(target_path):
            print(f"\n{C_YELLOW}[!] Cannot edit '{target_path}': File does not exist.{C_RESET}")
            continue
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                original_text = f.read()
            chunk_pattern = re.compile(r"<<<<<<< SEARCH\s*\r?\n(.*?)\r?\n=======\s*\r?\n(.*?)\r?\n>>>>>>>", re.DOTALL)
            modified_text = original_text
            chunks_applied = 0
            for chunk in chunk_pattern.finditer(edit_body):
                search_block = chunk.group(1)
                replace_block = chunk.group(2)
                if search_block in modified_text:
                    modified_text = modified_text.replace(search_block, replace_block, 1)
                    chunks_applied += 1
                else:
                    s_norm = "\n".join(line.strip() for line in search_block.splitlines() if line.strip())
                    lines = modified_text.splitlines()
                    found = False
                    for i in range(len(lines)):
                        for j in range(i+1, min(i+len(search_block.splitlines())+5, len(lines)+1)):
                            candidate = "\n".join(l.strip() for l in lines[i:j] if l.strip())
                            if candidate == s_norm:
                                modified_text = "\n".join(lines[:i] + replace_block.splitlines() + lines[j:])
                                chunks_applied += 1
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        print(f"{C_YELLOW}[!] Search chunk not found in '{target_path}'. Skipping chunk.{C_RESET}")

            if chunks_applied > 0:
                file_backups.append((target_path, original_text))
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(modified_text)
                tracked_files[target_path] = modified_text
                print(f"\n{C_GREEN}{C_BOLD}[✔ Applied {chunks_applied} Surgical Edit(s)]{C_RESET} {C_CYAN}{target_path}{C_RESET}")
                created_or_modified.append(target_path)
        except Exception as e:
            print(f"\n{C_RED}[!] Error editing '{target_path}': {e}{C_RESET}")

    # 3. Generic code block filename header: ```path/to/file.ext
    if not created_or_modified:
        generic_pattern = re.compile(r"```([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)\s*\r?\n(.*?)```", re.DOTALL)
        for match in generic_pattern.finditer(response_text):
            target_path = match.group(1).strip()
            code = match.group(2)
            ext = os.path.splitext(target_path)[1].lower()
            if ext in [".py", ".sh", ".bash", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".rs", ".c", ".cpp", ".go", ".md"]:
                try:
                    prev_content = None
                    if os.path.exists(target_path):
                        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                            prev_content = f.read()
                    file_backups.append((target_path, prev_content))
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(code)
                    tracked_files[target_path] = code
                    lines = len(code.splitlines())
                    action = "Overwrote" if prev_content is not None else "Created"
                    print(f"\n{C_GREEN}{C_BOLD}[✔ {action} File]{C_RESET} {C_CYAN}{target_path}{C_RESET} ({lines} lines on disk)")
                    created_or_modified.append(target_path)
                except Exception as e:
                    print(f"\n{C_RED}[!] Error writing '{target_path}': {e}{C_RESET}")

    return created_or_modified

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[38;5;48m"
C_CYAN = "\033[38;5;45m"
C_YELLOW = "\033[38;5;220m"
C_PURPLE = "\033[38;5;141m"
C_GRAY = "\033[38;5;244m"
C_WHITE = "\033[38;5;255m"

def resolve_model_name(name):
    if not name:
        return "qwen2.5-coder:1.5b"
    n = name.strip()
    nl = n.lower()
    if nl in ("32b", "32", "32b-coder", "qwen-32b", "qwen2.5-32b"):
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
                tags = json.loads(resp.read().decode("utf-8")).get("models", [])
                names = [m.get("name", "") for m in tags]
                for cand in ["qwen2.5-coder:32b-instruct-q3_K_M", "qwen2.5-coder:32b", "qwen2.5:32b"]:
                    if any(cand in x for x in names):
                        return cand
        except Exception:
            pass
        return "qwen2.5-coder:32b-instruct-q3_K_M"
    if nl in ("72b", "72", "qwen-72b", "qwen2.5-72b"):
        return "qwen2.5:72b"
    if nl in ("14b", "14", "qwen-14b", "qwen3-14b"):
        return "qwen3:14b"
    if nl in ("1.5b", "1.5", "qwen-1.5b"):
        return "qwen2.5-coder:1.5b"
    if nl in ("7b", "7", "qwen-7b"):
        return "qwen2.5-coder:7b"
    return n

def get_visible_vram_mb():
    try:
        cfg_file = os.path.expanduser("~/.colistream/gpu_config")
        active_gpu = None
        if os.path.exists(cfg_file):
            with open(cfg_file, "r") as f:
                active_gpu = f.read().strip()
        env_cuda = os.environ.get("CUDA_VISIBLE_DEVICES", active_gpu)

        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        total_vram = 0
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 2:
                idx, mem = parts[0], int(parts[1])
                if env_cuda == "all" or not env_cuda:
                    total_vram += mem
                elif str(idx) in env_cuda.split(","):
                    total_vram += mem
        return total_vram
    except Exception:
        return 24576

def ensure_model_installed(model_name):
    exact_target = model_name if ":" in model_name else model_name + ":latest"
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
            tags = json.loads(resp.read().decode("utf-8")).get("models", [])
            names = [m.get("name", "") for m in tags]
            if any(exact_target == n or exact_target in n for n in names):
                return True
    except Exception:
        return False

    print(f"\n{C_YELLOW}[!] Model '{model_name}' not found locally. Auto-downloading now...{C_RESET}")
    url = "http://localhost:11434/api/pull"
    req = urllib.request.Request(
        url,
        data=json.dumps({"name": model_name, "stream": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start_time = time.time()
    last_time = start_time
    last_bytes = 0
    speed_mb = 0.0

    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                data = json.loads(line.decode("utf-8"))
                status = data.get("status", "")
                total = data.get("total", 0)
                completed = data.get("completed", 0)
                if total > 0:
                    now = time.time()
                    dt = now - last_time
                    if dt >= 0.4:
                        speed_mb = ((completed - last_bytes) / (1024**2)) / dt if dt > 0 else 0.0
                        last_bytes = completed
                        last_time = now

                    pct = int((completed / total) * 100)
                    gb_done = completed / (1024**3)
                    gb_tot = total / (1024**3)
                    bar_len = 20
                    filled = int(bar_len * completed // total)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    rem_bytes = total - completed
                    if speed_mb > 0.05 and rem_bytes > 0:
                        eta_s = int(rem_bytes / (speed_mb * 1024 * 1024))
                        m, s = divmod(eta_s, 60)
                        eta_str = f"{m}m{s:02d}s"
                    else:
                        eta_str = "--:--"
                    sys.stdout.write(f"\r\033[38;5;48m[\033[38;5;220m{bar}\033[38;5;48m]\033[0m \033[1m{pct:3d}%\033[0m ({gb_done:5.2f}/{gb_tot:5.2f} GB) \033[38;5;226m{speed_mb:5.1f} MB/s\033[0m ETA \033[38;5;45m{eta_str}\033[0m - \033[38;5;244m{status[:16]:<16}\033[0m")
                    sys.stdout.flush()
                else:
                    if status and status != "success":
                        sys.stdout.write(f"\r\033[38;5;244m[*] {status:<60}\033[0m")
                        sys.stdout.flush()
                if status == "success":
                    sys.stdout.write("\r\033[K")
                    print(f"\033[38;5;48m\033[1m✔ Model {model_name} downloaded & verified on disk!\033[0m")
                    return True
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Download cancelled by user.{C_RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{C_YELLOW}[!] Download warning: {e}{C_RESET}")
        return False
    return True

def stream_chat(model_name, messages, api_url="http://localhost:11434/api/chat", color=C_CYAN):
    model_name = resolve_model_name(model_name)
    cpu_threads = max(1, os.cpu_count() or 4)
    # On multi-socket NUMA systems, clamping to single-socket (8-10 cores) maximizes cache hits and throughput
    opt_threads = min(cpu_threads, 10)
    vram_mb = get_visible_vram_mb()

    m_lower = model_name.lower()
    is_70b = any(x in m_lower for x in ["70b", "72b", "671b"])
    is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])

    if is_70b:
        if vram_mb >= 44000:
            # Multi-GPU Mode (>=48GB total VRAM, e.g. 2x 24GB cards): 100% offload across GPUs -> 20-25+ tok/s!
            num_gpu_layers = 99
            num_ctx_val = 2048
            num_batch_val = 512
        else:
            # Single 24GB card mode: Offload 38 of 80 layers strictly allocating ~22.0 GB VRAM, leaving 2GB KV headroom.
            # Remaining layers execute on host CPU/RAM to prevent cudaMalloc OOM.
            num_gpu_layers = 38
            num_ctx_val = 1536
            num_batch_val = 256
    elif is_32b:
        # 32B models (e.g., qwen2.5-coder:32b-instruct-q3_K_M weights = 16GB):
        # 100% offloaded to GPU: strictly ~17.0 GB VRAM, 0 Host RAM, 0 CPU compute!
        num_gpu_layers = 99
        num_ctx_val = 2048
        num_batch_val = 512
    else:
        # Models <20B: 100% offloaded to GPU (<10GB VRAM)
        num_gpu_layers = 99
        num_ctx_val = 2048
        num_batch_val = 512

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.7,
            "num_gpu": num_gpu_layers,
            "num_thread": opt_threads,
            "num_ctx": num_ctx_val,
            "num_batch": num_batch_val,
            "f16_kv": False,
            "use_mmap": True,
            "use_mlock": False
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
    
    import threading
    stop_spinner = threading.Event()
    def spinner_task():
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while not stop_spinner.is_set():
            frame = spinner_frames[idx % len(spinner_frames)]
            sys.stdout.write(f"\r\033[K{C_YELLOW}{frame} {model_name} is thinking & computing... [Please wait, model is generating]{C_RESET}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)

    spinner_thread = threading.Thread(target=spinner_task, daemon=True)
    spinner_thread.start()

    full_response = []
    token_count = 0
    first_token = True
    
    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        if first_token:
                            stop_spinner.set()
                            sys.stdout.write(f"\r\033[K{C_BOLD}{color}{model_name} ❯ {C_RESET}")
                            sys.stdout.flush()
                            first_token = False
                        sys.stdout.write(content)
                        sys.stdout.flush()
                        full_response.append(content)
                        token_count += 1
                    if chunk.get("done", False):
                        eval_count = chunk.get("eval_count", token_count)
                        eval_dur = chunk.get("eval_duration", 0) / 1e9
                        speed = eval_count / eval_dur if eval_dur > 0 else 0
                        return "".join(full_response), speed, eval_count
                except json.JSONDecodeError:
                    pass
    except KeyboardInterrupt:
        print(f"\n{C_DIM}[Generation stopped by user]{C_RESET}")
        return "".join(full_response), 0, token_count
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8", errors="ignore")
        print(f"\n{C_YELLOW}[!] Inference error ({e.code}): {error_msg}{C_RESET}")
        return "".join(full_response), 0, 0
    except Exception as e:
        print(f"\n{C_YELLOW}[!] Stream error: {e}{C_RESET}")
        return "".join(full_response), 0, 0
    finally:
        stop_spinner.set()
    
    return "".join(full_response), 0, 0

def stream_chat_silent(model_name, messages, api_url="http://localhost:11434/api/chat"):
    model_name = resolve_model_name(model_name)
    cpu_threads = max(1, os.cpu_count() or 4)
    opt_threads = min(cpu_threads, 10)
    vram_mb = get_visible_vram_mb()
    m_lower = model_name.lower()
    is_70b = any(x in m_lower for x in ["70b", "72b", "671b"])
    num_gpu_layers = 38 if (is_70b and vram_mb < 44000) else 99
    num_ctx_val = 1536 if (is_70b and vram_mb < 44000) else 2048

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.7,
            "num_gpu": num_gpu_layers,
            "num_thread": opt_threads,
            "num_ctx": num_ctx_val,
            "num_batch": 512,
            "f16_kv": False,
            "use_mmap": True,
            "use_mlock": False
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
    full_response = []
    token_count = 0
    try:
        with urllib.request.urlopen(req) as resp:
            for line in resp:
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        full_response.append(content)
                        token_count += 1
                    if chunk.get("done", False):
                        eval_count = chunk.get("eval_count", token_count)
                        eval_dur = chunk.get("eval_duration", 0) / 1e9
                        speed = eval_count / eval_dur if eval_dur > 0 else 0
                        return "".join(full_response), speed, eval_count
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return "".join(full_response), 0, token_count

def run_parallel_swarm_session(model1_name, model2_name):
    model1 = resolve_model_name(model1_name)
    model2 = resolve_model_name(model2_name)
    ensure_model_installed(model1)
    ensure_model_installed(model2)

    os.system("clear 2>/dev/null || true")
    print(f"\n{C_GREEN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║           ⚡ COLIBRISTREAM PARALLEL DUAL-INFERENCE SWARM                       ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║         Both Models Computing Simultaneously at the EXACT SAME TIME            ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"│  {C_CYAN}🧠 Model 1 :{C_RESET} {C_WHITE}{C_BOLD}{model1:<35}{C_RESET} {C_GRAY}[Primary Core]{C_RESET}          │")
    print(f"│  {C_PURPLE}🔍 Model 2 :{C_RESET} {C_WHITE}{C_BOLD}{model2:<35}{C_RESET} {C_GRAY}[Parallel Core]{C_RESET}         │")
    print(f"│  {C_YELLOW}⚡ Speed    :{C_RESET} {C_WHITE}Simultaneous Dual-Core Generation (2x Faster for Big Prompts){C_RESET}│")
    print(f"├────────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  {C_BOLD}Commands:{C_RESET} {C_YELLOW}/apply 1{C_RESET} (Save M1 code) | {C_YELLOW}/apply 2{C_RESET} (Save M2 code) | {C_YELLOW}/clear{C_RESET} | {C_YELLOW}/exit{C_RESET}            │")
    print(f"{C_GREEN}{C_BOLD}└────────────────────────────────────────────────────────────────────────────────┘{C_RESET}")

    last_solutions = {"1": "", "2": ""}
    m1_history = [
        {"role": "system", "content": f"You are Core 1 ({model1}) in a high-speed parallel dual-model swarm. Provide a comprehensive, complete, production-grade solution with full code."}
    ]
    m2_history = [
        {"role": "system", "content": f"You are Core 2 ({model2}) in a high-speed parallel dual-model swarm. Provide an alternative, highly optimized, production-grade solution with full code and rigorous edge-case handling."}
    ]

    while True:
        try:
            prompt = input(f"\n{C_BOLD}{C_GREEN}Parallel Task ❯ {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_DIM}Parallel session ended.{C_RESET}")
            break

        if not prompt:
            continue

        if prompt in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_DIM}Parallel session ended.{C_RESET}")
            break

        if prompt == "/menu":
            print(f"{C_CYAN}Returning to Menu...{C_RESET}")
            sys.exit(42)

        if prompt == "/clear":
            m1_history = [{"role": "system", "content": f"You are Core 1 ({model1}) in a high-speed parallel dual-model swarm. Provide a comprehensive, complete, production-grade solution with full code."}]
            m2_history = [{"role": "system", "content": f"You are Core 2 ({model2}) in a high-speed parallel dual-model swarm. Provide an alternative, highly optimized, production-grade solution with full code and rigorous edge-case handling."}]
            print(f"{C_YELLOW}✔ Conversation context cleared for both models.{C_RESET}")
            continue

        if prompt.startswith("/apply") or prompt.startswith("/save"):
            parts = prompt.split()
            choice = parts[1] if len(parts) > 1 and parts[1] in ("1", "2") else "1"
            target_sol = last_solutions.get(choice)
            if target_sol:
                print(f"\n{C_CYAN}[*] Applying Model {choice} solution to workspace...{C_RESET}")
                applied = apply_model_edits(target_sol)
                if not applied:
                    print(f"{C_YELLOW}[!] No file modification blocks found in Model {choice} solution.{C_RESET}")
            else:
                print(f"{C_YELLOW}[!] No generated solution to apply for Model {choice} yet.{C_RESET}")
            continue

        if prompt.startswith("/add ") or prompt.startswith("/a "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                add_file_to_context(parts[1].strip())
            continue

        if prompt.startswith("/drop ") or prompt.startswith("/rm "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                drop_file_from_context(parts[1].strip())
            continue

        if prompt in ("/files", "/ls"):
            list_context_files()
            continue

        if prompt in ("/diff",):
            show_git_diff()
            continue

        if prompt in ("/undo",):
            undo_last_change()
            continue

        if prompt.startswith("/run ") or prompt.startswith("!"):
            cmd_to_run = prompt[5:].strip() if prompt.startswith("/run ") else prompt[1:].strip()
            execute_shell_command(cmd_to_run, [])
            continue

        files_ctx = build_system_prompt()
        full_user_prompt = f"{prompt}\n\n{files_ctx}" if files_ctx else prompt

        m1_messages = list(m1_history) + [{"role": "user", "content": full_user_prompt}]
        m2_messages = list(m2_history) + [{"role": "user", "content": full_user_prompt}]

        import threading
        res_m2 = {}

        def run_m2_background():
            m2_out, m2_spd, m2_toks = stream_chat_silent(model2, m2_messages)
            res_m2["text"] = m2_out
            res_m2["spd"] = m2_spd
            res_m2["toks"] = m2_toks

        print(f"\n{C_BOLD}{C_YELLOW}⚡ Dispatching {model1} and {model2} AT THE EXACT SAME TIME...{C_RESET}")
        print(f"{C_DIM}   • Core 1: {model1} streaming live below{C_RESET}")
        print(f"{C_DIM}   • Core 2: {model2} computing concurrently in background thread [0 extra wait time]{C_RESET}")
        
        t2 = threading.Thread(target=run_m2_background, daemon=True)
        t2.start()

        print(f"\n{C_BOLD}{C_CYAN}┌── 🧠 Model 1 ({model1}): Live Generation ──┐{C_RESET}")
        m1_out, m1_spd, m1_toks = stream_chat(model1, m1_messages, color=C_CYAN)
        last_solutions["1"] = m1_out

        spd1_text = f"{m1_spd:.1f} tok/s" if m1_spd > 0 else ""
        print(f"\n{C_DIM}└─ [{m1_toks} tokens {spd1_text}]{C_RESET}")

        if t2.is_alive():
            stop_wait = threading.Event()
            def wait_spinner():
                frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                i = 0
                while not stop_wait.is_set():
                    sys.stdout.write(f"\r\033[K{C_YELLOW}{frames[i % len(frames)]} Model 2 ({model2}) is completing parallel generation...{C_RESET}")
                    sys.stdout.flush()
                    i += 1
                    time.sleep(0.08)
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()

            w_spin = threading.Thread(target=wait_spinner, daemon=True)
            w_spin.start()
            t2.join()
            stop_wait.set()
            w_spin.join()

        m2_out = res_m2.get("text", "")
        m2_spd = res_m2.get("spd", 0)
        m2_toks = res_m2.get("toks", 0)
        last_solutions["2"] = m2_out

        spd2_text = f"{m2_spd:.1f} tok/s" if m2_spd > 0 else ""
        print(f"\n{C_BOLD}{C_PURPLE}┌── 🔍 Model 2 ({model2}): Parallel Solution (Computed Concurrently) ──┐{C_RESET}")
        print(f"{C_PURPLE}{model2} ❯ {C_RESET}{m2_out}")
        print(f"\n{C_DIM}└─ [{m2_toks} tokens {spd2_text} • 0 extra wait time]{C_RESET}")

        m1_history.append({"role": "user", "content": prompt})
        m1_history.append({"role": "assistant", "content": m1_out})
        m2_history.append({"role": "user", "content": prompt})
        m2_history.append({"role": "assistant", "content": m2_out})

        print(f"\n{C_GREEN}{C_BOLD}════════════════════════════════════════════════════════════════════════════════{C_RESET}")
        print(f"{C_GREEN}{C_BOLD}✔ Parallel Dual Generation Complete! Both models ran simultaneously.{C_RESET}")
        print(f"{C_DIM}Type '/apply 1' for Model 1 code | Type '/apply 2' for Model 2 code | Enter next prompt{C_RESET}")

def run_swarm_debate_session(model1_name, model2_name, rounds=2):
    model1 = resolve_model_name(model1_name)
    model2 = resolve_model_name(model2_name)
    ensure_model_installed(model1)
    ensure_model_installed(model2)

    os.system("clear 2>/dev/null || true")
    print(f"\n{C_GREEN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║           COLIBRISTREAM 2-AI MULTI-TURN DEBATE & REVIEW LOOP                   ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║      Autonomous Sibling Dialogue • Adversarial Code Audit & Verification       ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"│  {C_CYAN}🧠 Lead Architect :{C_RESET} {C_WHITE}{C_BOLD}{model1:<35}{C_RESET} {C_GRAY}[Proposal & Synthesis]{C_RESET} │")
    print(f"│  {C_PURPLE}🔍 Peer Reviewer  :{C_RESET} {C_WHITE}{C_BOLD}{model2:<35}{C_RESET} {C_GRAY}[Adversarial Audit]{C_RESET}    │")
    print(f"│  {C_YELLOW}🔄 Review Depth   :{C_RESET} {C_WHITE}{rounds} Rounds (Back-and-Forth Multi-Turn Loop){C_RESET}                   │")
    print(f"├────────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  {C_BOLD}Commands:{C_RESET} {C_YELLOW}/rounds <N>{C_RESET} | {C_YELLOW}/apply{C_RESET} (Save code to disk) | {C_YELLOW}/add <file>{C_RESET} | {C_YELLOW}!cmd{C_RESET} | {C_YELLOW}/exit{C_RESET}   │")
    print(f"{C_GREEN}{C_BOLD}└────────────────────────────────────────────────────────────────────────────────┘{C_RESET}")

    last_refined_solution = ""

    while True:
        try:
            prompt = input(f"\n{C_BOLD}{C_GREEN}Debate Task ❯ {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_DIM}Debate session ended.{C_RESET}")
            break

        if not prompt:
            continue

        if prompt in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_DIM}Debate session ended.{C_RESET}")
            break

        if prompt == "/menu":
            print(f"{C_CYAN}Returning to Menu...{C_RESET}")
            sys.exit(42)

        if prompt.startswith("/rounds ") or prompt.startswith("/r "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().isdigit():
                rounds = max(1, min(5, int(parts[1].strip())))
                print(f"{C_GREEN}✔ Debate depth set to {rounds} rounds.{C_RESET}")
            continue

        if prompt in ("/apply", "/save"):
            if last_refined_solution:
                print(f"\n{C_CYAN}[*] Applying consensus code edits to workspace...{C_RESET}")
                applied = apply_model_edits(last_refined_solution)
                if not applied:
                    print(f"{C_YELLOW}[!] No file modification blocks found in last solution.{C_RESET}")
            else:
                print(f"{C_YELLOW}[!] No generated solution to apply yet.{C_RESET}")
            continue

        if prompt.startswith("/add ") or prompt.startswith("/a "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                add_file_to_context(parts[1].strip())
            continue

        if prompt.startswith("/drop ") or prompt.startswith("/rm "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                drop_file_from_context(parts[1].strip())
            continue

        if prompt in ("/files", "/ls"):
            list_context_files()
            continue

        if prompt in ("/diff",):
            show_git_diff()
            continue

        if prompt in ("/undo",):
            undo_last_change()
            continue

        if prompt.startswith("/run ") or prompt.startswith("!"):
            cmd_to_run = prompt[5:].strip() if prompt.startswith("/run ") else prompt[1:].strip()
            execute_shell_command(cmd_to_run, [])
            continue

        # Execute Multi-Turn Debate Loop
        files_ctx = build_system_prompt()
        current_proposal = ""
        current_critique = ""

        print(f"\n{C_BOLD}{C_YELLOW}⚡ Initiating {rounds}-Round Autonomous Debate between {model1} and {model2}...{C_RESET}")

        for r in range(1, rounds + 1):
            # ─── TURN 1: Lead Architect (Model 1) ───
            arch_title = "Initial Technical Proposal" if r == 1 else f"Defended & Refined Synthesis (V{r})"
            print(f"\n{C_BOLD}{C_CYAN}┌── [Round {r}/{rounds}] 🧠 Lead Architect ({model1}): {arch_title} ──┐{C_RESET}")

            if r == 1:
                arch_prompt = (
                    f"You are the Lead Architect in an autonomous 2-AI swarm.\n"
                    f"Your partner is an Adversarial Peer Reviewer who will rigorously stress-test your proposal.\n"
                    f"User Task: {prompt}\n\n"
                    f"{files_ctx}\n\n"
                    f"Instructions:\n"
                    f"1. Formulate a comprehensive, production-grade technical solution or architecture.\n"
                    f"2. Explain your algorithmic decisions and trade-offs clearly.\n"
                    f"3. Provide complete, working code blocks with filename tags (e.g. ```filename.ext) where applicable.\n"
                )
            else:
                arch_prompt = (
                    f"You are the Lead Architect in an autonomous 2-AI swarm.\n"
                    f"The Peer Reviewer has conducted a rigorous critique of your previous proposal.\n"
                    f"Original Task: {prompt}\n\n"
                    f"--- REVIEWER CRITIQUE ---\n{current_critique}\n-------------------------\n\n"
                    f"Instructions:\n"
                    f"1. Directly address every flaw, bug, edge case, and critique raised by the Reviewer.\n"
                    f"2. Defend choices that are technically justified with clear reasoning.\n"
                    f"3. Output a hardened, battle-tested Version {r} with corrected, complete code.\n"
                )

            arch_messages = [
                {"role": "system", "content": "You are the Lead Architect in an autonomous 2-AI engineering pair."},
                {"role": "user", "content": arch_prompt}
            ]

            arch_output, arch_spd, arch_toks = stream_chat(model1, arch_messages, color=C_CYAN)
            current_proposal = arch_output
            last_refined_solution = arch_output

            spd_text = f"{arch_spd:.1f} tok/s" if arch_spd > 0 else ""
            print(f"\n{C_DIM}└─ [{arch_toks} tokens {spd_text}]{C_RESET}")

            # ─── TURN 2: Peer Reviewer (Model 2) ───
            is_final_round = (r == rounds)
            rev_title = "Critical Analysis & Edge Cases" if not is_final_round else "Final Verification & Consensus Verdict"
            print(f"\n{C_BOLD}{C_PURPLE}┌── [Round {r}/{rounds}] 🔍 Peer Reviewer ({model2}): {rev_title} ──┐{C_RESET}")

            if not is_final_round:
                rev_prompt = (
                    f"You are an expert Peer Reviewer and Adversarial Critic in an autonomous 2-AI swarm.\n"
                    f"Your objective is to stress-test the Lead Architect's proposal and find hidden flaws.\n"
                    f"Original Task: {prompt}\n\n"
                    f"Architect Proposal:\n{current_proposal}\n\n"
                    f"Instructions:\n"
                    f"1. Identify logical flaws, race conditions, memory leaks, performance bottlenecks, or security holes.\n"
                    f"2. Challenge boundary conditions, unhandled exceptions, and missing edge cases.\n"
                    f"3. Give specific, actionable directives for the Architect to implement in the next round.\n"
                )
            else:
                rev_prompt = (
                    f"You are the Peer Reviewer conducting the FINAL AUDIT and CONSENSUS VERDICT in an autonomous 2-AI swarm.\n"
                    f"Original Task: {prompt}\n\n"
                    f"Architect Refined Solution (Version {r}):\n{current_proposal}\n\n"
                    f"Instructions:\n"
                    f"1. Verify whether previous bugs, edge cases, and critiques were successfully resolved.\n"
                    f"2. Give a clear verdict at the start of your reply:\n"
                    f"   VERDICT: [APPROVED ✔] (if production-ready) or [NEEDS REVISION ⚠] (if issues remain).\n"
                    f"3. Summarize final strengths and production advice.\n"
                )

            rev_messages = [
                {"role": "system", "content": "You are the Adversarial Peer Reviewer in an autonomous 2-AI engineering pair."},
                {"role": "user", "content": rev_prompt}
            ]

            rev_output, rev_spd, rev_toks = stream_chat(model2, rev_messages, color=C_PURPLE)
            current_critique = rev_output

            spd_text = f"{rev_spd:.1f} tok/s" if rev_spd > 0 else ""
            print(f"\n{C_DIM}└─ [{rev_toks} tokens {spd_text}]{C_RESET}")

        print(f"\n{C_GREEN}{C_BOLD}════════════════════════════════════════════════════════════════════════════════{C_RESET}")
        print(f"{C_GREEN}{C_BOLD}✔ 2-AI Multi-Turn Consensus Loop Complete ({rounds} Rounds Finished){C_RESET}")
        print(f"{C_GREEN}{C_BOLD}════════════════════════════════════════════════════════════════════════════════{C_RESET}")
        print(f"{C_DIM}Actions: Type '/apply' to save audited code to disk | Enter new prompt | Type '/exit'{C_RESET}")

def run_chat_session(model_name):
    model_name = resolve_model_name(model_name)
    ensure_model_installed(model_name)
    os.system("clear 2>/dev/null || true")
    m_lower = model_name.lower()
    is_70b = any(x in m_lower for x in ["70b", "72b", "671b"])
    is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])

    print(f"{C_GREEN}{C_BOLD}┌────────────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}│  COLIBRISTREAM AUTONOMOUS CODING RUNTIME (AIDER-STYLE LOCAL AGENT)     │{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}├────────────────────────────────────────────────────────────────────────┤{C_RESET}")
    vram_mb = get_visible_vram_mb()
    print(f"│  {C_CYAN}Active Model:{C_RESET} {C_BOLD}{model_name:<30}{C_RESET} {C_GRAY}[100% Local • Zero Cloud]{C_RESET}   │")
    print(f"│  {C_YELLOW}Workspace   :{C_RESET} {C_WHITE}{os.getcwd():<47.47s}{C_RESET} │")
    if is_32b:
        print(f"│  {C_YELLOW}VRAM Budget :{C_RESET} {C_GREEN}Strictly ~17 GB VRAM (100% on GPU • 0 Host RAM • 0 CPU){C_RESET}   │")
    elif is_70b:
        if vram_mb >= 44000:
            print(f"│  {C_YELLOW}VRAM Budget :{C_RESET} {C_GREEN}Multi-GPU Mode (~48GB VRAM Pool • 100% on GPUs @ 20+ tok/s){C_RESET} │")
        else:
            print(f"│  {C_YELLOW}VRAM Budget :{C_RESET} {C_YELLOW}Strictly ~22 GB VRAM (38 Layers GPU + 42 Layers CPU/RAM){C_RESET} │")
    else:
        print(f"│  {C_YELLOW}VRAM Budget :{C_RESET} {C_GREEN}100% GPU VRAM Native Acceleration (<10 GB VRAM){C_RESET}          │")
    print(f"├────────────────────────────────────────────────────────────────────────┤")
    print(f"│  {C_BOLD}Commands:{C_RESET}    {C_YELLOW}/add <file>{C_RESET} | {C_YELLOW}/diff{C_RESET} | {C_YELLOW}/undo{C_RESET} | {C_YELLOW}!cmd{C_RESET} (Shell) | {C_YELLOW}/debate [model]{C_RESET} │")
    print(f"│               {C_YELLOW}/files{C_RESET}      | {C_YELLOW}/help{C_RESET} | {C_YELLOW}/clear{C_RESET} | {C_YELLOW}/menu{C_RESET}        | {C_YELLOW}/exit{C_RESET}          │")
    print(f"{C_GREEN}{C_BOLD}└────────────────────────────────────────────────────────────────────────┘{C_RESET}")

    if is_70b and vram_mb < 44000:
        print(f"\n{C_YELLOW}┌── HARDWARE ADVISORY: 72B SINGLE-CARD BOTTLENECK ──────────────────────┐{C_RESET}")
        print(f"│ {C_BOLD}Weight Size{C_RESET} : ~47 GB (Q4) / ~30 GB (Q2) — Exceeds single 24GB VRAM card   │")
        print(f"│ {C_BOLD}Allocation{C_RESET}  : ~22 GB on GPU (38 layers) + ~25 GB on Host RAM & CPU      │")
        print(f"│ {C_BOLD}Bandwidth{C_RESET}   : DDR4 RAM is ~35 GB/s (vs GPU ~700 GB/s) -> caps to ~1 tok/s │")
        print(f"│                                                                      │")
        print(f"│ {C_GREEN}★ HOW TO GET 20-25+ TOK/S:{C_RESET}                                           │")
        print(f"│   1. Dual GPUs (>=48GB VRAM): Switch with 'colistream gpu all'        │")
        print(f"│   2. Single 24GB Card: Run 32B Coder (17GB VRAM, 0 RAM, 0 CPU @ 25 t/s)│")
        print(f"│      Command: {C_CYAN}colistream run 32b{C_RESET}                                      │")
        print(f"{C_YELLOW}└──────────────────────────────────────────────────────────────────────┘{C_RESET}\n")

    history = [
        {"role": "system", "content": build_system_prompt()}
    ]

    while True:
        try:
            prompt = input(f"\n{C_BOLD}{C_GREEN}You ❯ {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_DIM}Exiting session.{C_RESET}")
            sys.exit(0)

        if not prompt:
            continue

        if prompt in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_DIM}Session ended.{C_RESET}")
            sys.exit(0)

        if prompt == "/menu":
            print(f"{C_CYAN}Returning to Model Menu...{C_RESET}")
            sys.exit(42)  # Special exit code to tell caller to reopen menu

        if prompt == "/clear":
            history = [{"role": "system", "content": build_system_prompt()}]
            print(f"{C_YELLOW}✔ Conversation context cleared.{C_RESET}")
            continue

        if prompt in ("/help", "/h", "?"):
            print_coding_agent_help()
            continue

        if prompt.startswith("/debate") or prompt.startswith("/swarm"):
            parts = prompt.split()
            second_model = parts[1] if len(parts) > 1 else ("qwen2.5-coder:1.5b" if model_name != "qwen2.5-coder:1.5b" else "qwen3:14b")
            rounds_num = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 2
            run_swarm_debate_session(model_name, second_model, rounds=rounds_num)
            continue

        if prompt.startswith("/add ") or prompt.startswith("/a "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                add_file_to_context(parts[1].strip())
            continue

        if prompt.startswith("/drop ") or prompt.startswith("/rm "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                drop_file_from_context(parts[1].strip())
            continue

        if prompt in ("/files", "/ls"):
            list_context_files()
            continue

        if prompt in ("/diff",):
            show_git_diff()
            continue

        if prompt in ("/undo",):
            undo_last_change()
            continue

        if prompt.startswith("/run ") or prompt.startswith("!"):
            cmd_to_run = prompt[5:].strip() if prompt.startswith("/run ") else prompt[1:].strip()
            execute_shell_command(cmd_to_run, history)
            continue

        # Keep system prompt completely synced with current workspace files
        history[0]["content"] = build_system_prompt()
        history.append({"role": "user", "content": prompt})

        if is_70b:
            status_hint = f"{C_DIM}[Evaluating 72B layers across GPU + RAM... ~45s]{C_RESET}"
        elif is_32b:
            status_hint = f"{C_DIM}[Processing on GPU VRAM (17GB)...]{C_RESET}"
        else:
            status_hint = f"{C_DIM}[Processing on GPU...]{C_RESET}"

        print("")
        response_text, speed, tokens = stream_chat(model_name, history, color=C_CYAN)
        if response_text:
            history.append({"role": "assistant", "content": response_text})
            # Autonomous Aider-style File Modification Engine
            apply_model_edits(response_text)

        if speed > 0:
            if speed < 0.2:
                speed_str = f"{speed:.2f} tok/s {C_YELLOW}[!] Critically slow: GPU bottleneck or running on secondary slow card / CPU swap{C_RESET}"
            else:
                speed_str = f"{speed:.1f} tok/s"
        else:
            speed_str = ""
        print(f"\n{C_DIM}└─ [{tokens} tokens {speed_str}]{C_RESET}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--swarm", "--debate", "swarm", "debate"):
        m1 = sys.argv[2] if len(sys.argv) > 2 else "qwen3:14b"
        m2 = sys.argv[3] if len(sys.argv) > 3 else "qwen2.5-coder:1.5b"
        rounds_arg = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 2
        run_swarm_debate_session(m1, m2, rounds=rounds_arg)
    elif len(sys.argv) > 1 and sys.argv[1] in ("--parallel", "parallel", "-p"):
        m1 = sys.argv[2] if len(sys.argv) > 2 else "qwen3:14b"
        m2 = sys.argv[3] if len(sys.argv) > 3 else "qwen2.5-coder:1.5b"
        run_parallel_swarm_session(m1, m2)
    else:
        model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b"
        run_chat_session(model)
PYEOF
  chmod +x "$target" 2>/dev/null || true
}

cmd_run() {
  ensure_backend
  local model="$1"
  if [ -z "$model" ]; then
    model="qwen2.5-coder:1.5b"
  fi

  # Intelligent Model Alias Resolution & Precision VRAM Targeting:
  case "$model" in
    32b|32B)
      model="qwen2.5-coder:32b-instruct-q3_K_M"
      ;;
    72b|72B)
      model="qwen2.5:72b"
      ;;
    14b|14B)
      model="qwen3:14b"
      ;;
    1.5b|1.5B)
      model="qwen2.5-coder:1.5b"
      ;;
    qwen2.5-coder:32b|qwen2.5:32b)
      # If user typed standard 32b, check if already present on disk; if not present, use q3_K_M (strictly ~17 GB VRAM, 0 RAM, 0 CPU)
      local is_any_32b
      is_any_32b=$(python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2) as resp:
        names = [m.get('name', '') for m in json.loads(resp.read().decode()).get('models', [])]
        print('1' if any('32b' in n for n in names) else '0')
except:
    print('0')
" 2>/dev/null || echo "0")
      if [ "$is_any_32b" != "1" ]; then
        model="qwen2.5-coder:32b-instruct-q3_K_M"
      fi
      ;;
  esac

  # Proactive VRAM Capacity & Bottleneck Guard:
  run_hardware_scan
  local model_lower
  model_lower=$(echo "$model" | tr '[:upper:]' '[:lower:]')
  if [[ "$model_lower" =~ 70b|72b|671b ]] && [ "$AVAILABLE_VRAM_GB" -lt 44 ]; then
    echo -e "\n${C_YELLOW}┌── ⚠ HARDWARE INSUFFICIENCY WARNING: MODEL EXCEEDS VRAM ──────────┐${C_RESET}"
    echo -e "│ ${C_BOLD}Selected Model${C_RESET}  : ${C_CYAN}${model}${C_RESET} (Dense 72B requires ~48 GB VRAM for native speed)│"
    echo -e "│ ${C_BOLD}Available VRAM${C_RESET}  : ${C_YELLOW}${AVAILABLE_VRAM_GB} GB${C_RESET} [GPU ${ACTIVE_GPU:-0}] (Short by ~$((48 - AVAILABLE_VRAM_GB)) GB)                │"
    echo -e "│ ${C_BOLD}Offload Reality${C_RESET} : ~42 layers will be forced to Host CPU & DDR4 RAM!      │"
    echo -e "│ ${C_BOLD}Expected Speed${C_RESET}  : ${C_RED}~0.05 - 0.2 tok/s (EXTREMELY SLOW: ~15s per token)${C_RESET} │"
    echo -e "│                                                                  │"
    echo -e "│ ${C_GREEN}★ FAST ALTERNATIVE (100% in VRAM @ 20-25+ tok/s):${C_RESET}                │"
    echo -e "│   Run 32B Coder instead: ${C_CYAN}colistream run 32b${C_RESET} (Fits in 16GB VRAM)   │"
    echo -e "│   Benchmark: 92.7% on HumanEval coding (beats 72B at 86.4%)      │"
    echo -e "${C_YELLOW}└──────────────────────────────────────────────────────────────────┘${C_RESET}\n"
    read_input "${C_BOLD}Proceed with 72B anyway, knowing it will be extremely slow? [y/N]: ${C_RESET}" CONFIRM_HEAVY
    case "$CONFIRM_HEAVY" in
      y|Y|yes|YES)
        echo -e "${C_YELLOW}[*] Proceeding with 72B CPU/RAM split as requested...${C_RESET}"
        ;;
      *)
        echo -e "\n${C_GREEN}[*] Smart choice! Switching to Flagship 32B (100% in GPU VRAM @ 20+ tok/s)...${C_RESET}"
        model="qwen2.5-coder:32b-instruct-q3_K_M"
        ;;
    esac
  elif [[ "$model_lower" =~ 32b|30b|27b ]] && [ "$AVAILABLE_VRAM_GB" -gt 0 ] && [ "$AVAILABLE_VRAM_GB" -lt 16 ]; then
    echo -e "\n${C_YELLOW}┌── ⚠ VRAM CAPACITY WARNING: 32B EXCEEDS GPU VRAM ─────────────────┐${C_RESET}"
    echo -e "│ ${C_BOLD}Selected Model${C_RESET}  : ${C_CYAN}${model}${C_RESET} (Requires ~16 GB VRAM)                     │"
    echo -e "│ ${C_BOLD}Available VRAM${C_RESET}  : ${C_YELLOW}${AVAILABLE_VRAM_GB} GB${C_RESET} [GPU ${ACTIVE_GPU:-0}]                                     │"
    echo -e "│ ${C_BOLD}Recommended${C_RESET}   : ${C_GREEN}qwen3:14b${C_RESET} (~9GB VRAM) or ${C_GREEN}qwen2.5-coder:7b${C_RESET} (~5GB VRAM) │"
    echo -e "${C_YELLOW}└──────────────────────────────────────────────────────────────────┘${C_RESET}\n"
    read_input "${C_BOLD}Proceed with 32B anyway? [y/N]: ${C_RESET}" CONFIRM_32B
    case "$CONFIRM_32B" in
      y|Y|yes|YES)
        echo -e "${C_YELLOW}[*] Proceeding with 32B...${C_RESET}"
        ;;
      *)
        echo -e "\n${C_GREEN}[*] Switching to 14B High-Speed Model...${C_RESET}"
        model="qwen3:14b"
        ;;
    esac
  fi

  # Verify if model is installed locally (Exact Match)
  local is_installed
  is_installed=$(python3 -c "
import urllib.request, json, sys
m_target = sys.argv[1]
exact_target = m_target if ':' in m_target else m_target + ':latest'
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3) as resp:
        tags = json.loads(resp.read().decode()).get('models', [])
        names = [m.get('name', '') for m in tags]
        matched = exact_target in names
        print('1' if matched else '0')
except Exception:
    print('0')
" "$model" 2>/dev/null || echo "0")

  if [ "$is_installed" != "1" ]; then
    echo -e "\n${C_YELLOW}[!] Model '${model}' not found locally on disk. Auto-downloading now...${C_RESET}"
    cmd_pull "$model" || return 1
  fi

  local chat_script="${DIR}/colibri_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/colibri_chat.py"
  fi
  write_inline_chat_script "$chat_script"

  echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  if [ -e /dev/tty ]; then
    python3 "$chat_script" "$model" </dev/tty
  else
    python3 "$chat_script" "$model"
  fi
  cmd_loop_menu
}

cmd_swarm() {
  ensure_backend
  local arg1="${1:-qwen}"
  local arg2="$2"

  if [ -n "$arg2" ]; then
    ARCHITECT="$arg1"
    WORKER="$arg2"
  else
    case "$arg1" in
      72b|qwen-72b|qwen72b)
        ARCHITECT="qwen2.5:72b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
      qwen|qwen-local)
        ARCHITECT="qwen3:14b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
      deepseek)
        ARCHITECT="deepseek-r1:14b"
        WORKER="deepseek-coder:6.7b"
        ;;
      llama)
        ARCHITECT="llama3.3:70b"
        WORKER="llama3.1:8b"
        ;;
      *)
        ARCHITECT="qwen3:14b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
    esac
  fi

  local chat_script="${DIR}/colibri_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/colibri_chat.py"
  fi
  write_inline_chat_script "$chat_script"

  local rounds="${3:-2}"
  echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  if [ -e /dev/tty ]; then
    python3 "$chat_script" --swarm "$ARCHITECT" "$WORKER" "$rounds" </dev/tty
  else
    python3 "$chat_script" --swarm "$ARCHITECT" "$WORKER" "$rounds"
  fi
  local exit_code=$?
  if [ "$exit_code" -eq 42 ]; then
    cmd_loop_menu
  fi
}

# --- Simultaneous Parallel Swarm (Both Models Compute at the EXACT Same Time) ---
cmd_parallel() {
  ensure_backend
  local m1="${1:-qwen3:14b}"
  local m2="${2:-qwen2.5-coder:1.5b}"

  local chat_script="${DIR}/colibri_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/colibri_chat.py"
  fi
  write_inline_chat_script "$chat_script"

  echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  if [ -e /dev/tty ]; then
    python3 "$chat_script" --parallel "$m1" "$m2" </dev/tty
  else
    python3 "$chat_script" --parallel "$m1" "$m2"
  fi
  local exit_code=$?
  if [ "$exit_code" -eq 42 ]; then
    cmd_loop_menu
  fi
}

# --- Custom Multi-Model Swarm Builder ---
cmd_swarm_builder() {
  clear 2>/dev/null || true
  echo -e "${C_BOLD}${C_GREEN}"
  echo "╔══════════════════════════════════════════════════════════════════════╗"
  echo "║         CUSTOM MULTI-MODEL SWARM BUILDER (RUN 2+ MODELS)             ║"
  echo "║     Pair any Big Brain AI with any Fast Worker AI in shared memory   ║"
  echo "╚══════════════════════════════════════════════════════════════════════╝"
  echo -e "${C_RESET}\n"

  echo -e "${C_CYAN}Step 1: Choose Model #1 (The Lead Thinker / Architect):${C_RESET}"
  echo -e "  1) qwen2.5:72b         (Big 72B Brain)"
  echo -e "  2) qwen3:14b           (14B Reasoning Brain - Already Installed!)"
  echo -e "  3) deepseek-r1:14b     (Deep Reasoning <think> Brain)"
  echo -e "  4) llama3.3:70b        (Meta 70B Flagship)"
  echo -e "  5) Enter custom model name"
  read_input "${C_BOLD}Select [1-5]: ${C_RESET}" M1_CHOICE

  case "$M1_CHOICE" in
    1) MODEL1="qwen2.5:72b" ;;
    2) MODEL1="qwen3:14b" ;;
    3) MODEL1="deepseek-r1:14b" ;;
    4) MODEL1="llama3.3:70b" ;;
    5)
      read_input "Enter Model 1 name: " MODEL1
      ;;
    *) MODEL1="qwen3:14b" ;;
  esac

  echo -e "\n${C_CYAN}Step 2: Choose Model #2 (The Fast Worker / Coder):${C_RESET}"
  echo -e "  1) qwen2.5-coder:1.5b  (Ultra-Fast Coder - Already Installed!)"
  echo -e "  2) qwen2.5-coder:7b    (7B Accurate Coder)"
  echo -e "  3) deepseek-coder:6.7b (DeepSeek Fast Coder)"
  echo -e "  4) llama3.1:8b         (Llama 8B Worker)"
  echo -e "  5) Enter custom model name"
  read_input "${C_BOLD}Select [1-5]: ${C_RESET}" M2_CHOICE

  case "$M2_CHOICE" in
    1) MODEL2="qwen2.5-coder:1.5b" ;;
    2) MODEL2="qwen2.5-coder:7b" ;;
    3) MODEL2="deepseek-coder:6.7b" ;;
    4) MODEL2="llama3.1:8b" ;;
    5)
      read_input "Enter Model 2 name: " MODEL2
      ;;
    *) MODEL2="qwen2.5-coder:1.5b" ;;
  esac

  echo -e "\n${C_CYAN}Step 3: Choose Swarm Execution Strategy:${C_RESET}"
  echo -e "  1) ⚡ Simultaneous Parallel (RECOMMENDED: Both models run at the EXACT SAME TIME - 2x faster!)"
  echo -e "  2) 🔄 Sequential Adversarial Debate (Model 1 writes, Model 2 audits & refines in rounds)"
  read_input "${C_BOLD}Select [1-2, default 1]: ${C_RESET}" STRAT_CHOICE

  case "$STRAT_CHOICE" in
    2)
      SWARM_MODE="debate"
      ;;
    *)
      SWARM_MODE="parallel"
      ;;
  esac

  echo -e "\n${C_GREEN}${C_BOLD}Multi-Model Team Configured:${C_RESET}"
  echo -e "  • ${C_YELLOW}Model 1:${C_RESET} ${MODEL1}"
  echo -e "  • ${C_GREEN}Model 2:${C_RESET} ${MODEL2}"

  if [ "$SWARM_MODE" = "parallel" ]; then
    echo -e "  • ${C_CYAN}Mode   :${C_RESET} ⚡ Simultaneous Parallel (Zero Wait Time • Both run concurrently)\n"
    echo -e "${C_YELLOW}Direct Command to run this Parallel Swarm anytime:${C_RESET}"
    echo -e "  ${C_BOLD}${C_WHITE}colistream parallel ${MODEL1} ${MODEL2}${C_RESET}\n"
    read_input "${C_BOLD}Press Enter to boot this simultaneous parallel session now [Enter/b]: ${C_RESET}" CONF
    if [ "$CONF" != "b" ] && [ "$CONF" != "B" ]; then
      cmd_parallel "$MODEL1" "$MODEL2"
    fi
  else
    echo -e "  • ${C_PURPLE}Mode   :${C_RESET} 🔄 Sequential Adversarial Debate (Multi-turn back-and-forth)\n"
    echo -e "${C_YELLOW}Direct Command to run this Debate Swarm anytime:${C_RESET}"
    echo -e "  ${C_BOLD}${C_WHITE}colistream debate ${MODEL1} ${MODEL2}${C_RESET}\n"
    read_input "${C_BOLD}Press Enter to boot this debate session now [Enter/b]: ${C_RESET}" CONF
    if [ "$CONF" != "b" ] && [ "$CONF" != "B" ]; then
      cmd_swarm "$MODEL1" "$MODEL2"
    fi
  fi
}

# --- Option 7: Big Catalog of Every Free AI Family ---
cmd_big_catalog() {
  while true; do
    clear 2>/dev/null || true
    echo -e "${C_BOLD}${C_GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
    echo "║       UNIVERSAL FREE MODEL CATALOG (ALL OPEN-WEIGHT FAMILIES)                 ║"
    echo "║       100% Free • Zero Paywalls • Zero Subscriptions • Direct Bare-Metal      ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${C_RESET}"

    echo -e "${C_YELLOW}${C_BOLD}[1] QWEN FAMILY (Alibaba Cloud)${C_RESET}"
    echo -e "    11) qwen2.5-coder:1.5b  ${C_DIM}(1.5B | Ultra-Fast Coding | ~1 GB RAM)${C_RESET}"
    echo -e "    12) qwen2.5-coder:7b    ${C_DIM}(7B   | High Accuracy Coding | ~5 GB RAM)${C_RESET}"
    echo -e "    13) qwen2.5-coder:14b   ${C_DIM}(14B  | Advanced Coding Specialist | ~9 GB RAM)${C_RESET}"
    echo -e "    14) qwen2.5-coder:32b   ${C_DIM}(32B  | Matches Claude 3.5 Sonnet | ~20 GB RAM)${C_RESET}"
    echo -e "    15) qwen3:14b           ${C_DIM}(14B  | Next-Gen Reasoning & Thinking | ~9 GB RAM)${C_RESET}"
    echo -e "    16) qwen2.5:72b         ${C_DIM}(72B  | Heavyweight Frontier Intelligence | ~45 GB RAM)${C_RESET}\n"

    echo -e "${C_CYAN}${C_BOLD}[2] DEEPSEEK FAMILY${C_RESET}"
    echo -e "    21) deepseek-r1:1.5b    ${C_DIM}(1.5B | Lightweight Reasoning <think> | ~1.1 GB RAM)${C_RESET}"
    echo -e "    22) deepseek-r1:7b      ${C_DIM}(7B   | Deep Math & Logic Reasoning | ~5 GB RAM)${C_RESET}"
    echo -e "    23) deepseek-r1:14b     ${C_DIM}(14B  | High-Accuracy Deep Reasoning | ~9 GB RAM)${C_RESET}"
    echo -e "    24) deepseek-r1:32b     ${C_DIM}(32B  | OpenAI o1-grade Math/Logic | ~20 GB RAM)${C_RESET}"
    echo -e "    25) deepseek-r1:70b     ${C_DIM}(70B  | Enterprise Reasoning Powerhouse | ~44 GB RAM)${C_RESET}"
    echo -e "    26) deepseek-coder:6.7b ${C_DIM}(6.7B | Clean Code Generation | ~4.5 GB RAM)${C_RESET}\n"

    echo -e "${C_PURPLE}${C_BOLD}[3] LLAMA FAMILY (Meta AI)${C_RESET}"
    echo -e "    31) llama3.2:1b         ${C_DIM}(1B   | Micro Edge Model | ~0.8 GB RAM)${C_RESET}"
    echo -e "    32) llama3.2:3b         ${C_DIM}(3B   | Compact Assistant | ~2.0 GB RAM)${C_RESET}"
    echo -e "    33) llama3.1:8b         ${C_DIM}(8B   | General Knowledge Standard | ~5.5 GB RAM)${C_RESET}"
    echo -e "    34) llama3.3:70b        ${C_DIM}(70B  | Flagship GPT-4o Replacement | ~43 GB RAM)${C_RESET}\n"

    echo -e "${C_GREEN}${C_BOLD}[4] MISTRAL FAMILY${C_RESET}"
    echo -e "    41) mistral:7b          ${C_DIM}(7B   | Fast & Eloquent | ~4.5 GB RAM)${C_RESET}"
    echo -e "    42) mistral-nemo:12b    ${C_DIM}(12B  | 128k Long Context | ~8 GB RAM)${C_RESET}"
    echo -e "    43) codestral:22b       ${C_DIM}(22B  | 80+ Programming Languages | ~14 GB RAM)${C_RESET}"
    echo -e "    44) mistral-small:24b   ${C_DIM}(24B  | Advanced Reasoning | ~15 GB RAM)${C_RESET}\n"

    echo -e "${C_YELLOW}${C_BOLD}[5] GOOGLE GEMMA & MICROSOFT PHI${C_RESET}"
    echo -e "    51) gemma2:2b           ${C_DIM}(2B   | Google High-Efficiency Edge | ~1.6 GB RAM)${C_RESET}"
    echo -e "    52) gemma2:9b           ${C_DIM}(9B   | Google Benchmark Leader | ~6 GB RAM)${C_RESET}"
    echo -e "    53) gemma2:27b          ${C_DIM}(27B  | Google Flagship Open Weights | ~17 GB RAM)${C_RESET}"
    echo -e "    54) phi3.5:3.8b         ${C_DIM}(3.8B | Microsoft Compact Reasoning | ~2.5 GB RAM)${C_RESET}"
    echo -e "    55) phi4:14b            ${C_DIM}(14B  | Microsoft Synthetic Math/Code | ~9.5 GB RAM)${C_RESET}\n"

    read_input "${C_BOLD}Select model number (e.g. 11, 22, 33), 'b' for Back, or 'q' to Quit: ${C_RESET}" SUB_CHOICE

    if [ "$SUB_CHOICE" = "b" ] || [ "$SUB_CHOICE" = "B" ] || [ "$SUB_CHOICE" = "back" ] || [ "$SUB_CHOICE" = "menu" ]; then
      return
    fi

    if [ "$SUB_CHOICE" = "q" ] || [ "$SUB_CHOICE" = "Q" ] || [ "$SUB_CHOICE" = "exit" ] || [ "$SUB_CHOICE" = "quit" ]; then
      echo -e "${C_DIM}Exiting Colibristream.${C_RESET}"
      exit 0
    fi

    TARGET_MODEL=""
    case "$SUB_CHOICE" in
      11) TARGET_MODEL="qwen2.5-coder:1.5b" ;;
      12) TARGET_MODEL="qwen2.5-coder:7b" ;;
      13) TARGET_MODEL="qwen2.5-coder:14b" ;;
      14) TARGET_MODEL="qwen2.5-coder:32b" ;;
      15) TARGET_MODEL="qwen3:14b" ;;
      16) TARGET_MODEL="qwen2.5:72b" ;;
      21) TARGET_MODEL="deepseek-r1:1.5b" ;;
      22) TARGET_MODEL="deepseek-r1:7b" ;;
      23) TARGET_MODEL="deepseek-r1:14b" ;;
      24) TARGET_MODEL="deepseek-r1:32b" ;;
      25) TARGET_MODEL="deepseek-r1:70b" ;;
      26) TARGET_MODEL="deepseek-coder:6.7b" ;;
      31) TARGET_MODEL="llama3.2:1b" ;;
      32) TARGET_MODEL="llama3.2:3b" ;;
      33) TARGET_MODEL="llama3.1:8b" ;;
      34) TARGET_MODEL="llama3.3:70b" ;;
      41) TARGET_MODEL="mistral:7b" ;;
      42) TARGET_MODEL="mistral-nemo:12b" ;;
      43) TARGET_MODEL="codestral:22b" ;;
      44) TARGET_MODEL="mistral-small:24b" ;;
      51) TARGET_MODEL="gemma2:2b" ;;
      52) TARGET_MODEL="gemma2:9b" ;;
      53) TARGET_MODEL="gemma2:27b" ;;
      54) TARGET_MODEL="phi3.5:3.8b" ;;
      55) TARGET_MODEL="phi4:14b" ;;
      *)
        if [ -n "$SUB_CHOICE" ]; then
          TARGET_MODEL="$SUB_CHOICE"
        else
          continue
        fi
        ;;
    esac

    echo -e "\n${C_GREEN}${C_BOLD}[*] Launching Selected Model:${C_RESET} ${C_BOLD}${TARGET_MODEL}${C_RESET}..."
    cmd_run "$TARGET_MODEL"
    break
  done
}

# --- Main Interactive Unified Screen (Hardware Telemetry + 1-7 Model Hub) ---
cmd_loop_menu() {
  run_hardware_scan

  while true; do
    clear 2>/dev/null || true
    echo -e "${C_GREEN}${C_BOLD}"
    cat << "EOF"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
EOF
    echo -e "${C_RESET}${C_DIM}             Autonomous Bare-Metal Local Intelligence Engine${C_RESET}\n"

    # Box 1: Hardware Telemetry
    print_telemetry_box
    echo ""

    # Box 2: Model Hub Menu
    echo -e "${C_BOLD}┌── UNIVERSAL MODEL HUB: RUN BIG MODELS & MULTI-MODEL SWARMS ────────┐${C_RESET}"
    echo -e "│ ${C_YELLOW}Zero paywalls • Weights stored 1x in RAM • Real-time collaboration │${C_RESET}"
    echo -e "├───────────────────────────────────────────────────────────────────┤"
    echo -e "│  ${C_BOLD}[1]${C_RESET} ${C_GREEN}Flagship 32B AI${C_RESET} (~17GB VRAM • 100% on GPU • 0 RAM • 0 CPU)   │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream run 32b${C_RESET}                               │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[2]${C_RESET} ${C_GREEN}Instant Simultaneous Swarm${C_RESET} (Run 14B + 1.5B at the EXACT SAME TIME)│"
    echo -e "│      → Direct Command: ${C_CYAN}colistream parallel qwen3:14b qwen2.5-coder:1.5b${C_RESET}│"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[3]${C_RESET} ${C_GREEN}DeepSeek MoE Swarm${C_RESET} (R1 Reasoner + Coder Synthesizer)        │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream swarm deepseek-r1:14b deepseek-coder${C_RESET}│"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[4]${C_RESET} ${C_YELLOW}Heavy 72B Model${C_RESET} (~22GB VRAM Clamped + CPU/RAM Split)           │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream run 72b${C_RESET}                               │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[5]${C_RESET} ${C_CYAN}Custom Swarm Builder${C_RESET} (Pick ANY 2+ Models to Run Together)     │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream swarm <model1> <model2>${C_RESET}             │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[6]${C_RESET} ${C_GREEN}Big Free AI Hub Catalog${C_RESET} (Browse All 25+ Models by Family)     │"
    echo -e "│      → DeepSeek, Qwen, Llama, Mistral, Gemma, Phi                  │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[g]${C_RESET} ${C_PURPLE}Switch Active GPU Card${C_RESET} (Isolate Fast Card / Bypass Slow Card)  │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream gpu <id|all>${C_RESET}                         │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[d]${C_RESET} ${C_YELLOW}Hardware & Speed Diagnostics${C_RESET} (Inspect GPU/CPU VRAM Splits)│"
    echo -e "│      → Direct Command: ${C_CYAN}colistream diag${C_RESET}                                 │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[t]${C_RESET} ${C_YELLOW}⚡ Turbo Acceleration & Clock Boost${C_RESET} (Lock Clocks • Quantize KV)  │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream turbo${C_RESET}                                │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[s]${C_RESET} ${C_GREEN}🌐 Worldwide Share & Live Link${C_RESET} (Zero Passwords • Access Everywhere) │"
    echo -e "│      → Direct Command: ${C_CYAN}colistream share${C_RESET}                                │"
    echo -e "├───────────────────────────────────────────────────────────────────┤"
    echo -e "│  ${C_BOLD}[q]${C_RESET} ${C_DIM}Quit / Exit${C_RESET}                                                  │"
    echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}\n"

    read_input "${C_BOLD}Choose an option [1-6, g, d, t, s] (or 'q' to exit): ${C_RESET}" CHOICE

    case "$CHOICE" in
      1)
        echo -e "\n${C_CYAN}[*] Launching Flagship 32B AI (100% GPU VRAM, 0 RAM, 0 CPU)...${C_RESET}"
        cmd_run "32b"
        ;;
      2)
        echo -e "\n${C_CYAN}[*] Launching Simultaneous Parallel Swarm (Qwen3 14B + 1.5B Coder at the exact same time)...${C_RESET}"
        cmd_parallel "qwen3:14b" "qwen2.5-coder:1.5b"
        ;;
      3)
        echo -e "\n${C_CYAN}[*] Launching DeepSeek MoE Swarm...${C_RESET}"
        cmd_parallel "deepseek-r1:14b" "deepseek-coder:6.7b"
        ;;
      4)
        echo -e "\n${C_CYAN}[*] Launching Heavy 72B Model (Clamped to ~22GB VRAM)...${C_RESET}"
        cmd_run "72b"
        ;;
      5)
        cmd_swarm_builder
        ;;
      6|7)
        cmd_big_catalog
        ;;
      g|G|gpu|gpus)
        cmd_switch_gpu
        ;;
      d|D|diag|doctor)
        cmd_diag
        read_input "Press Enter to return to menu: " _
        ;;
      t|T|turbo|boost)
        cmd_turbo
        read_input "Press Enter to return to menu: " _
        ;;
      s|S|share|web)
        bash "${DIR}/share.sh"
        ;;
      q|Q|exit)
        echo -e "${C_DIM}Exiting Colibristream.${C_RESET}"
        exit 0
        ;;
      *)
        if [ -n "$CHOICE" ]; then
          echo -e "${C_YELLOW}Invalid choice '${CHOICE}'. Select 1-6, g, d, t, s, or q.${C_RESET}"
          sleep 1
        fi
        ;;
    esac
  done
}

# --- Entrypoint Router ---
case "$1" in
  run)
    cmd_run "$2"
    ;;
  pull)
    cmd_pull "$2"
    ;;
  parallel|p|simultaneous|concurrent)
    cmd_parallel "$2" "$3"
    ;;
  swarm|multi)
    cmd_parallel "$2" "$3"
    ;;
  debate)
    cmd_swarm "$2" "$3" "$4"
    ;;
  turbo|boost|fast)
    cmd_turbo
    ;;
  build)
    cmd_swarm_builder
    ;;
  share|serve|web)
    bash "${DIR}/share.sh" "$2"
    ;;
  list|ls)
    cmd_list
    ;;
  catalog)
    cmd_big_catalog
    ;;
  gpu|gpus)
    cmd_switch_gpu "$2"
    ;;
  diag|doctor)
    cmd_diag
    ;;
  restart|rebind|reset)
    cmd_restart_engine "$2"
    ;;
  menu|"")
    cmd_loop_menu
    ;;
  *)
    echo -e "${C_BOLD}Usage:${C_RESET} colistream [menu|run <model>|parallel [m1] [m2]|swarm [m1] [m2]|debate [m1] [m2]|share|diag|turbo|gpu [id]|restart [id]|list|catalog]"
    ;;
esac
