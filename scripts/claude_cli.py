"""Ask Claude through the Claude Code CLI, on the Max subscription, never API credit.

The operator approves every use of API credit (2026-11-07), so these scripts
must not call api.anthropic.com. `claude -p` bills the subscription only when no
ANTHROPIC_API_KEY is in its environment, so the key is stripped here. Tools are
denied (`--permission-mode manual --permission-prompts none`) except the ones a
caller names in `tools` (the big-show scout allows WebSearch/WebFetch). It runs
from the temp folder so no project CLAUDE.md is loaded into a one-shot prompt.

Returns the reply text, or None on any failure (callers already fall back).
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

MODEL = "haiku"


def ask_claude(prompt: str, timeout: int = 180, model: str = MODEL,
               tools: list[str] | None = None) -> str | None:
    exe = shutil.which("claude")
    if not exe:
        print("[LLM] claude CLI not found — skipping")
        return None
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    cmd = [exe, "-p", "--model", model, "--output-format", "text",
           "--permission-mode", "manual", "--permission-prompts", "none"]
    if tools:
        cmd += ["--allowedTools", *tools]
    try:
        r = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
            timeout=timeout, env=env, cwd=tempfile.gettempdir(),
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"[LLM] claude CLI failed: {e}")
        return None
    if r.returncode != 0:
        print(f"[LLM] claude CLI exit {r.returncode}: {(r.stderr or r.stdout).strip()[:200]}")
        return None
    return r.stdout


def ask_claude_json(prompt: str, **kw) -> list | None:
    """ask_claude, then pull the first JSON array out of the reply."""
    text = ask_claude(prompt, **kw)
    if text is None:
        return None
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        print("[LLM] reply was not valid JSON")
        return None
    return data if isinstance(data, list) else None
