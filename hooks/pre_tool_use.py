#!/usr/bin/env python3
"""
PreToolUse hook — rewrites noisy Bash commands to suppress verbose output
before they execute. This is more efficient than post-truncation because
the large output is never generated or sent to Claude at all.

Claude Code protocol:
  stdin:  JSON with tool_name, tool_input, ...
  stdout: {"decision": "approve", "toolInput": {...}} to modify input
          {"decision": "block", "reason": "..."} to block
          (empty / exit 0) to pass through unchanged
"""

import json
import re
import sys


# (pattern, replacement_or_callable)
# Applied in order; first match wins per rule, but multiple rules can apply.
REWRITES = [
    # --- Package managers: suppress install noise ---
    (r'\bnpm (install|i|ci)\b(?!.*--loglevel)',
     lambda m, c: c[:m.end()] + ' --loglevel=error' + c[m.end():]),

    (r'\byarn (install|add)\b(?!.*--silent)',
     lambda m, c: c[:m.end()] + ' --silent' + c[m.end():]),

    (r'\bpnpm (install|add)\b(?!.*--reporter)',
     lambda m, c: c[:m.end()] + ' --reporter=silent' + c[m.end():]),

    (r'\bpip3? install\b(?!.*-q)',
     lambda m, c: c[:m.end()] + ' -q' + c[m.end():]),

    (r'\bapt-get install\b(?!.*-qq)',
     lambda m, c: c[:m.end()] + ' -qq' + c[m.end():]),

    (r'\bcargo install\b(?!.*--quiet)',
     lambda m, c: c[:m.end()] + ' --quiet' + c[m.end():]),

    # --- Git log: always limit and use oneline unless already scoped ---
    (r'^git log\b(?!.*-n\s*\d)(?!.*--oneline)',
     lambda m, c: c[:m.end()] + ' --oneline -25' + c[m.end():]),

    (r'^git log\b(?!.*--oneline)',
     lambda m, c: c[:m.end()] + ' --oneline' + c[m.end():]),

    # --- Verbose build systems: tail errors instead of flooding ---
    (r'^make\b(?!.*\|)',
     lambda m, c: c + ' 2>&1 | tail -60'),

    (r'^cmake --build\b(?!.*\|)',
     lambda m, c: c + ' 2>&1 | tail -60'),

    # --- Cargo build (not test/run): quiet mode ---
    (r'^cargo build\b(?!.*--quiet)(?!.*\|)',
     lambda m, c: c[:m.end()] + ' --quiet' + c[m.end():]),
]


def rewrite_command(cmd: str) -> str:
    for pattern, replacer in REWRITES:
        m = re.search(pattern, cmd, re.MULTILINE)
        if m:
            cmd = replacer(m, cmd)
    return cmd


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if event.get("tool_name") != "Bash":
        sys.exit(0)

    tool_input = event.get("tool_input", {})
    original_cmd = tool_input.get("command", "")
    if not original_cmd:
        sys.exit(0)

    rewritten = rewrite_command(original_cmd)
    if rewritten == original_cmd:
        sys.exit(0)  # No change, pass through

    new_input = dict(tool_input)
    new_input["command"] = rewritten
    print(json.dumps({"decision": "approve", "toolInput": new_input}))
    sys.exit(0)


if __name__ == "__main__":
    main()
