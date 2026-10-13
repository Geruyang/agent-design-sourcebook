#!/usr/bin/env python3
"""Single source of truth for the long-horizon prompt lab.

Defines the pre-launch evaluation rubric (from the skill's task-brief-template) and
the four before/after prompt pairs, scores each pair against the rubric, and emits:

    data/prompt-pairs.json   machine-readable pairs + scores
    ui/data.js               window.PROMPT_LAB_DATA for the static UI (file:// safe)

The "before" prompts are competent, deliberately non-strawman prompt-engineered launch
prompts (persona, context, chain-of-thought, explicit output format, persistence). The
"after" briefs apply the long-horizon-prompting skill: pseudo-formal task specification,
non-counting outcomes, adversarial audit with a domain failure-mode checklist,
persistence paired with a verification gate, orchestration diversity policy, an
audit-gated return condition, effort floors, and contamination guards.

Run: python3 examples/long-horizon-prompt-lab/scripts/build_lab.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent

# Rubric dimensions, verbatim intent from the skill's pre-launch evaluation rubric
# (skills/long-horizon-prompting/references/task-brief-template.md). "2 means" is the
# adversary-proof bar; 1 is present-but-gameable; 0 is absent.
RUBRIC = [
    {"id": "predicate", "name": "Success predicate",
     "two": "An adversarial reader can decide unambiguously whether an artifact satisfies it; quantifiers and scope explicit."},
    {"id": "definitions", "name": "Definitions",
     "two": "Every load-bearing term defined, degenerate cases settled."},
    {"id": "non_counting", "name": "Non-counting outcomes",
     "two": "The plausible near misses for this specific problem are excluded by name."},
    {"id": "auditor", "name": "Auditor checklist",
     "two": "Enumerated, domain-specific failure modes including the circularity analogue."},
    {"id": "persistence_gate", "name": "Persistence-verification pairing",
     "two": "Every persistence instruction has a matching verification gate."},
    {"id": "return_condition", "name": "Return condition",
     "two": "A predicate over the artifact; fallback scoped to external budget exhaustion only."},
    {"id": "diversity", "name": "Diversity policy (parallel)",
     "two": "Early independence, idea-keyed registry, blocked-route rules, late cross-pollination."},
    {"id": "reporting", "name": "Reporting contract",
     "two": "Concrete artifacts required; claims must trace to session evidence."},
    {"id": "contamination", "name": "Contamination guards",
     "two": "Retrieval scope stated wherever result independence matters."},
    {"id": "harness", "name": "Harness separation",
     "two": "No hard constraint lives only in the prompt; budgets and permissions enforced outside."},
]
RUBRIC_IDS = [d["id"] for d in RUBRIC]

NA = "na"


def score_block(scores: dict) -> dict:
    applicable = [(k, v) for k, v in scores.items() if v != NA]
    total = sum(v for _, v in applicable)
    max_total = 2 * len(applicable)
    pct = round(100 * total / max_total) if max_total else 0
    return {"total": total, "max": max_total, "pct": pct}


PAIRS = [
    # ------------------------------------------------------------------ Pair 1
    {
        "id": "ml-optimization",
        "title": "Autonomous model-improvement run",
        "domain": "ML training / benchmark optimization",
        "topology": "Primary long-running agent + fresh-context reviewer",
        "horizon": "Hours, unattended, with cluster access",
        "summary": "A run told to beat a production model's benchmark score. The gap between "
                   "'beat the number' and 'produce a real, generalizing improvement' is exactly "
                   "the reward-hacking surface the skill warns about.",
        "before_techniques": [
            "Expert persona and rich task context",
            "Explicit numbered method and chain-of-thought request",
            "Persistence instruction ('do not give up')",
            "Named baseline metric and output-format spec",
        ],
        "before": """You are a world-class ML research engineer with deep expertise in model
training, optimization, and empirical evaluation. Your task is to improve our
text-classification model's accuracy on the internal benchmark we care about.

Context: our current production model (v3) scores 87.2 accuracy on our internal
eval set. We need to beat it. You have the training code in /repo, the training
data, and a GPU cluster. The eval harness is in eval/.

Work autonomously and be thorough. Think step by step:
  1. Analyze the current architecture and training setup.
  2. Brainstorm a comprehensive list of improvements (architecture, hyperparameters,
     data augmentation, loss functions, regularization).
  3. Systematically try the most promising ideas.
  4. For each experiment, record the eval accuracy.
  5. Keep iterating until you find something that beats 87.2.

Be persistent - do not give up if the first few ideas fail. Keep going until you
have a clear win. You are an expert, so use your best judgment and do not stop at
partial results. When done, write a detailed report of what you tried, what worked,
and the final accuracy you achieved.""",
        "after": """You are the autonomous research lead responsible for producing a real,
reproducible improvement to our production text-classification model. Work directly
in /repo. The current v3 model reports 87.2 accuracy on the internal evaluation set;
the training code and data are in the repository, and the evaluation entry point is
under eval/.

Your job is not to find one run whose displayed number is above 87.2. Your job is to
deliver a training change that improves the predeclared frozen benchmark without
evaluation leakage, survives an independent audit, and can be reproduced from a
clean checkout.

