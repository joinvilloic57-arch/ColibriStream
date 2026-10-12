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
    print(f"\n{C_BOLD}{C_GREEN}┌── COLIBRISTREAM AUTONOMOUS CODING AGENT COMMANDS ────────────────┐{C_RESET}")
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
        return "beam:500b-25b"
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
    if nl in ("14b", "14", "qwen-14b", "qwen3-14b"):
        return "qwen3:14b"
    if nl in ("1.5b", "1.5", "qwen-1.5b"):
        return "qwen2.5-coder:1.5b"
    if nl in ("7b", "7", "qwen-7b"):
        return "qwen2.5-coder:7b"
    return n

def get_gpu_count():
    env_active = os.environ.get("ACTIVE_GPU", "").strip()
    if env_active == "all":
        return 2
    cuda_vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if cuda_vis == "all":
        return 2
    if "," in cuda_vis:
        return len([c for c in cuda_vis.split(",") if c.strip()])
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        lines = [l for l in out.splitlines() if l.strip()]
        if len(lines) > 0:
            return len(lines)
    except Exception:
        pass
    cfg_file = os.path.expanduser("~/.colistream/gpu_config")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                if f.read().strip() == "all":
                    return 2
        except Exception:
            pass
    try:
        import subprocess
        out = subprocess.check_output("lspci 2>/dev/null | grep -iE 'vga compatible controller|3d controller|display controller' | wc -l", shell=True).decode().strip()
        if int(out) > 1:
            return int(out)
    except Exception:
        pass
    return 1

def get_visible_vram_mb():
    cfg_file = os.path.expanduser("~/.colistream/gpu_config")
    active_gpu = os.environ.get("ACTIVE_GPU", "").strip() or None
    if not active_gpu and os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                active_gpu = f.read().strip()
        except Exception:
            pass

    gpu_cnt = get_gpu_count()
    if active_gpu == "all" or gpu_cnt > 1:
        env_cuda = "all"
    else:
        env_cuda = os.environ.get("CUDA_VISIBLE_DEVICES", active_gpu or "0")

    try:
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
        if total_vram > 0:
            return total_vram
    except Exception:
        pass
    return 49152 if (active_gpu == "all" or gpu_cnt > 1) else 24576

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
    is_giant = any(x in m_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "405b", "beam"])
    is_32b = any(x in m_lower for x in ["32b", "30b", "27b"])

    gpu_cnt = get_gpu_count()
    cfg_file = os.path.expanduser("~/.colistream/gpu_config")
    active_gpu_cfg = ""
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                active_gpu_cfg = f.read().strip()
        except Exception:
            pass
    is_multi_gpu = (gpu_cnt > 1 or vram_mb >= 36000 or active_gpu_cfg == "all")

    if is_giant:
        if is_multi_gpu or vram_mb >= 44000:
            # Multi-GPU / 48GB VRAM Mode: 100% offload capped to 48 GB budget
            num_gpu_layers = 99
            num_ctx_val = 2048
            num_batch_val = 512
        else:
            # Single 24GB card mode: Offload partial layers (~21.5 GB VRAM)
            num_gpu_layers = 48
            num_ctx_val = 1536
            num_batch_val = 512
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
    gpu_cnt = get_gpu_count()
    is_70b = any(x in m_lower for x in ["70b", "72b", "671b"])
    num_gpu_layers = 99 if (gpu_cnt > 1 or vram_mb >= 36000 or not is_70b) else 38
    num_ctx_val = 2048 if (gpu_cnt > 1 or vram_mb >= 36000 or not is_70b) else 1536

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

