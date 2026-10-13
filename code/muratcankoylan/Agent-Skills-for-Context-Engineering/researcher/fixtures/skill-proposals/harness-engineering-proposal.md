# Skill Proposal: Harness Engineering From Autoresearch

## Source

- URL: https://github.com/karpathy/autoresearch/blob/master/program.md
- Title: Karpathy autoresearch program
- Author or organization: Andrej Karpathy
- Source type: code
- Retrieval status: retrieved
- Evaluation file: `researcher/fixtures/source-evaluations/approved-harness-source.json`
- Decision: HUMAN_REVIEW

## Mechanism

The source demonstrates a constrained autonomous experiment harness: the agent can edit one surface, the evaluator remains locked, each run receives fixed feedback, results are logged durably, and git rollback discards non-improving attempts. The transferable mechanism is not the nanoGPT task itself, but the boundary between editable and locked surfaces.

## Skill Target

- Target type: existing skill
- Target path: `skills/harness-engineering/SKILL.md`
- Activation scenario: designing an autonomous loop where editable artifacts are scored by locked evaluation surfaces
- Related skills: evaluation, filesystem-context, project-development
- Proposed location: SKILL.md

## Novelty Check

- Command: `python researcher/scripts/novelty_check.py --file researcher/fixtures/skill-proposals/harness-engineering-proposal.md --json`
- Verdict: pass
- Max mechanism overlap: 0.0866
- Top mechanism overlaps: `locked-editable-surfaces`, `structured-novelty-gate`
- Human-review rationale: Overlap is expected because the fixture seeded the harness pattern; the proposal predates the published mechanism registry and remains useful as a known-good example.

## Evidence

| Claim | Evidence | Source |
| --- | --- | --- |
| Autonomous loops need locked metrics | `prepare.py` owns evaluation while `train.py` is editable | Karpathy autoresearch |
| Durable result logs prevent repeated failures | `results.tsv` records commit, metric, memory, status, and description | Karpathy autoresearch |
| Rollback keeps failed attempts from polluting the frontier | Non-improving commits are reset | Karpathy autoresearch |

## Proposed Delta

```yaml
changes:
  - path: "skills/harness-engineering/SKILL.md"
    section: "Core Concepts"
    change_type: "add"
    summary: "Explain locked vs editable surfaces and fixed feedback loops."
```

## Quality Checks

- [x] Fits an existing activation scenario or justifies a new one.
- [x] Adds an operating rule, workflow, artifact, gotcha, or reference.
- [x] Records novelty-check verdict and top mechanism overlaps.
- [x] Avoids duplicating existing skill guidance or accepted mechanisms.
- [x] Keeps `SKILL.md` under 500 lines.
- [x] Uses progressive disclosure for detailed or volatile evidence.
- [x] Uses platform-agnostic wording.
- [x] Updates README, root `SKILL.md`, and manifests if publishing a new skill.

## Risks And Gaps

- Evidence limitations: one benchmark environment; should not imply every research task has one scalar metric.
- Possible duplication: overlaps with evaluation, but focuses on the control loop around evaluation.
- Volatile claims: avoid embedding star counts or time-sensitive popularity metrics.
- Required human review: O3 applies because evidence rigor is useful but narrow.

## Recommendation

`update-existing-skill`

Use the source as a core example for `harness-engineering`, with general wording that applies beyond nanoGPT.
