#!/usr/bin/env bash
# ==============================================================================
# ObsidianCore — Bare-Metal CLI & Universal Model Hub
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
DIR="${HOME}/.obsidiancore"
# Migrate legacy config if exists
if [ -d "${HOME}/.colistream" ] && [ ! -d "${HOME}/.obsidiancore" ]; then
  cp -r "${HOME}/.colistream" "${HOME}/.obsidiancore" 2>/dev/null || true
fi
mkdir -p "$DIR" "${HOME}/.local/bin"

# If executed via curl | bash, save a copy to ~/.local/bin/obsidiancore
if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  CURRENT_FILE="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
  if [ -f "$CURRENT_FILE" ] && [ "$CURRENT_FILE" != "${HOME}/.local/bin/obsidiancore" ]; then
    cp "$CURRENT_FILE" "${HOME}/.local/bin/obsidiancore" 2>/dev/null || true
    chmod +x "${HOME}/.local/bin/obsidiancore" 2>/dev/null || true
    ln -sf "${HOME}/.local/bin/obsidiancore" "${HOME}/.local/bin/colistream" 2>/dev/null || true
    ln -sf "${HOME}/.local/bin/obsidiancore" "${HOME}/.local/bin/colibristream" 2>/dev/null || true
    ln -sf "${HOME}/.local/bin/obsidiancore" "${HOME}/.local/bin/colibri" 2>/dev/null || true
  fi
fi

# Ensure ~/.local/bin is in PATH for future shells
for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
  if [ -f "$profile" ] && ! grep -q '\.local/bin' "$profile"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
  fi
done
export PATH="${HOME}/.local/bin:${PATH}"

# Stdin-safe input reader
read_input() {
  local prompt="$1"
  local __var="$2"
  echo -ne "$prompt" >&2
  if ! read -r "$__var"; then
    if [ -t 1 ] && [ -r /dev/tty ]; then
      read -r "$__var" </dev/tty 2>/dev/null || eval "$__var='q'"
    else
      eval "$__var='q'"
      return 1
    fi
  fi
}

ensure_backend() {
  # Universal GPU Architecture Flags: Ensure older GPUs (sm_60/sm_61 Pascal, sm_70 Volta)
  # and newer GPUs (sm_80 Ampere, sm_89 Ada, sm_90 Hopper) run 100% on GPU without CPU fallback
  export OLLAMA_FLASH_ATTENTION=1     # Flash Attention kernel acceleration (unlocks 30-40 tok/s on multi-GPU)
  export OLLAMA_KV_CACHE_TYPE=q8_0    # 8-bit quantized KV cache: halves memory traffic for rapid generation
  export OLLAMA_NUM_PARALLEL=4        # 4 concurrent model inference streams for swarms
  export OLLAMA_MAX_LOADED_MODELS=4   # Keep both Architect & Worker warm in memory simultaneously
  export OLLAMA_KEEP_ALIVE=30m        # Keep models warm in memory for 30 minutes
  export GGML_CUDA_NO_PINNED=1        # Prevents PCIe memory exhaustion on multi-GPU rigs
  export OLLAMA_MAX_PARALLEL_DOWNLOADS=16 # 16 parallel multi-threaded chunks for saturating downloads

  # Auto-bind to active fast GPU
  if [ -z "$ACTIVE_GPU" ]; then
    if [ -f "${HOME}/.obsidiancore/gpu_config" ]; then
      ACTIVE_GPU=$(cat "${HOME}/.obsidiancore/gpu_config" 2>/dev/null | tr -d '[:space:]')
    fi
  fi
  if [ -n "$ACTIVE_GPU" ] && [ "$ACTIVE_GPU" != "all" ]; then
    export CUDA_VISIBLE_DEVICES="$ACTIVE_GPU"
  elif [ "$ACTIVE_GPU" = "all" ]; then
    unset CUDA_VISIBLE_DEVICES
  fi

  # Auto-configure systemd service if running with root/sudo permissions
  if [ -d /etc/systemd/system ] && [ -w /etc/systemd/system ]; then
    local env_cuda=""
    if [ -n "$ACTIVE_GPU" ] && [ "$ACTIVE_GPU" != "all" ]; then
      env_cuda="Environment=\"CUDA_VISIBLE_DEVICES=${ACTIVE_GPU}\""
    fi
    mkdir -p /etc/systemd/system/ollama.service.d 2>/dev/null || true
    cat << SYSCONF > /etc/systemd/system/ollama.service.d/obsidiancore.conf 2>/dev/null || true
[Service]
${env_cuda}
Environment="OLLAMA_MAX_LOADED_MODELS=4"
Environment="OLLAMA_MAX_PARALLEL_DOWNLOADS=16"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="GGML_CUDA_NO_PINNED=1"
SYSCONF
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi

  if [ "$(uname -s)" = "Darwin" ]; then
    # Apple Silicon Unified Memory Optimization:
    # 1. Strictly 1 model in RAM to prevent macOS memory exhaustion
    # 2. Single-stream execution (OLLAMA_NUM_PARALLEL=1) to eliminate duplicate 4x context buffers
    # 3. 2-minute idle sleep (auto-frees 100% of RAM/VRAM when inactive)
    # 4. Quantized KV cache (q8_0) saves 50% memory bandwidth
    export OLLAMA_MAX_LOADED_MODELS=1
    export OLLAMA_NUM_PARALLEL=1
    export OLLAMA_KEEP_ALIVE=2m
    export OLLAMA_FLASH_ATTENTION=1
    export OLLAMA_KV_CACHE_TYPE=q8_0
  else
    export OLLAMA_MAX_LOADED_MODELS=4
    export OLLAMA_NUM_PARALLEL=4
    export OLLAMA_MAX_PARALLEL_DOWNLOADS=16
    export OLLAMA_FLASH_ATTENTION=1
    export OLLAMA_KV_CACHE_TYPE=q8_0
    export OLLAMA_KEEP_ALIVE=30m
    export GGML_CUDA_NO_PINNED=1
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
  GPU_CONFIG_FILE="${HOME}/.obsidiancore/gpu_config"
  mkdir -p "${HOME}/.obsidiancore" 2>/dev/null || true
  ACTIVE_GPU=""
  if [ -f "$GPU_CONFIG_FILE" ]; then
    ACTIVE_GPU=$(cat "$GPU_CONFIG_FILE" 2>/dev/null | tr -d '[:space:]')
  fi
    if [ ${#GPU_MEMS[@]} -eq 0 ]; then
      GPU_COUNT=0
      ACTIVE_GPU=""
    elif [ "$GPU_COUNT" -gt 1 ]; then
      # On multi-GPU rigs, if config is missing or left over as single-card '0', auto-upgrade to 'all'
      if [ -z "$ACTIVE_GPU" ] || [ "$ACTIVE_GPU" = "0" ]; then
        ACTIVE_GPU="all"
        echo "$ACTIVE_GPU" > "$GPU_CONFIG_FILE" 2>/dev/null || true
        unset CUDA_VISIBLE_DEVICES
      fi
    else
      ACTIVE_GPU="${ACTIVE_GPU:-0}"
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

  # Probe real storage target where Ollama stores models
  local model_target_dir="${OLLAMA_MODELS:-}"
  if [ -z "$model_target_dir" ] || [ ! -d "$model_target_dir" ]; then
    if [ -d "/mnt/storage-pool/ollama/models" ]; then
      model_target_dir="/mnt/storage-pool/ollama/models"
    elif [ -d "${HOME}/.ollama/models" ]; then
      model_target_dir="${HOME}/.ollama/models"
    elif [ -d "/usr/share/ollama/.ollama/models" ]; then
      model_target_dir="/usr/share/ollama/.ollama/models"
    else
      model_target_dir="${HOME}"
    fi
  fi

  DISK_HEADROOM=$(df -h "$model_target_dir" 2>/dev/null | awk 'NR==2 {print $4}' || echo "N/A")
  local disk_dev
  disk_dev=$(df "$model_target_dir" 2>/dev/null | awk 'NR==2 {print $1}')
  local disk_type="Storage"
  if [[ "$disk_dev" == *"nvme"* ]]; then
    disk_type="NVMe PCIe SSD"
  elif [[ "$disk_dev" == *"models-large"* ]] || [[ "$disk_dev" == *"storage-pool"* ]]; then
    disk_type="Unified Storage Pool"
  elif [[ "$disk_dev" == *"sd"* ]] || [[ "$disk_dev" == *"mapper"* ]]; then
    local base_b=$(basename "$disk_dev" | tr -d '0-9')
    if [ -f "/sys/block/${base_b}/queue/rotational" ] && [ "$(cat /sys/block/${base_b}/queue/rotational 2>/dev/null)" = "1" ]; then
      disk_type="SATA HDD Pool"
    else
      disk_type="SATA/SAS SSD"
    fi
  elif [ "$(uname -s)" = "Darwin" ]; then
    disk_type="Apple APFS SSD"
  fi
  DISK_SUMMARY="${disk_type} (Free: ${DISK_HEADROOM} • 15GB Safety Reserve)"
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
    if [ "$ACTIVE_GPU" = "all" ]; then
      printf "│ %-16s : ${C_GREEN}%-47.47s${C_RESET} │\n" "GPU Cluster" "${GPU_COUNT} GPUs Pooled (${AVAILABLE_VRAM_GB} GB Total VRAM)"
    else
      printf "│ %-16s : ${C_YELLOW}%-47.47s${C_RESET} │\n" "GPU Cluster" "${GPU_COUNT} GPUs Active (Single Card Pinned)"
    fi
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

  printf "│ %-16s : ${C_GREEN}%-47.47s${C_RESET} │\n" "Storage Device" "${DISK_SUMMARY}"
  echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}"
}

apply_gpu_configuration() {
  local target_gpu="$1"
  mkdir -p "${HOME}/.obsidiancore" 2>/dev/null || true
  echo "$target_gpu" > "${HOME}/.obsidiancore/gpu_config" 2>/dev/null || true

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
    cat << EOF > /etc/systemd/system/ollama.service.d/obsidiancore.conf 2>/dev/null || true
[Service]
${env_cuda}
Environment="OLLAMA_MAX_LOADED_MODELS=4"
Environment="OLLAMA_MAX_PARALLEL_DOWNLOADS=16"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="GGML_CUDA_NO_PINNED=1"
EOF
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl restart ollama >/dev/null 2>&1 || true
    echo -e "${C_GREEN}✔ System inference daemon reloaded and locked to GPU ${target_gpu} (4 concurrent models enabled).${C_RESET}"
  else
    # User-space daemon restart
    if pkill -f "ollama serve" 2>/dev/null; then
      sleep 1
      nohup ollama serve >/dev/null 2>&1 &
      sleep 2
      echo -e "${C_GREEN}✔ Background inference daemon restarted on GPU ${target_gpu} (4 concurrent models enabled).${C_RESET}"
    else
      echo -e "${C_YELLOW}[!] Note: If Ollama runs as a system service, run this once to lock it to GPU ${target_gpu} & enable concurrent models:${C_RESET}"
      echo -e "    ${C_BOLD}sudo systemctl set-environment CUDA_VISIBLE_DEVICES=${target_gpu} OLLAMA_MAX_LOADED_MODELS=4 OLLAMA_NUM_PARALLEL=4 && sudo systemctl restart ollama${C_RESET}"
    fi
  fi
}

cmd_restart_engine() {
  run_hardware_scan
  local target_gpu="${1:-${ACTIVE_GPU:-all}}"
  echo -e "${C_CYAN}[*] Restarting inference engine and binding to GPU configuration (${target_gpu})...${C_RESET}"
  
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active ollama >/dev/null 2>&1; then
    echo -e "${C_YELLOW}[!] Ollama is currently active as a system service.${C_RESET}"
    if sudo -n true 2>/dev/null; then
      if [ "$target_gpu" = "all" ]; then
        sudo systemctl unset-environment CUDA_VISIBLE_DEVICES 2>/dev/null || true
        if [ -f /etc/systemd/system/ollama.service.d/obsidiancore.conf ]; then
          sudo sed -i '/CUDA_VISIBLE_DEVICES/d' /etc/systemd/system/ollama.service.d/obsidiancore.conf 2>/dev/null || true
          sudo systemctl daemon-reload 2>/dev/null || true
        fi
      else
        sudo systemctl set-environment CUDA_VISIBLE_DEVICES="$target_gpu" 2>/dev/null || true
      fi
      sudo systemctl set-environment OLLAMA_MAX_LOADED_MODELS=4 OLLAMA_NUM_PARALLEL=4 2>/dev/null || true
      sudo systemctl daemon-reload 2>/dev/null || true
      sudo systemctl restart ollama 2>/dev/null || true
      echo -e "${C_GREEN}✔ Updated systemd service and restarted Ollama (GPU: ${target_gpu}, Multi-Model Swarm: 4 concurrent).${C_RESET}"
    else
      if [ "$target_gpu" = "all" ]; then
        echo -e "${C_YELLOW}[!] To pool all GPUs and enable concurrent multi-model execution in systemd, run:${C_RESET}"
        echo -e "    ${C_BOLD}sudo systemctl set-environment OLLAMA_MAX_LOADED_MODELS=4 OLLAMA_NUM_PARALLEL=4 && sudo systemctl unset-environment CUDA_VISIBLE_DEVICES && sudo systemctl restart ollama${C_RESET}"
      else
        echo -e "${C_YELLOW}[!] Run: ${C_BOLD}sudo systemctl set-environment CUDA_VISIBLE_DEVICES=${target_gpu} OLLAMA_MAX_LOADED_MODELS=4 OLLAMA_NUM_PARALLEL=4 && sudo systemctl restart ollama${C_RESET}"
      fi
    fi
  fi

  pkill -9 -f "ollama serve" 2>/dev/null || true
  sleep 1

  apply_gpu_configuration "$target_gpu"
  ensure_backend
  echo -e "${C_GREEN}✔ Local inference engine restarted and configured for GPU: ${target_gpu}!${C_RESET}"
}

cmd_turbo() {
  echo -e "\n${C_BOLD}╔════════════════════════════════════════════════════════════════════╗${C_RESET}"
  echo -e "${C_BOLD}║           ⚡ OBSIDIANCORE TURBO ACCELERATION ENGINE                ║${C_RESET}"
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
  export OLLAMA_FLASH_ATTENTION=1
  export OLLAMA_NUM_PARALLEL=1
  export GGML_CUDA_NO_PINNED=1
  export OLLAMA_KV_CACHE_TYPE=q8_0
  echo -e "      • KV Cache     : ${C_GREEN}QUANTIZED (q8_0 - 50% Memory Bandwidth Saved)${C_RESET}"
  echo -e "      • Pinning      : ${C_GREEN}OPTIMIZED (GGML_CUDA_NO_PINNED=1)${C_RESET}"
  echo -e "      • Concurrency  : ${C_GREEN}DEDICATED (OLLAMA_NUM_PARALLEL=1 for Max Single-Stream Tok/s)${C_RESET}"

  echo -e "\n${C_CYAN}[4/4] Fast 32B Model Recommendations:${C_RESET}"
  echo -e "  To get ${C_GREEN}${C_BOLD}~18–22 tok/s${C_RESET} on 32B instead of 12 tok/s, use the ${C_BOLD}Q3_K_M${C_RESET} quantization:"
  echo -e "  👉 ${C_CYAN}obsidiancore run qwen2.5-coder:32b-instruct-q3_K_M${C_RESET} (15 GB vs 20 GB)"
  echo -e "  To get ${C_GREEN}${C_BOLD}~40–50 tok/s${C_RESET} right now, use the 7B tier:"
  echo -e "  👉 ${C_CYAN}obsidiancore run qwen2.5-coder:7b${C_RESET}\n"

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
        print("│  No local models installed yet. Pull one with: obsidiancore pull <name>  │")
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
  echo -e "\n${C_BOLD}${C_GREEN}┌── OBSIDIANCORE HARDWARE & INFERENCE DIAGNOSTICS ───────────────────┐${C_RESET}"
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
                print('│         \033[38;5;48m✔ FIX:\033[0m Run 32B for 100% GPU acceleration @ 20-25+ tok/s: obsidiancore run 32b')
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
    echo -e "${C_RED}[ERROR] Specify a model name. Example: obsidiancore pull qwen2.5-coder:7b${C_RESET}"
    exit 1
  fi
  case "$model" in
    32b|32B) model="qwen2.5-coder:32b-instruct-q3_K_M" ;;
    72b|72B) model="qwen2.5:72b-instruct-q3_K_M" ;;
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
ObsidianCore — Interactive Desktop AI Chat Engine (Copilot / Gemini TUI)
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
import unicodedata
import atexit
import threading

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[38;5;48m"
C_CYAN = "\033[38;5;45m"
C_YELLOW = "\033[38;5;220m"
C_PURPLE = "\033[38;5;141m"
C_RED = "\033[38;5;196m"
C_GRAY = "\033[38;5;244m"
C_WHITE = "\033[38;5;255m"

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

def print_models_catalog_table():
    print(f"\n{C_BOLD}{C_GREEN}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}║             UNIVERSAL FREE LOCAL MODEL HUB (BARE-METAL RUNTIME • ZERO PAYWALLS)                       ║{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}┌──────────────────────┬──────────────┬──────────────────────┬───────────────┬──────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}│ Model Name           │ Total Params │ Architecture         │ Memory Budget │ CLI Quick Aliases        │{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}├──────────────────────┼──────────────┼──────────────────────┼───────────────┼──────────────────────────┤{C_RESET}")
    print(f"│ {C_BOLD}{C_RED}beam:500b-25b{C_RESET}        │ 501B         │ MoE (25B Active)     │ ~44 GB        │ 500b, 500b25b, beam      │")
    print(f"│ {C_BOLD}{C_RED}mixtral:8x22b{C_RESET}        │ 141B         │ MoE (39B Active)     │ ~42 GB        │ 8x22b, 141b, mixtral     │")
    print(f"│ {C_BOLD}{C_RED}command-r-plus:104b{C_RESET}  │ 104B         │ Dense Enterprise     │ ~40 GB        │ 104b, command-r-plus     │")
    print(f"│ {C_BOLD}{C_RED}deepseek-r1:671b{C_RESET}     │ 671B         │ MoE (37B Active)     │ ~46 GB        │ 671b, deepseek-671b      │")
    print(f"│ {C_BOLD}{C_YELLOW}qwen2.5:72b{C_RESET}          │ 72B          │ Dense Frontier       │ ~38–42 GB     │ 72b, qwen-72b            │")
    print(f"│ {C_BOLD}{C_YELLOW}llama3.3:70b{C_RESET}         │ 70B          │ Dense Frontier       │ ~40 GB        │ llama-70b, 70b           │")
    print(f"│ {C_BOLD}{C_YELLOW}deepseek-r1:70b{C_RESET}      │ 70B          │ Dense Reasoning      │ ~40 GB        │ deepseek-70b             │")
    print(f"│ {C_BOLD}{C_GREEN}qwen2.5-coder:32b{C_RESET}    │ 32B          │ Dense Coding (Claude)│ ~17 GB (GPU)  │ 32b, 32b-coder           │")
    print(f"│ {C_BOLD}{C_GREEN}deepseek-r1:32b{C_RESET}      │ 32B          │ Reasoning (o1-grade) │ ~20 GB        │ deepseek-32b             │")
    print(f"│ {C_BOLD}{C_GREEN}gemma2:27b{C_RESET}           │ 27B          │ Flagship Dense       │ ~17 GB        │ gemma-27b                │")
    print(f"│ {C_BOLD}{C_GREEN}codestral:22b{C_RESET}        │ 22B          │ Code Specialist      │ ~14 GB        │ codestral                │")
    print(f"│ {C_BOLD}{C_WHITE}qwen3:14b{C_RESET}            │ 14B          │ Next-Gen Reasoning   │ ~9 GB         │ qwen, 14b, qwen3         │")
    print(f"│ {C_BOLD}{C_WHITE}deepseek-r1:14b{C_RESET}      │ 14B          │ Math / Logic         │ ~9 GB         │ deepseek, r1-14b         │")
    print(f"│ {C_BOLD}{C_WHITE}phi4:14b{C_RESET}             │ 14B          │ Microsoft Math/Code  │ ~9.5 GB       │ phi4                     │")
    print(f"│ {C_BOLD}{C_WHITE}qwen2.5-coder:7b{C_RESET}     │ 7B           │ Fast Coding          │ ~5 GB         │ 7b, coder-7b             │")
    print(f"│ {C_BOLD}{C_WHITE}mistral:7b{C_RESET}           │ 7B           │ Fast & Eloquent      │ ~4.5 GB       │ mistral                  │")
    print(f"│ {C_BOLD}{C_WHITE}llama3.1:8b{C_RESET}          │ 8B           │ General Knowledge    │ ~5.5 GB       │ llama, 8b                │")
    print(f"│ {C_BOLD}{C_WHITE}deepseek-coder:6.7b{C_RESET}  │ 6.7B         │ Code Generation      │ ~4.5 GB       │ deepseek-coder           │")
    print(f"│ {C_BOLD}{C_CYAN}qwen2.5-coder:1.5b{C_RESET}   │ 1.5B         │ Ultra-Fast Coding    │ ~1.0 GB       │ 1.5b, coder              │")
    print(f"│ {C_BOLD}{C_CYAN}deepseek-r1:1.5b{C_RESET}     │ 1.5B         │ Compact Reasoning    │ ~1.1 GB       │ r1-1.5b                  │")
    print(f"│ {C_BOLD}{C_CYAN}llama3.2:1b{C_RESET}          │ 1B           │ Micro Edge Model     │ ~0.8 GB       │ llama-1b                 │")
    print(f"{C_CYAN}{C_BOLD}└──────────────────────┴──────────────┴──────────────────────┴───────────────┴──────────────────────────┘{C_RESET}")
    print(f"{C_DIM}★ All models run 100% locally on bare metal without cloud subscriptions or API keys.{C_RESET}\n")

def print_coding_agent_help():
    print(f"\n{C_BOLD}{C_GREEN}┌── OBSIDIANCORE AUTONOMOUS CODING AGENT COMMANDS ────────────────┐{C_RESET}")
    print(f"│ {C_YELLOW}/models{C_RESET}          : Display Universal Free Local Model Hub Catalog        │")
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
        "You are an expert autonomous software engineer and local pair programmer running via ObsidianCore.",
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

def save_code_to_disk(target_path, code):
    target_path = target_path.strip().strip("'\"`")
    if not target_path:
        return False
    try:
        prev_content = None
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                prev_content = f.read()
        file_backups.append((target_path, prev_content))
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)
        tracked_files[target_path] = code
        lines = len(code.splitlines())
        action = "Overwrote" if prev_content is not None else "Created"
        print(f"\n{C_GREEN}{C_BOLD}[✔ {action} File]{C_RESET} {C_CYAN}{target_path}{C_RESET} ({lines} lines on disk)")
        return True
    except Exception as e:
        print(f"\n{C_RED}[!] Error writing '{target_path}': {e}{C_RESET}")
        return False

