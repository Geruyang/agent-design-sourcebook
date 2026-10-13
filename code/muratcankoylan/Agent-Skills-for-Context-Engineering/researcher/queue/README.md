# Researcher Queue

The queue files are the persistent ledger that lets the autonomous loop run for days without losing state. Every change is append-only or replaces the entire file with a new sorted snapshot.

## Files

- `inbox.jsonl` - candidate sources discovered but not yet initialized as runs.
- `parked.jsonl` - run IDs that hit a human-review gate and are waiting for a reviewer.
- `done.jsonl` - run IDs that have been closed (accepted, rejected, reference-only, abandoned).
- `quarantine.jsonl` - sources removed from rotation because retrieval failed or the source registry rejects them.

## Source Record Shape

Each line in `inbox.jsonl` and `quarantine.jsonl` is a JSON object:

```json
{
  "source_id": "deterministic-hash",
  "url": "https://example.com/post",
  "title": "Short title",
  "author_or_org": "Org",
  "source_type": "paper | engineering_blog | documentation | benchmark | code | talk | other",
  "candidate_reason": "Why this source matters",
  "feed": "manual-seed | parallel-research | rss | other",
  "discovered_at": "ISO-8601",
  "attempts": 0,
  "last_status": "queued | initialized | failed"
}
```

Active runs live under `researcher/runs/<run-id>/` and have their own `run-state.json`. The loop scripts read those state files directly rather than duplicating active-run state here, so there is one source of truth per run.