def detect_swarm_file_targets(prompt):
    tokens = re.findall(r'[a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]{1,6}', prompt)
    valid_files = [t for t in tokens if not t.startswith(('http', 'www')) and not t.endswith(('.com', '.org', '.net', '.io'))]
    if len(valid_files) >= 2:
        return valid_files[0], valid_files[1]
    elif len(valid_files) == 1:
        f1 = valid_files[0]
        ext = f1.split('.')[-1]
        base = f1.rsplit('.', 1)[0]
        return f1, f"{base}_worker.{ext}"

    p_low = prompt.lower()
    pairs = [
        (('rust', 'server'), ('c', 'client'), ('server.rs', 'client.c')),
        (('c', 'server'), ('rust', 'client'), ('server.c', 'client.rs')),
        (('python', 'backend'), ('frontend', 'js'), ('backend.py', 'frontend.js')),
        (('python', 'server'), ('client',), ('server.py', 'client.py')),
        (('rust',), ('c',), ('server.rs', 'client.c')),
        (('c',), ('assembly',), ('engine.c', 'kernel.s')),
        (('asm',), ('c',), ('kernel.s', 'main.c')),
        (('backend',), ('frontend',), ('backend.py', 'frontend.js')),
        (('server',), ('client',), ('server.py', 'client.py')),
        (('rust',), ('python',), ('core.rs', 'binding.py')),
        (('html',), ('css',), ('index.html', 'style.css')),
    ]
    for c1, c2, (f1, f2) in pairs:
        if all(w in p_low for w in c1) and all(w in p_low for w in c2):
            return f1, f2

    if 'rust' in p_low:
        return 'server.rs', 'client.c'
    if 'c' in p_low:
        return 'server.c', 'client.c'
    if 'python' in p_low or 'py' in p_low:
        return 'server.py', 'client.py'
    if 'go' in p_low:
        return 'server.go', 'client.go'
    if 'html' in p_low or 'web' in p_low:
        return 'index.html', 'app.js'
    return 'core_service.rs', 'worker_client.c'

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
    total_cpus = os.cpu_count() or 8
    # Keep thread pool within single NUMA socket (max 8 threads) to maximize L3 cache hits & avoid QPI bus thrashing
    opt_threads = min(8, max(4, total_cpus // 10))
    vram_mb = get_visible_vram_mb()
    gpu_cnt = get_gpu_count()
    cfg_file = os.path.expanduser("~/.colistream/gpu_config")
    active_gpu_cfg = ""
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r") as f:
                active_gpu_cfg = f.read().strip()
        except Exception:
            pass
    is_multi_gpu = (gpu_cnt > 1 or vram_mb >= 36000 or active_gpu_cfg == "all")

    m_lower = model_name.lower()
    is_giant = any(x in m_lower for x in ["70b", "72b", "671b", "500b", "501b", "8x22b", "104b", "405b", "beam"])
    
    if is_dual_70b and is_giant:
        # Dual giant models: Capped strictly to 36-40 GB max combined VRAM (under 48GB limit)
        num_gpu_layers = 33
        num_ctx_val = 2048
    elif is_giant:
        if is_multi_gpu or vram_mb >= 44000:
            # 48GB VRAM limit respected
            num_gpu_layers = 99
            num_ctx_val = 2048
        else:
            num_gpu_layers = 48
            num_ctx_val = 1536
    else:
        num_gpu_layers = 99
        num_ctx_val = 2048

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
    start_t = time.time()
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
                        if eval_dur > 0:
                            stats_holder["speed"] = eval_cnt / eval_dur
                        stats_holder["tokens"] = eval_cnt
                        break
                except Exception:
                    pass
    except Exception as e:
        text_holder[0] += f"\n[Inference Error: {e}]"
    finally:
        done_event.set()

_PARALLEL_BACKEND_PROC = None

def _cleanup_parallel_backend():
    global _PARALLEL_BACKEND_PROC
    if _PARALLEL_BACKEND_PROC is not None:
        try:
            _PARALLEL_BACKEND_PROC.terminate()
            _PARALLEL_BACKEND_PROC.wait(timeout=2)
        except Exception:
            try:
                _PARALLEL_BACKEND_PROC.kill()
            except Exception:
                pass
        _PARALLEL_BACKEND_PROC = None

atexit.register(_cleanup_parallel_backend)

def ensure_parallel_backend(model1, model2):
    global _PARALLEL_BACKEND_PROC
    target_port = 11435

    def _warm_on_port(port, m):
        try:
            url = f"http://127.0.0.1:{port}/api/generate"
            payload = {"model": resolve_model_name(m), "keep_alive": "30m"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
            return True
        except Exception:
            return False

    print(f"\n{C_CYAN}[*] Initializing dedicated multi-model engine (Port 11435: 4 Concurrent Slots)...{C_RESET}")
    is_11435_alive = False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{target_port}/api/tags", timeout=1) as resp:
            is_11435_alive = (resp.status == 200)
    except Exception:
        is_11435_alive = False

    if not is_11435_alive:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{target_port}"
        if os.path.exists("/usr/share/ollama/.ollama/models"):
            env["OLLAMA_MODELS"] = "/usr/share/ollama/.ollama/models"
        env["OLLAMA_NOPRUNE"] = "true"
        env["OLLAMA_MAX_LOADED_MODELS"] = "4"
        env["OLLAMA_NUM_PARALLEL"] = "4"
        env["OLLAMA_KEEP_ALIVE"] = "30m"
        
        ollama_bin = "/usr/local/bin/ollama" if os.path.exists("/usr/local/bin/ollama") else "ollama"
        _PARALLEL_BACKEND_PROC = subprocess.Popen(
            [ollama_bin, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{target_port}/api/tags", timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.3)

    print(f"  • Pre-warming Model 1 ({model1}) and Model 2 ({model2}) in parallel...")
    th_w1 = threading.Thread(target=_warm_on_port, args=(target_port, model1), daemon=True)
    th_w2 = threading.Thread(target=_warm_on_port, args=(target_port, model2), daemon=True)
    th_w1.start()
    th_w2.start()
    th_w1.join()
    th_w2.join()
    print(f"{C_GREEN}✔ Dedicated Multi-Model Engine Ready! Both models locked in memory simultaneously.{C_RESET}")
    time.sleep(1)
    return f"http://127.0.0.1:{target_port}"

def run_parallel_swarm_session(model1_name, model2_name):
    model1 = resolve_model_name(model1_name)
    model2 = resolve_model_name(model2_name)
    ensure_model_installed(model1)
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
    print(f"\n{C_GREEN}{C_BOLD}⚡ COLIBRISTREAM DUAL-AI ADAPTIVE SWARM{C_RESET}")
    print(f"  {C_GREEN}• Lead Architect (Heavy Reasoning){C_RESET}: {C_WHITE}{C_BOLD}{lead_model}{C_RESET}")
    print(f"  {C_CYAN}• Fast Copilot   (Quick Responses){C_RESET}: {C_WHITE}{C_BOLD}{fast_model}{C_RESET}")
    print(f"  {C_YELLOW}• Adaptive Dispatch{C_RESET}: Fast answers for simple tasks • Deep compute on big model • Auto-handoff • Dual parallel code")
    print(f"  {C_GRAY}• Commands: /models | /1 <msg> | /2 <msg> | /assign <f1> <f2> | !cmd | /diff | /clear | /exit{C_RESET}")
    print(f"{C_GRAY}───────────────────────────────────────────────────────────────────────{C_RESET}")

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
            prompt = input(f"\n{C_BOLD}{C_GREEN}Dual Swarm Task ❯ {C_RESET}").strip()
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
            sys_m = f"You are {lead_model}, Lead Architect in Colibristream. Answer the user's question directly, accurately, and thoroughly."
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
            sys_m = f"You are {fast_model}, fast assistant in Colibristream. Answer the user's question directly, accurately, and concisely."
            msgs = [{"role": "system", "content": sys_m}] + list(m2_history) + [{"role": "user", "content": direct_q}]
            ans, _, _ = stream_chat(fast_model, msgs, color=C_CYAN, api_url=f"{api_base}/api/chat")
            m2_history.append({"role": "user", "content": direct_q})
            m2_history.append({"role": "assistant", "content": ans})
            last_solutions["2"] = ans
            apply_model_edits(ans, user_prompt=direct_q)
            continue

        last_user_prompt = prompt
        task_mode = classify_task_mode(prompt, assigned_targets)

        # ─── CASE 1: Fast Responsive Query (Simple Questions, Chat, Quick Lookups) ───
        if task_mode == "fast_response":
            print(f"\n{C_CYAN}{C_BOLD}🔍 Fast Copilot ({fast_model}):{C_RESET}")
            fast_sys = (
                f"You are {fast_model}, an agile local AI assistant in Colibristream.\n"
                f"Answer the user's request directly, accurately, and concisely.\n"
                f"Do NOT invent unrelated files or source code unless specifically requested.\n"
                f"If this task requires deep architectural computation or frontier math beyond your capability, conclude with '[NEED_ARCHITECT]'."
            )
            files_ctx = "\nActive Workspace Files:\n" + "\n".join(tracked_files.keys()) if tracked_files else ""
            msgs = [{"role": "system", "content": fast_sys + files_ctx}] + list(m2_history) + [{"role": "user", "content": prompt}]
            ans, spd, toks = stream_chat(fast_model, msgs, color=C_CYAN, api_url=f"{api_base}/api/chat")

            # Check if Fast Model requested Handoff / Escalation to Lead Architect
            if "[NEED_ARCHITECT]" in ans or "need_architect" in ans.lower():
                clean_ans = ans.replace("[NEED_ARCHITECT]", "").strip()
                print(f"\n\n{C_YELLOW}⚡ Copilot requested handoff: Escalating to Lead Architect ({lead_model})...{C_RESET}")
                lead_sys = (
                    f"You are {lead_model}, Lead Architect in Colibristream.\n"
                    f"Your copilot ({fast_model}) requested your deep reasoning on this user request.\n"
                    f"Provide an authoritative, in-depth solution addressing the request directly."
                )
                lead_msgs = [{"role": "system", "content": lead_sys}] + list(m1_history) + [
                    {"role": "user", "content": f"{prompt}\n\n[Copilot Notes]: {clean_ans}"}
                ]
                print(f"{C_GREEN}{C_BOLD}🧠 Lead Architect ({lead_model}) [Authoritative Resolution]:{C_RESET}")
                lead_ans, _, _ = stream_chat(lead_model, lead_msgs, color=C_GREEN, api_url=f"{api_base}/api/chat")
                m1_history.append({"role": "user", "content": prompt})
                m1_history.append({"role": "assistant", "content": lead_ans})
                last_solutions["1"] = lead_ans
                apply_model_edits(lead_ans, user_prompt=prompt)
            else:
                m2_history.append({"role": "user", "content": prompt})
                m2_history.append({"role": "assistant", "content": ans})
                last_solutions["2"] = ans
                apply_model_edits(ans, user_prompt=prompt)
            continue

        # ─── CASE 2: Heavy Task on Big Model with Fast Copilot Assessment ───
        if task_mode == "heavy_architect":
            print(f"\n{C_CYAN}{C_BOLD}⚡ Fast Copilot ({fast_model}) [Initial Assessment]:{C_RESET}")
            quick_sys = f"You are {fast_model}. Give a brief 2-sentence initial assessment of this task while Lead Architect ({lead_model}) computes the complete solution."
            fast_brief, _, _ = stream_chat(fast_model, [{"role": "system", "content": quick_sys}, {"role": "user", "content": prompt}], color=C_CYAN, api_url=f"{api_base}/api/chat")

            print(f"\n\n{C_GREEN}{C_BOLD}🧠 Lead Architect ({lead_model}) [Comprehensive Solution]:{C_RESET}")
            files_ctx = build_system_prompt() if tracked_files else ""
            ctx_inject = f"\n\n{files_ctx}" if files_ctx else ""
            lead_sys = (
                f"You are {lead_model}, Lead Architect in Colibristream.\n"
                f"Provide a comprehensive, production-grade technical solution for the user's request."
            )
            lead_msgs = [{"role": "system", "content": lead_sys}] + list(m1_history) + [{"role": "user", "content": f"{prompt}{ctx_inject}"}]
            lead_ans, _, _ = stream_chat(lead_model, lead_msgs, color=C_GREEN, api_url=f"{api_base}/api/chat")
            m1_history.append({"role": "user", "content": prompt})
            m1_history.append({"role": "assistant", "content": lead_ans})
            last_solutions["1"] = lead_ans
            apply_model_edits(lead_ans, user_prompt=prompt)
            continue

        # ─── CASE 3 & 4: Dual Collaborative Planning or Dual Coding ───
        f1_cand, f2_cand = detect_swarm_file_targets(prompt)
        if task_mode == "dual_plan":
            file1 = assigned_targets[0] or (f1_cand if f1_cand != 'core_service.rs' else 'core_engine_spec.md')
            file2 = assigned_targets[1] or (f2_cand if f2_cand != 'worker_client.c' else 'interface_telemetry_spec.md')
            m1_sys = (
                f"You are Model 1 ({model1}) — Lead Engine & Systems Architect in a 2-AI collaborative swarm.\n"
                f"You and Model 2 ({model2}) are co-authoring the project plan together in real time without duplicating work.\n\n"
                f"YOUR EXCLUSIVE SCOPE (Low-Level Systems & Engine):\n"
                f"- Phase 3 & Phase 4: Low-level Core Engine, Bare-Metal Runtime (Rust/C/Assembly), Memory Mapping (mmap), and the Universal Local Model Hub.\n"
                f"- Output technical specification in markdown: ```write:{file1}\n"
            )
            m2_sys = (
                f"You are Model 2 ({model2}) — Interface & Integration Architect in a 2-AI collaborative swarm.\n"
                f"You and Model 1 ({model1}) are co-authoring the project plan together in real time without duplicating work.\n\n"
                f"YOUR EXCLUSIVE SCOPE (Client Interface & Telemetry Scanner):\n"
                f"- Phase 1 & Phase 2: Web Landing Page (sleek, zero bloat, dark terminal aesthetic) and CLI Transition.\n"
                f"- Output interface specification in markdown: ```write:{file2}\n"
            )
            m1_user_msg = f"[COLLABORATIVE TASK: Focus on Phase 3 & 4 (Core Engine, Runtime & Model Hub Architecture)]\n\nUser Request: {prompt}"
            m2_user_msg = f"[COLLABORATIVE TASK: Focus on Phase 1 & 2 (Web Landing Page, Terminal Interface & Hardware Scanner)]\n\nUser Request: {prompt}"
        else: # dual_code
            file1 = assigned_targets[0] or f1_cand
            file2 = assigned_targets[1] or f2_cand
            m1_sys = (
                f"You are Model 1 ({model1}) — Lead Engine & Backend Architect in a 2-AI simultaneous coding swarm.\n"
                f"YOUR RESPONSIBILITY: Component 1 ('{file1}'). Output code in: ```write:{file1}\n"
            )
            m2_sys = (
                f"You are Model 2 ({model2}) — Client & Integration Specialist in a 2-AI simultaneous coding swarm.\n"
                f"YOUR RESPONSIBILITY: Component 2 ('{file2}'). Output code in: ```write:{file2}\n"
            )
            m1_user_msg = f"[COLLABORATIVE TASK: Implement Component 1 in '{file1}']\n\nUser Request: {prompt}"
            m2_user_msg = f"[COLLABORATIVE TASK: Implement Component 2 in '{file2}' connecting to '{file1}']\n\nUser Request: {prompt}"

        m1_messages = [{"role": "system", "content": m1_sys}] + list(m1_history) + [{"role": "user", "content": m1_user_msg}]
        m2_messages = [{"role": "system", "content": m2_sys}] + list(m2_history) + [{"role": "user", "content": m2_user_msg}]

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

        th1 = threading.Thread(target=stream_model_tokens_concurrent, args=(model1, m1_messages, t1_text, t1_stats, done1, is_dual_70b, api_base), daemon=True)
        th2 = threading.Thread(target=stream_model_tokens_concurrent, args=(model2, m2_messages, t2_text, t2_stats, done2, is_dual_70b, api_base), daemon=True)
        th1.start()
        th2.start()

        print(f"\n{C_BOLD}{C_GREEN}⚡ Dual Swarm Generating ({model1} + {model2}):{C_RESET}")
        print(f"  {C_CYAN}• Model 1{C_RESET} -> {C_BOLD}{file1}{C_RESET}")
        print(f"  {C_PURPLE}• Model 2{C_RESET} -> {C_BOLD}{file2}{C_RESET}")
        print(f"{C_GRAY}───────────────────────────────────────────────────────────────────────{C_RESET}")

        start_time = time.time()
        try:
            sys.stdout.write("\033[?25l")
            while not (done1.is_set() and done2.is_set()):
                sniff1 = sniff_file_from_code(t1_text[0], file1)
                sniff2 = sniff_file_from_code(t2_text[0], file2)

                tok1 = t1_stats.get("tokens", 0)
                tok2 = t2_stats.get("tokens", 0)
                spd1 = t1_stats.get("speed", 0.0)
                spd2 = t2_stats.get("speed", 0.0)

                s1_text = f"{C_GREEN}DONE ({tok1} tok){C_RESET}" if done1.is_set() else (
                    f"{C_CYAN}{tok1} tok ({spd1:.1f} t/s){C_RESET}" if tok1 > 0 else f"{C_YELLOW}evaluating prompt...{C_RESET}"
                )
                s2_text = f"{C_GREEN}DONE ({tok2} tok){C_RESET}" if done2.is_set() else (
                    f"{C_PURPLE}{tok2} tok ({spd2:.1f} t/s){C_RESET}" if tok2 > 0 else f"{C_YELLOW}evaluating prompt...{C_RESET}"
                )

                elapsed = time.time() - start_time
                line = f"  🧠 M1 [{sniff1}]: {s1_text}  │  🔍 M2 [{sniff2}]: {s2_text}  ({elapsed:.1f}s)"
                sys.stdout.write(f"\r\033[K{line}")
                sys.stdout.flush()
                time.sleep(0.08)

            th1.join()
            th2.join()

            sys.stdout.write("\r\033[K")
            sniff1 = sniff_file_from_code(t1_text[0], file1)
            sniff2 = sniff_file_from_code(t2_text[0], file2)
            tok1 = t1_stats.get("tokens", 0)
            tok2 = t2_stats.get("tokens", 0)
            spd1 = t1_stats.get("speed", 0.0)
            spd2 = t2_stats.get("speed", 0.0)
            total_dur = time.time() - start_time
            print(f"  {C_GREEN}✔ Model 1 [{model1[:10]} -> {sniff1}]: {tok1} tokens ({spd1:.1f} t/s){C_RESET}")
            print(f"  {C_GREEN}✔ Model 2 [{model2[:10]} -> {sniff2}]: {tok2} tokens ({spd2:.1f} t/s) in {total_dur:.1f}s{C_RESET}")
            print(f"{C_GRAY}───────────────────────────────────────────────────────────────────────{C_RESET}")
        except KeyboardInterrupt:
            done1.set()
            done2.set()
            sys.stdout.write("\033[?25h\033[0m\n")
            sys.stdout.flush()
            print(f"\n{C_YELLOW}[!] Interrupted by user.{C_RESET}")
            continue
        finally:
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.flush()

        last_solutions["1"] = t1_text[0]
        last_solutions["2"] = t2_text[0]

        saved1 = apply_model_edits(t1_text[0], explicit_filename=sniff1, user_prompt=prompt)
        saved2 = apply_model_edits(t2_text[0], explicit_filename=sniff2, user_prompt=prompt)
        file1_saved = saved1[0] if saved1 else sniff1
        file2_saved = saved2[0] if saved2 else sniff2

        if not saved1 and t1_text[0].strip():
            code1 = extract_code_block(t1_text[0])
            if save_code_to_disk(file1_saved, code1):
                saved1 = [file1_saved]
        if not saved2 and t2_text[0].strip():
            code2 = extract_code_block(t2_text[0])
            if save_code_to_disk(file2_saved, code2):
                saved2 = [file2_saved]

        lines1_cnt = len(open(file1_saved, "r", errors="ignore").readlines()) if os.path.exists(file1_saved) else 0
        lines2_cnt = len(open(file2_saved, "r", errors="ignore").readlines()) if os.path.exists(file2_saved) else 0

        print(f"\n{C_BOLD}{C_GREEN}⚡ Dual Files Auto-Saved:{C_RESET}")
        print(f"  {C_GREEN}✔ Model 1 ({model1[:14]}):{C_RESET} {C_BOLD}{file1_saved}{C_RESET} ({lines1_cnt} lines on disk)")
        print(f"  {C_GREEN}✔ Model 2 ({model2[:14]}):{C_RESET} {C_BOLD}{file2_saved}{C_RESET} ({lines2_cnt} lines on disk)")

        m1_history.append({"role": "user", "content": prompt})
        m1_history.append({"role": "assistant", "content": t1_text[0]})
        m2_history.append({"role": "user", "content": prompt})
        m2_history.append({"role": "assistant", "content": t2_text[0]})

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
                    f"3. Provide complete, working code blocks tagged with the exact filename (e.g. ```write:filename.ext or put '# filename: filename.ext' on line 1) so Colibristream can save it directly to disk.\n"
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
                    f"4. Tag all code blocks with the exact filename (e.g. ```write:filename.ext or put '# filename: filename.ext' on line 1) so Colibristream can save it directly to disk.\n"
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
    last_response_text = ""
    last_user_prompt = ""

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
        last_user_prompt = prompt
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
            last_response_text = response_text
            # Autonomous Aider-style File Modification Engine
            apply_model_edits(response_text, user_prompt=prompt)

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