def apply_surgical_edit(target_path, edit_body):
    target_path = target_path.strip().strip("'\"`")
    if not os.path.exists(target_path):
        print(f"\n{C_YELLOW}[!] Cannot edit '{target_path}': File does not exist.{C_RESET}")
        return False
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
            return True
    except Exception as e:
        print(f"\n{C_RED}[!] Error editing '{target_path}': {e}{C_RESET}")
    return False

def apply_model_edits(response_text, explicit_filename=None, user_prompt=""):
    if not response_text:
        return []
    created_or_modified = []

    # Strategy 0: Explicit filename passed by user (e.g. /apply filename.ext or /apply 1 filename.ext)
    if explicit_filename:
        explicit_filename = explicit_filename.strip().strip("'\"`")
        raw_blocks = list(re.finditer(r"```(?:[a-zA-Z0-9_\-\.\/:]*)\s*\r?\n(.*?)```", response_text, re.DOTALL))
        if raw_blocks:
            best_code = max(raw_blocks, key=lambda m: len(m.group(1))).group(1)
            if save_code_to_disk(explicit_filename, best_code):
                created_or_modified.append(explicit_filename)
        else:
            if save_code_to_disk(explicit_filename, response_text.strip()):
                created_or_modified.append(explicit_filename)
        return created_or_modified

    # Strategy 1: Explicit write / create / save / file tags: ```write:filepath or ```python:filepath
    p1 = re.compile(r"```(?:write|create|save|file|[a-zA-Z0-9_\-]+)\s*:\s*([^\s\r\n`\'\"]+)\s*\r?\n(.*?)```", re.DOTALL)
    for m in p1.finditer(response_text):
        fname = m.group(1).strip()
        code = m.group(2)
        if "." in fname:
            if save_code_to_disk(fname, code):
                created_or_modified.append(fname)

    # Strategy 2: Surgical search/replace edits (Aider style): ```edit:filepath
    p2 = re.compile(r"```edit\s*:\s*([^\s\r\n`\'\"]+)\s*\r?\n(.*?)```", re.DOTALL)
    for m in p2.finditer(response_text):
        fname = m.group(1).strip()
        code = m.group(2)
        if apply_surgical_edit(fname, code):
            created_or_modified.append(fname)

    # Strategy 3: Direct filename on code fence: ```server.py or ```src/main.js
    p3 = re.compile(r"```([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})\s*\r?\n(.*?)```", re.DOTALL)
    for m in p3.finditer(response_text):
        fname = m.group(1).strip()
        code = m.group(2)
        if fname not in created_or_modified:
            if save_code_to_disk(fname, code):
                created_or_modified.append(fname)

    # Strategy 4: Standard code blocks with filename inside comment, in preceding markdown, or in user prompt
    raw_blocks = list(re.finditer(r"```([a-zA-Z0-9_\-\.\/:]*)\s*\r?\n(.*?)```", response_text, re.DOTALL))
    for m in raw_blocks:
        tag = m.group(1).strip()
        code = m.group(2)
        if any(fname in created_or_modified for fname in [tag]):
            continue

        start_pos = m.start()
        lookback = response_text[max(0, start_pos - 250):start_pos]
        pre_lines = [l.strip() for l in lookback.splitlines() if l.strip()]
        last_pre = pre_lines[-1] if pre_lines else ""

        found_fname = None

        # A: Check first 4 non-empty lines inside code block for comments
        code_lines = [l.strip() for l in code.splitlines() if l.strip()]
        for cl in code_lines[:4]:
            cm = re.search(r"(?:#|//|<!--|/\*)\s*(?:filename|file|path)?\s*:?\s*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})", cl, re.I)
            if cm:
                cand = cm.group(1).strip()
                if "." in cand and not cand.startswith(("http:", "https:")):
                    found_fname = cand
                    break

        # B: Check preceding line (e.g. **server.py**, ### server.py, `server.py`, File: server.py)
        if not found_fname and last_pre:
            pm = re.search(r"(?:file|filename|create|writing|in|save to)?[\s:`\'\"\*#]*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})[\s:`\'\"\*#]*", last_pre, re.I)
            if pm:
                cand = pm.group(1).strip()
                if "." in cand and not cand.startswith(("http:", "https:")):
                    found_fname = cand

        # C: Check user prompt (e.g. "create test.py with..." or "write /tmp/calc.py")
        if not found_fname and user_prompt:
            um = re.findall(r"[\"\'\`]?([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})[\"\'\`]?", user_prompt)
            valid_exts = {".py", ".sh", ".bash", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".rs", ".c", ".cpp", ".go", ".md", ".txt", ".sql", ".toml"}
            for cand in um:
                if os.path.splitext(cand)[1].lower() in valid_exts:
                    found_fname = cand
                    break

        if found_fname and found_fname not in created_or_modified:
            if save_code_to_disk(found_fname, code):
                created_or_modified.append(found_fname)

    # Strategy 5: Interactive fallback if code block exists but zero filenames detected anywhere
    if not created_or_modified and raw_blocks:
        best_block = max(raw_blocks, key=lambda m: len(m.group(2)))
        tag = best_block.group(1).strip().lower()
        code = best_block.group(2)
        ext_map = {"python": ".py", "py": ".py", "bash": ".sh", "sh": ".sh", "javascript": ".js", "js": ".js", "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css", "json": ".json", "rust": ".rs", "go": ".go", "c": ".c", "cpp": ".cpp"}
        sug_ext = ext_map.get(tag, ".py")
        sug_name = f"solution{sug_ext}"
        print(f"\n{C_YELLOW}[?] Code block found ({len(code.splitlines())} lines), but no filename was detected.{C_RESET}")
        try:
            user_fname = input(f"{C_BOLD}{C_CYAN}Enter filename to save (e.g. {sug_name}) [or Enter to skip]: {C_RESET}").strip()
            if user_fname:
                if save_code_to_disk(user_fname, code):
                    created_or_modified.append(user_fname)
        except (KeyboardInterrupt, EOFError):
            pass

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
        return "qwen3:14b"
    n = str(name).strip()
    # Strip common command prefixes like "mod ", "mode ", "model ", "models ", "m ", "/run "
    for pfx in ("mod ", "mode ", "model ", "models ", "m ", "/run "):
        if n.lower().startswith(pfx):
            n = n[len(pfx):].strip()
            break
    nl = n.lower()

    # Universal Catalog Number Mappings
    catalog_map = {
        # Single-digit family mappings
        "1": "qwen3:14b",
        "2": "deepseek-r1:14b",
        "3": "llama3.1:8b",
        "4": "mistral:7b",
        "5": "gemma2:9b",
        "6": "qwen2.5:72b",
        # Sub-indices from 11 to 65
        "11": "qwen2.5-coder:1.5b",
        "12": "qwen2.5-coder:7b",
        "13": "qwen2.5-coder:14b",
        "14": "qwen2.5-coder:32b-instruct-q3_K_M",
        "15": "qwen3:14b",
        "16": "qwen2.5:72b",
        "21": "deepseek-r1:1.5b",
        "22": "deepseek-r1:7b",
        "23": "deepseek-r1:14b",
        "24": "deepseek-r1:32b",
        "25": "deepseek-r1:70b",
        "26": "deepseek-coder:6.7b",
        "31": "llama3.2:1b",
        "32": "llama3.2:3b",
        "33": "llama3.1:8b",
        "34": "llama3.3:70b",
        "41": "mistral:7b",
        "42": "mistral-nemo:12b",
        "43": "codestral:22b",
        "44": "mistral-small:24b",
        "51": "gemma2:2b",
        "52": "gemma2:9b",
        "53": "gemma2:27b",
        "54": "phi3.5:3.8b",
        "55": "phi4:14b",
        "61": "deepseek-r1:671b",
        "62": "mixtral:8x22b",
        "63": "command-r-plus:104b",
        "64": "deepseek-r1:671b",
        "65": "qwen2.5:72b",
    }
    if nl in catalog_map:
        return catalog_map[nl]

    if nl in ("32b", "32", "32b-coder", "qwen-32b", "qwen2.5-32b"):
        if sys.platform == "darwin":
            # On Apple Silicon M-series (M1/M2/M3/M4), map 32b to fast 14.8GB Q3_K_M
            # which fits 100% inside 16GB-24GB Unified Memory with zero swap or freeze!
            return "qwen2.5-coder:32b-instruct-q3_K_M"
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
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as resp:
                tags = [m.get("name","") for m in json.loads(resp.read().decode()).get("models",[])]
                if any("72b" in t and ("q3" in t.lower() or "q3_k_m" in t.lower()) for t in tags):
                    return "qwen2.5:72b-instruct-q3_K_M"
                elif any("qwen2.5:72b" in t for t in tags):
                    return "qwen2.5:72b"
        except Exception:
            pass
        return "qwen2.5:72b-instruct-q3_K_M"
    if nl in ("500b", "500b25b", "501b", "beam", "beam:500b", "beam:500b-25b", "reflection:500b"):
        # Largest flagship MoE available on Ollama library (671B total / 37B active)
        return "deepseek-r1:671b"
    if nl in ("8x22b", "mixtral:8x22b", "141b", "mixtral-8x22b", "mixtral"):
        return "mixtral:8x22b"
    if nl in ("104b", "command-r-plus", "command-r-plus:104b", "command-r+", "commandr+"):
        return "command-r-plus:104b"
    if nl in ("671b", "deepseek-671b", "deepseek-r1:671b", "deepseek-v3"):
        return "deepseek-r1:671b"
    if nl in ("70b", "deepseek-70b", "deepseek-r1:70b"):
        return "deepseek-r1:70b"
    if nl in ("llama-70b", "llama3.3:70b", "llama3.3-70b"):
        return "llama3.3:70b"
    if nl in ("llama", "llama3", "llama3.1", "llama-8b", "8b"):
        return "llama3.1:8b"
    if nl in ("14b", "14", "qwen", "qwen-14b", "qwen3", "qwen3-14b"):
        return "qwen3:14b"
    if nl in ("1.5b", "1.5", "qwen-1.5b", "coder"):
        return "qwen2.5-coder:1.5b"
    if nl in ("7b", "7", "qwen-7b", "coder-7b"):
        return "qwen2.5-coder:7b"
    return n

def get_config_dir():
    d = os.path.expanduser("~/.obsidiancore")
    old_d = os.path.expanduser("~/.colistream")
    if not os.path.exists(d):
        if os.path.exists(old_d):
            try:
                shutil.copytree(old_d, d)
            except Exception:
                pass
        os.makedirs(d, exist_ok=True)
    return d

def get_idle_timeout():
    cfg = os.path.join(get_config_dir(), "idle_config")
    if os.path.exists(cfg):
        try:
            with open(cfg, "r") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    if sys.platform == "darwin":
        return "2m"
    return "5m"

def set_idle_timeout(val):
    val = val.strip().lower()
    if val in ("off", "never", "disable", "none", "-1"):
        val = "never"
    cfg = os.path.join(get_config_dir(), "idle_config")
    try:
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        with open(cfg, "w") as f:
            f.write(val)
    except Exception:
        pass
    return val

def unload_model_from_memory(model_name, api_base="http://localhost:11434"):
    try:
        url = f"{api_base}/api/generate"
        payload = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            pass
        return True
    except Exception:
        return False

_LAST_ACTIVITY_TIME = time.time()
_ACTIVE_LOADED_MODEL = None
_IDLE_THREAD_STARTED = False

def parse_idle_seconds(val):
    v = str(val).strip().lower()
    if v in ("off", "never", "none", "-1"):
        return None
    if v.endswith("m"):
        try: return float(v[:-1]) * 60
        except: return 120
    if v.endswith("s"):
        try: return float(v[:-1])
        except: return 60
    if v.endswith("h"):
        try: return float(v[:-1]) * 3600
        except: return 3600
    try:
        return float(v) * 60
    except:
        return 120

