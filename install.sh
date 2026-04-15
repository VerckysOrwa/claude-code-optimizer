#!/usr/bin/env bash
# token-saver-claude — install script
# Works whether you cloned the repo or are running it from inside Claude Code.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"

HOOK_PRE="$HOOKS_DIR/pre_tool_use.py"
HOOK_POST="$HOOKS_DIR/truncate_output.py"

echo ""
echo "  token-saver-claude installer"
echo "  =============================="

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "  ERROR: python3 is required but not found."
    echo "  Install Python 3 then re-run this script."
    exit 1
fi

# ── 2. Directories ────────────────────────────────────────────────────────────
mkdir -p "$HOOKS_DIR"

# ── 3. Copy hooks ─────────────────────────────────────────────────────────────
cp "$REPO_DIR/hooks/pre_tool_use.py"    "$HOOK_PRE"
cp "$REPO_DIR/hooks/truncate_output.py" "$HOOK_POST"
chmod +x "$HOOK_PRE" "$HOOK_POST"
echo "  [OK] hooks installed → $HOOKS_DIR"

# ── 4. CLAUDE.md ──────────────────────────────────────────────────────────────
if [[ -f "$CLAUDE_MD" ]]; then
    echo "  [SKIP] CLAUDE.md already exists — not overwritten"
    echo "         Add the contents of CLAUDE.md.template manually if needed"
else
    cp "$REPO_DIR/CLAUDE.md.template" "$CLAUDE_MD"
    echo "  [OK] CLAUDE.md created → $CLAUDE_MD"
fi

# ── 5. settings.json ──────────────────────────────────────────────────────────
EXISTING=""
if [[ -f "$SETTINGS" ]]; then
    EXISTING="$(cat "$SETTINGS" | tr -d '[:space:]')"
fi

HOOKS_JSON=$(cat << EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 $HOOK_PRE" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 $HOOK_POST" }]
      },
      {
        "matcher": "Read",
        "hooks": [{ "type": "command", "command": "python3 $HOOK_POST" }]
      }
    ]
  }
}
EOF
)

if [[ -z "$EXISTING" || "$EXISTING" == "{}" ]]; then
    echo "$HOOKS_JSON" > "$SETTINGS"
    echo "  [OK] settings.json written → $SETTINGS"
else
    echo ""
    echo "  [ACTION NEEDED] settings.json already has content."
    echo "  Merge this 'hooks' block into $SETTINGS:"
    echo ""
    echo "$HOOKS_JSON"
    echo ""
fi

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "  Done! Restart Claude Code and run /doctor to confirm hooks are active."
echo ""
