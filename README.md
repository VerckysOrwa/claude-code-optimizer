# token-saver-claude

A Claude Code plugin that reduces token consumption — especially for coding tasks.
Stops rate limits from hitting faster than expected by intercepting noisy commands
before they run, truncating large outputs, and enforcing concise response behavior.

---

## Install

**Step 1 — Add the marketplace:**

```
/plugin marketplace add https://github.com/VerckysOrwa/claude-code-optimizer
```

**Step 2 — Install the plugin:**

```
/plugin install token-saver-claude@token-saver-claude
```

**Step 3 — Reload:**

```
/reload-plugins
```

Done. The hooks and rules are now active for every session.

---

## How It Works

```
You type a prompt
       │
       ▼
 [PreToolUse hook]      rewrites commands before they execute
       │                npm install → npm install --loglevel=error
       │                git log     → git log --oneline -25
       ▼
   Tool runs
       │
       ▼
 [PostToolUse hook]     truncates output if still too large
       │                failed commands → shows tail (errors at bottom)
       │                passing commands → shows head
       ▼
 [Efficiency rules]     Claude responds without preambles,
                        uses diffs only, searches before reading
```

---

## What Gets Applied

### Command rewriting (PreToolUse)

Intercepts `Bash` calls and rewrites them before execution.
Large output is **never generated**, so it never enters the context window.

| You write | What runs |
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

### Output truncation (PostToolUse)

| Tool | Limit | Strategy |
|---|---|---|
| Bash | 80 lines | Failed → tail · Passing → head |
| Read | 100 lines | Head with hidden line count |

### Efficiency rules

Applied every session via the plugin's rules file:

- No preambles or summaries — answer directly
- Code changes via `Edit` tool only (diffs, not full rewrites)
- `Grep`/`Glob` before reading files
- Never re-read files already in context
- Never open `node_modules/`, `dist/`, `.git/`, lock files, build artifacts
- `/compact` at 30 turns · `/clear` between unrelated tasks

---

## Commands

### `/token-stats`

Shows token estimates from your recent sessions — how many turns, which tools were called most, and what produced the largest outputs.

```
/token-stats
```

---

## Tips

| Habit | Why |
|---|---|
| `/compact` every ~30 turns | Compresses history in-place |
| `/clear` between unrelated tasks | Resets context to zero |
| Name the exact file:line you want changed | Skips the exploration phase |
| Ask for diffs, not full rewrites | Cuts output 10–20x |

---

## Uninstall

```
/plugin uninstall token-saver-claude@token-saver-claude
```

---

## Requirements

- Claude Code (recent version with `/plugin` support)
- Python 3.8+