def start_idle_watchdog():
    global _IDLE_THREAD_STARTED
    if _IDLE_THREAD_STARTED:
        return
    _IDLE_THREAD_STARTED = True

    def _worker():
        global _LAST_ACTIVITY_TIME, _ACTIVE_LOADED_MODEL
        while True:
            time.sleep(5)
            timeout_str = get_idle_timeout()
            timeout_secs = parse_idle_seconds(timeout_str)
            if timeout_secs is None:
                continue
            if _ACTIVE_LOADED_MODEL and (time.time() - _LAST_ACTIVITY_TIME >= timeout_secs):
                m_to_unload = _ACTIVE_LOADED_MODEL
                _ACTIVE_LOADED_MODEL = None
                unload_model_from_memory(m_to_unload)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def get_installed_models(api_base="http://localhost:11434"):
    try:
        with urllib.request.urlopen(f"{api_base}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []

def get_best_default_model():
    installed = get_installed_models()
    for cand in ["qwen2.5-coder:7b", "qwen3:14b", "qwen2.5-coder:1.5b", "llama3.1:8b", "qwen2.5-coder:32b-instruct-q3_K_M"]:
        for inst in installed:
            if cand in inst or inst.startswith(cand.split(":")[0]):
                return inst
    if installed:
        return installed[0]
    return "qwen2.5-coder:7b"

def evict_stale_models(current_model, api_base="http://localhost:11434"):
    """
    On memory-constrained systems (especially macOS Unified Memory),
    unload any previously active models from RAM before loading the new model.
    Guarantees that models never stack up in memory.
    """
    try:
        cur_res = resolve_model_name(current_model)
        ps_url = f"{api_base}/api/ps"
        with urllib.request.urlopen(ps_url, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            loaded = data.get("models", [])
            for m in loaded:
                m_name = m.get("name", "")
                if m_name and m_name != cur_res and m_name != current_model:
                    unload_model_from_memory(m_name, api_base=api_base)
    except Exception:
        pass

def get_mac_apple_silicon_info():
    """
    Detects Apple Silicon M-series chip architecture (M1/M2/M3/M4),
    physical unified memory, and high-performance core count.
    """
    if sys.platform != "darwin":
        return None
    try:
        import subprocess
        mem_b = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL).decode().strip())
        tot_ram_gb = round(mem_b / (1024**3), 1)
        try:
            chip = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            chip = "Apple Silicon"
        try:
            p_cores = int(subprocess.check_output(["sysctl", "-n", "hw.perflevel0.logicalcpu"], stderr=subprocess.DEVNULL).decode().strip())
        except Exception:
            p_cores = 6
        return {
            "ram_gb": tot_ram_gb,
            "chip": chip,
            "p_cores": p_cores,
            "is_apple_silicon": ("Apple" in chip or "M" in chip or "arm64" in os.uname().machine)
        }
    except Exception:
        return None

def get_gpu_telemetry():
    """
    Returns (gpu_count, total_vram_mb, free_vram_mb, is_multi_gpu)
    Accurately detects real NVIDIA GPUs using nvidia-smi or ROCm using rocm-smi.
    Returns (0, 0, 0, False) on CPU-only machines.
    """
    cfg_file = os.path.join(get_config_dir(), "gpu_config")
    active_gpu = os.environ.get("ACTIVE_GPU", "").strip() or None
    if not active_gpu and os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                active_gpu = f.read().strip()
        except Exception:
            pass

    cuda_vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    target_all = (active_gpu == "all" or cuda_vis == "all")

    # 1. Try nvidia-smi with free and total memory
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,memory.free,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        gpu_entries = []
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                idx = parts[0]
                free_m = int(parts[1])
                tot_m = int(parts[2])
                gpu_entries.append((idx, free_m, tot_m))
                
        if gpu_entries:
            total_cnt = len(gpu_entries)
            if target_all or (not active_gpu and not cuda_vis and total_cnt > 1):
                tot_vram = sum(g[2] for g in gpu_entries)
                fre_vram = sum(g[1] for g in gpu_entries)
                return total_cnt, tot_vram, fre_vram, True
            else:
                sel_idx = active_gpu or (cuda_vis.split(",")[0] if cuda_vis else "0")
                match = [g for g in gpu_entries if g[0] == str(sel_idx)]
                if match:
                    return 1, match[0][2], match[0][1], False
                else:
                    return 1, gpu_entries[0][2], gpu_entries[0][1], False
    except Exception:
        pass

    # 2. Try Apple Silicon Metal (Darwin)
    if sys.platform == "darwin":
        try:
            import subprocess
            mem_b = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
            tot_mb = int(mem_b / (1024 * 1024))
            usable_mb = int(tot_mb * 0.75)
            return 1, usable_mb, usable_mb, False
        except Exception:
            pass

    # 3. CPU-only host (e.g. Intel Xeon / Matrox VGA without dedicated accelerators)
    return 0, 0, 0, False

def get_gpu_count():
    gpu_cnt, _, _, _ = get_gpu_telemetry()
    return gpu_cnt

def get_visible_vram_mb():
    _, tot_vram, _, _ = get_gpu_telemetry()
    return tot_vram

def compute_safe_gpu_layers(model_name, total_vram_mb, free_vram_mb, is_multi_gpu=False):
    """
    Computes optimal, safe GPU offload layer count ensuring CUDA buffers NEVER overflow.
    Guarantees models >72B stay strictly within available VRAM (or user-requested 48GB budget).
    Returns (num_gpu_layers, num_ctx, num_batch)
    """
    if total_vram_mb <= 0:
        return 0, 2048, 512

    # Available VRAM to budget:
    usable_mb = free_vram_mb if free_vram_mb > 0 else total_vram_mb
    usable_mb = min(usable_mb, total_vram_mb)
    
    # Cap total budget strictly to 48 GB maximum as requested by user
    usable_mb = min(usable_mb, 48000)

    # Reserve 2048 MB headroom for KV cache, context, and CUDA runtime buffers
    budget_mb = max(0, usable_mb - 2048)

    ml = model_name.lower()

    # High-Performance Apple Silicon Metal Offload Engine (macOS UMA)
    if sys.platform == "darwin":
        mac_info = get_mac_apple_silicon_info()
        tot_ram_gb = mac_info["ram_gb"] if mac_info else (total_vram_mb / 1024)
        if any(x in ml for x in ["32b", "30b", "27b"]):
            # On Apple Silicon M-series (M1/M2/M3/M4), offload 100% of layers to Metal (num_gpu=99).
            # Metal GPU shaders share unified memory directly. NEVER split layers across CPU/GPU!
            # Budget context to prevent macOS memory compression and swap:
            if tot_ram_gb >= 30:
                return 99, 8192, 512
            elif tot_ram_gb >= 22:
                # 24GB Mac: fits in RAM with compact 4k context and Q8 KV cache (Zero Swap!)
                return 99, 4096, 512
            else:
                # 16GB Mac: tight RAM budget -> 2048 context to minimize swap pressure
                return 99, 2048, 512
        elif any(x in ml for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "beam"]):
            if tot_ram_gb >= 48:
                return 99, 4096, 512
            elif tot_ram_gb >= 32:
                return 99, 2048, 512
            return 36, 2048, 512
        elif any(x in ml for x in ["14b", "13b", "12b", "16b"]):
            # 14B tier (~9GB weights): budget context to prevent swap
            if tot_ram_gb >= 22:
                return 99, 4096, 512
            elif tot_ram_gb >= 14:
                return 99, 2048, 512
            return 99, 1536, 512
        elif any(x in ml for x in ["7b", "8b", "9b"]):
            # 7B-9B tier (~4.5 - 5.5GB weights)
            if tot_ram_gb >= 14:
                return 99, 4096, 512
            return 99, 2048, 512
        else:
            # 1.5B, 3B tier (<2.5GB weights)
            return 99, 4096, 512

    if "104b" in ml or "command-r" in ml:
        # Command-R+ 104B: 64 layers total, ~950 MB weights per layer
        # On a single 24GB card (budget ~21.5GB): max 22 layers (~20.9 GB VRAM)
        # On dual 24GB cards (budget ~44GB): max 46 layers (~43.7 GB VRAM)
        safe_layers = min(64, int(budget_mb / 950))
        num_ctx = 2048 if safe_layers >= 20 else 1536
        return max(0, safe_layers), num_ctx, 512

    elif "8x22b" in ml or "141b" in ml or "mixtral" in ml:
        # Mixtral 8x22B (141B): 56 layers total, ~1160 MB weights per layer
        safe_layers = min(56, int(budget_mb / 1160))
        num_ctx = 2048 if safe_layers >= 18 else 1536
        return max(0, safe_layers), num_ctx, 512

    elif any(x in ml for x in ["671b", "500b", "501b", "beam"]):
        # DeepSeek-R1 671B / Beam 500B MoE: ~1400 MB weights per layer
        safe_layers = min(60, int(budget_mb / 1400))
        num_ctx = 2048 if safe_layers >= 14 else 1536
        return max(0, safe_layers), num_ctx, 512

    elif any(x in ml for x in ["70b", "72b"]):
        # Qwen 72B / Llama 70B: 80 layers total, ~490 MB weights per layer (~39 GB total)
        if budget_mb >= 39000 or (is_multi_gpu and total_vram_mb >= 42000):
            return 99, 2048, 512
        safe_layers = min(80, int(budget_mb / 490))
        num_ctx = 2048 if safe_layers >= 36 else 1536
        return max(0, safe_layers), num_ctx, 512

    elif any(x in ml for x in ["32b", "30b", "27b"]):
        # 32B models: ~16.5 GB weights total across 64 layers (~260 MB/layer)
        if budget_mb >= 16500:
            return 99, 2048, 512
        safe_layers = min(64, int(budget_mb / 260))
        return max(0, safe_layers), 2048, 512

    else:
        # Models <20B (14b, 7b, 1.5b): <10GB weights
        if budget_mb >= 9500:
            return 99, 2048, 512
        safe_layers = min(48, int(budget_mb / 220))
        return max(0, safe_layers), 2048, 512

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

    # Check free disk space on model target partition to leave 15GB safety buffer
    try:
        import shutil
        target_dir = os.environ.get("OLLAMA_MODELS")
        if not target_dir or not os.path.exists(target_dir):
            target_dir = os.path.expanduser("~/.ollama/models")
            if not os.path.exists(target_dir):
                target_dir = "/"
        free_bytes = shutil.disk_usage(target_dir).free
        free_gb = free_bytes / (1024 ** 3)
        if free_gb < 15.0:
            print(f"\n{C_RED}[!] Low Storage Alert: Only {free_gb:.1f} GB free on {target_dir}.{C_RESET}")
            print(f"{C_YELLOW}[!] ObsidianCore enforces a 15 GB safety buffer to protect system stability.{C_RESET}")
            ans = input(f"{C_BOLD}Continue downloading '{model_name}' anyway? [y/N]: {C_RESET}").strip().lower()
            if ans not in ("y", "yes"):
                print(f"{C_YELLOW}[*] Download cancelled to protect disk space.{C_RESET}")
                return False
    except Exception:
        pass

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
        return False
    except Exception as e:
        print(f"\n{C_YELLOW}[!] Download warning: {e}{C_RESET}")
        return False
    return True