SUCCESS CONDITION

Before launch, the runtime records the current git SHA, evaluation command, evaluator
dependency-image digest, and SHA-256 manifests of the evaluation set, harness, and
transitive evaluator-owned modules. It then denies the primary agent all evaluation-
data access; the agent receives only the digests. Predeclare seeds 17, 29, 43, 71, and
101. Only the final reviewer may access evaluation data and run v3 plus exactly one
committed candidate with those seeds.

The task is complete only if all of the following are true:

1. The candidate's mean frozen-evaluation accuracy is above 87.2.
2. Let d_i be candidate accuracy minus v3 accuracy, in percentage points, for seed i.
   The lower endpoint of the two-sided 95% paired Student-t interval
   mean(d) +/- t(0.975, 4) * stdev(d) / sqrt(5) is strictly greater than zero.
3. The candidate is produced by a committed code or configuration change and a
   reproducible training command from a clean checkout.
4. The frozen evaluation data, metric implementation, and harness are byte-identical
   to the recorded snapshot.
5. A separately launched fresh-context reviewer, with read-only access to candidate
   artifacts and no access to the research history, runs the only candidate
   evaluation and accepts the leakage, selection, and preprocessing audits below.

The evaluation set is frozen data used only for final measurement. It must never be
copied, sampled, relabeled, or indirectly exposed to training or model selection.
An improvement on a re-drawn split, a subset, or a modified metric is not an
improvement for this task.

RESULTS THAT DO NOT COUNT

- A single-seed win, a cherry-picked seed, or a gain whose confidence interval
  includes zero.
- A gain obtained by modifying the evaluation set, evaluator, label mapping, metric,
  thresholding rule, or preprocessing path.
- Any train/evaluation overlap, including duplicates or transformed near-duplicates.
- A configuration that was never trained and evaluated end to end.
- A validation-only improvement that disappears on the frozen evaluation set.
- A list of promising ideas, experiment logs without a passing candidate, or a
  narrative report in place of runnable artifacts.

WORK POLICY

Start by reproducing v3 on training and validation data. Then explore materially
different hypothesis families rather than repeatedly tuning one knob: data quality or
augmentation, optimization and loss, regularization, and architecture or
representation. Maintain experiments/results.jsonl with the git SHA, exact command,
seed, input-data manifest, training/validation metrics, and artifact path for every
run. Keep frozen-evaluation data and outputs inaccessible during research. Select and
commit exactly one candidate using training and validation evidence only. If its one
final frozen evaluation fails, return INCOMPLETE; do not use that result to select a
second candidate.

Before declaring the search blocked, complete and record at least three materially
different hypothesis families. This effort requirement does not weaken the success
condition. GPU-hour and wall-clock limits are enforced by the runtime, not by this
prompt.

INDEPENDENT VERIFICATION

The runtime must launch the final reviewer in a separate context with a read-only
evaluation worktree and the pinned dependency image. Give it the immutable experiment
ledger, dataset-access logs, training/validation artifacts, frozen manifests,
candidate commit, and result artifacts, but no narrative research history. Require
the reviewer to:

- hash all train, validation, and evaluation examples and check exact overlap; use a
  near-duplicate detector, normalization procedure, similarity threshold, and manual
  adjudication rule recorded before training and never tuned after overlap inspection;
- confirm the evaluator and frozen files are unchanged from the initial snapshot;
- rerun all five paired seeds from a clean checkout;
- compare the baseline and candidate preprocessing paths for train/serve skew;
- check that every reported aggregate can be recomputed from the per-seed JSON; and
- revert the complete candidate patch, rerun the same five seeds, and confirm the
  paired difference from the recorded v3 results includes zero under the same
  prespecified interval calculation.

DELIVERABLES AND RETURN RULE

Return only after a candidate satisfies every success condition and survives the
independent audit. The final response must identify the candidate commit and link to:
the exact training command, frozen manifests, code diff, five baseline result files,
five candidate result files, confidence-interval calculation, and reviewer verdict.

If the externally enforced budget is exhausted first, label the run INCOMPLETE and
return only the verified experiment ledger and the exact remaining gap. Never present
an incomplete or unaudited candidate as an improvement.

