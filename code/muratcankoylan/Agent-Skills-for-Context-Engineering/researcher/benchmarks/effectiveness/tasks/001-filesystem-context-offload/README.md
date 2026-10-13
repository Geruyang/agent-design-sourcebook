# 001 - Filesystem context offload

## Hypothesis

An agent equipped with the `filesystem-context` skill will:

1. Write the simulated tool output to a file under `scratch/` instead of returning it inline.
2. Use targeted retrieval (grep + read with line ranges) to answer the follow-up question without re-loading the full payload.
3. Use noticeably fewer total tokens than the control condition.

A control agent (no skills) is expected to dump the full payload back into context or otherwise inflate token usage.

## Setup

The `starting/` directory contains:

- `tool_output.txt`: ~5,000 lines of synthetic agent-trace data with one targeted fact buried at line 4321.
- `instructions.md`: brief reminder of what files are present.

The agent receives `task.md` as its prompt.

## Grading

`verify.sh` checks:

1. `scratch/` directory exists (skill behavior expected).
2. At least one file in `scratch/` contains lines copied from `tool_output.txt` (the agent actually offloaded).
3. The agent's final response contains the targeted fact (`API_RATE_LIMIT=8475`).

A run passes when all three checks pass. Token cost and wall time are recorded regardless and reported as effect sizes against the `control` condition.

## Categories of behavior we expect to differentiate

- `control`: agent likely returns the full output inline or fails to find the fact; high tokens.
- `target` (filesystem-context loaded): agent should offload and retrieve targeted; lower tokens, success.
- `negative` (bdi-mental-states loaded, filesystem-context absent): equivalent to control.
- `full` (all skills): success rate should match `target`; tokens may be slightly higher from extra context.
