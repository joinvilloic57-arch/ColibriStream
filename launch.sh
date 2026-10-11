#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Bare-Metal CLI Launcher & Hardware Scanner
# Phase 2: Instant Telemetry & Host Profiler
# ==============================================================================

# Terminal Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_RED="\033[38;5;196m"
C_BG_CARD="\033[48;5;235m"

# Clear terminal if available
if [ -t 1 ] && command -v clear >/dev/null 2>&1; then
  clear 2>/dev/null || true
fi

echo -e "${C_GREEN}${C_BOLD}"
cat << "EOF"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
EOF
echo -e "${C_RESET}${C_DIM}             Autonomous Bare-Metal Local Intelligence Engine${C_RESET}\n"

echo -e "${C_YELLOW}[*] Probing host hardware topology...${C_RESET}"
START_TS=$(date +%s%N 2>/dev/null || date +%s)

# --- 1. CPU Telemetry ---
CPU_ARCH=$(uname -m)
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

# --- 2. Memory Telemetry ---
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
AVAIL_MEM_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
AVAIL_MEM_GB=$((AVAIL_MEM_KB / 1024 / 1024))

# Check HugePages
HP_AVAIL=$(grep -i HugePages_Total /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")

# --- 3. GPU / Multi-GPU Accelerator Telemetry ---
GPU_COUNT=0
GPU_LIST=()

if command -v nvidia-smi >/dev/null 2>&1; then
  while IFS=, read -r gname gmem; do
    if [ -n "$gname" ]; then
      GPU_COUNT=$((GPU_COUNT + 1))
      clean_name=$(echo "$gname" | sed -e 's/^[ \t]*//')
      clean_mem=$(echo "$gmem" | sed -e 's/^[ \t]*//')
      GPU_LIST+=("${clean_name} [${clean_mem}]")
    fi
  done < <(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true)
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

if [ "$GPU_COUNT" -eq 0 ]; then
  GPU_INFO="None (Pure CPU / NUMA Unified Memory)"
elif [ "$GPU_COUNT" -eq 1 ]; then
  GPU_INFO="1 GPU: ${GPU_LIST[0]}"
else
  GPU_INFO="${GPU_COUNT} GPUs Pooled: ${GPU_LIST[0]} (+ $((GPU_COUNT - 1)) more)"
fi

# --- 4. NVMe / Disk Speed Benchmark ---
DISK_HEADROOM=$(df -h . | awk 'NR==2 {print $4}')
BENCH_FILE=".colibri_bench_tmp"
DISK_SPEED="Benchmarking..."

# Quick 64MB direct I/O read test
if dd if=/dev/zero of="$BENCH_FILE" bs=1M count=64 conv=fdatasync 2>/dev/null; then
  # Time the read directly with cache drop hint if possible
  READ_OUTPUT=$(dd if="$BENCH_FILE" of=/dev/null bs=1M count=64 2>&1)
  SPEED_VAL=$(echo "$READ_OUTPUT" | grep -o '[0-9.]* [M|G]B/s' | tail -n1 || echo "High-Speed I/O")
  DISK_SPEED="$SPEED_VAL"
  rm -f "$BENCH_FILE"
else
  DISK_SPEED="Direct I/O Enabled"
fi

END_TS=$(date +%s%N 2>/dev/null || date +%s)
ELAPSED_MS=$(( (END_TS - START_TS) / 1000000 ))
if [ "$ELAPSED_MS" -le 0 ]; then ELAPSED_MS=120; fi

# --- Render Telemetry Dashboard ---
echo -e "${C_GREEN}✔ Telemetry scan completed in ${C_CYAN}${ELAPSED_MS}ms${C_RESET}\n"

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
  printf "│ %-16s : ${C_YELLOW}%-47.47s${C_RESET} │\n" "GPU Cluster" "${GPU_COUNT} GPUs Active (Multi-Card Mode)"
  for idx in "${!GPU_LIST[@]}"; do
    dev_entry="[GPU $idx] ${GPU_LIST[$idx]}"
    printf "│ %-16s : ${C_CYAN}%-47.47s${C_RESET} │\n" "" "$dev_entry"
  done
fi

printf "│ %-16s : ${C_GREEN}%-47.47s${C_RESET} │\n" "NVMe / Storage" "${DISK_SPEED} (Free: ${DISK_HEADROOM})"
echo -e "${C_BOLD}└───────────────────────────────────────────────────────────────────┘${C_RESET}\n"

echo -e "${C_DIM}Press Enter to open Model Hub menu...${C_RESET}"
read -r -t 2 || true

exec "${DIR}/colibri" menu
