#!/usr/bin/env bash
# ==============================================================================
# Colibristream — Terminal Visual Viewport
# Renders the exact 1-page visual directly inside your SSH terminal
# ==============================================================================

# ANSI styling
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_GREEN="\033[38;5;48m"
C_CYAN="\033[38;5;45m"
C_WHITE="\033[38;5;255m"
C_GRAY="\033[38;5;244m"
C_DARK="\033[38;5;236m"
C_BG="\033[48;5;234m"

if [ -t 1 ] && command -v clear >/dev/null 2>&1; then
  clear 2>/dev/null || true
fi

echo ""
echo -e "       ${C_DARK}┌─────────────────────────────────────────────────────────────┐${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}  ${C_GREEN}● BARE-METAL v0.1.0${C_RESET}                               ${C_GRAY}github ↗${C_RESET}  ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}                                                             ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}                      ${C_BOLD}${C_WHITE}colibri${C_GREEN}stream${C_RESET}                          ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}                                                             ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}    ${C_GRAY}Run massive AI models on bare metal for ${C_GREEN}${C_BOLD}free${C_RESET}${C_GRAY}.${C_RESET}             ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}  ${C_GRAY}Multi-AI swarms that talk ${C_GREEN}${C_BOLD}without eating your RAM${C_RESET}${C_GRAY}.${C_RESET}          ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}     ${C_GRAY}Zero cloud. Zero subscriptions. ${C_GREEN}${C_BOLD}100% private${C_RESET}${C_GRAY}.${C_RESET}            ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}                                                             ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}   ${C_BG}${C_WHITE}  ${C_GREEN}\$${C_WHITE} curl -fsSL https://colibristream.run | bash   ${C_GREEN}[ Copy ]${C_RESET}   ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}                                                             ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}│${C_RESET}              ${C_DIM}Paste into your terminal to launch${C_RESET}              ${C_DARK}│${C_RESET}"
echo -e "       ${C_DARK}└─────────────────────────────────────────────────────────────┘${C_RESET}"
echo ""
echo -e "${C_DIM}Run ${C_GREEN}./launch.sh${C_DIM} to execute this command and boot the hardware scan.${C_RESET}"
echo ""
