# Continuous Operation Runbook

This runbook explains how to run the researcher harness as a daemon on macOS so it can advance the research-to-skill loop for days without manual intervention.

## What Runs

| Job | Frequency | Purpose |
| --- | --- | --- |
| `loop_step.py` | every 10 minutes | pull from inbox, advance one active run by one state, park anything that needs human or judge review |
| `loop_discover.py` | twice daily (05:00 and 17:00 local) | append new candidate sources from configured feeds into the inbox |
| `loop_daily.py` | once daily (06:30 local) | run repo validation, activation cases, benchmarks, write a dated snapshot, flag volatile claims due for review |
| `loop_status.py` | piggy-backs on every `loop_step` and `loop_daily` | refresh the dashboard and parked review surface |

All schedules and budgets live in `researcher/orchestration/config.json`. Default budgets:

- max active runs: 3
- max runs per day: 6
- max parked: 12
- max failures per day: 5
- max inbox size: 200

When any budget is exceeded the loop stops doing destructive work and continues only with bookkeeping until the human reviews.

## Install

```bash
researcher/orchestration/launchd/install.sh
```

The script:

1. Substitutes the repository path into the launchd plists.
2. Writes them under `~/Library/LaunchAgents/`.
3. Bootstraps them under the current user agent domain.
4. Enables the labels so they survive logout/login.

Logs land in `researcher/reports/logs/`:

- `loop_step.log`, `loop_discover.log`, `loop_daily.log`, `loop_status.log`
- `launchd-loop-step.out` and `.err` for raw launchd output

## Uninstall

```bash
researcher/orchestration/launchd/uninstall.sh
```

## Manual Operation

You can run the loop scripts directly without launchd:

```bash
python3 researcher/scripts/loop_discover.py            # pull new sources into inbox
python3 researcher/scripts/loop_step.py --allow-fetch  # advance one step
python3 researcher/scripts/loop_daily.py               # benchmarks + snapshot
python3 researcher/scripts/loop_status.py              # refresh dashboard
```

`--allow-fetch` enables HTTP GET retrieval through Python's stdlib `urllib`. Without it the loop parks runs that need source retrieval and waits for a human.

## Human Review Surface

Read these files when checking on the loop:

- `researcher/reports/status.md` - high-level dashboard.
- `researcher/reports/parked-review.md` - runs waiting for a reviewer.
- `researcher/reports/snapshots/<date>.md` - daily snapshot.
- `researcher/reports/benchmark-history.jsonl` - append-only benchmark trend.
- `researcher/queue/inbox.jsonl` - candidate sources awaiting initialization.
- `researcher/queue/quarantine.jsonl` - sources removed from rotation.

Parked runs require one of these actions:

| Reason | Action |
| --- | --- |
| `needs source retrieval` | retrieve manually and run `research_loop.py retrieve --run-dir <run> --file <evidence>` |
| `needs evaluation` | complete the source evaluation JSON and run `research_loop.py evaluate --run-dir <run>` |
| `needs human or model action from state proposed` | finish the proposal and run `research_loop.py novelty --run-dir <run>` |
| `needs merge approval` | review the PR notes; merge only after explicit approval |

## Safety

- The loop never invokes LLMs or paid APIs.
- Source retrieval uses stdlib `urllib` with a 30-second timeout and a 1.5MB cap.
- Sources that fail twice are quarantined.
- The mechanism registry can only be updated through `research_loop.py promote-mechanisms` with a recorded reviewer; the loop does not edit it.
- Push and merge are always human-controlled.

## Daily Rhythm

A reasonable cadence for a human running this:

1. Morning: read the latest snapshot and parked review.
2. Pick up to three parked runs and either advance, reject, or abandon them.
3. Approve any mechanism promotions whose runs are publish-ready.
4. Leave the loop running for the next day.