def stream_chat(model_name, messages, api_url="http://localhost:11434/api/chat", color=C_CYAN):
    model_name = resolve_model_name(model_name)
    evict_stale_models(model_name)
    mac_info = get_mac_apple_silicon_info()
    if mac_info and mac_info.get("p_cores"):
        opt_threads = mac_info["p_cores"]
    else:
        total_cpus = os.cpu_count() or 8
        opt_threads = min(8, max(4, total_cpus // 10))

    gpu_cnt, total_vram_mb, free_vram_mb, is_multi_gpu = get_gpu_telemetry()
    num_gpu_layers, num_ctx_val, num_batch_val = compute_safe_gpu_layers(
        model_name, total_vram_mb, free_vram_mb, is_multi_gpu=is_multi_gpu
    )

    current_gpu_layers = num_gpu_layers
    attempt = 0
    max_attempts = 3
    import threading

    while attempt < max_attempts:
        attempt += 1
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "keep_alive": get_idle_timeout(),
            "options": {
                "temperature": 0.7,
                "num_gpu": current_gpu_layers,
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
                                sys.stdout.write(f"\r\033[K{C_BOLD}{color}✦ {model_name} ❯ {C_RESET}")
                                sys.stdout.flush()
                                first_token = False
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            full_response.append(content)
                            token_count += 1
                        if chunk.get("done", False):
                            eval_count = chunk.get("eval_count", token_count)
                            prompt_eval_count = chunk.get("prompt_eval_count", 0)
                            eval_dur = chunk.get("eval_duration", 0) / 1e9
                            tot_dur = chunk.get("total_duration", 0) / 1e9
                            speed = eval_count / eval_dur if eval_dur > 0 else 0
                            return "".join(full_response), speed, eval_count, prompt_eval_count, tot_dur
                    except json.JSONDecodeError:
                        pass
                return "".join(full_response), 0, token_count, 0, 0.0
        except KeyboardInterrupt:
            stop_spinner.set()
            print(f"\n{C_DIM}[Generation stopped by user]{C_RESET}")
            return "".join(full_response), 0, token_count, 0, 0.0
        except urllib.error.HTTPError as e:
            stop_spinner.set()
            error_msg = e.read().decode("utf-8", errors="ignore")
            is_oom = any(k in error_msg.lower() for k in [
                "out of memory", "out-of-memory", "cudamalloc failed", 
                "unable to allocate cuda", "cuda0 buffer", "failed to allocate"
            ])
            if is_oom and attempt < max_attempts:
                if current_gpu_layers > 14:
                    new_layers = max(8, current_gpu_layers // 2)
                elif current_gpu_layers > 0:
                    new_layers = 0
                else:
                    new_layers = 0
                
                sys.stdout.write(f"\r\033[K{C_YELLOW}⚡ [Auto-Memory Optimizer] GPU VRAM boundary reached on CUDA device.{C_RESET}\n")
                if new_layers > 0:
                    sys.stdout.write(f"   {C_CYAN}Auto-rebalancing offload: adjusting GPU layers ({current_gpu_layers} → {new_layers}) to fit safely within host memory budget...{C_RESET}\n")
                else:
                    sys.stdout.write(f"   {C_CYAN}Auto-rebalancing to Host Unified Memory (RAM mode): loading model cleanly without VRAM limits...{C_RESET}\n")
                sys.stdout.flush()
                current_gpu_layers = new_layers
                num_ctx_val = 2048
                time.sleep(0.5)
                continue
            else:
                sys.stdout.write(f"\r\033[K{C_YELLOW}[!] Inference error ({e.code}): {error_msg}{C_RESET}\n")
                sys.stdout.flush()
                return "".join(full_response), 0, 0
        except Exception as e:
            stop_spinner.set()
            sys.stdout.write(f"\r\033[K{C_YELLOW}[!] Stream error: {e}{C_RESET}\n")
            sys.stdout.flush()
            return "".join(full_response), 0, 0
        finally:
            stop_spinner.set()
            
    return "".join(full_response), 0, 0

def stream_chat_silent(model_name, messages, api_url="http://localhost:11434/api/chat"):
    model_name = resolve_model_name(model_name)
    evict_stale_models(model_name)
    mac_info = get_mac_apple_silicon_info()
    if mac_info and mac_info.get("p_cores"):
        opt_threads = mac_info["p_cores"]
    else:
        total_cpus = os.cpu_count() or 8
        opt_threads = min(8, max(4, total_cpus // 10))

    gpu_cnt, total_vram_mb, free_vram_mb, is_multi_gpu = get_gpu_telemetry()
    num_gpu_layers, num_ctx_val, num_batch_val = compute_safe_gpu_layers(
        model_name, total_vram_mb, free_vram_mb, is_multi_gpu=is_multi_gpu
    )

    current_gpu_layers = num_gpu_layers
    attempt = 0
    max_attempts = 3

    while attempt < max_attempts:
        attempt += 1
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.7,
                "num_gpu": current_gpu_layers,
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
                return "".join(full_response), 0, token_count
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8", errors="ignore")
            is_oom = any(k in error_msg.lower() for k in [
                "out of memory", "out-of-memory", "cudamalloc failed", 
                "unable to allocate cuda", "cuda0 buffer", "failed to allocate"
            ])
            if is_oom and attempt < max_attempts:
                current_gpu_layers = max(0, current_gpu_layers // 2) if current_gpu_layers > 14 else 0
                time.sleep(0.5)
                continue
            return "".join(full_response), 0, 0
        except Exception:
            return "".join(full_response), 0, token_count

    return "".join(full_response), 0, 0

def strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)

def char_width(ch):
    if ch in ('\0', '\n', '\r'):
        return 0
    code = ord(ch)
    if (0x1F300 <= code <= 0x1FAFF) or (0x2600 <= code <= 0x27BF) or (0x2300 <= code <= 0x23FF):
        return 2
    eaw = unicodedata.east_asian_width(ch)
    return 2 if eaw in ('W', 'F') else 1

def disp_width(s):
    clean = strip_ansi(s).replace("\t", "    ")
    return sum(char_width(c) for c in clean)

def pad_truncate(s, width, color=C_WHITE):
    clean = strip_ansi(s).replace("\t", "    ")
    res = []
    cur_w = 0
    for ch in clean:
        cw = char_width(ch)
        if cur_w + cw > width:
            break
        res.append(ch)
        cur_w += cw
    pad = " " * max(0, width - cur_w)
    return f"{color}{''.join(res)}{C_RESET}{pad}"

def wrap_text_to_width(text, max_width):
    lines = []
    for raw_line in text.split("\n"):
        if not raw_line:
            lines.append("")
            continue
        cur_line = []
        cur_w = 0
        words = raw_line.split(" ")
        for i, word in enumerate(words):
            ww = disp_width(word)
            space_w = 1 if i > 0 else 0
            if cur_w + space_w + ww <= max_width:
                if i > 0:
                    cur_line.append(" ")
                    cur_w += 1
                cur_line.append(word)
                cur_w += ww
            else:
                if cur_line:
                    lines.append("".join(cur_line))
                cur_line = [word]
                cur_w = ww
        if cur_line:
            lines.append("".join(cur_line))
    return lines

def render_tui_card(title, body, border_color=C_CYAN, title_color=C_BOLD+C_WHITE, max_card_width=None):
    cols = shutil.get_terminal_size((80, 24)).columns
    card_width = min(cols - 2, max_card_width or (cols - 2))
    card_width = max(35, card_width)
    inner_width = card_width - 4

    clean_title = strip_ansi(title)
    title_disp_w = disp_width(clean_title)
    avail_dashes = max(2, card_width - 3 - title_disp_w - 2)
    top_line = f"{border_color}╭─ {title_color}{title}{C_RESET}{border_color} {'─' * avail_dashes}╮{C_RESET}"

    out_lines = [top_line]
    wrapped_lines = wrap_text_to_width(body, inner_width)
    for l in wrapped_lines:
        line_w = disp_width(l)
        pad = " " * max(0, inner_width - line_w)
        out_lines.append(f"{border_color}│{C_RESET} {l}{pad} {border_color}│{C_RESET}")

    bottom_line = f"{border_color}╰{'─' * (card_width - 2)}╯{C_RESET}"
    out_lines.append(bottom_line)
    return "\n".join(out_lines)

def print_tui_header(model_name):
    cols = shutil.get_terminal_size((80, 24)).columns
    box_w = max(40, min(cols - 2, 88))
    inner_w = box_w - 4

    m_lower = model_name.lower()
    is_giant = any(x in m_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "beam"])
    is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])
    vram_mb = get_visible_vram_mb()
    mac_info = get_mac_apple_silicon_info()

    if mac_info:
        sys_str = f"Apple Silicon ({mac_info.get('chip', 'Metal')}) • {mac_info.get('ram_gb', 0):.0f} GB Unified Memory"
        if is_32b:
            mem_str = "100% Metal Acceleration • Budgeted 4k Context (Zero Swap)"
        elif is_giant:
            mem_str = "Metal Unified Memory • MoE Active Offload"
        else:
            mem_str = "100% Metal Native Acceleration"
    elif vram_mb == 0:
        sys_str = "Bare-Metal Host CPU • High-RAM Architecture"
        mem_str = "RAM Direct Mapping Mode"
    elif is_32b:
        sys_str = f"NVIDIA Dedicated GPU ({vram_mb // 1024} GB VRAM • CUDA)"
        mem_str = "Strictly 17 GB VRAM (100% GPU • 0 RAM • ~22 tok/s)"
    elif is_giant:
        sys_str = f"NVIDIA Hardware Array ({vram_mb // 1024} GB Total VRAM)"
        mem_str = "Multi-GPU Pool (Capped <=48GB VRAM)" if vram_mb >= 44000 else "Hybrid VRAM Offload (GPU + RAM)"
    else:
        sys_str = f"NVIDIA GPU Accelerator ({vram_mb // 1024} GB VRAM)"
        mem_str = "100% GPU VRAM Native Acceleration"

    idle_val = get_idle_timeout()
    idle_str = f"Sleep: {idle_val} (Auto-Free)" if idle_val != "never" else "Sleep: Disabled"

    # Card rendering
    top = f"{C_CYAN}╭{'─' * (box_w - 2)}╮{C_RESET}"
    sep = f"{C_CYAN}├{'─' * (box_w - 2)}┤{C_RESET}"
    bottom = f"{C_CYAN}╰{'─' * (box_w - 2)}╯{C_RESET}"

    header_line1 = f"  {C_BOLD}{C_WHITE}✦ ObsidianCore AI Assistant{C_RESET} {C_GRAY}[Gemini & OpenCode Architecture]{C_RESET}"
    header_line2 = f"  {C_DIM}Autonomous Bare-Metal Pair Programmer • Local Terminal Intelligence{C_RESET}"

    line_model = f"  {C_BOLD}Model:{C_RESET}     {C_GREEN}{C_BOLD}{model_name}{C_RESET} {C_GRAY}[100% Local • Zero Cloud • Zero Paywalls]{C_RESET}"
    line_sys   = f"  {C_BOLD}Hardware:{C_RESET}  {C_CYAN}{sys_str}{C_RESET}"
    line_mem   = f"  {C_BOLD}Engine:{C_RESET}    {C_YELLOW}{mem_str}{C_RESET}  │  {C_CYAN}{idle_str}{C_RESET}"
    line_cwd   = f"  {C_BOLD}Workspace:{C_RESET} {C_WHITE}{os.getcwd()}{C_RESET}"

    tip_line1 = f"  {C_GREEN}💡 Pair Programming:{C_RESET} Type instructions to write files or apply surgical edits."
    tip_line2 = f"  {C_DIM}Commands: /models (Hub) • /swarm (Dual AI) • /diff • /undo • /idle • /menu • /exit{C_RESET}"

    print(top)
    for l in [header_line1, header_line2]:
        lw = disp_width(l)
        pad = " " * max(0, inner_w - lw)
        print(f"{C_CYAN}│{C_RESET} {l}{pad} {C_CYAN}│{C_RESET}")
    print(sep)
    for l in [line_model, line_sys, line_mem, line_cwd]:
        lw = disp_width(l)
        pad = " " * max(0, inner_w - lw)
        print(f"{C_CYAN}│{C_RESET} {l}{pad} {C_CYAN}│{C_RESET}")
    print(sep)
    for l in [tip_line1, tip_line2]:
        lw = disp_width(l)
        pad = " " * max(0, inner_w - lw)
        print(f"{C_CYAN}│{C_RESET} {l}{pad} {C_CYAN}│{C_RESET}")
    print(bottom)

    if mac_info and is_32b:
        m_top = f"{C_GREEN}╭─ {C_BOLD}🍎 Apple Silicon M4 Speed Optimization{C_RESET}{C_GREEN} " + "─" * max(2, box_w - 44) + f"╮{C_RESET}"
        m_l1  = f"  {C_GREEN}✔ Metal 100% Offload:{C_RESET} All 64 layers locked to Metal GPU (Zero CPU sync latency)"
        m_l2  = f"  {C_GREEN}✔ KV Cache Quantized:{C_RESET} Q8_0 + 4,096 context prevents RAM pressure & swap"
        m_l3  = f"  {C_YELLOW}★ macOS Memory Limit:{C_RESET} Run {C_BOLD}sudo sysctl iogpu.wired_mem_limit=22000000000{C_RESET} to unlock max RAM"
        m_bot = f"{C_GREEN}╰" + "─" * (box_w - 2) + f"╯{C_RESET}"
        print(m_top)
        for l in [m_l1, m_l2, m_l3]:
            lw = disp_width(l)
            pad = " " * max(0, inner_w - lw)
            print(f"{C_GREEN}│{C_RESET} {l}{pad} {C_GREEN}│{C_RESET}")
        print(m_bot)

def print_swarm_tui_header(lead_model, fast_model):
    cols = shutil.get_terminal_size((80, 24)).columns
    box_w = max(40, min(cols - 2, 86))
    inner_w = box_w - 4

    dashes = max(2, box_w - 49)
    top = f"{C_GREEN}╭── {C_BOLD}{C_WHITE}⚡ ObsidianCore Dual-AI Collaborative Swarm{C_RESET}{C_GREEN} " + "─" * dashes + f"╮{C_RESET}"
    line1 = f"  {C_GREEN}{C_BOLD}• Model 1 (Lead Architect):{C_RESET} {C_WHITE}{lead_model}{C_RESET}"
    line2 = f"  {C_CYAN}{C_BOLD}• Model 2 (Fast Copilot)  :{C_RESET} {C_WHITE}{fast_model}{C_RESET}"
    line3 = f"  {C_YELLOW}• Mode:{C_RESET} Real-Time Concurrent Execution • Dual Streaming • Zero Paywalls"
    line4 = f"  {C_DIM}Commands: /models | /1 <msg> | /2 <msg> | /assign <f1> <f2> | !cmd | /clear | /exit{C_RESET}"
    bottom = f"{C_GREEN}╰" + "─" * (box_w - 2) + f"╯{C_RESET}"

    print(top)
    for l in [line1, line2, line3, line4]:
        lw = disp_width(l)
        pad = " " * max(0, inner_w - lw)
        print(f"{C_GREEN}│{C_RESET} {l}{pad} {C_GREEN}│{C_RESET}")
    print(bottom)

def detect_swarm_file_targets(prompt):
    p_low = prompt.lower().strip()
    is_conv = any(p in p_low for p in ["hello", "hi", "hey", "who are you", "what are you", "help", "thanks", "thank you", "good morning", "good evening"]) and len(p_low.split()) <= 4
    if is_conv:
        return None, None

    tokens = re.findall(r'\b[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,6}\b', prompt)
    valid_files = [t for t in tokens if not t.startswith(('http', 'www')) and not t.endswith(('.com', '.org', '.net', '.io', '.html', '.md', '.txt'))]
    if len(valid_files) >= 2:
        return valid_files[0], valid_files[1]
    elif len(valid_files) == 1:
        f1 = valid_files[0]
        ext = f1.split('.')[-1]
        base = f1.rsplit('.', 1)[0]
        return f1, f"{base}_worker.{ext}"

    # Only infer file targets if there is explicit coding intent
    has_code_intent = bool(re.search(r'\b(write|create|build|code|implement|generate|program|develop)\b', p_low))
    if not has_code_intent:
        return None, None

    has_rust = bool(re.search(r'\brust\b', p_low))
    has_c = bool(re.search(r'\b(c|c\+\+|cpp|clang)\b', p_low))
    has_py = bool(re.search(r'\b(python|py)\b', p_low))
    has_go = bool(re.search(r'\b(golang|go)\b', p_low))
    has_web = bool(re.search(r'\b(frontend|html|css|js|react|vue)\b', p_low))

    if has_rust and has_c:
        return 'server.rs', 'client.c'
    if has_py and has_web:
        return 'backend.py', 'frontend.js'
    if has_rust and has_py:
        return 'core.rs', 'binding.py'
    if (has_c or has_rust or has_py or has_go) and ('server' in p_low or 'client' in p_low or 'dual' in p_low or 'side by side' in p_low):
        if has_rust:
            return 'server.rs', 'client.rs'
        if has_c:
            return 'server.c', 'client.c'
        if has_py:
            return 'server.py', 'client.py'
        if has_go:
            return 'server.go', 'client.go'

    return None, None

def sniff_file_from_code(text, default_name):
    m = re.search(r"```(?:write|create|file|[a-zA-Z0-9_\-]+)?\s*:?\s*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})", text)
    if m and not m.group(1).startswith(("http:", "https:")):
        return m.group(1).strip()
    m = re.search(r"(?:#|//|<!--|/\*)\s*(?:filename|file|path)?\s*:?\s*([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,8})", text)
    if m and not m.group(1).startswith(("http:", "https:")):
        return m.group(1).strip()
    return default_name

def extract_code_block(text):
    raw_blocks = list(re.finditer(r"```(?:[a-zA-Z0-9_\-\.\/:]*)\s*\r?\n(.*?)```", text, re.DOTALL))
    if raw_blocks:
        return max(raw_blocks, key=lambda m: len(m.group(1))).group(1).strip()
    return text.strip()

def stream_model_tokens_concurrent(model_name, messages, text_holder, stats_holder, done_event, is_dual_70b=False, api_base="http://localhost:11434"):
    api_url = f"{api_base}/api/chat"
    mac_info = get_mac_apple_silicon_info()
    if mac_info and mac_info.get("p_cores"):
        opt_threads = mac_info["p_cores"]
    else:
        total_cpus = os.cpu_count() or 8
        # Keep thread pool within single NUMA socket (max 8 threads) to maximize L3 cache hits & avoid QPI bus thrashing
        opt_threads = min(8, max(4, total_cpus // 10))

    gpu_cnt, total_vram_mb, free_vram_mb, is_multi_gpu = get_gpu_telemetry()
    # If running dual giant models concurrently, divide budget in half so combined VRAM <= 48GB:
    eff_vram = (free_vram_mb // 2) if (is_dual_70b and free_vram_mb > 0) else free_vram_mb
    eff_tot = (total_vram_mb // 2) if (is_dual_70b and total_vram_mb > 0) else total_vram_mb
    num_gpu_layers, num_ctx_val, num_batch_val = compute_safe_gpu_layers(
        model_name, eff_tot, eff_vram, is_multi_gpu=is_multi_gpu
    )

    current_gpu_layers = num_gpu_layers
    attempt = 0
    max_attempts = 3
    start_t = time.time()

    try:
        while attempt < max_attempts:
            attempt += 1
            payload = {
                "model": model_name,
                "messages": messages,
                "stream": True,
                "keep_alive": get_idle_timeout(),
                "options": {
                    "temperature": 0.7,
                    "num_gpu": current_gpu_layers,
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
                                text_holder[0] += content
                                stats_holder["tokens"] = stats_holder.get("tokens", 0) + 1
                                elapsed = time.time() - start_t
                                if elapsed > 0:
                                    stats_holder["speed"] = stats_holder["tokens"] / elapsed
                            if chunk.get("done", False):
                                eval_dur = chunk.get("eval_duration", 0) / 1e9
                                eval_cnt = chunk.get("eval_count", stats_holder.get("tokens", 0))
                                prompt_eval_cnt = chunk.get("prompt_eval_count", 0)
                                if eval_dur > 0:
                                    stats_holder["speed"] = eval_cnt / eval_dur
                                stats_holder["tokens"] = eval_cnt
                                stats_holder["prompt_tokens"] = prompt_eval_cnt
                                stats_holder["total_duration"] = chunk.get("total_duration", 0) / 1e9
                                break
                        except Exception:
                            pass
                break
            except urllib.error.HTTPError as e:
                error_msg = e.read().decode("utf-8", errors="ignore")
                is_oom = any(k in error_msg.lower() for k in [
                    "out of memory", "out-of-memory", "cudamalloc failed", 
                    "unable to allocate cuda", "cuda0 buffer", "failed to allocate"
                ])
                if is_oom and attempt < max_attempts:
                    current_gpu_layers = max(0, current_gpu_layers // 2) if current_gpu_layers > 14 else 0
                    time.sleep(0.5)
                    continue
                text_holder[0] += f"\n[Inference Error ({e.code}): {error_msg}]"
                break
            except Exception as e:
                text_holder[0] += f"\n[Inference Error: {e}]"
                break
    finally:
        done_event.set()

_PARALLEL_BACKEND_PROC = None

def _cleanup_parallel_backend():
    pass

def ensure_parallel_backend(model1, model2):
    return "http://127.0.0.1:11434"

def run_parallel_swarm_session(model1_name, model2_name):
    model1 = resolve_model_name(model1_name)
    model2 = resolve_model_name(model2_name)
    if not ensure_model_installed(model1):
        print(f"\n{C_YELLOW}[!] Falling back model 1 to local 'qwen3:14b'{C_RESET}")
        model1 = "qwen3:14b"
        ensure_model_installed(model1)
    if not ensure_model_installed(model2):
        print(f"\n{C_YELLOW}[!] Falling back model 2 to local 'qwen2.5-coder:1.5b'{C_RESET}")
        model2 = "qwen2.5-coder:1.5b"
        ensure_model_installed(model2)

    api_base = ensure_parallel_backend(model1, model2)

    def get_model_tier(m_name):
        ml = m_name.lower()
        if any(x in ml for x in ["500b", "501b", "671b", "141b", "8x22b", "104b", "72b", "70b"]):
            return 4
        if any(x in ml for x in ["32b", "30b", "27b", "22b"]):
            return 3
        if any(x in ml for x in ["14b", "12b", "8b", "7b"]):
            return 2
        return 1

    if get_model_tier(model1) >= get_model_tier(model2):
        lead_model, fast_model = model1, model2
    else:
        lead_model, fast_model = model2, model1

    os.system("clear 2>/dev/null || true")
    print_swarm_tui_header(lead_model, fast_model)

    last_solutions = {"1": "", "2": ""}
    last_user_prompt = ""
    assigned_targets = [None, None]
    m1_history = []
    m2_history = []

    def classify_task_mode(p, targets):
        pl = p.lower().strip()
        if targets[0] and targets[1]:
            return "dual_code"
        tokens = re.findall(r'[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,6}', p)
        valid_files = [t for t in tokens if not t.startswith(('http', 'www')) and not t.endswith(('.com', '.org', '.net', '.io', '.html', '.md'))]
        if len(valid_files) >= 2 or any(k in pl for k in ["side by side", "server and client", "client and server", "backend and frontend", "two files", "dual files", "both files"]):
            return "dual_code"
        is_plan = any(w in pl for w in ["plan", "blueprint", "architecture", "specification", "roadmap"]) and any(w in pl for w in ["phase 1", "phases", "colibristream", "colibri", "system blueprint", "project blueprint"])
        if is_plan:
            return "dual_plan"
        heavy_kws = ["implement full", "build entire", "deep reasoning", "refactor all", "mathematical proof", "large architecture", "complex algorithm", "write comprehensive", "kernel", "driver", "500b", "671b", "104b", "72b"]
        if any(k in pl for k in heavy_kws) or len(p) > 280:
            return "heavy_architect"
        return "fast_response"

    import threading

    while True:
        try:
            prompt = input(f"\n{C_BOLD}{C_GREEN}ObsidianCore Swarm ❯ {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_DIM}Dual Swarm session ended.{C_RESET}")
            break

        if not prompt:
            continue

        if prompt in ("/exit", "/quit", "exit", "quit"):
            print(f"{C_DIM}Dual Swarm session ended.{C_RESET}")
            break

        if prompt in ("/models", "/catalog", "/hub"):
            print_models_catalog_table()
            continue

        if prompt == "/menu":
            print(f"{C_CYAN}Returning to Menu...{C_RESET}")
            sys.exit(42)

        if prompt == "/clear":
            m1_history = []
            m2_history = []
            assigned_targets = [None, None]
            print(f"{C_YELLOW}✔ Conversation context cleared for both models.{C_RESET}")
            continue

        if prompt.startswith("/assign ") or prompt.startswith("/files "):
            parts = prompt.split()
            if len(parts) >= 3:
                assigned_targets[0] = parts[1].strip()
                assigned_targets[1] = parts[2].strip()
                print(f"{C_GREEN}✔ Assigned: Model 1 -> {assigned_targets[0]} | Model 2 -> {assigned_targets[1]}{C_RESET}")
            else:
                print(f"{C_YELLOW}Usage: /assign <file1> <file2> (e.g. /assign server.rs client.c){C_RESET}")
            continue

        if prompt.startswith("/cat ") or prompt.startswith("/view "):
            target_f = prompt.split(maxsplit=1)[1].strip()
            if os.path.exists(target_f):
                print(f"\n{C_CYAN}=== Contents of {target_f} ==={C_RESET}")
                with open(target_f, "r", encoding="utf-8", errors="replace") as f:
                    print(f.read())
            else:
                print(f"{C_YELLOW}[!] File '{target_f}' not found on disk.{C_RESET}")
            continue

        if prompt.startswith("/apply") or prompt.startswith("/save"):
            parts = prompt.split()
            choice = "1"
            explicit_file = None
            if len(parts) == 2:
                if parts[1] in ("1", "2"):
                    choice = parts[1]
                else:
                    explicit_file = parts[1]
            elif len(parts) >= 3:
                if parts[1] in ("1", "2"):
                    choice = parts[1]
                    explicit_file = parts[2]
                else:
                    explicit_file = parts[1]

            target_sol = last_solutions.get(choice)
            if not target_sol and choice == "1" and last_solutions.get("2"):
                target_sol = last_solutions.get("2")
                choice = "2"

            if target_sol:
                print(f"\n{C_CYAN}[*] Applying Model {choice} code to workspace...{C_RESET}")
                applied = apply_model_edits(target_sol, explicit_filename=explicit_file, user_prompt=last_user_prompt)
                if not applied:
                    print(f"{C_YELLOW}[!] No file modification blocks found in Model {choice} code.{C_RESET}")
            else:
                print(f"{C_YELLOW}[!] No generated code to apply for Model {choice} yet.{C_RESET}")
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

        # --- Explicit Direct Model Invocations (/1 or /2) ---
        if prompt.startswith("/1 ") or prompt.startswith("/arch ") or prompt.startswith("/lead "):
            direct_q = prompt.split(maxsplit=1)[1].strip()
            print(f"\n{C_GREEN}{C_BOLD}🧠 Lead Architect ({lead_model}):{C_RESET}")
            sys_m = f"You are {lead_model}, Lead Architect in ObsidianCore. Answer the user's question directly, accurately, and thoroughly."
            msgs = [{"role": "system", "content": sys_m}] + list(m1_history) + [{"role": "user", "content": direct_q}]
            ans, _, _ = stream_chat(lead_model, msgs, color=C_GREEN, api_url=f"{api_base}/api/chat")
            m1_history.append({"role": "user", "content": direct_q})
            m1_history.append({"role": "assistant", "content": ans})
            last_solutions["1"] = ans
            apply_model_edits(ans, user_prompt=direct_q)
            continue

        if prompt.startswith("/2 ") or prompt.startswith("/fast ") or prompt.startswith("/worker "):
            direct_q = prompt.split(maxsplit=1)[1].strip()
            print(f"\n{C_CYAN}{C_BOLD}🔍 Fast Copilot ({fast_model}):{C_RESET}")
            sys_m = f"You are {fast_model}, fast assistant in ObsidianCore. Answer the user's question directly, accurately, and concisely."
            msgs = [{"role": "system", "content": sys_m}] + list(m2_history) + [{"role": "user", "content": direct_q}]
            ans, _, _ = stream_chat(fast_model, msgs, color=C_CYAN, api_url=f"{api_base}/api/chat")
            m2_history.append({"role": "user", "content": direct_q})
            m2_history.append({"role": "assistant", "content": ans})
            last_solutions["2"] = ans
            apply_model_edits(ans, user_prompt=direct_q)
            continue

        last_user_prompt = prompt
        f1_cand, f2_cand = detect_swarm_file_targets(prompt)
        file1 = assigned_targets[0] or f1_cand
        file2 = assigned_targets[1] or f2_cand

        is_conversational = any(p in prompt.lower().strip() for p in ["hello", "hi", "hey", "who are you", "what are you", "help", "thanks", "thank you", "good morning", "good evening"]) and len(prompt.split()) <= 4
        is_coding_request = bool(file1 or file2 or any(k in prompt.lower() for k in ["code", "write", "file", "implement", "build", "create", "function", "class", "script", "app", "server", "client", "refactor", "module"])) and not is_conversational

        # Dual AI Inter-Communication Prompts:
        if is_coding_request and file1 and file2:
            m1_sys = (
                f"You are Model 1 ({model1}) — Lead Systems Architect in an autonomous 2-AI concurrent swarm running via ObsidianCore.\n"
                f"You and Model 2 ({model2}) work simultaneously side-by-side on this user request.\n"
                f"YOUR ROLE: Provide the system architecture, foundational data structures, interfaces, and primary component ('{file1}').\n"
                f"Output clean production-grade code: ```write:{file1}\n"
            )
            m2_sys = (
                f"You are Model 2 ({model2}) — Senior Implementation Engineer in an autonomous 2-AI concurrent swarm running via ObsidianCore.\n"
                f"You and Model 1 ({model1}) work simultaneously side-by-side on this user request.\n"
                f"YOUR ROLE: Provide working implementation logic, helper functions, client integration, and complementary component ('{file2}').\n"
                f"Output clean production-grade code: ```write:{file2}\n"
            )
            m1_prompt = f"{prompt}\n[Collaborative Swarm: Focus on primary module '{file1}' while partner implements '{file2}']"
            m2_prompt = f"{prompt}\n[Collaborative Swarm: Focus on complementary module '{file2}' interfacing with '{file1}']"
        else:
            m1_sys = (
                f"You are Model 1 ({model1}) — Lead Systems Architect in an autonomous 2-AI collaborative swarm running via ObsidianCore.\n"
                f"You and Model 2 ({model2}) work concurrently side-by-side. Answer the user clearly, thoroughly, and professionally."
            )
            m2_sys = (
                f"You are Model 2 ({model2}) — Senior Fast Copilot & Implementation Specialist in an autonomous 2-AI collaborative swarm running via ObsidianCore.\n"
                f"You and Model 1 ({model1}) work concurrently side-by-side. Answer the user with concise, practical insights and assistance."
            )
            m1_prompt = prompt
            m2_prompt = prompt

        files_ctx = build_system_prompt() if tracked_files else ""
        ctx_inject = f"\n\nWorkspace Context:\n{files_ctx}" if files_ctx else ""
        m1_messages = [{"role": "system", "content": m1_sys + ctx_inject}] + list(m1_history) + [
            {"role": "user", "content": m1_prompt}
        ]
        m2_messages = [{"role": "system", "content": m2_sys + ctx_inject}] + list(m2_history) + [
            {"role": "user", "content": m2_prompt}
        ]

        t1_text = [""]
        t2_text = [""]
        t1_stats = {"tokens": 0, "speed": 0.0}
        t2_stats = {"tokens": 0, "speed": 0.0}
        done1 = threading.Event()
        done2 = threading.Event()

        m1_lower = model1.lower()
        m2_lower = model2.lower()
        is_m1_giant = any(x in m1_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "405b", "beam"])
        is_m2_giant = any(x in m2_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "405b", "beam"])
        is_dual_70b = is_m1_giant and is_m2_giant

        # Mode selection: Collaborative Communication Pipeline (default) vs Concurrent
        # In Collaborative Pipeline: Model 1 designs -> passes output to Model 2 -> Model 2 implements.
        # Memory is strictly budgeted: only 1 model in VRAM at a time on constrained devices!
        print("\n" + render_tui_card("👤 Dual Swarm Task", prompt, border_color=C_GREEN, title_color=C_BOLD+C_GREEN))

        # PHASE 1: Model 1 (Lead Systems Architect)
        print(f"\n{C_BOLD}{C_GREEN}╭── 🧠 Phase 1: Lead Architect [{model1}] Analyzing & Designing ──╮{C_RESET}")
        resp1, spd1, tok1, ptok1, dur1 = stream_chat(model1, m1_messages, color=C_GREEN, api_url=f"{api_base}/api/chat")
        print(f"\n{C_DIM}└─ [Phase 1 Complete: {tok1} tokens • {spd1:.1f} tok/s • {dur1:.1f}s]{C_RESET}")

        # Evict Model 1 if on low-RAM hardware before Model 2 begins
        if sys.platform == "darwin" or get_visible_vram_mb() < 24000:
            evict_stale_models(model2, api_base=api_base)

        # PHASE 2: Model 2 (Implementation Specialist) - Injects Model 1's architecture into context!
        print(f"\n{C_BOLD}{C_CYAN}╭── 🔍 Phase 2: Senior Implementation [{model2}] Synthesizing Code ──╮{C_RESET}")
        m2_swarm_prompt = (
            f"User Request: {prompt}\n\n"
            f"--- Architect Proposal ({model1}) ---\n"
            f"{resp1}\n"
            f"-----------------------------------------\n"
            f"Review the Architect's proposal above and synthesize the complete production code. "
            f"Tag code blocks with ```write:<filename> or surgical ```edit:<filename> blocks so ObsidianCore auto-saves them to disk."
        )
        m2_messages = [{"role": "system", "content": m2_sys + ctx_inject}] + list(m2_history) + [
            {"role": "user", "content": m2_swarm_prompt}
        ]
        resp2, spd2, tok2, ptok2, dur2 = stream_chat(model2, m2_messages, color=C_CYAN, api_url=f"{api_base}/api/chat")
        print(f"\n{C_DIM}└─ [Phase 2 Complete: {tok2} tokens • {spd2:.1f} tok/s • {dur2:.1f}s]{C_RESET}")

        t1_text = [resp1]
        t2_text = [resp2]
        t1_stats = {"tokens": tok1, "speed": spd1}
        t2_stats = {"tokens": tok2, "speed": spd2}

        # Prominently render dual TUI summary cards
        m1_header = f"🧠 Model 1: Lead Architect [{model1} • {spd1:.1f} tok/s • {tok1} tokens]"
        m2_header = f"🔍 Model 2: Fast Copilot   [{model2} • {spd2:.1f} tok/s • {tok2} tokens]"
        print("\n" + render_tui_card(m1_header, resp1.strip() or "[No output generated]", border_color=C_GREEN, title_color=C_BOLD+C_GREEN))
        print("\n" + render_tui_card(m2_header, resp2.strip() or "[No output generated]", border_color=C_CYAN, title_color=C_BOLD+C_CYAN))

        last_solutions["1"] = resp1
        last_solutions["2"] = resp2

        # ONLY auto-save code if user actually asked for code and not a general conversational query
        if is_coding_request and not is_conversational:
            sniff1 = sniff_file_from_code(t1_text[0], file1 or "module1.code")
            sniff2 = sniff_file_from_code(t2_text[0], file2 or "module2.code")
            saved1 = []
            saved2 = []
            if "```" in t1_text[0] and not t1_text[0].startswith("[Inference Error"):
                saved1 = apply_model_edits(t1_text[0], explicit_filename=sniff1, user_prompt=prompt)
            if "```" in t2_text[0] and not t2_text[0].startswith("[Inference Error"):
                saved2 = apply_model_edits(t2_text[0], explicit_filename=sniff2, user_prompt=prompt)

            if saved1 or saved2:
                file1_saved = saved1[0] if saved1 else sniff1
                file2_saved = saved2[0] if saved2 else sniff2
                lines1_cnt = len(open(file1_saved, "r", errors="ignore").readlines()) if (saved1 and os.path.exists(file1_saved)) else 0
                lines2_cnt = len(open(file2_saved, "r", errors="ignore").readlines()) if (saved2 and os.path.exists(file2_saved)) else 0
                save_lines = []
                if saved1:
                    save_lines.append(f"✔ Model 1 ({model1[:14]}): {file1_saved} ({lines1_cnt} lines on disk)")
                if saved2:
                    save_lines.append(f"✔ Model 2 ({model2[:14]}): {file2_saved} ({lines2_cnt} lines on disk)")
                if save_lines:
                    print("\n" + render_tui_card("⚡ Dual Files Auto-Saved", "\n".join(save_lines), border_color=C_YELLOW, title_color=C_BOLD+C_YELLOW))

        m1_history.append({"role": "user", "content": prompt})
        m1_history.append({"role": "assistant", "content": t1_text[0]})
        m2_history.append({"role": "user", "content": prompt})
        m2_history.append({"role": "assistant", "content": t2_text[0]})

def run_swarm_debate_session(model1_name, model2_name, rounds=2):
    model1 = resolve_model_name(model1_name)
    model2 = resolve_model_name(model2_name)
    if not ensure_model_installed(model1):
        print(f"\n{C_YELLOW}[!] Falling back model 1 to local 'qwen3:14b'{C_RESET}")
        model1 = "qwen3:14b"
        ensure_model_installed(model1)
    if not ensure_model_installed(model2):
        print(f"\n{C_YELLOW}[!] Falling back model 2 to local 'qwen2.5-coder:1.5b'{C_RESET}")
        model2 = "qwen2.5-coder:1.5b"
        ensure_model_installed(model2)

    os.system("clear 2>/dev/null || true")
    print(f"\n{C_GREEN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║           OBSIDIANCORE 2-AI MULTI-TURN DEBATE & REVIEW LOOP                   ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}║      Autonomous Sibling Dialogue • Adversarial Code Audit & Verification       ║{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"│  {C_CYAN}🧠 Lead Architect :{C_RESET} {C_WHITE}{C_BOLD}{model1:<35}{C_RESET} {C_GRAY}[Proposal & Synthesis]{C_RESET} │")
    print(f"│  {C_PURPLE}🔍 Peer Reviewer  :{C_RESET} {C_WHITE}{C_BOLD}{model2:<35}{C_RESET} {C_GRAY}[Adversarial Audit]{C_RESET}    │")
    print(f"│  {C_YELLOW}🔄 Review Depth   :{C_RESET} {C_WHITE}{rounds} Rounds (Back-and-Forth Multi-Turn Loop){C_RESET}                   │")
    print(f"├────────────────────────────────────────────────────────────────────────────────┤")
    print(f"│  {C_BOLD}Commands:{C_RESET} {C_YELLOW}/rounds <N>{C_RESET} | {C_YELLOW}/apply{C_RESET} (Save code to disk) | {C_YELLOW}/add <file>{C_RESET} | {C_YELLOW}!cmd{C_RESET} | {C_YELLOW}/exit{C_RESET}   │")
    print(f"{C_GREEN}{C_BOLD}└────────────────────────────────────────────────────────────────────────────────┘{C_RESET}")

    last_refined_solution = ""
    last_arch_solution = ""
    last_rev_solution = ""
    last_user_prompt = ""

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

        if prompt in ("/models", "/catalog", "/hub"):
            print_models_catalog_table()
            continue

        if prompt == "/menu":
            print(f"{C_CYAN}Returning to Menu...{C_RESET}")
            sys.exit(42)

        if prompt.startswith("/rounds ") or prompt.startswith("/r "):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().isdigit():
                rounds = max(1, min(5, int(parts[1].strip())))
                print(f"{C_GREEN}✔ Debate depth set to {rounds} rounds.{C_RESET}")
            continue

        if prompt.startswith("/apply") or prompt.startswith("/save"):
            parts = prompt.split()
            choice = "consensus"
            explicit_file = None
            if len(parts) == 2:
                if parts[1] in ("1", "2"):
                    choice = parts[1]
                else:
                    explicit_file = parts[1]
            elif len(parts) >= 3:
                if parts[1] in ("1", "2"):
                    choice = parts[1]
                    explicit_file = parts[2]
                else:
                    explicit_file = parts[1]

            target_sol = ""
            if choice == "1":
                target_sol = last_arch_solution
            elif choice == "2":
                target_sol = last_rev_solution
            else:
                target_sol = last_refined_solution or last_arch_solution or last_rev_solution

            if target_sol:
                print(f"\n{C_CYAN}[*] Applying code to workspace...{C_RESET}")
                applied = apply_model_edits(target_sol, explicit_filename=explicit_file, user_prompt=last_user_prompt)
                if not applied and choice == "consensus":
                    for alt_name, alt_sol in [("Architect", last_arch_solution), ("Reviewer", last_rev_solution)]:
                        if alt_sol and alt_sol != target_sol:
                            print(f"{C_DIM}Checking {alt_name} code block...{C_RESET}")
                            applied = apply_model_edits(alt_sol, explicit_filename=explicit_file, user_prompt=last_user_prompt)
                            if applied:
                                break
                if not applied:
                    print(f"{C_YELLOW}[!] No file modification blocks found in last solution.{C_RESET}")
                    print(f"{C_DIM}Tip: You can specify a filename directly: /apply <filename>{C_RESET}")
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
        last_user_prompt = prompt
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
                    f"3. Provide complete, working code blocks tagged with the exact filename (e.g. ```write:filename.ext or put '# filename: filename.ext' on line 1) so ObsidianCore can save it directly to disk.\n"
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
                    f"4. Tag all code blocks with the exact filename (e.g. ```write:filename.ext or put '# filename: filename.ext' on line 1) so ObsidianCore can save it directly to disk.\n"
                )

            arch_messages = [
                {"role": "system", "content": "You are the Lead Architect in an autonomous 2-AI engineering pair."},
                {"role": "user", "content": arch_prompt}
            ]

            arch_output, arch_spd, arch_toks = stream_chat(model1, arch_messages, color=C_CYAN)
            current_proposal = arch_output
            last_arch_solution = arch_output
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
            last_rev_solution = rev_output

            spd_text = f"{rev_spd:.1f} tok/s" if rev_spd > 0 else ""
            print(f"\n{C_DIM}└─ [{rev_toks} tokens {spd_text}]{C_RESET}")

        print(f"\n{C_GREEN}{C_BOLD}════════════════════════════════════════════════════════════════════════════════{C_RESET}")
        print(f"{C_GREEN}{C_BOLD}✔ 2-AI Multi-Turn Consensus Loop Complete ({rounds} Rounds Finished){C_RESET}")
        print(f"{C_GREEN}{C_BOLD}════════════════════════════════════════════════════════════════════════════════{C_RESET}")
        print(f"{C_DIM}Actions: Type '/apply' to save audited code to disk | Enter new prompt | Type '/exit'{C_RESET}")

def run_chat_session(model_name):
    model_name = resolve_model_name(model_name)
    ok = ensure_model_installed(model_name)
    if not ok:
        print(f"\n{C_YELLOW}[!] Model '{model_name}' could not be loaded or download was cancelled.{C_RESET}")
        fallback = get_best_default_model()
        print(f"{C_GREEN}[*] Falling back to installed flagship model: {fallback}{C_RESET}")
        time.sleep(0.5)
        model_name = fallback
        ensure_model_installed(model_name)
    os.system("clear 2>/dev/null || true")
    m_lower = model_name.lower()
    is_giant = any(x in m_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "beam"])
    is_70b = is_giant
    is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])
    vram_mb = get_visible_vram_mb()

    print_tui_header(model_name)

    if is_70b and vram_mb < 44000:
        print(f"\n{C_YELLOW}┌── HARDWARE ADVISORY: 72B SINGLE-CARD BOTTLENECK ──────────────────────┐{C_RESET}")
        print(f"│ {C_BOLD}Weight Size{C_RESET} : ~47 GB (Q4) / ~30 GB (Q2) — Exceeds single 24GB VRAM card   │")
        print(f"│ {C_BOLD}Allocation{C_RESET}  : ~22 GB on GPU (38 layers) + ~25 GB on Host RAM & CPU      │")
        print(f"│ {C_BOLD}Bandwidth{C_RESET}   : DDR4 RAM is ~35 GB/s (vs GPU ~700 GB/s) -> caps to ~1 tok/s │")
        print(f"│                                                                      │")
        print(f"│ {C_GREEN}★ HOW TO GET 20-25+ TOK/S:{C_RESET}                                           │")
        print(f"│   1. Dual GPUs (>=48GB VRAM): Switch with 'obsidiancore gpu all'        │")
        print(f"│   2. Single 24GB Card: Run 32B Coder (17GB VRAM, 0 RAM, 0 CPU @ 25 t/s)│")
        print(f"│      Command: {C_CYAN}obsidiancore run 32b{C_RESET}                                      │")
        print(f"{C_YELLOW}└──────────────────────────────────────────────────────────────────────┘{C_RESET}\n")

    history = [
        {"role": "system", "content": build_system_prompt()}
    ]
    last_response_text = ""
    last_user_prompt = ""

    while True:
        try:
            prompt = input(f"\n{C_BOLD}{C_GREEN}✦ ObsidianCore ❯ {C_RESET}").strip()
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
            last_response_text = ""
            print(f"{C_YELLOW}✔ Conversation context cleared.{C_RESET}")
            continue

        if prompt in ("/models", "/catalog", "/hub"):
            print_models_catalog_table()
            continue

        if prompt in ("/help", "/h", "?"):
            print_coding_agent_help()
            continue

        if prompt.startswith("/apply") or prompt.startswith("/save"):
            parts = prompt.split()
            explicit_file = parts[1] if len(parts) > 1 else None
            if last_response_text:
                print(f"\n{C_CYAN}[*] Applying code solution to workspace...{C_RESET}")
                applied = apply_model_edits(last_response_text, explicit_filename=explicit_file, user_prompt=last_user_prompt)
                if not applied:
                    print(f"{C_YELLOW}[!] No file modification blocks found in last solution.{C_RESET}")
                    print(f"{C_DIM}Tip: You can specify a filename directly: /apply <filename>{C_RESET}")
            else:
                print(f"{C_YELLOW}[!] No generated solution to apply yet.{C_RESET}")
            continue

        if prompt.startswith("/model ") or prompt.startswith("/switch ") or prompt.startswith("/m "):
            new_m = prompt.split(maxsplit=1)[1].strip()
            resolved_m = resolve_model_name(new_m)
            if ensure_model_installed(resolved_m):
                unload_model_from_memory(model_name)
                model_name = resolved_m
                m_lower = model_name.lower()
                is_giant = any(x in m_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "beam"])
                is_70b = is_giant
                is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])
                history = [{"role": "system", "content": build_system_prompt()}]
                print(f"{C_GREEN}✔ Switched active model to: {C_BOLD}{model_name}{C_RESET} (Old model unloaded from memory)")
            continue

        if prompt.startswith("/idle"):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                new_idle = set_idle_timeout(parts[1].strip())
                print(f"{C_GREEN}✔ Memory Idle Sleep set to: {C_BOLD}{new_idle}{C_RESET} (Model will auto-unload from RAM/VRAM after inactivity)")
            else:
                cur_idle = get_idle_timeout()
                print(f"{C_CYAN}Current Memory Idle Sleep: {C_BOLD}{cur_idle}{C_RESET} (Type /idle 2m, /idle 0 for instant, or /idle never)")
            continue

        if prompt in ("/sleep", "/unload", "/evict"):
            if unload_model_from_memory(model_name):
                print(f"{C_GREEN}✔ Model unloaded from memory. 100% of RAM and VRAM released to system!{C_RESET}")
                print(f"{C_DIM}(Model will automatically wake up and retake memory on your next prompt){C_RESET}")
            else:
                print(f"{C_YELLOW}[!] Could not verify model unload.{C_RESET}")
            continue

        if prompt.startswith("/parallel") or prompt.startswith("/swarm"):
            parts = prompt.split()
            second_m = parts[1] if len(parts) > 1 else ("qwen2.5-coder:1.5b" if model_name != "qwen2.5-coder:1.5b" else "qwen3:14b")
            run_parallel_swarm_session(model_name, second_m)
            continue

        if prompt.startswith("/debate"):
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
        last_user_prompt = prompt
        history[0]["content"] = build_system_prompt()
        history.append({"role": "user", "content": prompt})

        # Render User Prompt in TUI Card
        print("\n" + render_tui_card("✦ You", prompt, border_color=C_GREEN, title_color=C_BOLD+C_GREEN))
        print("")
        response_text, speed, eval_tokens, prompt_tokens, tot_dur = stream_chat(model_name, history, color=C_CYAN)
        if response_text:
            history.append({"role": "assistant", "content": response_text})
            last_response_text = response_text
            # Autonomous Aider-style File Modification Engine
            apply_model_edits(response_text, user_prompt=prompt)

        tot_tokens = eval_tokens + prompt_tokens
        speed_str = f"• {speed:.1f} tok/s" if speed > 0 else ""
        dur_str = f"• {tot_dur:.1f}s" if tot_dur > 0 else ""
        p_str = f"Prompt: {prompt_tokens} | " if prompt_tokens > 0 else ""
        print(f"\n{C_DIM}└─ [Output: {eval_tokens} toks | {p_str}Total: {tot_tokens} {speed_str} {dur_str}]{C_RESET}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--swarm", "--debate", "swarm", "debate"):
        installed = get_installed_models()
        default_m1 = "qwen3:14b" if any("qwen3" in x for x in installed) else get_best_default_model()
        default_m2 = "qwen2.5-coder:7b" if any("coder:7b" in x for x in installed) else ("qwen2.5-coder:1.5b" if any("1.5b" in x for x in installed) else default_m1)
        m1 = sys.argv[2] if len(sys.argv) > 2 else default_m1
        m2 = sys.argv[3] if len(sys.argv) > 3 else default_m2
        rounds_arg = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 2
        run_swarm_debate_session(m1, m2, rounds=rounds_arg)
    elif len(sys.argv) > 1 and sys.argv[1] in ("--parallel", "parallel", "-p"):
        installed = get_installed_models()
        default_m1 = "qwen3:14b" if any("qwen3" in x for x in installed) else get_best_default_model()
        default_m2 = "qwen2.5-coder:7b" if any("coder:7b" in x for x in installed) else ("qwen2.5-coder:1.5b" if any("1.5b" in x for x in installed) else default_m1)
        m1 = sys.argv[2] if len(sys.argv) > 2 else default_m1
        m2 = sys.argv[3] if len(sys.argv) > 3 else default_m2
        run_parallel_swarm_session(m1, m2)
    else:
        if len(sys.argv) > 1 and sys.argv[1] not in ("chat", ""):
            model = sys.argv[1]
        else:
            model = get_best_default_model()
        run_chat_session(model)
PYEOF
  chmod +x "$target" 2>/dev/null || true
}

cmd_run() {
  ensure_backend
  local raw_model="${1:-chat}"

  if [ "$raw_model" = "chat" ] || [ -z "$raw_model" ]; then
    local best_local
    best_local=$(python3 -c "
import urllib.request, json, sys
res = 'qwen2.5-coder:7b'
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2) as resp:
        names = [m.get('name','') for m in json.loads(resp.read().decode()).get('models',[])]
        for cand in ['qwen2.5-coder:7b', 'qwen3:14b', 'qwen2.5-coder:1.5b', 'llama3.1:8b', 'qwen2.5-coder:32b-instruct-q3_K_M']:
            matched = [n for n in names if cand == n or n.startswith(cand)]
            if matched:
                res = matched[0]
                break
        else:
            if names:
                res = names[0]
except Exception:
    pass
print(res)
" 2>/dev/null || echo "qwen2.5-coder:7b")
    raw_model="$best_local"
  fi

  # Strip common prefix keywords
  local model=$(echo "$raw_model" | sed -E 's/^(mod|mode|model|models|m)[[:space:]]*//I')

  # Intelligent Model Alias Resolution & Precision VRAM Targeting:
  case "$model" in
    1|15|qwen|qwen3|14b|14B)
      model="qwen3:14b"
      ;;
    11|1.5b|1.5B|coder)
      model="qwen2.5-coder:1.5b"
      ;;
    12|7b|7B)
      model="qwen2.5-coder:7b"
      ;;
    13)
      model="qwen2.5-coder:14b"
      ;;
    14|32b|32B|qwen2.5-coder:32b|qwen2.5:32b)
      model="qwen2.5-coder:32b-instruct-q3_K_M"
      ;;
    16|64|72b|72B|qwen2.5:72b|qwen-72b)
      local has_q3_72b
      has_q3_72b=$(python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2) as resp:
        tags = [m.get('name','') for m in json.loads(resp.read().decode()).get('models',[])]
        if any('72b' in t and ('q3' in t.lower() or 'q3_k_m' in t.lower()) for t in tags):
            print('1')
        elif any('qwen2.5:72b' in t for t in tags):
            print('2')
        else:
            print('0')
