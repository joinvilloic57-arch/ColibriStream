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

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[38;5;48m"
C_CYAN = "\033[38;5;45m"
C_YELLOW = "\033[38;5;220m"
C_PURPLE = "\033[38;5;141m"
C_GRAY = "\033[38;5;244m"
C_WHITE = "\033[38;5;255m"

def stream_chat(model_name, messages, api_url="http://localhost:11434/api/chat"):
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.7
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
    
    full_response = []
    start_time = time.time()
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
    
    return "".join(full_response), 0, 0

def run_chat_session(model_name):
    os.system("clear 2>/dev/null || true")
    print(f"{C_GREEN}{C_BOLD}┌────────────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}│  COLIBRISTREAM DESKTOP AI — BARE-METAL CHAT SESSION                     │{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}├────────────────────────────────────────────────────────────────────────┤{C_RESET}")
    print(f"│  {C_CYAN}Active Model:{C_RESET} {C_BOLD}{model_name:<30}{C_RESET} {C_GRAY}[100% Local • Zero Cloud]{C_RESET}   │")
    print(f"│  {C_DIM}Commands:{C_RESET}    {C_YELLOW}/menu{C_RESET} (Back to Menu) | {C_YELLOW}/clear{C_RESET} (Reset Context) | {C_YELLOW}/exit{C_RESET}      │")
    print(f"{C_GREEN}{C_BOLD}└────────────────────────────────────────────────────────────────────────┘{C_RESET}\n")

    history = [
        {"role": "system", "content": "You are a helpful, expert AI running locally on bare-metal hardware via Colibristream. Be concise, fast, and write clean code."}
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
            history = [history[0]]
            print(f"{C_YELLOW}✔ Conversation context cleared.{C_RESET}")
            continue

        history.append({"role": "user", "content": prompt})

        print(f"\n{C_BOLD}{C_CYAN}{model_name} ❯ {C_RESET}", end="", flush=True)
        response_text, speed, tokens = stream_chat(model_name, history)
        history.append({"role": "assistant", "content": response_text})

        speed_str = f"{speed:.1f} tok/s" if speed > 0 else ""
        print(f"\n{C_DIM}└─ [{tokens} tokens {speed_str}]{C_RESET}")

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b"
    run_chat_session(model)
