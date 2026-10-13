# Published Router Benchmark Results

Each `<date>.md` file in this directory is a committed snapshot of a router benchmark sweep. Raw per-run JSON outputs live under `researcher/benchmarks/router/results/<date>-<seed>/` and are gitignored; only the curated summary published here is tracked in the repo.

Every report includes:

- Run metadata (timestamp, repo commit, fixture SHA, seed, model list, replications).
- Executive summary calling out the actually meaningful findings.
- Per-model leaderboard with bootstrap 95% CIs.
- Per-skill confusion matrix.
- Hardest-prompts breakdown.
- Reproduction command.

When a benchmark exposes a routing failure, follow up by editing the activation description of the failing skill, rerunning the benchmark, and comparing the new report against the previous one to show the delta.

History across runs is also appended to `researcher/reports/router-history.jsonl` (gitignored) by the runner.