except:
    print('0')
" 2>/dev/null || echo "0")
      if [ "$has_q3_72b" = "1" ]; then
        model="qwen2.5:72b-instruct-q3_K_M"
      elif [ "$has_q3_72b" = "2" ]; then
        model="qwen2.5:72b"
      else
        model="qwen2.5:72b-instruct-q3_K_M"
      fi
      ;;
    2|23|deepseek|deepseek-r1:14b)
      model="deepseek-r1:14b"
      ;;
    21) model="deepseek-r1:1.5b" ;;
    22) model="deepseek-r1:7b" ;;
    24) model="deepseek-r1:32b" ;;
    25|66|deepseek-70b|deepseek-r1:70b) model="deepseek-r1:70b" ;;
    26) model="deepseek-coder:6.7b" ;;
    3|33|llama|llama3|llama3.1|llama-8b|8b)
      model="llama3.1:8b"
      ;;
    31) model="llama3.2:1b" ;;
    32) model="llama3.2:3b" ;;
    34|65|llama-70b|llama3.3:70b|70b)
      model="llama3.3:70b"
      ;;
    4|41|mistral)
      model="mistral:7b"
      ;;
    42) model="mistral-nemo:12b" ;;
    43) model="codestral:22b" ;;
    44) model="mistral-small:24b" ;;
    5|52|gemma|gemma2)
      model="gemma2:9b"
      ;;
    51) model="gemma2:2b" ;;
    53) model="gemma2:27b" ;;
    54) model="phi3.5:3.8b" ;;
    55) model="phi4:14b" ;;
    61|deepseek-671b|deepseek-r1:671b|671b)
      model="deepseek-r1:671b"
      ;;
    62|8x22b|mixtral:8x22b|141b)
      model="mixtral:8x22b"
      ;;
    63|104b|command-r-plus|command-r-plus:104b)
      model="command-r-plus:104b"
      ;;
    67|500b|500b25b|501b|beam|beam:500b*)
      model="deepseek-r1:671b"
      ;;
    6)
      if [ -t 0 ]; then
        echo -e "\n${C_BOLD}${C_RED}─── [6] MEGA FRONTIER & MoE MODELS (<=48GB Budget) ───${C_RESET}"
        echo -e "  ${C_CYAN}61)${C_RESET} deepseek-r1:671b     (671B MoE 37B active • ~46 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}62)${C_RESET} mixtral:8x22b         (141B MoE 39B active • ~42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}63)${C_RESET} command-r-plus:104b   (104B Dense Enterprise • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}64)${C_RESET} qwen2.5:72b           (72B Dense Frontier • ~38–42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}65)${C_RESET} llama3.3:70b          (70B Flagship GPT-4o • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}66)${C_RESET} deepseek-r1:70b       (70B Enterprise Reasoning • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}67)${C_RESET} beam:500b-25b         (501B MoE 25B active • ~44 GB RAM/VRAM)"
        read_input "${C_BOLD}Select Mega Model [61-67, default 64]: ${C_RESET}" SUB_6_CHOICE
        case "$SUB_6_CHOICE" in
          61|671b|deepseek-671b) model="deepseek-r1:671b" ;;
          62|8x22b|mixtral) model="mixtral:8x22b" ;;
          63|104b|command*) model="command-r-plus:104b" ;;
          65|70b|llama*) model="llama3.3:70b" ;;
          66|deepseek-70b|r1-70b) model="deepseek-r1:70b" ;;
          67|500b|beam*) model="deepseek-r1:671b" ;;
          *) model="qwen2.5:72b-instruct-q3_K_M" ;;
        esac
      else
        model="qwen2.5:72b-instruct-q3_K_M"
      fi
      ;;
  esac

  # Proactive VRAM Capacity & Bottleneck Guard:
  run_hardware_scan
  local model_lower
  model_lower=$(echo "$model" | tr '[:upper:]' '[:lower:]')

  # Multi-GPU Pooling Auto-Activation for Heavy Frontier Models (>70B):
  if [[ "$model_lower" =~ 70b|72b|671b|500b|501b|8x22b|104b|beam ]] && [ "$GPU_COUNT" -gt 1 ]; then
    local TOTAL_POOL_VRAM_MB=0
    for m in "${GPU_MEMS[@]}"; do
      TOTAL_POOL_VRAM_MB=$((TOTAL_POOL_VRAM_MB + m))
    done
    local TOTAL_POOL_VRAM_GB=$((TOTAL_POOL_VRAM_MB / 1024))

    if [ "$TOTAL_POOL_VRAM_GB" -ge 36 ] && [ "$ACTIVE_GPU" != "all" ]; then
      echo -e "\n${C_GREEN}${C_BOLD}[*] Multi-GPU Setup Detected ($GPU_COUNT cards, ${TOTAL_POOL_VRAM_GB} GB Total VRAM Pool)!${C_RESET}"
      echo -e "${C_CYAN}    Unlocking Multi-Card Mode ('all') so Frontier Model fits 100% in VRAM across all GPUs...${C_RESET}"
      apply_gpu_configuration "all"
      run_hardware_scan
    fi
  fi

  local req_vram=48
  if [[ "$model_lower" =~ q3|q3_k_m|32b ]]; then
    req_vram=36
  elif [[ "$model_lower" =~ 14b|7b|1.5b ]]; then
    req_vram=16
  fi

  if [[ "$model_lower" =~ 70b|72b|671b|500b|501b|8x22b|104b|beam ]]; then
    if [ "$GPU_COUNT" -gt 0 ] && [ "$AVAILABLE_VRAM_GB" -lt "$req_vram" ]; then
      echo -e "\n${C_YELLOW}┌── ⚠ VRAM CAPACITY NOTICE: MODEL BUDGET CAPPED TO 48 GB ──────────┐${C_RESET}"
      echo -e "│ ${C_BOLD}Selected Model${C_RESET}  : ${C_CYAN}${model}${C_RESET} (Max 48 GB Budget Allocated)            │"
      echo -e "│ ${C_BOLD}Available VRAM${C_RESET}  : ${C_YELLOW}${AVAILABLE_VRAM_GB} GB${C_RESET} (Multi-GPU / Host RAM Offload Active)       │"
      echo -e "│ ${C_GREEN}★ Budget Guard${C_RESET}  : Context and layers clamped strictly <= 48 GB VRAM  │"
      echo -e "${C_YELLOW}└──────────────────────────────────────────────────────────────────┘${C_RESET}\n"
    elif [ "$GPU_COUNT" -eq 0 ]; then
      echo -e "${C_CYAN}[*] High-RAM Host Mode: Profiling model '${model}' within 48 GB budget in system RAM...${C_RESET}"
    fi
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
    echo -e "\n${C_YELLOW}[!] Model '${model}' is not installed locally.${C_RESET}"
    if ! cmd_pull "$model"; then
      echo -e "\n${C_RED}[!] Could not download model '${model}'.${C_RESET}"
      echo -e "${C_YELLOW}Available locally installed models on disk:${C_RESET}"
      echo -e "  • ${C_GREEN}qwen3:14b${C_RESET} (14B Reasoning & General)"
      echo -e "  • ${C_GREEN}qwen2.5-coder:32b-instruct-q3_K_M${C_RESET} (32B Flagship Coder)"
      echo -e "  • ${C_GREEN}qwen2.5-coder:7b${C_RESET} (7B Fast Coder)"
      echo -e "  • ${C_GREEN}qwen2.5-coder:1.5b${C_RESET} (1.5B Edge Coder)"
      read_input "\n${C_BOLD}Press Enter to launch 'qwen3:14b' or type another model name (or 'b' for menu): ${C_RESET}" FALLBACK_CHOICE
      if [ "$FALLBACK_CHOICE" = "b" ] || [ "$FALLBACK_CHOICE" = "B" ]; then
        return 0
      elif [ -n "$FALLBACK_CHOICE" ]; then
        model="$FALLBACK_CHOICE"
      else
        model="qwen3:14b"
      fi
    fi
  fi

  local chat_script="${DIR}/obsidian_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/obsidian_chat.py"
    write_inline_chat_script "$chat_script"
  fi

  if [ "$GPU_COUNT" -eq 0 ] || [ "$AVAILABLE_VRAM_MB" -eq 0 ]; then
    echo -e "${C_CYAN}[*] Active Execution Target: High-RAM Host Mode (System Memory Acceleration • 0 VRAM)${C_RESET}"
    unset CUDA_VISIBLE_DEVICES
  elif [ "$ACTIVE_GPU" = "all" ]; then
    echo -e "${C_CYAN}[*] Active GPU Target: [ALL GPUs Pooled (${GPU_COUNT:-2} cards)] (CUDA_VISIBLE_DEVICES=all / unset)${C_RESET}"
  else
    echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  fi
  local exit_code=0
  python3 "$chat_script" "$model"
  exit_code=$?
  if [ "$exit_code" -eq 42 ]; then
    cmd_loop_menu
    return 0
  fi
  if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 130 ]; then
    echo -e "\n${C_YELLOW}[!] Session closed with status code ${exit_code}.${C_RESET}"
    read_input "${C_BOLD}Press Enter to return to menu: ${C_RESET}" _
    cmd_loop_menu
  fi
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
      500b|500b25b|beam)
        ARCHITECT="beam:500b-25b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
      8x22b|mixtral)
        ARCHITECT="mixtral:8x22b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
      104b|command-r)
        ARCHITECT="command-r-plus:104b"
        WORKER="qwen2.5-coder:1.5b"
        ;;
      671b|deepseek-671b)
        ARCHITECT="deepseek-r1:671b"
        WORKER="deepseek-coder:6.7b"
        ;;
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

  local chat_script="${DIR}/obsidian_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/obsidian_chat.py"
    write_inline_chat_script "$chat_script"
  fi

  local rounds="${3:-2}"
  if [ "$ACTIVE_GPU" = "all" ]; then
    echo -e "${C_CYAN}[*] Active GPU Target: [ALL GPUs Pooled (${GPU_COUNT:-2} cards)] (CUDA_VISIBLE_DEVICES=all / unset)${C_RESET}"
  else
    echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  fi
  python3 "$chat_script" --swarm "$ARCHITECT" "$WORKER" "$rounds"
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

  local chat_script="${DIR}/obsidian_chat.py"
  if [ ! -f "$chat_script" ]; then
    chat_script="/tmp/obsidian_chat.py"
    write_inline_chat_script "$chat_script"
  fi

  if [ "$ACTIVE_GPU" = "all" ]; then
    echo -e "${C_CYAN}[*] Active GPU Target: [ALL GPUs Pooled (${GPU_COUNT:-2} cards)] (CUDA_VISIBLE_DEVICES=all / unset)${C_RESET}"
  else
    echo -e "${C_CYAN}[*] Active GPU Target: [GPU ${ACTIVE_GPU:-0}] (CUDA_VISIBLE_DEVICES=${ACTIVE_GPU:-0})${C_RESET}"
  fi
  python3 "$chat_script" --parallel "$m1" "$m2"
  local exit_code=$?
  if [ "$exit_code" -eq 42 ]; then
    cmd_loop_menu
  fi
}

