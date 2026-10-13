# Long-Horizon Prompting Website

A dependency-free educational website and before/after lab for the
[`long-horizon-prompting`](../../skills/long-horizon-prompting/) skill. It explains the method,
provides a copyable builder template and checklist, maps the research evidence and caveats, and
shows four complete prompt rewrites.

This example was built by applying the skill to itself: each "after" is a complete launch prompt
produced with the skill's brief-writing workflow, and the scoring uses the rubric from
[`task-brief-template.md`](../../skills/long-horizon-prompting/references/task-brief-template.md).

![Aggregate before/after](screenshots/shot-hero.png)

## Website

This is a **Long-Horizon Prompting** project site hosted from this monorepo. The on-page brand
is Long-Horizon Prompting; GitHub Pages serves it under the repository path:

`https://muratcankoylan.github.io/Agent-Skills-for-Context-Engineering/`

Pages:

- `index.html`: topic overview, brief anatomy, system boundaries, and routes into the site
- `guide.html`: eight-step method, prompt/harness split, copyable template, checklist, and gotchas
- `lab.html`: complete prompt comparisons, downloads, copy controls, rubric, and residual risks
- `references.html`: research, vendor guidance, CDC case notes, evidence labels, and caveats

Website prompts expand fully. The screenshot renderer adds a capture-only body class so release
PNGs remain bounded without changing the site.

### Publish from this repository

1. In this monorepo: **Settings → Pages → Build and deployment → Source = GitHub Actions**.
2. Merge to `main` (or run **Deploy long-horizon prompt lab** via workflow_dispatch).
3. Open `https://muratcankoylan.github.io/Agent-Skills-for-Context-Engineering/`

Deployment is defined in `.github/workflows/deploy-prompt-lab.yml`. The deploy job runs only on
`main`.


## What is here

```
report/            CDC case-study artifacts, fetched local with provenance
  cdc_prompt.pdf     OpenAI's published GPT-5.6 Sol Ultra Cycle Double Cover prompt
  cdc_proof.pdf      The candidate proof (unreviewed; see caveats)
  cdc_prompt.txt     Text extraction (for grep/diff)
  cdc_proof.txt
  PROVENANCE.md      Source URLs, SHA-256, retrieval date, caveats
scripts/
  fetch_report.sh    Re-fetch the report PDFs and re-extract text
  verify_report.py   Assert the skill's annotated CDC reference matches the published prompt
  install_skill.sh   Install the skill into .cursor/skills and validate it
  build_lab.py       Source of truth: prompt pairs + rubric scores -> data/ and ui/data.js
  validate_site.py   Deterministic pages, metadata, link, reference, sitemap, and prompt checks
  capture.mjs        Render the UI and capture the release screenshots
data/prompt-pairs.json  Machine-readable pairs and scores
ui/                Static multi-page site and generated prompt downloads
screenshots/       Generated PNGs for sharing
```

## The four use cases

Each "before" is a genuine prompt-engineered launch prompt (expert persona, task context,
chain-of-thought, explicit output format, persistence). None is a strawman. Each "after" is a
complete, copy-ready prompt that applies the pseudo-formal task-brief method; it is not a template
or an outline.

| Use case | Domain | Topology | Failure the brief pre-blocks |
| --- | --- | --- | --- |
| Autonomous model-improvement run | ML training | Single agent | "Beat the number" invites train-on-eval and single-seed noise wins |
| Parallel approximation-ratio proof | Algorithms / theory | 64-worker orchestration | Frequent-sync consensus is a diversity-collapse recipe |
| Long-horizon distributed-systems RCA | Concurrency | Multi-session single agent | "Find the root cause" has no checkable success predicate |
| Autonomous security audit / red-team | AppSec | Parallel workers | Persistence + checklist inflates unconfirmed findings |

The dominant edit differs by case (contamination guards for ML, diversity policy for the proof,
a reproduction predicate for RCA, non-counting outcomes for the audit), which is the point: the
skill is a checklist of independent failure modes, not one trick.

## Reproduce

```bash
# From the repo root. Requires python3 with pypdf and Pillow, and Node with Chrome available.
python3 -m pip install pypdf Pillow skills-ref

# 1. Bring the exemplar report local and verify the skill reference is faithful to it
examples/long-horizon-prompt-lab/scripts/fetch_report.sh
python3 examples/long-horizon-prompt-lab/scripts/verify_report.py

# 2. Install the skill into this project's .cursor/skills and validate it
examples/long-horizon-prompt-lab/scripts/install_skill.sh

# 3. Build, validate, serve, or capture the site
cd examples/long-horizon-prompt-lab
npm ci
npm test
npm run serve
# In another terminal: npm run capture
```

Open `http://localhost:8000/`. Prompt Lab cases use URL hashes such as
`lab.html#security-audit`. The site remains file-safe for local inspection, while HTTP is
recommended for clipboard behavior and production parity.

## How to read the scorecard

Each dimension is scored 0 (absent), 1 (present but gameable), or 2 (adversary-proof), straight
from the skill's rubric. `n/a` marks dimensions that do not apply (the diversity policy is
irrelevant to a single-agent run). The total is over applicable dimensions only.

## Honesty and limits

- The scores use the **skill's own rubric**, so a high "after" score means the brief fully
  applies the skill's checklist, measured by that checklist. This is a structural comparison of
  specification quality, not an outcome benchmark. It shows the briefs are harder to satisfy with
  a near miss; it does not claim any particular run succeeds.
- Every pair carries a **residual risk** the brief cannot remove (harness-enforced budgets,
  lenient proof verification, solvability framing on ill-posed problems, prompt-advisory scope
  limits). These are shown in the UI, not hidden.
- The CDC candidate proof in `report/` had **no peer review or formalization at publication**.
  The validated artifact of interest is the prompt structure, not the theorem. See
  `report/PROVENANCE.md`.
- `.cursor/` is gitignored in this repo, so the installed skill copy is not committed;
  `scripts/install_skill.sh` is the reproducible record of the install.

## Skills demonstrated

`long-horizon-prompting` (primary). Adjacent skills referenced by the briefs' division of labor:
`harness-engineering` (runtime-enforced budgets and permissions), `multi-agent-patterns`
(topology behind the orchestration policy), `advanced-evaluation` (adversarial audit design).
