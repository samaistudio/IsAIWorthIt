"""Parser for Claude Code session logs (~/.claude/projects/<project>/<session>.jsonl).

Reads each main session file plus its subagent logs, and returns one summary row per
session. Prompt text is classified in memory and then dropped: nothing but counts,
categories and timestamps leaves this module.
"""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from ..classify import is_correction, task_type

IDLE_GAP_MIN = 10  # gaps longer than this are treated as breaks, not work


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _prompt_text(content) -> str:
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def _project_label(folder: str) -> str:
    # "-Users-name-projects-myapp" -> "myapp" (no user paths kept)
    return folder.rstrip("-").split("-")[-1] or "unknown"


def parse_session(path: Path) -> dict | None:
    times: list[datetime] = []
    prompts: list[str] = []
    tools: Counter = Counter()
    usage = Counter()
    model = None
    cost = None
    lines = (0, 0)

    def read(file: Path, main: bool):
        nonlocal model, cost, lines
        for raw in file.open(encoding="utf-8", errors="ignore"):
            try:
                o = json.loads(raw)
            except json.JSONDecodeError:
                continue
            t = o.get("type")
            if o.get("timestamp") and t in ("user", "assistant"):
                times.append(_ts(o["timestamp"]))
            if main and t == "user" and (o.get("origin") or {}).get("kind") == "human":
                prompts.append(_prompt_text(o["message"]["content"]))
            elif t == "assistant":
                msg = o.get("message", {})
                model = msg.get("model") or model
                for k in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
                    usage[k] += (msg.get("usage") or {}).get(k, 0) or 0
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools[block.get("name", "?").split("__")[-1] if block.get("name", "").startswith("mcp__") else block.get("name", "?")] += 1
            elif main and t == "cost-state":
                cost = o.get("totalCostUSD", cost)
                lines = (o.get("totalLinesAdded", 0), o.get("totalLinesRemoved", 0))

    read(path, main=True)
    sub_dir = path.with_suffix("") / "subagents"
    subagent_files = sorted(sub_dir.glob("*.jsonl")) if sub_dir.is_dir() else []
    for f in subagent_files:
        read(f, main=False)

    if not prompts or not times:
        return None
    times.sort()
    active = sum(
        min((b - a).total_seconds() / 60, IDLE_GAP_MIN) for a, b in zip(times, times[1:])
    )
    return {
        "id": path.stem,
        "source": "claude_code",
        "project": _project_label(path.parent.name),
        "started_at": times[0].isoformat(),
        "ended_at": times[-1].isoformat(),
        "active_minutes": round(active, 1),
        "model": model,
        "user_turns": len(prompts),
        "correction_turns": sum(is_correction(p) for p in prompts[1:]),
        "tool_calls": sum(tools.values()),
        "subagents": len(subagent_files),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cache_read_tokens": usage["cache_read_input_tokens"],
        "cost_usd": round(cost or 0.0, 4),
        "lines_added": lines[0],
        "lines_removed": lines[1],
        "task_type": task_type(prompts[0]),
        "classified_by": "rules",
        "tools": dict(tools),
    }


def iter_sessions(root: Path = Path.home() / ".claude" / "projects"):
    for path in sorted(root.glob("*/*.jsonl")):
        row = parse_session(path)
        if row:
            yield row
