#!/usr/bin/env bash
# ==============================================================================
# Colibristream Worldwide Share — Zero-Password Global Access Engine
# Automatically starts local server, creates encrypted public HTTPS tunnel,
# updates the installer, and gives you instant access from ANY computer or phone.
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/.colistream"
mkdir -p "$LOG_DIR"
TUNNEL_LOG="${LOG_DIR}/tunnel_share.log"

# Terminal Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_YELLOW="\033[38;5;220m"
C_PURPLE="\033[38;5;141m"
C_WHITE="\033[38;5;255m"

# Ensure cloudflared exists in user space (~/.local/bin) without sudo
CLOUDFLARED_BIN=""
if command -v cloudflared >/dev/null 2>&1; then
  CLOUDFLARED_BIN="$(command -v cloudflared)"
elif [ -f "${HOME}/.local/bin/cloudflared" ]; then
  CLOUDFLARED_BIN="${HOME}/.local/bin/cloudflared"
else
  echo -e "${C_CYAN}[*] Downloading zero-dependency user-space tunnel engine (no password needed)...${C_RESET}"
  mkdir -p "${HOME}/.local/bin"
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64)  CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
    aarch64) CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" ;;
    *)       CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" ;;
  esac
  curl -fsSL "$CF_URL" -o "${HOME}/.local/bin/cloudflared"
  chmod +x "${HOME}/.local/bin/cloudflared"
  CLOUDFLARED_BIN="${HOME}/.local/bin/cloudflared"
fi

# Detect Local IP (for same-WiFi access)
LOCAL_IP=""
if command -v ip >/dev/null 2>&1; then
  LOCAL_IP=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1 || echo "")
fi

# Step 1: Ensure local web server is running on port 8888 (User space, no sudo)
HTTP_SPAWNED=0
if ! curl -s -I http://localhost:8888/ >/dev/null 2>&1; then
  echo -e "${C_CYAN}[1/3] Starting local zero-password web server on port 8888...${C_RESET}"
  python3 -m http.server 8888 --directory "$DIR" >/dev/null 2>&1 &
  HTTP_PID=$!
  HTTP_SPAWNED=1
  sleep 1
else
  echo -e "${C_GREEN}[1/3] Local web server is already active on port 8888.${C_RESET}"
fi

