---
description: Show token usage estimates from recent Claude Code sessions to identify what's consuming your quota
---

Run the token-saver diagnostics tool to show token estimates per session, top tools used, and largest individual outputs.

Find and execute the token_stats.py script from the installed plugin:

```bash
STATS=$(find ~/.claude/plugins -name token_stats.py -path "*token-saver-claude*" 2>/dev/null | head -1)
if [ -n "$STATS" ]; then
  python3 "$STATS" --sessions 5
else
  echo "token-saver-claude plugin not found. Install it first with /plugin install."
fi
```

Then explain the output to the user — what's eating the most tokens and what they can do about it.
