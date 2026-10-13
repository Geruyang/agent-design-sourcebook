# Mechanism Registry

The mechanism registry is the durable index of accepted patterns that can update skills. It exists so novelty checks compare proposed behavior changes, not broad keyword overlap.

Each line in `registry.jsonl` is one accepted mechanism with:

- `mechanism_id`: stable kebab-case identifier
- `owning_skill`: published skill that owns the pattern
- `activation_scenario`: situation where the mechanism applies
- `behavior_change`: what a future agent should do differently
- `evidence`: source URLs or repo artifacts supporting the mechanism
- `failure_modes`: failures the mechanism prevents
- `status`: `accepted`, `candidate`, `deprecated`, or `rejected`

Only `accepted` and `candidate` mechanisms participate in novelty checks. Rejected mechanisms should remain in run logs or rejected proposal files unless they are useful enough to prevent repeated rediscovery.

## Promotion Flow

Runs propose mechanisms in `proposals/mechanism-proposal.jsonl`. Promotion is gated:

1. The run must pass run-readiness validation for `accepted` or `candidate` mechanisms.
2. A human reviewer must be recorded.
3. Accepted and candidate mechanisms append to `registry.jsonl`.
4. Every promotion appends an event to `ledgers/accepted.jsonl`.
5. Rejected mechanisms append to `ledgers/rejected.jsonl` so future agents do not rediscover them.
