"""What generating this edition cost, read from the Claude Code transcript.

Claude Code logs every model response, with its token usage, to
~/.claude/projects/<project>/<session>.jsonl. The run that is building the
paper is the most recently written transcript that called
`daily-brief context`; everything from that call on is this edition's work.
"""

import json
import time
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
MARKER = "daily-brief context"

# USD per million tokens: input, output, cache read (Anthropic API list prices).
# Cache writes cost 1.25x input (5-minute TTL) or 2x input (1-hour TTL).
PRICES = {
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}


def _transcript(max_age_hours: float = 6) -> Path | None:
    cutoff = time.time() - max_age_hours * 3600
    files = [f for f in PROJECTS.glob("*/*.jsonl") if f.stat().st_mtime >= cutoff]
    for f in sorted(files, key=lambda f: f.stat().st_mtime, reverse=True):
        with f.open(errors="ignore") as fh:
            if any(MARKER in line for line in fh):
                return f
    return None


def _calls_marker(rec: dict) -> bool:
    content = (rec.get("message") or {}).get("content")
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_use" and MARKER in json.dumps(b.get("input", {}))
        for b in content
    )


def run_usage(prices: dict | None = None) -> dict | None:
    """Token totals, model and API-equivalent cost of the current run, or None."""
    path = _transcript()
    if not path:
        return None
    records = []
    for line in path.open(errors="ignore"):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # the line being written right now
    start = max((i for i, r in enumerate(records) if _calls_marker(r)), default=0)

    # One response is logged once per content block, with the same id and usage.
    responses = {}
    for r in records[start:]:
        m = r.get("message")
        if r.get("type") == "assistant" and isinstance(m, dict) and m.get("usage") and m.get("id"):
            responses[m["id"]] = m
    if not responses:
        return None

    table = {**PRICES, **(prices or {})}
    totals = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    cost, models = 0.0, {}
    for m in responses.values():
        u, model = m["usage"], m.get("model", "")
        write = u.get("cache_creation_input_tokens") or 0
        write_1h = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0
        totals["input"] += u.get("input_tokens") or 0
        totals["output"] += u.get("output_tokens") or 0
        totals["cache_write"] += write
        totals["cache_read"] += u.get("cache_read_input_tokens") or 0
        models[model] = models.get(model, 0) + 1
        if model in table:
            p_in, p_out, p_read = table[model]
            cost += ((u.get("input_tokens") or 0) * p_in + (u.get("output_tokens") or 0) * p_out
                     + (write - write_1h) * p_in * 1.25 + write_1h * p_in * 2
                     + (u.get("cache_read_input_tokens") or 0) * p_read) / 1e6
    model = max(models, key=models.get)
    return {
        "model": model,
        "tokens": sum(totals.values()),
        **totals,
        "cost_usd": round(cost, 2) if all(m in table for m in models) else None,
    }
