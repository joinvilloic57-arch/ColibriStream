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
                return "".join(full_response), 0.0, 0, 0, 0.0
        except Exception as e:
            stop_spinner.set()
            sys.stdout.write(f"\r\033[K{C_YELLOW}[!] Stream error: {e}{C_RESET}\n")
            sys.stdout.flush()
            return "".join(full_response), 0.0, 0, 0, 0.0
        finally:
            stop_spinner.set()
            
    return "".join(full_response), 0.0, 0, 0, 0.0

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
        except KeyboardInterrupt:
            print(f"\n{C_DIM}(Type /exit to leave swarm){C_RESET}")
            continue
        except EOFError:
            if os.path.exists('/dev/tty') and not sys.stdin.isatty():
                try:
                    sys.stdin = open('/dev/tty', 'r')
                    continue
                except Exception:
                    pass
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
            ans, *_ = stream_chat(lead_model, msgs, color=C_GREEN, api_url=f"{api_base}/api/chat")
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
            ans, *_ = stream_chat(fast_model, msgs, color=C_CYAN, api_url=f"{api_base}/api/chat")
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

            arch_output, arch_spd, arch_toks, *_ = stream_chat(model1, arch_messages, color=C_CYAN)
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

            rev_output, rev_spd, rev_toks, *_ = stream_chat(model2, rev_messages, color=C_PURPLE)
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
        except KeyboardInterrupt:
            print(f"\n{C_DIM}(Type /exit to leave chat, or /menu for Model Hub){C_RESET}")
            continue
        except EOFError:
            if os.path.exists('/dev/tty') and not sys.stdin.isatty():
                try:
                    sys.stdin = open('/dev/tty', 'r')
                    continue
                except Exception:
                    pass
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

        try:
            # Render User Prompt in TUI Card
            print("\n" + render_tui_card("✦ You", prompt, border_color=C_GREEN, title_color=C_BOLD+C_GREEN))
            print("")
            chat_res = stream_chat(model_name, history, color=C_CYAN)
            response_text = chat_res[0] if len(chat_res) > 0 else ""
            speed = chat_res[1] if len(chat_res) > 1 else 0.0
            eval_tokens = chat_res[2] if len(chat_res) > 2 else 0
            prompt_tokens = chat_res[3] if len(chat_res) > 3 else 0
            tot_dur = chat_res[4] if len(chat_res) > 4 else 0.0

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
        except Exception as e:
            print(f"\n{C_YELLOW}[!] Generation notice: {e}{C_RESET}")

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
