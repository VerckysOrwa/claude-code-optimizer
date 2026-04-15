#!/usr/bin/env python3
"""
PostToolUse hook — truncates large Bash/Read outputs.

Smart truncation strategy for coding tasks:
- Failed commands (exit_code != 0): show TAIL (errors are at the end)
- Passing commands / file reads: show HEAD with count of hidden lines

Claude Code protocol:
  stdin:  JSON event with tool_name, tool_input, tool_response
  stdout: {"tool_response": {...}} to override what Claude sees
          (empty / exit 0) to pass through unchanged
"""

import json
import sys

# Lines shown before truncation kicks in
MAX_LINES = {
    "Bash": 80,
    "Read": 100,
}

# These tools/commands always pass through — truncating would lose critical info
ALWAYS_PASS_COMMANDS = [
    "git diff",
    "git show",
    "git stash show",
]


def is_always_pass(cmd: str) -> bool:
    return any(cmd.lstrip().startswith(p) for p in ALWAYS_PASS_COMMANDS)


def smart_truncate(text: str, max_lines: int, failed: bool) -> str | None:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return None

    hidden = len(lines) - max_lines
    note_prefix = f"[token-saver] {hidden} lines hidden"

    if failed:
        # Show the TAIL — build/compile errors appear at the end
        kept = lines[-max_lines:]
        header = f"{note_prefix} (showing last {max_lines} — errors at tail)\n\n"
        return header + "\n".join(kept)
    else:
        # Show the HEAD
        kept = lines[:max_lines]
        footer = f"\n\n{note_prefix} (showing first {max_lines})."
        return "\n".join(kept) + footer


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = event.get("tool_name", "")
    if tool_name not in MAX_LINES:
        sys.exit(0)

    tool_input = event.get("tool_input", {})
    cmd = tool_input.get("command", "") if tool_name == "Bash" else ""

    if is_always_pass(cmd):
        sys.exit(0)

    tool_response = event.get("tool_response", {})
    exit_code = tool_response.get("exit_code", 0) if isinstance(tool_response, dict) else 0
    failed = exit_code not in (None, 0)

    raw = (
        tool_response.get("output")
        if tool_name == "Bash"
        else tool_response.get("content")
    )
    if not raw or not isinstance(raw, str):
        sys.exit(0)

    trimmed = smart_truncate(raw, MAX_LINES[tool_name], failed)
    if trimmed is None:
        sys.exit(0)

    result = dict(tool_response)
    key = "output" if tool_name == "Bash" else "content"
    result[key] = trimmed
    print(json.dumps({"tool_response": result}))
    sys.exit(0)


if __name__ == "__main__":
    main()