External search is allowed for standard ML techniques and library documentation. Do
not search for this benchmark's labels, hidden examples, or leaderboard solution, and
do not use any retrieved artifact that reveals evaluation content.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 1, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": NA,
                       "reporting": 1, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": NA,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Success predicate",
             "text": "'Beat 87.2' becomes a CI-bounded margin over >=5 seeds on a hash-pinned frozen slice. A 0.1-point single-seed bump no longer satisfies the letter."},
            {"dim": "Persistence-verification pairing",
             "text": "'Keep going until a clear win' with no gate is the documented persistence-hacking surface (claim-long-horizon-persistence-hacking). The brief pairs persistence with a leakage/seed/harness-mutation audit."},
            {"dim": "Contamination guards",
             "text": "Adds explicit no-leakage and no-leaderboard-lookup guards; the before prompt let the agent train on eval or copy answers."},
            {"dim": "Reporting contract",
             "text": "'Detailed report of what you tried' (status theater) becomes runnable artifacts: diff, training command, per-seed eval JSON."},
        ],
        "residual": "The brief cannot enforce the write-protection on frozen_eval or the GPU "
                    "budget; both are assumed to live in the harness. If they do not, a "
                    "persistence-trained model still has a mutation path the prompt only "
                    "discourages. The effort floor is a permission, not a schedule.",
    },
    # ------------------------------------------------------------------ Pair 2
    {
        "id": "approx-proof",
        "title": "Parallel approximation-ratio proof search",
        "domain": "Algorithms / theory (metric TSP)",
        "topology": "Orchestrator with up to 64 parallel workers",
        "horizon": "Long, multi-round parallel search",
        "summary": "The direct analogue of the CDC exemplar in a different domain. The original "
                   "bakes in a diversity-collapse antipattern; the optimized prompt preserves "
                   "independence and makes a verified algorithm-and-proof package the return gate.",
        "before_techniques": [
            "Orchestrator persona with an explicit worker budget",
            "Enumerated solution directions (LP, Christofides, sampling, local search)",
            "Team-collaboration and consensus protocol",
            "Rigor and persistence instructions",
        ],
        "before": """You are an expert orchestrator managing up to 64 parallel research agents,
each a strong combinatorial-optimization theorist. Mission: improve the best known
approximation ratio for metric Traveling Salesman below the current published bound,
and prove the improved guarantee.

Assign agents to promising directions: LP relaxations, Christofides-style
constructions, random sampling, local-search analysis, and any other angles. Have
them collaborate and share findings frequently in a shared channel so everyone stays
in sync, and vote each round on the most promising approach. Encourage the team to
converge quickly on the best idea and pour resources into it.

Think carefully and be rigorous. Do not stop until the team is confident it has an
improvement. Once the team agrees the proof is correct, return the new ratio and the
proof.""",
        "after": """You are the root research agent for a long-running, parallel attempt to improve
the worst-case approximation ratio for metric Traveling Salesman. You may coordinate
up to 64 equally capable research agents. Use that capacity dynamically; your role is
to preserve independent search, demand checkable mathematics, and return only a
complete candidate theorem that survives adversarial review.

FIRST FREEZE THE TARGET

From primary literature, identify the current published worst-case approximation
constant for polynomial-time metric TSP, including the exact theorem statement,
computational model, scope, publication, assumptions, and guarantee type
(deterministic, expected, or high probability). Record it as c_current in
research/target.md before launching the main search. Public literature search is
required to establish c_current, map prior approaches, and avoid presenting a known
result as new. Record the search cutoff date, publication status, and primary sources.
Do not retrieve private evaluation answers, unpublished artifacts supplied for this
run, or benchmark-specific hidden solutions.

Unless the target theorem specifies otherwise, a metric TSP instance is a complete
undirected graph on at least three vertices with nonnegative symmetric rational edge
costs encoded in binary and satisfying the triangle inequality. OPT(I) is the minimum
cost of a Hamiltonian cycle. Algorithm A must output a Hamiltonian cycle, and its
running-time proof must account for bit complexity, optimization oracles, sampling,
and decomposition procedures.

An improvement must give a guarantee at least as strong as c_current in the same
computational model. For deterministic A, require

    cost(A(I)) <= alpha * OPT(I)

for every fixed instance. For randomized A, require

    E_r[cost(A(I; r))] <= alpha * OPT(I)

for every fixed instance, where the expectation is only over A's internal randomness.
Any failure-probability qualification must be explicit and must match or strengthen
the target theorem. In every case alpha is one fixed constant strictly below
c_current; restricted instance families do not count.

COMPLETE SUCCESS

Return a result only if it contains:

1. executable pseudocode for A, including tie handling and every randomized step;
2. a polynomial running-time proof;
3. an explicit alpha < c_current;
4. a modular proof of the ratio for every metric instance, with each lemma's premises
   and conclusion stated locally; and
5. independent adversarial reviews that find no unresolved theorem-strength gap.

RESULTS THAT DO NOT COUNT

- A better ratio only for a special metric family or only in expectation over inputs.
- An average-case, smoothed, empirical, finite-size, or asymptotic observation.
- A conditional theorem that depends on an unproved conjecture.
- A reduction to a lemma or open problem equivalent in strength to the target.
- An integrality-gap bound without an algorithm attaining the claimed ratio.
- A randomized guarantee silently rewritten as a deterministic one.
- A bound with an additive term, hidden dependence on instance size, or uninstantiated
  epsilon or o(1) term that does not imply one fixed alpha < c_current.
- An existential distribution, tree, decomposition, or fractional object without a
  polynomial-time construction or sampler.
- An algorithm returning a multigraph, walk, fractional solution, or disconnected
  structure without a proved polynomial-time conversion to a Hamiltonian cycle that
  preserves the claimed bound.
- A proof sketch containing an isolated missing lemma, a "routine" compatibility
  claim, or a best-effort explanation of why the problem is difficult.

PARALLEL SEARCH POLICY

Begin with independent workers exploring genuinely different idea families: LP/SDP
relaxations, best-of-many Christofides variants, entropy or random-sampling methods,
local-search analyses, decomposition and flow arguments, and new formulations not on
this list. Do not tell most first-round workers which route looks most promising.

Maintain research/approach-registry.md. Group routes by mathematical mechanism, not
by wording, and record for each route its invariant, concrete artifact, strongest
proved statement, and exact gap. Redirect workers away from crowded families. A route
that merely reformulates the target or ends at an equally hard lemma is not progress.
Mark such routes blocked in research/blocked-routes.md; reopen one only when a worker
supplies a materially new mechanism.

Preserve independent development until each active family produces a concrete
artifact or an evidence-backed blocker. Retire falsified routes immediately.
Cross-pollinate only after surviving routes have recorded their premises, strongest
result, and exact gap. Every worker assignment must state its objective, required
output (lemma, construction, counterexample, or calculation), allowed sources/tools,
and boundaries. Reject status reports and confidence claims without a mathematical
artifact.

ADVERSARIAL VERIFICATION

For every candidate, launch fresh-context reviewers who did not develop it. Give them
the target theorem, algorithm, and modular proof, but not the builders' discussion.
Assign explicit attacks:

- find hidden restrictions on the metric or instance class;
- recompute every constant and inequality, especially boundary cases;
- check whether "with high probability," expectation, and worst-case claims were
  interchanged;
- separate integrality-gap facts from algorithmic guarantees;
- detect circular use of a statement equivalent to the claimed improvement;
- verify feasibility of every intermediate and final object;
- check that every existential object is constructible or samplable in polynomial
  time;
- audit conditioning, independence, and correlation assumptions in randomized
  arguments;
- reject hidden additive, asymptotic, precision, or failure-probability
  qualifications;
- expand every compatibility or feasibility step labeled obvious or routine; and
- test the algorithm on small adversarial instances to falsify claims, without
  treating finite testing as proof.

Unanimous worker agreement is not evidence of correctness. Treat rapid consensus as
a possible diversity failure and audit the content itself. Each reviewer must return
numbered objections classified as blocking or non-blocking. Every blocking objection
must be resolved by a specific proof revision and rechecked by a fresh reviewer.
Maintain research/open-objections.md; it must contain zero unresolved blocking
objections at return.

RETURN RULE

Return only the complete algorithm-and-proof package after every theorem-strength
claim survives the adversarial checklist. Do not return merely because workers are
confident or because one approach dominates the registry.

If the externally enforced compute budget ends before complete success, label the
result INCOMPLETE and return the strongest rigorously proved statements, the approach
registry, blocked routes, and each exact remaining gap. Do not claim that no
improvement exists; failure of this search is not an impossibility proof.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": 0,
                       "reporting": 1, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": 2,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Diversity policy",
             "text": "'Share frequently, vote, converge quickly, pour resources into the best idea' is a textbook diversity-collapse recipe (claim-long-horizon-diversity-collapse). The brief replaces it with early independence, an idea-keyed registry, blocked-route bookkeeping, and late cross-pollination."},
            {"dim": "Return condition",
             "text": "'Until the team is confident' / 'the team agrees the proof is correct' uses unanimity as the halt signal. The brief makes the return a predicate over an artifact that survives fresh-context adversarial audit."},
            {"dim": "Non-counting outcomes",
             "text": "Adds the domain's real near misses: reductions to equally hard problems, conditional results, special-metric bounds, integrality-gap conflation."},
            {"dim": "Auditor checklist",
             "text": "Generic 'be rigorous' becomes a six-item hunt list including the circularity analogue (a bound equivalent to the target)."},
        ],
        "residual": "This is the domain where the verification bottleneck bites hardest: LLM "
                    "judges of proofs are systematically lenient (claim-long-horizon-verification-"
                    "gap), so even a fresh-context adversarial audit is not a proof of "
                    "correctness. A real ratio-improvement claim still needs external human or "
                    "formal verification; the brief maximizes candidate quality, it does not "
                    "close the theorem.",
    },
    # ------------------------------------------------------------------ Pair 3
    {
        "id": "systems-debug",
        "title": "Long-horizon distributed-systems RCA",
        "domain": "Distributed systems / concurrency",
        "topology": "Multi-session primary agent + fresh-context reviewer",
        "horizon": "Days, multi-session, spans context windows",
        "summary": "A rare, non-deterministic data-corruption bug. Without a reproduction as the "
                   "success predicate, 'find the root cause' collapses into a plausible narrative "
                   "the agent cannot be held to.",
        "before_techniques": [
            "Senior-engineer persona and precise symptom description",
            "Explicit sources to inspect (code, history, logs)",
            "Hypothesis-with-reasoning request and an exhaustive checklist",
            "Persistence and progress-update cadence",
        ],
        "before": """You are a senior distributed-systems engineer. We have an intermittent
data-corruption bug: roughly once every few million writes, a record in our sharded
key-value store ends up holding a value from a different key. It is rare,
non-deterministic, and we have not reproduced it reliably.

Investigate thoroughly and find the root cause, then fix it. Dig into the codebase
(/srv/kvstore), the commit history, the logs in /var/log/kvstore, and the concurrency
model. Form hypotheses, and for each explain your reasoning. Be exhaustive - consider
race conditions, memory issues, serialization bugs, clock skew, retries, and network
partitions.

This is important and hard, so be persistent and keep working until you understand
what is happening. Give me regular progress updates as you go. When finished, write a
detailed post-mortem explaining the root cause and your fix.""",
        "after": """You own an intermittent data-corruption incident in our sharded key-value
store. Work in /srv/kvstore and use the logs in /var/log/kvstore. Under concurrent
writes, roughly once every few million operations, a record is observed with a value
that was written for a different key. Your task is to reproduce that cross-key bleed,
identify the exact code mechanism, implement the fix, and leave a regression test
that would have caught it.

Do not optimize for a plausible post-mortem. Optimize for a causal demonstration.

WHAT COUNTS AS SOLVED

The incident is solved only when all of these artifacts exist:

1. A deterministic test or fault-injection harness that triggers cross-key bleed on
   a clean checkout in 20 of 20 runs under a controlled schedule. The schedule must
   be legal under the deployed runtime and memory model, reachable without test-only
   state mutation, and match the production incident in code path, shard state,
   ownership epoch, retry state, and observed failure mode.
2. A code-level causal explanation connecting the triggering schedule and state
   transition to the wrong key/value association.
3. A minimal fix that eliminates the reproduced failure.
4. An external reproducer that fails 20/20 on the pinned parent commit and passes
   100/100 on the fixed commit under the identical recorded schedule, plus a
   predeclared four-thread-count by three-seed stress matrix with every cell passing.
5. A fresh-context review that keeps the reproducer unchanged, reverts only the
   production-code fix, recovers the 20/20 failure, and confirms that the fix removes
   the cause rather than hiding the symptom.

If the verified cause is outside the repository (for example a runtime, filesystem,
hardware, or operational mechanism), completion may substitute an externally
replayable causal demonstration plus an owned-system configuration or containment
change. The same before/after/revert evidence is required, and fault injection must
exercise the verified non-code cause in regression.

"Root cause" means the specific mechanism whose activation is sufficient to reproduce
the corruption and whose correction prevents that same reproduction. "Fixed" does
not mean the observed frequency became lower. Retries, checksums, dropped writes, or
extra validation that merely masks the bad association are not fixes. The fixed build
must execute the same workload and reach the same precondition while preserving
acknowledged writes, concurrency, retries, and shard movement. It must introduce no
new errors or timeouts and must pass the unchanged availability, durability,
throughput, and latency acceptance gates. Preventing the trigger from running does
not count as a fix.

NON-SOLUTIONS

Do not return any of the following as completion:

- a hypothesis list, probability ranking, or narrative without a triggering test;
- "probably a race," "network issue," "clock skew," or "data drift" without the
  responsible code path and state transition;
- a stress test that sometimes fails but cannot control the failing interleaving;
- a mitigation that reduces incidence while the deterministic reproduction remains;
- a mechanism explaining only a different corruption mode; or
- a post-mortem without the reproduction, patch, and regression evidence.

INVESTIGATION POLICY

Start by pinning the current commit and turning the symptom into an executable
invariant. In the reproducer, every write uses a globally unique payload encoding its
key ID, request ID, and write generation. At the visibility point guaranteed by the
store's documented consistency model, after a defined quiescence barrier, cross-key
bleed occurs if the API response or durable record for key K contains a payload whose
encoded key is not K. Preserve key, payload provenance, shard, request ID, retry
generation, ownership epoch, and thread/task identity in the trace. Identify the first
layer where key and payload provenance diverge: API lookup, cache, serialization,
routing, or durable storage. A different latent defect with the same outward symptom
does not count as reproduction of this incident.

Build investigation/verified-ledger.md. Every entry must link to a command, log,
trace, test result, or diff from the current session. Record both supporting and
falsifying evidence. At the start of every later session, read the ledger and, if a
reproducer exists, rerun the smallest verified reproducer before doing new work.

Explore independent mechanism families: buffer or object reuse, serialization and
key/value framing, shard routing and ownership transfer, retry/idempotency behavior,
ABA or generation reuse, and unsynchronized publication. Use deterministic schedulers,
barriers, fault injection, and targeted tracing to turn timing hypotheses into
controlled interleavings. Do not keep pushing one theory after evidence falsifies it.
Before declaring the investigation blocked, produce evidence on at least four
materially different mechanism families.

ADVERSARIAL REVIEW

The runtime must launch the final reviewer in a separate context with read-only access
to candidate artifacts and no access to the investigation history. Give it the pinned
parent commit, original production log spans and traces, the predeclared incident
signature, reproducer, candidate trace, causal explanation, fix, and regression test.
Require the reviewer to:

- reproduce the failure 20/20 before the fix;
- apply the fix and observe 0/100 under the identical failing schedule, then pass
  every cell of the separate thread-count by scheduling-seed matrix;
- revert only the fix and recover the failure;
- check for ABA, lost-update, retry, and memory-lifetime explanations that the patch
  may merely perturb rather than correct;
- verify that the test detects cross-key bleed rather than a generic timeout or
  dropped write; and
- compare the candidate trace with the original production evidence and reject a
  reproducer whose code path, shard state, ownership epoch, retry state, or first
  divergence layer does not match; and
- trace every post-mortem claim to a run, log span, code location, or diff.

DELIVERABLES AND RETURN RULE

Return only after the reproduction, causal mechanism, minimal patch, regression
matrix, and fresh-context audit all pass. The final response must link to those
artifacts and explain the causal chain from triggering interleaving to the incorrect
key/value association at the API, cache, serialization, routing, or storage layer
where it first occurs, in enough detail for another engineer to reproduce it.

If the external runtime budget ends first, label the result INCOMPLETE. Return the
verified ledger, smallest reproducer achieved, falsified hypotheses, and exact next
experiment. Do not promote a likely explanation to root cause.

External search is limited to documented language, runtime, storage-engine, and
library semantics. A similar public bug is background evidence only; it is not the
answer unless its mechanism is reproduced in this codebase.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": NA,
                       "reporting": 0, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": NA,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Success predicate",
             "text": "'Find the root cause' becomes 'a mechanism with a deterministic reproduction that disappears when neutralized', which an adversarial reader can actually check."},
            {"dim": "Reporting contract",
             "text": "'Regular progress updates' + 'detailed post-mortem' is status theater. The brief requires a reproduction, a diff, and a regression test, with every claim traced to a log line or run (claim-long-horizon-evidence-audit)."},
            {"dim": "Return condition",
             "text": "'Until you understand what is happening' (confidence) becomes an artifact predicate: repro + fix + passing regression test that survive audit."},
            {"dim": "State ledger (persistence)",
             "text": "Adds a re-injected verified-progress ledger for the multi-session run, the countermeasure PushBench found rescued long tasks that prompt-only setups failed (claim-long-horizon-state-ledger)."},
        ],
        "residual": "A controlled reproducer can still expose a different latent defect with the "
                    "same outward symptom; matching the production signature remains a human "
                    "judgment. Hardware-originated faults may also resist deterministic software "
                    "reproduction. Re-injecting the verified ledger across sessions is a harness "
                    "job, not something this prompt can enforce by itself.",
    },
    # ------------------------------------------------------------------ Pair 4
    {
        "id": "security-audit",
        "title": "Autonomous security audit / red-team",
        "domain": "Application security",
        "topology": "Orchestrator with parallel workers per attack surface",
        "horizon": "Long, unattended, against a staging target",
        "summary": "Persistence plus a category checklist plus 'list every vulnerability' produces "
                   "an inflated report of unconfirmed findings. The optimized prompt makes an "
                   "independently reproduced proof of concept the unit of a finding.",
        "before_techniques": [
            "Offensive-security persona and named targets",
            "Comprehensive attack-surface checklist",
            "Severity-rating scheme and professional report format",
            "Attacker-mindset persistence framing",
        ],
        "before": """You are an elite offensive-security researcher. Audit our web application
(source in /app, staging at https://staging.internal) and find security
vulnerabilities.

Look everywhere: authentication, authorization, injection (SQL, command, template),
SSRF, deserialization, secrets in code, dependency CVEs, business-logic flaws, and
access control. Use your full expertise. For each issue, rate severity
(Critical/High/Medium/Low) and explain the risk.

Be extremely thorough and persistent - a real attacker would be, so you should be
too. Do not stop until you have done a comprehensive sweep. Produce a professional
pentest report listing every vulnerability you find, sorted by severity, with
remediation advice.""",
        "after": """You are leading an authorized security assessment of our web application. The
only active application target is the source tree at /app and the staging origin
https://staging.internal. An assessor-controlled callback origin may be added as the
sole in-scope exception for SSRF confirmation only when the runtime explicitly
allowlists and records it in the rules-of-engagement snapshot. Do not target any
other host, third-party service, employee account, or production system.
Do not perform denial of service, destructive writes, persistence, social engineering,
or data exfiltration beyond the minimum synthetic record needed to prove impact.
Test SSRF only against an assessor-controlled callback explicitly allowlisted by the
runtime. If none exists, stop at source-level reachability and mark active validation
blocked; never target loopback, link-local, cloud-metadata, private internal, or
third-party addresses. For command-execution tests, use only a fixed side-effect-free
command that emits a nonce. Do not write files, open a shell, access secrets, or
establish persistence. Stop active testing if staging routes to production or exposes
non-synthetic data.

Your objective is to produce independently reproducible, evidence-backed findings,
not a long list of possible weaknesses.

WHAT COUNTS AS A FINDING

A confirmed vulnerability must include:

1. an in-scope affected component and exact preconditions;
2. a minimal proof of concept that independently succeeds in two restored baseline
   environments or against two separately provisioned synthetic objects, without
   reusing cookies, tokens, mutated records, or another worker's state; for a
   race-sensitive defect, use a controlled concurrency harness with trigger traces
   and a negative control;
3. concrete demonstrated impact such as unauthorized access to a synthetic record,
   privilege escalation in a test account, or controlled code execution;
4. complete request/response or execution captures with tokens, secrets, personal
   data, and unrelated payload content redacted;
5. the responsible code, configuration, dependency call site, or deployment setting;
6. a severity rating under the project rubric, or, if none exists, a CVSS v4.0 vector
   plus separate business-impact rationale and explicit environmental assumptions;
   and
7. a reviewable patch or precise remediation. If an isolated patch-and-deploy path is
   explicitly authorized, include evidence that the PoC fails after remediation while
   intended behavior passes. Otherwise label remediation validation NOT EXECUTED;
   lack of deployment authority does not invalidate a reproduced vulnerability.

A scanner alert, suspicious code pattern, dependency advisory, missing header, or
theoretical attack path is not a confirmed vulnerability until the application's
actual usage is shown exploitable under these rules.

RESULTS THAT DO NOT COUNT

- Raw scanner, linter, SAST, or dependency output.
- A known CVE that is present in a lockfile but not exploitable through this
  application's configuration and reachable code path.
- A proof that depends on seeded privileged data, an already compromised account, or
  access outside the stated preconditions.
- Informational hardening advice presented as a security finding.
- Multiple findings that are only different symptoms of one root cause.
- A severity label without reproduced impact.
- Any out-of-scope or rules-of-engagement violation, even if technically interesting.

SEARCH AND ORCHESTRATION

Before active testing, write audit/roe-snapshot.md with the source git SHA, staging
build identifier, evidence that the deployed build corresponds to that source,
resolved target origin, enforced rate limits, available test identities and roles,
and synthetic-data namespace. If source provenance or safe fixtures cannot be
established, do not substitute real accounts or data; mark affected tests blocked.

Map the application's trust boundaries from source and observed staging behavior
before testing. Cover authentication and session lifecycle, authorization and IDOR,
SQL/command/template injection, SSRF, deserialization, secrets and credential paths,
dependency reachability, and business-logic invariants. Explicitly disposition
browser-side XSS, CSRF and CORS; OAuth, password-reset and MFA flows; file upload,
path traversal and XML parsing; API or GraphQL mass assignment; tenant isolation;
replay, race and idempotency defects; and proxy, cache, or request-smuggling
boundaries where present.

Use parallel workers only for independent attack surfaces. Keep first-round workers
blind to unrelated promising findings so the team does not collapse onto one class.
Maintain audit/coverage.md keyed by attack surface and audit/findings-registry.md
keyed by root cause. Each worker assignment must include its objective, in-scope
target, allowed tools, prohibited actions, and required artifact. Reject status
reports that do not contain a request, trace, script, code path, or falsified
hypothesis. Give each worker a distinct test identity and namespaced synthetic data.
Serialize operations that mutate shared application state. Every artifact records
the staging build, identity, namespace, request ID, and timestamp.

Do not stop after the first strong finding. Derive a coverage inventory from every
route, RPC, background job, trust-boundary crossing, role, tenant/object/action
combination, parser or sink, upload/download path, and outbound-request site found in
source or staging. Mark each item tested, unreachable, out of scope, or blocked, with
evidence. Coverage is complete only when every item is dispositioned and every
reachable authorization boundary has both an allowed and denied control. Mark a route
blocked when progress requires an out-of-scope action or unavailable prerequisite;
reopen it only for a materially different safe test.

INDEPENDENT REPRODUCTION

For each candidate finding, launch a fresh-context reviewer who did not discover it.
Provide only the scope, clean staging instructions, candidate PoC, relevant source
snapshot, and claimed impact. Require the reviewer to:

- start from a new account or anonymous session as specified by the preconditions;
- reproduce the PoC twice and preserve sanitized evidence;
- confirm the effect is not seeded test behavior, intended authorization, or a stale
  session, proxy, WAF, debug-fixture, or other worker's mutation;
- run an unexploited negative-control request;
- verify the root-cause mapping and collapse duplicate symptoms;
- challenge the severity against actual privileges and impact; and
- inspect the remediation and, only in an explicitly authorized isolated deployment,
  apply it and run the PoC plus intended-workflow regression tests.

DELIVERABLES AND RETURN RULE

Return a final assessment only after every included vulnerability survives independent
reproduction. Assign monotonically increasing identifiers and put each finding under
audit/findings/F-NNN/ (for example F-001), with a report, PoC, sanitized evidence,
root-cause reference, severity rationale, and remediation check. Include the coverage
ledger separately; unconfirmed hypotheses belong there, clearly labeled, and must
not be counted as vulnerabilities.

If no candidate survives verification, return zero confirmed findings plus the
coverage ledger. Do not claim the application is secure; state only what was tested.
If the externally enforced budget ends before coverage is complete, label the
assessment INCOMPLETE and identify the untested surfaces.

CVE databases, framework documentation, and public writeups may be used as background.
Never copy a public claim into the report without proving exploitability here. Prompt
instructions do not enforce scope: the network allowlist, credentials, rate limits,
and destructive-action blocks must remain enforced by the runtime throughout. Never
authenticate with a discovered credential against production or a third party. Record
only its source location, type, and cryptographic fingerprint; do not copy the secret
into an artifact. Treat validity and external impact as unverified unless established
entirely within staging.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": 1,
                       "reporting": 0, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": 2,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Non-counting outcomes",
             "text": "The highest-leverage change: theoretical findings, scanner output, and unexploited dependency CVEs are excluded by name, killing report-padding as a way to satisfy the letter."},
            {"dim": "Persistence-verification pairing",
             "text": "'Do not stop until comprehensive' with no confirmation gate rewards fabricated/inflated findings. The brief pairs it with independent PoC re-verification per finding."},
            {"dim": "Contamination guards",
             "text": "Blocks laundering known CVEs from the dependency list as 'findings' without a PoC, and pins retrieval to background only."},
            {"dim": "Harness separation",
             "text": "RoE, the in-scope allowlist, and destructive-action prohibitions are moved to network/runtime enforcement; the prompt states them only for planning."},
        ],
        "residual": "Scope and destructive-action limits stated in a prompt are advisory under "
                    "optimization pressure. If the network policy does not actually fence the "
                    "target allowlist, a persistent agent can still reach out of scope. The "
                    "brief reduces report-padding, but confirming impact without ever causing "
                    "harm on a live target is a RoE/harness problem the words cannot solve.",
    },
]

# Honest framing shown in the UI: the rubric is the skill's own pre-launch rubric, so a
# high "after" score means "fully applies the skill's checklist," measured by that checklist,
# not by an independent third party. The before prompts are competent prompt-engineered
# launch prompts, not strawmen.
HONESTY_NOTE = (
    "Scores use the skill's own 10-dimension pre-launch rubric, so a high 'after' score means "
    "the brief fully applies the skill's checklist as measured by that checklist. This is a "
    "structural comparison, not an outcome benchmark: it shows the briefs are harder to satisfy "
    "by a near miss, not that any specific run succeeds. The 'before' prompts are competent, "
    "prompt-engineered launch prompts (persona, context, chain-of-thought, explicit format, "
    "persistence), not strawmen. Each pair lists a residual risk the optimized prompt still "
    "cannot remove."
)


def build() -> dict:
    pairs_out = []
    for p in PAIRS:
        before = score_block(p["scores"]["before"])
        after = score_block(p["scores"]["after"])
        pairs_out.append({
            **{k: p[k] for k in (
                "id", "title", "domain", "topology", "horizon", "summary",
                "before_techniques", "before", "after", "deltas", "residual", "scores")},
            "score_summary": {
                "before": before,
                "after": after,
                "gain_pp": after["pct"] - before["pct"],
            },
        })
    agg_before = sum(p["score_summary"]["before"]["pct"] for p in pairs_out) / len(pairs_out)
    agg_after = sum(p["score_summary"]["after"]["pct"] for p in pairs_out) / len(pairs_out)
    return {
        "meta": {
            "title": "Prompts for work that does not end in one turn.",
            "subtitle": "Four launch prompts, rewritten as complete, ready-to-run prompts for long-running agents.",
            "skill": "long-horizon-prompting",
            "exemplar": "OpenAI GPT-5.6 Sol Ultra Cycle Double Cover run (July 2026)",
            "rubric_source": "skills/long-horizon-prompting/references/task-brief-template.md",
            "honesty_note": HONESTY_NOTE,
            "aggregate": {
                "before_pct": round(agg_before),
                "after_pct": round(agg_after),
                "gain_pp": round(agg_after - agg_before),
                "pairs": len(pairs_out),
            },
        },
        "rubric": RUBRIC,
        "pairs": pairs_out,
    }


def main() -> int:
    data = build()
    (LAB / "data").mkdir(exist_ok=True)
    (LAB / "ui").mkdir(exist_ok=True)
    json_path = LAB / "data" / "prompt-pairs.json"
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    js_path = LAB / "ui" / "data.js"
    js_path.write_text(
        "// Generated by scripts/build_lab.py - do not edit by hand.\n"
        "window.PROMPT_LAB_DATA = " + json.dumps(data, indent=2) + ";\n",
        encoding="utf-8",
    )
    prompts_dir = LAB / "ui" / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    expected_prompt_files: set[str] = set()
    for pair in data["pairs"]:
        for source_key, suffix in (("before", "original"), ("after", "optimized")):
            filename = f"{pair['id']}-{suffix}.txt"
            expected_prompt_files.add(filename)
            (prompts_dir / filename).write_text(pair[source_key].strip() + "\n", encoding="utf-8")
    for stale in prompts_dir.glob("*.txt"):
        if stale.name not in expected_prompt_files:
            stale.unlink()

    agg = data["meta"]["aggregate"]
    print(
        f"Wrote {json_path.relative_to(LAB)}, {js_path.relative_to(LAB)}, "
        f"and {len(expected_prompt_files)} prompt text files"
    )
    print(f"Pairs: {agg['pairs']} | aggregate before {agg['before_pct']}% -> after {agg['after_pct']}% "
          f"(+{agg['gain_pp']}pp)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