# Step 2: Launch Encrypted Cloudflare Tunnel (User space, no sudo)
echo -e "${C_CYAN}[2/3] Establishing encrypted worldwide HTTPS tunnel...${C_RESET}"
rm -f "$TUNNEL_LOG"
"$CLOUDFLARED_BIN" tunnel --url http://localhost:8888 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# Step 3: Wait for Public URL to establish (max 10 seconds)
PUBLIC_URL=""
for i in {1..20}; do
  if [ -f "$TUNNEL_LOG" ]; then
    PUBLIC_URL=$(grep -o 'https://[-a-z0-9]*\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1 || true)
    if [ -n "$PUBLIC_URL" ]; then
      break
    fi
  fi
  sleep 0.5
done

if [ -z "$PUBLIC_URL" ]; then
  echo -e "${C_YELLOW}[!] Tunnel handshake timed out. Checking background log...${C_RESET}"
  cat "$TUNNEL_LOG" 2>/dev/null || true
  exit 1
fi

# Step 4: Auto-update index.html and web/index.html to point to this live worldwide URL
echo -e "${C_CYAN}[3/3] Auto-configuring website and universal installer...${C_RESET}"

# Patch index.html dynamically
sed -i "s|const PUBLIC_INSTALL_CMD = .*|const PUBLIC_INSTALL_CMD = \"curl -fsSL ${PUBLIC_URL}/install.sh \| bash\";|g" "${DIR}/index.html" "${DIR}/web/index.html" 2>/dev/null || true
sed -i "s|<span>curl -fsSL .*/install.sh \| bash</span>|<span>curl -fsSL ${PUBLIC_URL}/install.sh \| bash</span>|g" "${DIR}/index.html" "${DIR}/web/index.html" 2>/dev/null || true

# Rebuild standalone installer so curling the URL extracts the complete engine
if [ -f "/tmp/generate_standalone_installer.sh" ]; then
  bash /tmp/generate_standalone_installer.sh >/dev/null 2>&1 || true
fi

# Cleanup on exit (Ctrl+C)
cleanup() {
  echo -e "\n\n${C_YELLOW}[*] Shutting down worldwide share tunnel...${C_RESET}"
  kill "$TUNNEL_PID" 2>/dev/null || true
  if [ "$HTTP_SPAWNED" -eq 1 ]; then
    kill "$HTTP_PID" 2>/dev/null || true
  fi
  # Restore index.html to universal GitHub raw installer URL
  sed -i "s|const PUBLIC_INSTALL_CMD = .*|const PUBLIC_INSTALL_CMD = \"curl -fsSL https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh \| bash\";|g" "${DIR}/index.html" "${DIR}/web/index.html" 2>/dev/null || true
  sed -i "s|<span>curl -fsSL .*/install.sh \| bash</span>|<span>curl -fsSL https://raw.githubusercontent.com/joinvilloic57-arch/ColibriStream/main/install.sh \| bash</span>|g" "${DIR}/index.html" "${DIR}/web/index.html" 2>/dev/null || true
  echo -e "${C_GREEN}✔ Cleaned up. Universal GitHub installer restored.${C_RESET}"
  exit 0
}
trap cleanup SIGINT SIGTERM

clear 2>/dev/null || true
echo -e "${C_GREEN}${C_BOLD}"
cat << "BANNER"
   ______      ___ __          _      __                         
  / ____/___  / (_) /_  _____ (_)____/ /__________  ____ _____ ___ 
 / /   / __ \/ / / __ \/ ___// / ___/ __/ ___/ _ \/ __ `/ __ `__ \
/ /___/ /_/ / / / /_/ / /   / (__  ) /_/ /  /  __/ /_/ / / / / / /
\____/\____/_/_/_.___/_/   /_/____/\__/_/   \___/\__,_/_/ /_/ /_/ 
BANNER
echo -e "${C_RESET}${C_DIM}           Worldwide Gateway • Zero Password • Instant Access Everywhere${C_RESET}\n"

echo -e "${C_GREEN}${C_BOLD}╔════════════════════════════════════════════════════════════════════════════════╗${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}║          COLIBRISTREAM IS NOW LIVE WORLDWIDE (ZERO PASSWORDS NEEDED)           ║${C_RESET}"
echo -e "${C_GREEN}${C_BOLD}╚════════════════════════════════════════════════════════════════════════════════╝${C_RESET}\n"

echo -e "${C_BOLD}🌐 WEB ACCESS FROM ANY DEVICE (Phone, Laptop, Tablet, PC):${C_RESET}"
echo -e "   👉 ${C_CYAN}${C_BOLD}${PUBLIC_URL}${C_RESET}\n"

echo -e "${C_BOLD}💻 1-LINE INSTALL COMMAND (Paste into terminal on ANY computer):${C_RESET}"
echo -e "   👉 ${C_GREEN}${C_BOLD}curl -fsSL ${PUBLIC_URL}/install.sh | bash${C_RESET}\n"

if [ -n "$LOCAL_IP" ]; then
  echo -e "${C_DIM}📡 Same Local Network Alternative (Wi-Fi):${C_RESET}"
  echo -e "   👉 ${C_WHITE}http://${LOCAL_IP}:8888${C_RESET}\n"
fi

echo -e "${C_DIM}──────────────────────────────────────────────────────────────────────────────────${C_RESET}"
echo -e "${C_GREEN}✔ 100% User-Space — Zero sudo, zero root, zero passwords required!${C_RESET}"
echo -e "${C_GREEN}✔ Works on ANY computer across the internet (Linux, Mac, WSL)!${C_RESET}"
echo -e "${C_YELLOW}Press [Ctrl+C] to stop sharing.${C_RESET}\n"

# Keep running until Ctrl+C
wait "$TUNNEL_PID"
