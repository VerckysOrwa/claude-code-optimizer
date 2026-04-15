# token-saver-claude

Reduces token consumption in Claude Code sessions — especially for coding tasks.
Prevents hitting rate limits by intercepting noisy commands before they run,
truncating large outputs, and enforcing concise response behavior via global rules.

---

## How It Works

```
User prompt
     │
     ▼
[PreToolUse hook]      ← rewrites commands before execution
     │                   npm install → npm install --loglevel=error
     │                   git log    → git log --oneline -25
     ▼
  Tool executes
     │
     ▼
[PostToolUse hook]     ← truncates if output still exceeds 80/100 lines
     │                   failed commands show tail (errors at bottom)
     ▼
[CLAUDE.md rules]      ← instructs Claude: no preambles, diffs only, grep first
     │
     ▼
  Claude responds
```

---

## Installation

### Option 1 — Inside Claude Code (recommended)

Open a Claude Code session and paste this message:

```
Clone https://github.com/verckys/token-saver-claude into ~/token-saver-claude,
then run bash ~/token-saver-claude/install.sh
```

Claude Code will handle the clone and run the installer for you.
After it finishes, restart Claude Code and run `/doctor` to confirm hooks loaded.

---

### Option 2 — One-liner in your terminal

```bash
git clone https://github.com/verckys/token-saver-claude ~/token-saver-claude \
  && bash ~/token-saver-claude/install.sh
```

---

### Option 3 — Manual

```bash
# 1. Clone
git clone https://github.com/verckys/token-saver-claude ~/token-saver-claude

# 2. Copy hooks
mkdir -p ~/.claude/hooks
cp ~/token-saver-claude/hooks/pre_tool_use.py   ~/.claude/hooks/
cp ~/token-saver-claude/hooks/truncate_output.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/pre_tool_use.py ~/.claude/hooks/truncate_output.py

# 3. Global behavior rules
cp ~/token-saver-claude/CLAUDE.md.template ~/.claude/CLAUDE.md
# (skip if you already have a CLAUDE.md — merge manually)

# 4. Register hooks in settings
# If ~/.claude/settings.json is empty, replace with:
cat > ~/.claude/settings.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/pre_tool_use.py" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/truncate_output.py" }]
      },
      {
        "matcher": "Read",
        "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/truncate_output.py" }]
      }
    ]
  }
}
EOF
# (if settings.json already has content, merge the "hooks" block manually)

# 5. Verify
# Restart Claude Code, then run:
#   /doctor
```

---

## What Gets Installed

```
~/.claude/
├── CLAUDE.md                    ← global conciseness rules
├── hooks/
│   ├── pre_tool_use.py          ← PreToolUse hook: rewrites noisy commands
│   └── truncate_output.py       ← PostToolUse hook: truncates large outputs
```

---

## Components

### `CLAUDE.md` — Response behavior rules

Loaded automatically every session. Tells Claude to:
- Skip preambles and summaries — answer directly
- Use `Edit` (diffs only) for code changes, never rewrite whole files
- `Grep`/`Glob` before reading files; use `offset`+`limit` on large files
- Never re-read files already seen this session
- Never open `node_modules/`, `dist/`, `.git/`, lock files, or build artifacts
- Run `/compact` at 30 turns, `/clear` between unrelated tasks

### `hooks/pre_tool_use.py` — Command rewriting

Intercepts `Bash` tool calls before execution and rewrites them to suppress verbose output.
The large output is **never generated**, so it never enters the context window at all.

| Command | Rewritten to |
|---|---|
| `npm install` | `npm install --loglevel=error` |
| `pip install X` | `pip install -q X` |
| `yarn install` | `yarn install --silent` |
| `pnpm install` | `pnpm install --reporter=silent` |
| `apt-get install X` | `apt-get install -qq X` |
| `git log` | `git log --oneline -25` |
| `make` | `make 2>&1 \| tail -60` |
| `cmake --build .` | `cmake --build . 2>&1 \| tail -60` |
| `cargo build` | `cargo build --quiet` |

Rules are idempotent — commands that already have the relevant flag pass through unchanged.
`git diff`, `git show`, `git stash show` are never modified.

### `hooks/truncate_output.py` — Output truncation

If a command still produces large output after rewriting, this hook truncates it.

| Tool | Limit | Strategy |
|---|---|---|
| `Bash` | 80 lines | Failed command → show **tail** (errors at bottom). Passing → show **head**. |
| `Read` | 100 lines | Show **head** with count of hidden lines. |

### `token_stats.py` — Diagnostics

Reads your local Claude Code session history and reports token estimates per session.

```bash
python3 ~/token-saver-claude/token_stats.py
python3 ~/token-saver-claude/token_stats.py --sessions 10
```

---

## Usage Tips

| Habit | Why it helps |
|---|---|
| `/compact` every ~30 turns | Compresses history in-place |
| `/clear` between unrelated tasks | Resets context to zero |
| Name the exact file and line you want changed | Skips the exploration phase |
| Ask for diffs, not full file rewrites | Cuts output tokens 10–20x |

---

## Customization

**Change truncation limits** — edit `~/.claude/hooks/truncate_output.py`:
```python
MAX_LINES = {
    "Bash": 80,   # raise if you're losing important output
    "Read": 100,
}
```

**Disable a command rewrite** — edit `~/.claude/hooks/pre_tool_use.py` and remove the relevant tuple from `REWRITES`.

**Add a new rewrite rule:**
```python
# Example: suppress a custom build tool
(r'\bmytool\b(?!.*--quiet)',
 lambda m, c: c[:m.end()] + ' --quiet' + c[m.end():]),
```

---

## Uninstall

```bash
rm ~/.claude/hooks/pre_tool_use.py
rm ~/.claude/hooks/truncate_output.py
rm ~/.claude/CLAUDE.md   # or edit to remove the token-saver rules

# Edit ~/.claude/settings.json and remove the "hooks" block
```

---

## Troubleshooting

**Hooks not loading** — run `/doctor` inside Claude Code. Make sure the paths in `settings.json` use your actual home directory.

**A command was rewritten but shouldn't be** — open `~/.claude/hooks/pre_tool_use.py` and remove or guard the relevant rule in `REWRITES`.

**Truncation is cutting off errors** — the hook already shows the tail for failed commands. If you still lose output, increase `MAX_LINES["Bash"]` in `truncate_output.py`.

**Token stats show no data** — the history file (`~/.claude/history.jsonl`) must exist. Complete at least one full Claude Code session first.

---

## Requirements

- Claude Code (any recent version)
- Python 3.8+
- Git
