# Content Curation Rubric

Use this rubric to decide whether an external source deserves entry into the research pipeline. It extracts the reusable policy from `researcher/llm-as-a-judge.md` and resolves the gate ambiguity: any failed gate rejects the source unless a human explicitly overrides it.

## Gatekeeper Triage

All gates must pass before dimensional scoring.

| Gate | Pass | Fail |
| --- | --- | --- |
| G1 Mechanism Specificity | Defines a concrete mechanism, pattern, metric, workflow, or architecture | Uses vague advice like "improve prompts" without explaining how |
| G2 Implementable Artifacts | Includes code, schemas, prompt templates, diagrams, API contracts, configs, or enough procedure to implement | Pure commentary with no artifact or reproducible procedure |
| G3 Beyond Basics | Covers advanced context, harness, memory, tool, evaluation, multi-agent, or research operations patterns | Introductory content only |
| G4 Source Verifiability | Author or organization is identifiable and technically credible | Anonymous, unverifiable, or marketing-only source |

If any gate fails, record `REJECT` with the failed gate and stop.

## Dimensional Scoring

Score each dimension as 0, 1, or 2.

| Dimension | Weight | Score 2 | Score 1 | Score 0 |
| --- | --- | --- | --- | --- |
| D1 Technical Depth and Actionability | 35% | Directly implementable with artifacts or exact procedure | Useful but requires interpretation | No path to implementation |
| D2 Repo Relevance | 30% | Directly maps to context engineering, harness engineering, or skill authoring | Adjacent to repo scope | Out of scope |
| D3 Evidence and Rigor | 20% | Quantitative evidence, baselines, ablations, public logs, or reproducible method | Plausible experience report | Unsupported claim |
| D4 Novelty and Insight | 15% | New mechanism, counterintuitive finding, or high-value failure mode | Useful synthesis of known ideas | Common knowledge |

Formula:

```text
weighted_total = D1*0.35 + D2*0.30 + D3*0.20 + D4*0.15
```

## Decisions

| Decision | Condition |
| --- | --- |
| APPROVE | All gates pass and weighted total >= 1.4 |
| HUMAN_REVIEW | All gates pass and 0.9 <= weighted total < 1.4 |
| REJECT | Any gate fails or weighted total < 0.9 |

## Overrides

- O1: D1 = 0 forces `REJECT`.
- O2: D2 = 0 forces `REJECT`.
- O3: D3 = 1 and total >= 1.4 forces `HUMAN_REVIEW`.
- O4: D4 = 2 and total < 1.4 forces `HUMAN_REVIEW`.

## Required Evidence

Every approved or reviewed source must include:

1. Retrieved source URL and retrieval status.
2. Specific quoted or paraphrased evidence for every passing gate.
3. A mechanism summary in one paragraph.
4. Candidate skill impact: new skill, update existing skill, reference-only, or reject.
5. Known limitations, missing evidence, or assumptions.

## Output Shape

Use `../templates/source-evaluation.json` for machine-readable output. If the model cannot produce valid JSON, log the raw output and route to human review instead of silently fixing the evaluation.
