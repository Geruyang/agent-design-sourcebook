/**
 * Stage 3: Skill effectiveness benchmark.
 *
 * Hypothesis: loading a relevant skill improves outcome quality or token
 * efficiency on tasks the skill claims to address. Irrelevant skills should
 * have no effect (negative control).
 *
 * Scaffold only in v2.2.x. Full implementation lands in v2.4.0 once the task
 * set reaches 20 and the budget for the full sweep is signed off.
 *
 * The runner already supports --dry-run to print the plan and cost forecast
 * against the currently-built task set.
 */

import { join } from "node:path";
import { existsSync, readdirSync, statSync, readFileSync, mkdirSync } from "node:fs";

import {
  RESEARCHER_DIR,
  apiKeyFingerprint,
  assertBudget,
  buildRunPlan,
  forecastCost,
  parseCliFlags,
  resolveConfig,
  runHeader,
  todayUtc,
} from "./common.ts";

interface EffectivenessTaskMetadata {
  id: string;
  slug: string;
  target_skill: string;
  irrelevant_skill: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  notes?: string;
}

const TASKS_DIR = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "tasks");
const RESULTS_DIR = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "results");
const CONDITIONS = ["control", "target", "negative", "full", "target_plus_one", "target_plus_unrelated"] as const;

const ESTIMATED_TOKENS_INPUT = 20_000;
const ESTIMATED_TOKENS_OUTPUT = 4_000;
const ESTIMATED_USD_PER_RUN = 0.18;

async function main(): Promise<number> {
  const flags = parseCliFlags(process.argv.slice(2));
  const defaultFixture = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "tasks");
  const config = resolveConfig(flags, defaultFixture);

  console.log(runHeader("Effectiveness Benchmark (Stage 3)"));
  console.log(`tasks dir: ${TASKS_DIR}`);
  console.log(`models: ${config.models.join(", ")}`);
  console.log(`reps per (task, condition, model): ${config.reps}`);
  console.log(`seed: ${config.seed}`);
  console.log(`dry-run: ${config.dryRun}`);
  console.log(`api key: ${apiKeyFingerprint()}`);

  if (!existsSync(TASKS_DIR)) {
    console.error(`Tasks directory missing: ${TASKS_DIR}`);
    return 1;
  }

  const tasks = discoverTasks();
  console.log(`tasks discovered: ${tasks.length}`);

  if (tasks.length === 0) {
    console.error("No tasks present yet. Add at least one task under researcher/benchmarks/effectiveness/tasks/.");
    return 1;
  }

  const planIds: string[] = [];
  for (const task of tasks) {
    for (const condition of CONDITIONS) {
      planIds.push(`${task.id}|${condition}`);
    }
  }
  const plan = buildRunPlan(planIds, config.models, config.reps, config.seed);
  const forecast = forecastCost(plan, ESTIMATED_TOKENS_INPUT, ESTIMATED_TOKENS_OUTPUT, ESTIMATED_USD_PER_RUN);
  console.log(`planned runs: ${forecast.totalRuns}`);
  console.log(`conditions per task: ${CONDITIONS.length}`);
  console.log(`est. tokens per run: ${ESTIMATED_TOKENS_INPUT}in / ${ESTIMATED_TOKENS_OUTPUT}out`);
  console.log(`est. total cost: ${forecast.estimatedTotalUsd} USD`);

  assertBudget(plan, forecast, config);

  if (config.dryRun) {
    console.log("Dry-run: no SDK calls made.");
    console.log("First three tasks:");
    for (const task of tasks.slice(0, 3)) {
      console.log(`  - ${task.id} target=${task.target_skill} difficulty=${task.difficulty}`);
    }
    return 0;
  }

  console.error(
    "Stage 3 executor not yet wired in v2.2.x scaffold. See researcher/benchmarks/PLAN.md for the v2.4.0 implementation contract. " +
      "Use --dry-run to validate task and config shape today.",
  );
  mkdirSync(join(RESULTS_DIR, `${todayUtc()}-${config.seed}`), { recursive: true });
  return 0;
}

function discoverTasks(): EffectivenessTaskMetadata[] {
  const tasks: EffectivenessTaskMetadata[] = [];
  for (const entry of readdirSync(TASKS_DIR).sort()) {
    const dir = join(TASKS_DIR, entry);
    if (!statSync(dir).isDirectory()) continue;
    const metaPath = join(dir, "metadata.json");
    if (!existsSync(metaPath)) continue;
    try {
      const meta = JSON.parse(readFileSync(metaPath, "utf-8")) as EffectivenessTaskMetadata;
      tasks.push(meta);
    } catch (error) {
      console.warn(`Skipping ${entry}: invalid metadata.json (${(error as Error).message})`);
    }
  }
  return tasks;
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(error);
    process.exit(2);
  });
