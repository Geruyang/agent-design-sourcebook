#!/usr/bin/env python3
"""Discover candidate sources and append them to the inbox.

By default the discoverer only reads `researcher/discovery/manual-seed.jsonl`.
Paid feeds (Parallel deep research, web search) are off by default and require
explicit config opt-in plus separate adapter scripts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loop_common import (
    QUEUE_DIR,
    RESEARCHER,
    active_run_urls,
    append_jsonl,
    closed_run_urls,
    load_config,
    queue_lock,
    read_jsonl,
    source_id_for,
    utc_now,
    write_jsonl,
)


def load_manual_seed(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"manual-seed line {line_number} invalid JSON: {exc}") from exc
    return records


def _normalize_url(url: str) -> str:
    return url.strip().lower()


def existing_urls(inbox: list[dict[str, Any]], quarantine: list[dict[str, Any]]) -> set[str]:
    urls: set[str] = set()
    for record in inbox + quarantine:
        url = record.get("url")
        if isinstance(url, str):
            urls.add(_normalize_url(url))
    urls.update(_normalize_url(value) for value in active_run_urls())
    urls.update(_normalize_url(value) for value in closed_run_urls())
    return urls


def normalize_candidate(record: dict[str, Any], feed: str) -> dict[str, Any]:
    raw_url = str(record.get("url", "")).strip()
    if not raw_url:
        raise ValueError("candidate is missing url")
    normalized = _normalize_url(raw_url)
    return {
        "source_id": source_id_for(normalized),
        "url": raw_url,
        "url_normalized": normalized,
        "title": str(record.get("title", "")).strip(),
        "author_or_org": str(record.get("author_or_org", "")).strip(),
        "source_type": str(record.get("source_type", "other")).strip(),
        "candidate_reason": str(record.get("candidate_reason", "")).strip(),
        "feed": feed,
        "discovered_at": utc_now(),
        "attempts": 0,
        "last_status": "queued",
    }


def discover(config: dict[str, Any], dry_run: bool, limit: int | None) -> dict[str, Any]:
    feeds = config.get("feeds", {})
    inbox_path = QUEUE_DIR / "inbox.jsonl"
    quarantine_path = QUEUE_DIR / "quarantine.jsonl"
    discovery_max = limit if limit is not None else config.get("limits", {}).get("discovery_max_new_per_run", 8)
    max_inbox_size = config.get("budgets", {}).get("max_inbox_size", 200)

    with queue_lock("inbox"):
        inbox = read_jsonl(inbox_path)
        quarantine = read_jsonl(quarantine_path)
        seen = existing_urls(inbox, quarantine)
        new_records: list[dict[str, Any]] = []

        manual_seed_rel = feeds.get("manual_seed")
        if manual_seed_rel:
            manual_path = RESEARCHER.parent / manual_seed_rel
            for record in load_manual_seed(manual_path):
                try:
                    candidate = normalize_candidate(record, feed="manual-seed")
                except ValueError as exc:
                    print(f"skipping manual-seed candidate: {exc}", file=sys.stderr)
                    continue
                key = candidate.get("url_normalized") or candidate["url"]
                if key in seen:
                    continue
                new_records.append(candidate)
                seen.add(key)
                if len(new_records) >= discovery_max:
                    break

        if feeds.get("enable_parallel_deep_research"):
            print(
                "parallel deep research feed is enabled in config but not implemented in this loop. "
                "skipping until adapter is added.",
                file=sys.stderr,
            )
        if feeds.get("enable_web_search"):
            print(
                "web search feed is enabled in config but not implemented in this loop. "
                "skipping until adapter is added.",
                file=sys.stderr,
            )

        capacity_remaining = max(0, max_inbox_size - len(inbox))
        if len(new_records) > capacity_remaining:
            new_records = new_records[:capacity_remaining]

        if not dry_run and new_records:
            inbox.extend(new_records)
            write_jsonl(inbox_path, inbox)

        return {
            "ok": True,
            "dry_run": dry_run,
            "new": len(new_records),
            "inbox_size": len(inbox) if not dry_run else len(inbox) + len(new_records),
            "capacity_remaining": capacity_remaining - len(new_records),
            "first_new": new_records[:3],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover candidate sources and append to inbox")
    parser.add_argument("--dry-run", action="store_true", help="show what would be added without writing")
    parser.add_argument("--limit", type=int, default=None, help="override discovery_max_new_per_run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = discover(config, args.dry_run, args.limit)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        suffix = " (dry-run)" if result["dry_run"] else ""
        print(
            f"Discovery added {result['new']} sources{suffix}; "
            f"inbox now {result['inbox_size']}, capacity remaining {result['capacity_remaining']}"
        )
        for record in result["first_new"]:
            print(f"- {record['source_id']} {record['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
