# Pairwise Skill Revision Rubric

Use this rubric when comparing two candidate revisions of the same skill or two competing new-skill drafts.

## Preconditions

- Both candidates use the same source evidence.
- Both candidates target the same activation scenario.
- Both candidates pass deterministic structure checks.
- Neither candidate changes the rubric used to compare it.

## Dimensions

Score each candidate independently from 0 to 2, then compare.

| Dimension | Weight | Score 2 |
| --- | --- | --- |
| Behavioral Improvement | 35% | The candidate gives future agents clearer actions, decisions, or recovery paths |
| Evidence Fidelity | 20% | Claims are grounded in retrieved sources and do not overstate evidence |
| Activation Clarity | 15% | The description and When to Activate section route the skill cleanly |
| Corpus Fit | 15% | The candidate avoids duplication and respects related skill boundaries |
| Simplicity | 15% | The candidate achieves the improvement with fewer concepts, fewer lines, and less maintenance burden |

## Tie Breakers

If totals are within 0.1:

1. Prefer the simpler candidate.
2. Prefer the candidate with fewer volatile claims in `SKILL.md`.
3. Prefer the candidate that updates an existing skill over adding a new one.
4. Prefer the candidate with clearer gotchas.
5. Route to human review if the tie remains.

## Required Output

```yaml
candidate_a:
  path: ""
  weighted_total: 0.0
  strengths: []
  risks: []
candidate_b:
  path: ""
  weighted_total: 0.0
  strengths: []
  risks: []
winner: "A | B | tie | human_review"
tie_breaker_used: ""
decision_rationale: ""
```

## Failure Modes

1. **Verbose candidate wins by judge bias**: Penalize irrelevant detail under Simplicity.
2. **Evidence drift**: Reject claims that do not map back to retrieved sources.
3. **False novelty**: Compare against existing skills before scoring either candidate.
4. **Prompt-only comparison**: Run deterministic structure checks before rubric scoring.