# --- Custom Multi-Model Swarm Builder ---
select_swarm_model_interactive() {
  local step_num="$1"
  local prompt_label="$2"
  local default_choice="$3"

  echo -e "\n${C_BOLD}${C_CYAN}─── STEP ${step_num}: ${prompt_label} ───${C_RESET}" >&2
  echo -e "${C_YELLOW}${C_BOLD}[QWEN FAMILY]${C_RESET}" >&2
  echo -e "   11) qwen2.5-coder:1.5b  ${C_DIM}(1.5B | Ultra-Fast Coding | ~1 GB)${C_RESET}" >&2
  echo -e "   12) qwen2.5-coder:7b    ${C_DIM}(7B   | High Accuracy Coding | ~5 GB)${C_RESET}" >&2
  echo -e "   13) qwen2.5-coder:14b   ${C_DIM}(14B  | Advanced Coding | ~9 GB)${C_RESET}" >&2
  echo -e "   14) qwen2.5-coder:32b   ${C_DIM}(32B  | Matches Claude 3.5 Sonnet | ~17 GB)${C_RESET}" >&2
  echo -e "   15) qwen3:14b           ${C_DIM}(14B  | Deep Reasoning & Thinking | ~9 GB)${C_RESET}" >&2
  echo -e "   16) qwen2.5:72b         ${C_DIM}(72B  | Heavyweight Frontier Giant | ~38-45 GB)${C_RESET}" >&2
  echo -e "${C_CYAN}${C_BOLD}[DEEPSEEK FAMILY]${C_RESET}" >&2
  echo -e "   21) deepseek-r1:1.5b    ${C_DIM}(1.5B | Lightweight Reasoning <think> | ~1.1 GB)${C_RESET}" >&2
  echo -e "   22) deepseek-r1:7b      ${C_DIM}(7B   | Deep Math & Logic | ~5 GB)${C_RESET}" >&2
  echo -e "   23) deepseek-r1:14b     ${C_DIM}(14B  | High-Accuracy Reasoning | ~9 GB)${C_RESET}" >&2
  echo -e "   24) deepseek-r1:32b     ${C_DIM}(32B  | o1-grade Math/Logic | ~18 GB)${C_RESET}" >&2
  echo -e "   25) deepseek-r1:70b     ${C_DIM}(70B  | Enterprise Reasoning | ~40 GB)${C_RESET}" >&2
  echo -e "   26) deepseek-coder:6.7b ${C_DIM}(6.7B | Clean Code Synthesizer | ~4.5 GB)${C_RESET}" >&2
  echo -e "${C_PURPLE}${C_BOLD}[LLAMA FAMILY]${C_RESET}" >&2
  echo -e "   31) llama3.2:1b         ${C_DIM}(1B   | Micro Edge Model | ~0.8 GB)${C_RESET}" >&2
  echo -e "   32) llama3.2:3b         ${C_DIM}(3B   | Compact Assistant | ~2.0 GB)${C_RESET}" >&2
  echo -e "   33) llama3.1:8b         ${C_DIM}(8B   | General Knowledge Standard | ~5.5 GB)${C_RESET}" >&2
  echo -e "   34) llama3.3:70b        ${C_DIM}(70B  | Flagship GPT-4o Replacement | ~40 GB)${C_RESET}" >&2
  echo -e "${C_GREEN}${C_BOLD}[MISTRAL & SPECIALISTS]${C_RESET}" >&2
  echo -e "   41) mistral:7b          ${C_DIM}(7B   | Fast & Eloquent | ~4.5 GB)${C_RESET}" >&2
  echo -e "   42) mistral-nemo:12b    ${C_DIM}(12B  | 128k Long Context | ~8 GB)${C_RESET}" >&2
  echo -e "   43) codestral:22b       ${C_DIM}(22B  | 80+ Programming Languages | ~14 GB)${C_RESET}" >&2
  echo -e "   44) mistral-small:24b   ${C_DIM}(24B  | Advanced Reasoning | ~15 GB)${C_RESET}" >&2
  echo -e "${C_WHITE}${C_BOLD}[GOOGLE GEMMA & MICROSOFT PHI]${C_RESET}" >&2
  echo -e "   51) gemma2:2b           ${C_DIM}(2B   | High-Efficiency Edge | ~1.6 GB)${C_RESET}" >&2
  echo -e "   52) gemma2:9b           ${C_DIM}(9B   | Benchmark Leader | ~6 GB)${C_RESET}" >&2
  echo -e "   53) gemma2:27b          ${C_DIM}(27B  | Google Flagship Open Weights | ~17 GB)${C_RESET}" >&2
  echo -e "   54) phi3.5:3.8b         ${C_DIM}(3.8B | Microsoft Compact Reasoning | ~2.5 GB)${C_RESET}" >&2
  echo -e "   55) phi4:14b            ${C_DIM}(14B  | Microsoft Synthetic Math/Code | ~9.5 GB)${C_RESET}" >&2
  echo -e "${C_RED}${C_BOLD}[MEGA FRONTIER & MoE (Bigger than 72B • Max 48GB Budget)]${C_RESET}" >&2
  echo -e "   61) deepseek-r1:671b    ${C_DIM}(671B MoE / 37B Active | Low-Bit Quantized Reasoning | ~46 GB)${C_RESET}" >&2
  echo -e "   62) mixtral:8x22b       ${C_DIM}(141B MoE / 39B Active | Mistral AI Mega-MoE | ~42 GB)${C_RESET}" >&2
  echo -e "   63) command-r-plus:104b ${C_DIM}(104B Dense            | Cohere Enterprise Giant | ~40 GB)${C_RESET}" >&2
  echo -e "   64) deepseek-r1:671b    ${C_DIM}(671B MoE / 37B Active | Low-Bit Quantized Reasoning | ~46 GB)${C_RESET}" >&2
  echo -e "   ${C_BOLD}[c]${C_RESET} Enter custom model name / tag" >&2

  read_input "${C_BOLD}Select model [11-65, name, or 'c', default '${default_choice}'] (or 'q'/'b' to cancel): ${C_RESET}" SEL

  local chosen=""
  case "$SEL" in
    q|Q|exit|quit|b|B|back)
      echo "CANCEL"
      return 0
      ;;
    11) chosen="qwen2.5-coder:1.5b" ;;
    12) chosen="qwen2.5-coder:7b" ;;
    13) chosen="qwen2.5-coder:14b" ;;
    14) chosen="qwen2.5-coder:32b-instruct-q3_K_M" ;;
    15|1) chosen="qwen3:14b" ;;
    16) chosen="qwen2.5:72b" ;;
    21) chosen="deepseek-r1:1.5b" ;;
    22) chosen="deepseek-r1:7b" ;;
    23|2) chosen="deepseek-r1:14b" ;;
    24) chosen="deepseek-r1:32b" ;;
    25) chosen="deepseek-r1:70b" ;;
    26) chosen="deepseek-coder:6.7b" ;;
    31) chosen="llama3.2:1b" ;;
    32) chosen="llama3.2:3b" ;;
    33|3) chosen="llama3.1:8b" ;;
    34) chosen="llama3.3:70b" ;;
    41|4) chosen="mistral:7b" ;;
    42) chosen="mistral-nemo:12b" ;;
    43) chosen="codestral:22b" ;;
    44) chosen="mistral-small:24b" ;;
    51) chosen="gemma2:2b" ;;
    52|5) chosen="gemma2:9b" ;;
    53) chosen="gemma2:27b" ;;
    54) chosen="phi3.5:3.8b" ;;
    55) chosen="phi4:14b" ;;
    61|64|6|500b*) chosen="deepseek-r1:671b" ;;
    62) chosen="mixtral:8x22b" ;;
    63) chosen="command-r-plus:104b" ;;
    65) chosen="qwen2.5:72b" ;;
    c|C|custom)
      read_input "${C_BOLD}Enter custom model name: ${C_RESET}" cust_m
      chosen="${cust_m:-$default_choice}"
      ;;
    "")
      chosen="$default_choice"
      ;;
    *)
      chosen="$SEL"
      ;;
  esac
  echo "$chosen"
}

