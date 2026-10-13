# Skill Change Rubric

Use this rubric after a source passes content curation. It decides whether the extracted mechanism should change the published skill corpus.

## Hard Gates

| Gate | Pass | Fail |
| --- | --- | --- |
| S1 Distinct Activation | The change has a clear trigger or improves an existing trigger | No clear activation scenario |
| S2 Implementable Guidance | The change tells an agent what to do, when to do it, and what to avoid | Adds only background knowledge |
| S3 Corpus Fit | The change belongs in an existing skill or justifies a new skill boundary | Duplicates existing content without improvement |
| S4 Evidence Traceability | Every non-obvious claim maps to a retrieved source or internal example | Unsupported or uncited claim |
| S5 Maintainer Burden | The claim is stable enough for `SKILL.md` or isolated in references if volatile | Adds brittle numbers or vendor-specific churn to core instructions |

Any failed gate routes to `HUMAN_REVIEW` or `REJECT`; do not publish automatically.

## Scoring

| Dimension | Weight | What To Check |
| --- | --- | --- |
| Actionability | 30% | Can a future agent apply this without additional research? |
| Relevance | 25% | Does it improve context engineering, harness engineering, evaluation, memory, tools, or agent architecture? |
| Non-Duplication | 20% | Does it add a new mechanism, failure mode, or sharper operating rule? |
| Evidence | 15% | Is the claim backed by reproducible artifacts, benchmarks, or credible production experience? |
| Skill Ergonomics | 10% | Does it keep discovery, line count, and progressive disclosure clean? |

Score each dimension 0, 1, or 2. Approve only when weighted total is at least 1.4 and no hard gate fails.

## New Skill vs Existing Skill

Update an existing skill when:

- The mechanism shares the same activation scenario.
- The current skill already owns the concept.
- The update is a sharper guideline, gotcha, example, or reference.

Create a new skill only when:

- The activation scenario is distinct and likely to be recognized by future agents.
- The workflow has its own operating sequence.
- Combining it with an existing skill would blur boundaries or exceed the 500-line budget.

Keep as reference-only when:

- The source is credible but volatile.
- The mechanism is interesting but not yet an operating rule.
- Evidence is useful for background but not enough for published instructions.

## Required Proposal Fields

Every proposed skill change must include:

```yaml
target: "new skill | existing skill | reference only"
target_path: ""
activation_trigger: ""
mechanism: ""
evidence:
  - source_url: ""
    retrieved: true
    supports: ""
proposed_delta:
  section: ""
  change_type: "add | update | remove"
  summary: ""
risks:
  - ""
review_decision: "approve | human_review | reject"
```

## Failure Modes

1. **Encyclopedia bloat**: Adding every interesting paper turns skills into literature reviews. Only publish mechanisms that change agent behavior.
2. **Claim rot**: Model-specific numbers age quickly. Put volatile evidence in dated references, not timeless guidance.
3. **Trigger collision**: Similar descriptions cause agents to activate the wrong skill. Keep skill boundaries sharper than taxonomy labels.
4. **Reference laundering**: Secondary summaries can point to primary sources but should not carry technical claims alone.
5. **One-source overfit**: A single credible source can justify human review, but broad guidance should have either reproduced evidence or multiple converging sources.
