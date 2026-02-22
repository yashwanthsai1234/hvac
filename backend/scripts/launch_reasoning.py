"""Launch Claude Code in tmux to run LLM reasoning on all 129 triggers.

No API key needed — Claude Code handles the model calls itself.

Usage:
    python backend/scripts/launch_reasoning.py [--dry-run]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SESSION_NAME = "hvac-reasoning"
MODEL = "haiku"
PROMPT_FILE = Path(__file__).parent / "reasoning_prompt.md"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def tmux_session_exists(name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
    )
    return result.returncode == 0


def create_tmux_session(name: str) -> None:
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", name, "-x", "220", "-y", "50",
         "-c", str(PROJECT_ROOT)],
        check=True,
    )


def send_keys(name: str, text: str, enter: bool = True) -> None:
    subprocess.run(
        ["tmux", "send-keys", "-t", name, "-l", text],
        check=True,
    )
    if enter:
        time.sleep(0.3)
        subprocess.run(
            ["tmux", "send-keys", "-t", name, "Enter"],
            check=True,
        )


def capture_pane(name: str) -> str:
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", name, "-p", "-S", "-50"],
        capture_output=True, text=True,
    )
    return result.stdout


def wait_for_ready(name: str, timeout: int = 30) -> bool:
    start = time.time()
    prev = ""
    while time.time() - start < timeout:
        output = capture_pane(name)
        if output == prev and ("❯" in output or "$" in output.split("\n")[-2:]):
            return True
        prev = output
        time.sleep(2)
    return False


def launch():
    prompt_text = PROMPT_FILE.read_text()

    if tmux_session_exists(SESSION_NAME):
        print(f"Session '{SESSION_NAME}' already exists.")
        print(f"  Attach: tmux attach -t {SESSION_NAME}")
        print(f"  Kill:   tmux kill-session -t {SESSION_NAME}")
        sys.exit(1)

    print(f"[1/4] Creating tmux session '{SESSION_NAME}'...")
    create_tmux_session(SESSION_NAME)

    print(f"[2/4] Activating venv...")
    send_keys(SESSION_NAME, f"source {PROJECT_ROOT}/backend/.venv/bin/activate")
    time.sleep(2)

    print(f"[3/4] Starting Claude Code (model: {MODEL}, skip permissions)...")
    send_keys(SESSION_NAME, f"claude --model {MODEL} --dangerously-skip-permissions")
    time.sleep(5)

    # Accept the bypass permissions prompt
    subprocess.run(["tmux", "send-keys", "-t", SESSION_NAME, "Down", ""], check=True)
    time.sleep(0.5)
    subprocess.run(["tmux", "send-keys", "-t", SESSION_NAME, "Enter", ""], check=True)
    print("  Accepted bypass permissions prompt.")

    # Wait for Claude to initialize
    time.sleep(5)

    print(f"[4/4] Sending reasoning prompt ({len(prompt_text)} chars)...")
    send_keys(SESSION_NAME, prompt_text)

    print(f"""
Reasoning session launched!

  Monitor:  tmux attach -t {SESSION_NAME}
  Kill:     tmux kill-session -t {SESSION_NAME}

Claude is now reading triggers.jsonl and generating reasoning for all 129 triggers.
Output will be written to: backend/data/dossiers.json
""")


def dry_run():
    prompt_text = PROMPT_FILE.read_text()
    print(f"Prompt file: {PROMPT_FILE}")
    print(f"Prompt length: {len(prompt_text)} chars")
    print(f"Session name: {SESSION_NAME}")
    print(f"Model: {MODEL}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"\n--- Prompt preview (first 500 chars) ---")
    print(prompt_text[:500])
    print("...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch Claude Code reasoning in tmux")
    parser.add_argument("--dry-run", action="store_true", help="Preview without launching")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        launch()
