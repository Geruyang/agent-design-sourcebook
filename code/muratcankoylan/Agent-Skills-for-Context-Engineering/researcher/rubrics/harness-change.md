# Harness Change Rubric

Use this rubric when a source proposes changes to a research loop, evaluation harness, agent operating procedure, or PR automation policy.

## Harness Definition

A harness is the control system around an agent: prompts, editable surfaces, tools, evals, logs, retry rules, rollback rules, and human approval gates. Harness engineering is separate from content authoring because agents can game or weaken their own harnesses if the boundary is not explicit.

## Locked vs Editable Surfaces

Every harness proposal must classify files or settings:

| Surface | Examples | Rule |
| --- | --- | --- |
| Locked | Rubrics, evaluation scripts, source registry, merge policy | Agent may propose changes, but cannot use changed version to score the same proposal |
| Editable | Skill draft, source evaluation, research thread, proposal text | Agent can modify during the loop |
| Append-only | Result logs, rejected source log, experiment history | Agent can append, not rewrite |
| Human-controlled | Merge decisions, credential setup, destructive actions | Agent cannot automate without explicit approval |

## Gates

| Gate | Pass | Fail |
| --- | --- | --- |
| H1 Objective Clarity | The harness has a measurable objective and stop/continue rule | Goal is vague or impossible to evaluate |
| H2 Metric Integrity | Metrics are locked, external, and resistant to gaming | Agent can change the metric or hidden answer key |
| H3 Artifact Durability | The loop writes durable logs, candidates, failures, and decisions | State only exists in chat context |
| H4 Recovery Path | Crashes, bad sources, and failed proposals have explicit handling | Failures are ignored or retried indefinitely |
| H5 Human Governance | PR, merge, and policy-changing boundaries are explicit | Agent can merge or change governance autonomously |

Any failed gate requires human review.

## Scoring

Score each dimension 0, 1, or 2.

| Dimension | Weight | Score 2 |
| --- | --- | --- |
| Feedback Quality | 25% | Fast, unambiguous feedback from locked metrics or rubrics |
| Search Discipline | 20% | Supports novelty, ablation, pruning, and upstream refresh |
| Auditability | 20% | Durable logs reconstruct what happened and why |
| Safety and Governance | 20% | Clear approval gates and rollback paths |
| Cost Control | 15% | Bounded token, compute, and review cost per loop |

Approve harness changes only when total >= 1.5 and all gates pass. Otherwise route to human review.

## Required Checks

Before accepting a harness change:

1. Run the old harness on at least one known artifact if possible.
2. Run the proposed harness on the same artifact and compare decisions.
3. Confirm that stricter checks do not block obviously valid examples.
4. Confirm that looser checks do not admit known bad examples.
5. Record whether the change affects future proposals only or invalidates earlier results.

## Common Anti-Patterns

1. **Self-scored harness edits**: The same agent proposes and approves a new rubric. Require independent review or old-rubric scoring.
2. **Mutable benchmark**: The loop optimizes a metric the agent can edit. Lock metrics outside the editable surface.
3. **No discard path**: Bad experiments accumulate and become implicit context. Log and isolate rejected attempts.
4. **No pruning round**: Agents stack components and rarely remove them. Require leave-one-out or simplification checks for complex proposals.
5. **Stale upstream view**: Long-running agents stop checking new sources. Schedule periodic source refresh before major decisions.