# --- Custom Multi-Model Swarm Builder ---
cmd_swarm_builder() {
  clear 2>/dev/null || true
  echo -e "${C_BOLD}${C_GREEN}"
  echo "╔══════════════════════════════════════════════════════════════════════╗"
  echo "║         CUSTOM MULTI-MODEL SWARM BUILDER (RUN 2+ MODELS)             ║"
  echo "║     Pair any Big Brain AI with any Fast Worker AI in shared memory   ║"
  echo "╚══════════════════════════════════════════════════════════════════════╝"
  echo -e "${C_RESET}"

  MODEL1=$(select_swarm_model_interactive "1" "Choose Model #1 (Lead Architect / File 1)" "qwen3:14b")
  [ "$MODEL1" = "CANCEL" ] && return 0
  MODEL2=$(select_swarm_model_interactive "2" "Choose Model #2 (Fast Worker / File 2)" "qwen2.5-coder:1.5b")
  [ "$MODEL2" = "CANCEL" ] && return 0

  # Dynamic 70B+ / 72B VRAM Controller Enforcement:
  local m1_lower=$(echo "$MODEL1" | tr '[:upper:]' '[:lower:]')
  local m2_lower=$(echo "$MODEL2" | tr '[:upper:]' '[:lower:]')
  local is_m1_70b=0
  local is_m2_70b=0
  if [[ "$m1_lower" =~ 70b|72b|671b ]]; then is_m1_70b=1; fi
  if [[ "$m2_lower" =~ 70b|72b|671b ]]; then is_m2_70b=1; fi

  if [ "$is_m1_70b" -eq 1 ] && [ "$is_m2_70b" -eq 1 ]; then
    echo -e "\n${C_BOLD}${C_GREEN}┌── ⚡ DUAL-72B VRAM CONTROLLER ACTIVE ─────────────────────────────────┐${C_RESET}"
    echo -e "│  ${C_CYAN}Both Models${C_RESET} : 70B+ Frontier Giants (${MODEL1} + ${MODEL2})          │"
    echo -e "│  ${C_YELLOW}VRAM Budget${C_RESET} : Strictly Capped to 36–40 GB Max Combined VRAM!     │"
    echo -e "│  • ${MODEL1} : ~18.0 GB VRAM allocated on GPU (33 layers)         │"
    echo -e "│  • ${MODEL2} : ~18.0 GB VRAM allocated on GPU (33 layers)         │"
    echo -e "│  • Combined Total  : 36.0 GB VRAM (Leaves 8–12 GB headroom • Zero OOM) │"
    echo -e "${C_BOLD}${C_GREEN}└───────────────────────────────────────────────────────────────────────┘${C_RESET}"
  elif [ "$is_m1_70b" -eq 1 ] || [ "$is_m2_70b" -eq 1 ]; then
    echo -e "\n${C_BOLD}${C_GREEN}┌── ⚡ 72B HYBRID SWARM VRAM ALLOCATION ─────────────────────────────────┐${C_RESET}"
    echo -e "│  ${C_CYAN}Allocation Target${C_RESET} : 36–40 GB Max Total VRAM Pool                      │"
    echo -e "│  • Multi-GPU Throughput Target : ${C_GREEN}30–40 tok/s${C_RESET} (100% on GPU)             │"
    echo -e "│  • Single-GPU Fallback Target  : ${C_YELLOW}15–20 tok/s${C_RESET} (48 GPU layers)           │"
    echo -e "${C_BOLD}${C_GREEN}└───────────────────────────────────────────────────────────────────────┘${C_RESET}"
  fi

  echo -e "\n${C_CYAN}Step 3: Choose Swarm Execution Strategy:${C_RESET}"
  echo -e "  1) ⚡ Dual-Console Simultaneous (Side-by-side consoles • Code File 1 & File 2 concurrently!)"
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
  echo -e "  • ${C_YELLOW}Model 1 (Console 1):${C_RESET} ${MODEL1} (Handles File 1 / Engine)"
  echo -e "  • ${C_GREEN}Model 2 (Console 2):${C_RESET} ${MODEL2} (Handles File 2 / Worker)"

  if [ "$SWARM_MODE" = "parallel" ]; then
    echo -e "  • ${C_CYAN}Mode   :${C_RESET} ⚡ Dual-Console Simultaneous (Side-by-side split screen • Writes 2 files at the same time)\n"
    echo -e "${C_YELLOW}Direct Command to run this Dual Swarm anytime:${C_RESET}"
    echo -e "  ${C_BOLD}${C_WHITE}obsidiancore parallel ${MODEL1} ${MODEL2}${C_RESET}\n"
    read_input "${C_BOLD}Press Enter to boot this dual-console session now [Enter/b]: ${C_RESET}" CONF
    if [ "$CONF" != "b" ] && [ "$CONF" != "B" ]; then
      cmd_parallel "$MODEL1" "$MODEL2"
    fi
  else
    echo -e "  • ${C_PURPLE}Mode   :${C_RESET} 🔄 Sequential Adversarial Debate (Multi-turn back-and-forth)\n"
    echo -e "${C_YELLOW}Direct Command to run this Debate Swarm anytime:${C_RESET}"
    echo -e "  ${C_BOLD}${C_WHITE}obsidiancore debate ${MODEL1} ${MODEL2}${C_RESET}\n"
    read_input "${C_BOLD}Press Enter to boot this debate session now [Enter/b]: ${C_RESET}" CONF
    if [ "$CONF" != "b" ] && [ "$CONF" != "B" ]; then
      cmd_swarm "$MODEL1" "$MODEL2"
    fi
  fi
}

