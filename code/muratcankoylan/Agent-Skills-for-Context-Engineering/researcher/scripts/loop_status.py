#!/usr/bin/env python3
"""Human-facing status dashboard for the autonomous research loop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loop_common import (
    QUEUE_DIR,
    REPORTS_DIR,
    RESEARCHER,
    ROOT,
    categorize_runs,
    load_run_state,
    read_jsonl,
    runs_created_today,
    utc_now,
)


STATUS_FILE = REPORTS_DIR / "status.md"
PARKED_REVIEW_FILE = REPORTS_DIR / "parked-review.md"


def latest_benchmark() -> dict[str, Any] | None:
    history = REPORTS_DIR / "benchmark-history.jsonl"
    if not history.exists():
        return None
    last: dict[str, Any] | None = None
    for line in history.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    return last


def latest_snapshot() -> Path | None:
    snapshot_dir = REPORTS_DIR / "snapshots"
    if not snapshot_dir.exists():
        return None
    candidates = sorted(snapshot_dir.glob("*.md"))
    return candidates[-1] if candidates else None


def render_status() -> dict[str, Any]:
    buckets = categorize_runs()
    parked = read_jsonl(QUEUE_DIR / "parked.jsonl")
    inbox = read_jsonl(QUEUE_DIR / "inbox.jsonl")
    quarantine = read_jsonl(QUEUE_DIR / "quarantine.jsonl")
    done = read_jsonl(QUEUE_DIR / "done.jsonl")
    bench = latest_benchmark()
    snapshot = latest_snapshot()

    lines = [
        f"# Researcher Loop Status",
        f"_generated {utc_now()}_",
        "",
        "## Queue",
        f"- inbox: {len(inbox)}",
        f"- active runs: {len(buckets['active'])}",
        f"- parked runs: {len(parked)}",
        f"- closed runs (state): {len(buckets['closed'])}",
        f"- done ledger: {len(done)}",
        f"- quarantined: {len(quarantine)}",
        f"- runs created today: {runs_created_today()}",
        "",
        "## Latest Benchmark",
    ]
    if bench:
        summary = bench.get("summary", {})
        lines.extend(
            [
                f"- timestamp: {bench.get('timestamp')}",
                f"- ok: {bench.get('ok')}",
                f"- checks: {summary.get('benchmarks')} failures: {summary.get('failures')} scenarios: {summary.get('scenarios')}",
            ]
        )
    else:
        lines.append("- no benchmark history yet")
    lines.append("")
    lines.append("## Latest Snapshot")
    lines.append(f"- {snapshot.relative_to(ROOT)}" if snapshot else "- no snapshot yet")
    lines.append("")
    lines.append("## Active Runs")
    if not buckets["active"]:
        lines.append("- none")
    for run_dir in buckets["active"]:
        state = load_run_state(run_dir) or {}
        lines.append(
            f"- {run_dir.name}: state={state.get('current_state')} updated={state.get('updated_at')}"
        )
    lines.append("")
    lines.append("## Parked Runs")
    if not parked:
        lines.append("- none")
    for record in parked:
        lines.append(f"- {record.get('run_id')}: {record.get('reason')} (parked {record.get('parked_at')})")
    lines.append("")
    lines.append("## Inbox Preview")
    if not inbox:
        lines.append("- empty")
    for record in inbox[:5]:
        lines.append(f"- {record.get('source_id')} {record.get('url')}")

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if parked:
        parked_lines = [f"# Parked Runs Needing Review", f"_generated {utc_now()}_", ""]
        for record in parked:
            run_dir = RESEARCHER / "runs" / record.get("run_id", "")
            state = load_run_state(run_dir) or {}
            parked_lines.extend(
                [
                    f"## {record.get('run_id')}",
                    f"- reason: {record.get('reason')}",
                    f"- parked at: {record.get('parked_at')}",
                    f"- current state: {state.get('current_state')}",
                    f"- title: {state.get('title')}",
                    f"- source: {state.get('source_url')}",
                    f"- thread: {(run_dir / 'THREAD.md').relative_to(ROOT) if (run_dir / 'THREAD.md').exists() else 'missing'}",
                    "",
                ]
            )
        PARKED_REVIEW_FILE.write_text("\n".join(parked_lines), encoding="utf-8")
    elif PARKED_REVIEW_FILE.exists():
        PARKED_REVIEW_FILE.write_text("# Parked Runs Needing Review\n\n- none\n", encoding="utf-8")

    return {
        "status_path": str(STATUS_FILE.relative_to(ROOT)),
        "parked_review_path": str(PARKED_REVIEW_FILE.relative_to(ROOT)) if parked else None,
        "queue": {
            "inbox": len(inbox),
            "active": len(buckets["active"]),
            "parked": len(parked),
            "closed": len(buckets["closed"]),
            "done": len(done),
            "quarantine": len(quarantine),
        },
        "runs_created_today": runs_created_today(),
        "latest_benchmark_ok": bench.get("ok") if bench else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write loop status dashboard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = render_status()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"status written to {result['status_path']}")
        if result["parked_review_path"]:
            print(f"parked review at {result['parked_review_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
