# Researcher SDK Runner

TypeScript runner for the router (Stage 2) and effectiveness (Stage 3) benchmarks. Uses the [Cursor SDK](https://cursor.com/docs/sdk/typescript) to run real agents against the skill corpus.

See `researcher/benchmarks/PLAN.md` for methodology, hypothesis, statistical design, and reproducibility rules.

## Setup

```bash
cd researcher/benchmarks/sdk-runner
npm install
export CURSOR_API_KEY="cursor_..."
```

API keys come from [Cursor Dashboard > Integrations](https://cursor.com/dashboard/integrations). The runner never reads `CURSOR_API_KEY` from anywhere except the explicit env var; it is passed through to every SDK call so cross-tenant mistakes are impossible.

Enable [Privacy Mode](https://cursor.com/help/security-and-privacy/privacy) on the account before any benchmark run so eval traffic stays out of training data.

## Commands

```bash
npm run typecheck

npm run router:dry-run       # print plan and cost forecast, no agent calls
npm run router:run           # execute Stage 2 router benchmark

npm run effectiveness:dry-run
npm run effectiveness:run    # execute Stage 3 effectiveness benchmark
```

Flags shared by both runners:

- `--models <id,id,...>`: subset to specific models (default: `composer-2`).
- `--reps <N>`: replications per condition (default: 3).
- `--max-runs <N>`: hard cap on agent invocations.
- `--max-budget-usd <N>`: estimated cost cap; runner refuses to start if forecast exceeds.
- `--seed <N>`: deterministic shuffling of skill order and tie-breaking.
- `--fixture <path>`: alternate fixture JSONL.
- `--dry-run`: print plan, do not call the SDK.
- `--concurrency <N>`: bounded parallel SDK calls (default 1). 4 to 8 is reasonable; respect Cursor rate limits.
- `--no-resume`: ignore existing per-run results in the destination directory and re-execute everything. Default is to resume by skipping any plan item that already has a result file.

## Output

Runs append a single-line summary to:

- `researcher/reports/router-history.jsonl` (Stage 2)
- `researcher/reports/effectiveness-history.jsonl` (Stage 3)

Per-run raw outputs land under:

- `researcher/benchmarks/router/results/<timestamp>-<seed>/`
- `researcher/benchmarks/effectiveness/results/<timestamp>-<seed>/`

Both `results/` directories are gitignored. Curated released results live in release notes or a published-results file.

## Cost gates

The runner refuses to call the SDK unless either `--max-runs` or `--max-budget-usd` is set (or `--unsafe-no-cost-cap` is explicitly passed). Default budgets are intentionally conservative.

## Reproducibility

Every run records:

- Runner package version
- `CURSOR_API_KEY` fingerprint (last 4 chars only)
- Repo commit SHA at runtime
- Model ids resolved at start
- Fixture revision SHA
- Seed
- Full config snapshot

Third parties can reproduce a run with `node src/runRouter.ts --config <captured-config.json>`.