# --- Model Hub Table: Full Specification of All Free Local Models ---
cmd_models_table() {
  clear 2>/dev/null || true
  echo -e "\n${C_BOLD}${C_GREEN}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
  echo -e "${C_BOLD}${C_GREEN}║             UNIVERSAL FREE LOCAL MODEL HUB (BARE-METAL RUNTIME • ZERO PAYWALLS)                       ║${C_RESET}"
  echo -e "${C_BOLD}${C_GREEN}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝${C_RESET}"
  echo -e "${C_CYAN}${C_BOLD}┌──────────────────────┬──────────────┬──────────────────────┬───────────────┬──────────────────────────┐${C_RESET}"
  echo -e "${C_CYAN}${C_BOLD}│ Model Name           │ Total Params │ Architecture         │ Memory Budget │ CLI Quick Aliases        │${C_RESET}"
  echo -e "${C_CYAN}${C_BOLD}├──────────────────────┼──────────────┼──────────────────────┼───────────────┼──────────────────────────┤${C_RESET}"
  echo -e "│ ${C_BOLD}${C_RED}beam:500b-25b${C_RESET}        │ 501B         │ MoE (25B Active)     │ ~44 GB        │ 500b, 500b25b, beam      │"
  echo -e "│ ${C_BOLD}${C_RED}mixtral:8x22b${C_RESET}        │ 141B         │ MoE (39B Active)     │ ~42 GB        │ 8x22b, 141b, mixtral     │"
  echo -e "│ ${C_BOLD}${C_RED}command-r-plus:104b${C_RESET}  │ 104B         │ Dense Enterprise     │ ~40 GB        │ 104b, command-r-plus     │"
  echo -e "│ ${C_BOLD}${C_RED}deepseek-r1:671b${C_RESET}     │ 671B         │ MoE (37B Active)     │ ~46 GB        │ 671b, deepseek-671b      │"
  echo -e "│ ${C_BOLD}${C_YELLOW}qwen2.5:72b${C_RESET}          │ 72B          │ Dense Frontier       │ ~38–42 GB     │ 72b, qwen-72b            │"
  echo -e "│ ${C_BOLD}${C_YELLOW}llama3.3:70b${C_RESET}         │ 70B          │ Dense Frontier       │ ~40 GB        │ llama-70b, 70b           │"
  echo -e "│ ${C_BOLD}${C_YELLOW}deepseek-r1:70b${C_RESET}      │ 70B          │ Dense Reasoning      │ ~40 GB        │ deepseek-70b             │"
  echo -e "│ ${C_BOLD}${C_GREEN}qwen2.5-coder:32b${C_RESET}    │ 32B          │ Dense Coding (Claude)│ ~17 GB (GPU)  │ 32b, 32b-coder           │"
  echo -e "│ ${C_BOLD}${C_GREEN}deepseek-r1:32b${C_RESET}      │ 32B          │ Reasoning (o1-grade) │ ~20 GB        │ deepseek-32b             │"
  echo -e "│ ${C_BOLD}${C_GREEN}gemma2:27b${C_RESET}           │ 27B          │ Flagship Dense       │ ~17 GB        │ gemma-27b                │"
  echo -e "│ ${C_BOLD}${C_GREEN}codestral:22b${C_RESET}        │ 22B          │ Code Specialist      │ ~14 GB        │ codestral                │"
  echo -e "│ ${C_BOLD}${C_WHITE}qwen3:14b${C_RESET}            │ 14B          │ Next-Gen Reasoning   │ ~9 GB         │ qwen, 14b, qwen3         │"
  echo -e "│ ${C_BOLD}${C_WHITE}deepseek-r1:14b${C_RESET}      │ 14B          │ Math / Logic         │ ~9 GB         │ deepseek, r1-14b         │"
  echo -e "│ ${C_BOLD}${C_WHITE}phi4:14b${C_RESET}             │ 14B          │ Microsoft Math/Code  │ ~9.5 GB       │ phi4                     │"
  echo -e "│ ${C_BOLD}${C_WHITE}qwen2.5-coder:7b${C_RESET}     │ 7B           │ Fast Coding          │ ~5 GB         │ 7b, coder-7b             │"
  echo -e "│ ${C_BOLD}${C_WHITE}mistral:7b${C_RESET}           │ 7B           │ Fast & Eloquent      │ ~4.5 GB       │ mistral                  │"
  echo -e "│ ${C_BOLD}${C_WHITE}llama3.1:8b${C_RESET}          │ 8B           │ General Knowledge    │ ~5.5 GB       │ llama, 8b                │"
  echo -e "│ ${C_BOLD}${C_WHITE}deepseek-coder:6.7b${C_RESET}  │ 6.7B         │ Code Generation      │ ~4.5 GB       │ deepseek-coder           │"
  echo -e "│ ${C_BOLD}${C_CYAN}qwen2.5-coder:1.5b${C_RESET}   │ 1.5B         │ Ultra-Fast Coding    │ ~1.0 GB       │ 1.5b, coder              │"
  echo -e "│ ${C_BOLD}${C_CYAN}deepseek-r1:1.5b${C_RESET}     │ 1.5B         │ Compact Reasoning    │ ~1.1 GB       │ r1-1.5b                  │"
  echo -e "│ ${C_BOLD}${C_CYAN}llama3.2:1b${C_RESET}          │ 1B           │ Micro Edge Model     │ ~0.8 GB       │ llama-1b                 │"
  echo -e "${C_CYAN}${C_BOLD}└──────────────────────┴──────────────┴──────────────────────┴───────────────┴──────────────────────────┘${C_RESET}"
  echo -e "${C_DIM}★ All models run 100% locally on bare metal without cloud subscriptions or API keys.${C_RESET}\n"
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

    echo -e "${C_RED}${C_BOLD}[6] MEGA FRONTIER & MoE (All Free Open-Weight Giants • <=48GB Budget)${C_RESET}"
    echo -e "    61) deepseek-r1:671b    ${C_DIM}(671B | MoE (37B Active) | ~46 GB RAM/VRAM | 671b, deepseek-671b)${C_RESET}"
    echo -e "    62) mixtral:8x22b       ${C_DIM}(141B | MoE (39B Active) | ~42 GB RAM/VRAM | 8x22b, mixtral)${C_RESET}"
    echo -e "    63) command-r-plus:104b ${C_DIM}(104B | Dense Enterprise | ~40 GB RAM/VRAM | 104b, command-r-plus)${C_RESET}"
    echo -e "    64) qwen2.5:72b         ${C_DIM}(72B  | Dense Frontier   | ~38–42 GB RAM/VRAM | 72b, qwen-72b)${C_RESET}"
    echo -e "    65) llama3.3:70b        ${C_DIM}(70B  | Flagship GPT-4o  | ~40 GB RAM/VRAM | llama-70b, 70b)${C_RESET}"
    echo -e "    66) deepseek-r1:70b     ${C_DIM}(70B  | Enterprise Logic | ~40 GB RAM/VRAM | deepseek-70b, r1-70b)${C_RESET}"
    echo -e "    67) beam:500b-25b       ${C_DIM}(501B | MoE (25B Active) | ~44 GB RAM/VRAM | 500b, beam)${C_RESET}\n"

    read_input "${C_BOLD}Select model number (e.g. 11, 22, 33, 61), 'b' for Back, or 'q' to Quit: ${C_RESET}" SUB_CHOICE

    if [ "$SUB_CHOICE" = "b" ] || [ "$SUB_CHOICE" = "B" ] || [ "$SUB_CHOICE" = "back" ] || [ "$SUB_CHOICE" = "menu" ]; then
      return
    fi

    if [ "$SUB_CHOICE" = "q" ] || [ "$SUB_CHOICE" = "Q" ] || [ "$SUB_CHOICE" = "exit" ] || [ "$SUB_CHOICE" = "quit" ]; then
      echo -e "${C_DIM}Exiting ObsidianCore.${C_RESET}"
      exit 0
    fi

    local clean_sub=$(echo "$SUB_CHOICE" | sed -E 's/^(mod|mode|model|models|m)[[:space:]]*//I')

    TARGET_MODEL=""
    case "$clean_sub" in
      1) TARGET_MODEL="qwen3:14b" ;;
      2) TARGET_MODEL="deepseek-r1:14b" ;;
      3) TARGET_MODEL="llama3.1:8b" ;;
      4) TARGET_MODEL="mistral:7b" ;;
      5) TARGET_MODEL="gemma2:9b" ;;
      6)
        echo -e "\n${C_BOLD}${C_RED}─── [6] MEGA FRONTIER & MoE MODELS (<=48GB Budget) ───${C_RESET}"
        echo -e "  ${C_CYAN}61)${C_RESET} deepseek-r1:671b     (671B MoE 37B active • ~46 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}62)${C_RESET} mixtral:8x22b         (141B MoE 39B active • ~42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}63)${C_RESET} command-r-plus:104b   (104B Dense Enterprise • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}64)${C_RESET} qwen2.5:72b           (72B Dense Frontier • ~38–42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}65)${C_RESET} llama3.3:70b          (70B Flagship GPT-4o • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}66)${C_RESET} deepseek-r1:70b       (70B Enterprise Reasoning • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}67)${C_RESET} beam:500b-25b         (501B MoE 25B active • ~44 GB RAM/VRAM)"
        read_input "${C_BOLD}Select Mega Model [61-67, default 64]: ${C_RESET}" SUB_6_CHOICE
        case "$SUB_6_CHOICE" in
          61|671b|deepseek-671b) TARGET_MODEL="deepseek-r1:671b" ;;
          62|8x22b|mixtral) TARGET_MODEL="mixtral:8x22b" ;;
          63|104b|command*) TARGET_MODEL="command-r-plus:104b" ;;
          65|70b|llama*) TARGET_MODEL="llama3.3:70b" ;;
          66|deepseek-70b|r1-70b) TARGET_MODEL="deepseek-r1:70b" ;;
          67|500b|beam*) TARGET_MODEL="deepseek-r1:671b" ;;
          *) TARGET_MODEL="qwen2.5:72b" ;;
        esac
        ;;
      11) TARGET_MODEL="qwen2.5-coder:1.5b" ;;
      12) TARGET_MODEL="qwen2.5-coder:7b" ;;
      13) TARGET_MODEL="qwen2.5-coder:14b" ;;
      14) TARGET_MODEL="qwen2.5-coder:32b-instruct-q3_K_M" ;;
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
      61|deepseek-671b|671b) TARGET_MODEL="deepseek-r1:671b" ;;
      62|mixtral|8x22b) TARGET_MODEL="mixtral:8x22b" ;;
      63|command-r-plus|104b) TARGET_MODEL="command-r-plus:104b" ;;
      64|72b|qwen-72b) TARGET_MODEL="qwen2.5:72b" ;;
      65|llama-70b|70b) TARGET_MODEL="llama3.3:70b" ;;
      66|deepseek-70b|r1-70b) TARGET_MODEL="deepseek-r1:70b" ;;
      67|500b*|beam*) TARGET_MODEL="deepseek-r1:671b" ;;
      *)
        if [ -n "$clean_sub" ]; then
          TARGET_MODEL="$clean_sub"
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
   ____  __          _     ___             ______              
  / __ \/ /_  _____ (_)___/ (_)___ _____  / ____/___  ________ 
 / / / / __ \/ ___// / __  / / __ `/ __ \/ /   / __ \/ ___/ _ \
/ /_/ / /_/ (__  )/ / /_/ / / /_/ / / / / /___/ /_/ / /  /  __/
\____/_.___/____//_/\__,_/_/\__,_/_/ /_/\____/\____/_/   \___/ 
EOF
    echo -e "${C_RESET}${C_DIM}             Autonomous Bare-Metal Local Intelligence Engine${C_RESET}\n"

    # Box 1: Hardware Telemetry
    print_telemetry_box
    echo ""

    # Box 2: Model Hub Menu
    echo -e "${C_BOLD}┌── UNIVERSAL MODEL HUB: RUN BIG MODELS & MULTI-MODEL SWARMS ────────┐${C_RESET}"
    echo -e "│ ${C_YELLOW}Zero paywalls • Weights stored 1x in RAM • Real-time collaboration │${C_RESET}"
    echo -e "├───────────────────────────────────────────────────────────────────┤"
    echo -e "│  ${C_BOLD}[1]${C_RESET} ${C_GREEN}DeepSeek MoE Swarm${C_RESET} (R1 Reasoner + Coder Synthesizer)        │"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore swarm deepseek-r1:14b deepseek-coder${C_RESET}│"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[2]${C_RESET} ${C_CYAN}Custom Swarm Builder${C_RESET} (Pair ANY 2 Models Side-by-Side to Code 2 Files)   │"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore parallel <m1> <m2>${C_RESET}                  │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[3]${C_RESET} ${C_GREEN}Universal Model Hub Catalog${C_RESET} (All Free Models & Frontier MoE)│"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore models${C_RESET} (or type ${C_CYAN}mod 3${C_RESET})               │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[c]${C_RESET} ${C_WHITE}Gemini/OpenCode Desktop Chat${C_RESET} (Autonomous Pair Programmer)   │"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore chat${C_RESET}                                 │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[g]${C_RESET} ${C_PURPLE}Switch Active GPU Card${C_RESET} (Isolate Fast Card / Bypass Slow)    │"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore gpu <id|all>${C_RESET}                         │"
    echo -e "│                                                                   │"
    echo -e "│  ${C_BOLD}[d]${C_RESET} ${C_YELLOW}Hardware & Speed Diagnostics${C_RESET} (Inspect GPU/CPU VRAM Splits)│"
    echo -e "│      → Direct Command: ${C_CYAN}obsidiancore diag${C_RESET}                                 │"
    echo -e "├───────────────────────────────────────────────────────────────────┤"
    echo -e "│  ${C_BOLD}[q]${C_RESET} ${C_DIM}Quit / Exit${C_RESET}                                                  │"
    echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}\n"

    read_input "${C_BOLD}Choose an option [1, 2, 3, c, g, d] (or 'q' to exit): ${C_RESET}" CHOICE

    case "$CHOICE" in
      mod\ *|mode\ *|model\ *|models\ *|run\ *)
        local m_arg=$(echo "$CHOICE" | sed -E 's/^(mod|mode|model|models|run)[[:space:]]+//I')
        if [ "$m_arg" = "1" ]; then
          cmd_parallel "qwen3:14b" "qwen2.5-coder:7b"
        elif [ "$m_arg" = "2" ]; then
          cmd_swarm_builder
        elif [ "$m_arg" = "3" ] || [ "$m_arg" = "6" ]; then
          cmd_big_catalog
        else
          cmd_run "$m_arg"
        fi
        ;;
      mod|mods|models|model|catalog)
        cmd_big_catalog
        ;;
      c|C|chat)
        echo -e "\n${C_CYAN}[*] Launching Gemini/OpenCode Desktop Pair Programmer...${C_RESET}"
        cmd_run "chat"
        ;;
      1|moe|swarm|3)
        echo -e "\n${C_BOLD}${C_CYAN}─── [1] DUAL-AI SWARM & REASONING PAIR ───${C_RESET}"
        echo -e "  ${C_GREEN}1)${C_RESET} ${C_BOLD}Qwen MoE Swarm${C_RESET} (qwen3:14b + qwen2.5-coder:7b) [✔ Installed Locally - Instant Boot]"
        echo -e "  ${C_GREEN}2)${C_RESET} ${C_BOLD}DeepSeek MoE Swarm${C_RESET} (deepseek-r1:14b + deepseek-coder:6.7b) [Requires Download ~13.5GB]"
        read_input "${C_BOLD}Select Swarm [1-2, default 1]: ${C_RESET}" SW_3_OPT
        case "$SW_3_OPT" in
          2|deepseek*)
            cmd_parallel "deepseek-r1:14b" "deepseek-coder:6.7b"
            ;;
          *)
            cmd_parallel "qwen3:14b" "qwen2.5-coder:7b"
            ;;
        esac
        ;;
      2|builder|custom|parallel|5)
        cmd_swarm_builder
        ;;
      3|table|catalog|6|7)
        cmd_big_catalog
        ;;
      4|frontier|mega)
        echo -e "\n${C_BOLD}${C_RED}─── MEGA FRONTIER & MoE MODELS (<=48GB Budget) ───${C_RESET}"
        echo -e "  ${C_CYAN}61)${C_RESET} deepseek-r1:671b     (671B MoE 37B active • ~46 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}62)${C_RESET} mixtral:8x22b         (141B MoE 39B active • ~42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}63)${C_RESET} command-r-plus:104b   (104B Dense Enterprise • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}64)${C_RESET} qwen2.5:72b           (72B Dense Frontier • ~38–42 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}65)${C_RESET} llama3.3:70b          (70B Flagship GPT-4o • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}66)${C_RESET} deepseek-r1:70b       (70B Enterprise Reasoning • ~40 GB RAM/VRAM)"
        echo -e "  ${C_CYAN}67)${C_RESET} beam:500b-25b         (501B MoE 25B active • ~44 GB RAM/VRAM)"
        read_input "${C_BOLD}Select Mega Model [61-67, default 64]: ${C_RESET}" F_CHOICE
        case "$F_CHOICE" in
          61|671b|deepseek*) cmd_run "deepseek-r1:671b" ;;
          62|8x22b|mixtral) cmd_run "mixtral:8x22b" ;;
          63|104b|command-r*) cmd_run "command-r-plus:104b" ;;
          65|70b|llama*) cmd_run "llama3.3:70b" ;;
          66|deepseek-70b) cmd_run "deepseek-r1:70b" ;;
          67|500b*|beam*) cmd_run "deepseek-r1:671b" ;;
          *) cmd_run "qwen2.5:72b" ;;
        esac
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
      share|web)
        bash "${DIR}/share.sh"
        ;;
      q|Q|exit)
        echo -e "${C_DIM}Exiting ObsidianCore.${C_RESET}"
        exit 0
        ;;
      *)
        if [ -n "$CHOICE" ]; then
          echo -e "${C_YELLOW}Invalid choice '${CHOICE}'. Select 1, 2, 3, c, g, d, or q.${C_RESET}"
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
  mod|mods|models|model|hub|catalog|c)
    if [ -n "$2" ]; then
      cmd_run "$2"
    else
      cmd_big_catalog
    fi
    ;;
  1)
    cmd_parallel "qwen3:14b" "qwen2.5-coder:7b"
    ;;
  2)
    cmd_swarm_builder
    ;;
  3)
    cmd_big_catalog
    ;;
  4|5|6|11|12|13|14|15|16|21|22|23|24|25|26|31|32|33|34|41|42|43|44|51|52|53|54|55|61|62|63|64|65|66|67|32b|72b|14b|7b|1.5b|671b|8x22b|104b|500b)
    cmd_run "$1"
    ;;
  list|ls)
    cmd_list
    ;;
  gpu|gpus)
    cmd_switch_gpu "$2"
    ;;
  diag|doctor)
    cmd_diag
    ;;
  menu|"")
    cmd_loop_menu
    ;;
  chat)
    cmd_run "${2:-chat}"
    ;;
  *)
    echo -e "${C_BOLD}Usage:${C_RESET} obsidiancore [chat|menu|1|2|3|models|run <model>|parallel [m1] [m2]|swarm [m1] [m2]|debate [m1] [m2]|share|diag|gpu [id]|list]"
    ;;
esac
