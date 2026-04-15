#!/usr/bin/env python3
"""
token-saver stats — reads the Claude Code history JSONL and reports
token usage patterns to help you identify what's eating your quota.

Usage:
    python3 ~/.claude/plugins/token-saver/token_stats.py
    python3 ~/.claude/plugins/token-saver/token_stats.py --sessions 5
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


HISTORY_FILE = Path.home() / ".claude" / "history.jsonl"


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def load_sessions(history_path: Path, max_sessions: int = 10):
    if not history_path.exists():
        print(f"No history file found at {history_path}")
        return []

    sessions = []
    current = []

    with open(history_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                current.append(entry)
                # Claude Code writes a summary entry at session end
                if entry.get("type") == "summary":
                    sessions.append(current)
                    current = []
            except json.JSONDecodeError:
                continue

    if current:
        sessions.append(current)

    return sessions[-max_sessions:]


def analyze_session(entries: list) -> dict:
    stats = {
        "turns": 0,
        "total_chars": 0,
        "tool_calls": defaultdict(int),
        "tool_output_chars": defaultdict(int),
        "largest_outputs": [],
    }

    for entry in entries:
        etype = entry.get("type")
        if etype in ("human", "assistant"):
            stats["turns"] += 1

        content = entry.get("content", "")
        if isinstance(content, str):
            stats["total_chars"] += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "") or str(block.get("content", ""))
                    stats["total_chars"] += len(text)
                    # Tool result blocks
                    if block.get("type") == "tool_result":
                        tool = block.get("tool_use_id", "unknown")
                        size = len(str(block.get("content", "")))
                        stats["tool_output_chars"]["tool_result"] += size
                        if size > 2000:
                            stats["largest_outputs"].append((size, tool))
                    if block.get("type") == "tool_use":
                        stats["tool_calls"][block.get("name", "unknown")] += 1

    stats["estimated_tokens"] = estimate_tokens_from_chars(stats["total_chars"])
    stats["largest_outputs"].sort(reverse=True)
    return stats


def estimate_tokens_from_chars(chars: int) -> int:
    return chars // 4


def fmt_k(n: int) -> str:
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Claude Code token usage stats")
    parser.add_argument("--sessions", type=int, default=5, help="Number of sessions to show")
    args = parser.parse_args()

    sessions = load_sessions(HISTORY_FILE, args.sessions)
    if not sessions:
        print("No sessions found.")
        return

    print(f"\n{'='*55}")
    print(f"  Claude Code Token Usage — last {len(sessions)} session(s)")
    print(f"{'='*55}\n")

    total_tokens = 0
    for i, entries in enumerate(sessions, 1):
        stats = analyze_session(entries)
        tokens = stats["estimated_tokens"]
        total_tokens += tokens

        print(f"Session {i}: {stats['turns']} turns | ~{fmt_k(tokens)} tokens")

        if stats["tool_calls"]:
            top_tools = sorted(stats["tool_calls"].items(), key=lambda x: -x[1])[:5]
            tools_str = ", ".join(f"{t}({c})" for t, c in top_tools)
            print(f"  Tools used: {tools_str}")

        if stats["largest_outputs"]:
            top = stats["largest_outputs"][:3]
            sizes = ", ".join(f"~{fmt_k(s//4)} tok" for s, _ in top)
            print(f"  Largest tool outputs: {sizes}")

        print()

    print(f"Total estimated tokens across {len(sessions)} sessions: ~{fmt_k(total_tokens)}")
    print("\nTip: Run /compact mid-session or /clear between tasks to reset context.\n")


if __name__ == "__main__":
    main()
