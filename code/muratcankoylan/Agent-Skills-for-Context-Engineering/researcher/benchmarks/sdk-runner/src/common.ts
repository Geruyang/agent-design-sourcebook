/**
 * Shared utilities for the researcher SDK benchmark runner.
 *
 * Pure helpers only. No SDK calls live here so the helpers can be
 * unit-tested or invoked from --dry-run without an API key.
 */

import { createHash } from "node:crypto";
import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, existsSync, appendFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SDK_RUNNER_DIR = dirname(fileURLToPath(import.meta.url));
export const RUNNER_ROOT = resolve(SDK_RUNNER_DIR, "..");
export const RESEARCHER_DIR = resolve(RUNNER_ROOT, "..", "..");
export const REPO_ROOT = resolve(RESEARCHER_DIR, "..");

export type SkillId = string;

export interface ResolvedConfig {
  models: string[];
  reps: number;
  maxRuns: number;
  maxBudgetUsd: number;
  seed: number;
  fixturePath: string;
  dryRun: boolean;
  unsafeNoCostCap: boolean;
  concurrency: number;
  noResume: boolean;
}

export interface RunPlanItem {
  promptId: string;
  modelId: string;
  rep: number;
  shuffleSeed: number;
}

export interface CliFlags {
  models?: string[];
  reps?: number;
  maxRuns?: number;
  maxBudgetUsd?: number;
  seed?: number;
  fixture?: string;
  dryRun: boolean;
  unsafeNoCostCap: boolean;
  concurrency?: number;
  noResume: boolean;
}

const DEFAULT_MODELS = ["composer-2"];

export function parseCliFlags(argv: string[]): CliFlags {
  const flags: CliFlags = { dryRun: false, unsafeNoCostCap: false, noResume: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case "--dry-run":
        flags.dryRun = true;
        break;
      case "--unsafe-no-cost-cap":
        flags.unsafeNoCostCap = true;
        break;
      case "--no-resume":
        flags.noResume = true;
        break;
      case "--models":
        flags.models = (argv[++i] ?? "").split(",").map((value) => value.trim()).filter(Boolean);
        break;
      case "--reps":
        flags.reps = Number(argv[++i]);
        break;
      case "--max-runs":
        flags.maxRuns = Number(argv[++i]);
        break;
      case "--max-budget-usd":
        flags.maxBudgetUsd = Number(argv[++i]);
        break;
      case "--seed":
        flags.seed = Number(argv[++i]);
        break;
      case "--fixture":
        flags.fixture = argv[++i] ?? "";
        break;
      case "--concurrency":
        flags.concurrency = Number(argv[++i]);
        break;
      default:
        if (arg?.startsWith("--")) {
          throw new Error(`Unknown flag: ${arg}`);
        }
    }
  }
  return flags;
}

export function resolveConfig(
  flags: CliFlags,
  defaultFixturePath: string,
): ResolvedConfig {
  if (!flags.unsafeNoCostCap && !flags.maxRuns && !flags.maxBudgetUsd && !flags.dryRun) {
    throw new Error(
      "Refusing to run without a cost cap. Pass --max-runs or --max-budget-usd or --unsafe-no-cost-cap. " +
        "Use --dry-run to see the plan without any agent calls.",
    );
  }
  return {
    models: flags.models?.length ? flags.models : DEFAULT_MODELS,
    reps: flags.reps && flags.reps > 0 ? flags.reps : 3,
    maxRuns: flags.maxRuns ?? Number.MAX_SAFE_INTEGER,
    maxBudgetUsd: flags.maxBudgetUsd ?? Number.MAX_SAFE_INTEGER,
    seed: flags.seed ?? 1,
    fixturePath: flags.fixture ?? defaultFixturePath,
    dryRun: flags.dryRun,
    unsafeNoCostCap: flags.unsafeNoCostCap,
    concurrency: flags.concurrency && flags.concurrency > 0 ? flags.concurrency : 1,
    noResume: flags.noResume,
  };
}

/**
 * Bounded-concurrency executor. Runs `worker(item, index)` for every input,
 * keeping at most `limit` workers active at any time. Preserves output order.
 * Failures inside a worker bubble up; callers are expected to wrap workers in
 * their own try/catch when partial failure is acceptable.
 */
export async function runConcurrently<T, R>(
  items: T[],
  limit: number,
  worker: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  const concurrency = Math.max(1, Math.min(limit, items.length));
  let next = 0;
  async function run(): Promise<void> {
    while (true) {
      const index = next++;
      if (index >= items.length) return;
      results[index] = await worker(items[index] as T, index);
    }
  }
  const workers = Array.from({ length: concurrency }, () => run());
  await Promise.all(workers);
  return results;
}

/**
 * Pure-function key derivation for a per-run result file. Used both by the
 * runner (when writing) and the resume scan (when checking). Keeping this in
 * one place prevents the two from drifting.
 */
export function resultFileName(promptId: string, modelId: string, rep: number): string {
  return `${promptId}-${modelId}-${rep}.json`;
}

export function loadJsonl<T>(path: string): T[] {
  if (!existsSync(path)) {
    throw new Error(`Fixture missing: ${path}`);
  }
  const lines = readFileSync(path, "utf-8").split("\n");
  const records: T[] = [];
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const trimmed = lines[lineIndex]?.trim();
    if (!trimmed) continue;
    try {
      records.push(JSON.parse(trimmed) as T);
    } catch (error) {
      throw new Error(`Invalid JSONL at ${path}:${lineIndex + 1}: ${(error as Error).message}`);
    }
  }
  return records;
}

export function appendHistoryEntry(historyPath: string, entry: Record<string, unknown>): void {
  mkdirSync(dirname(historyPath), { recursive: true });
  appendFileSync(historyPath, JSON.stringify(entry) + "\n");
}

export function writeJson(path: string, data: unknown): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(data, null, 2) + "\n");
}

export function utcNow(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

export function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

export function repoCommitSha(): string | null {
  try {
    return execSync("git rev-parse HEAD", { cwd: REPO_ROOT, encoding: "utf-8" }).trim();
  } catch {
    return null;
  }
}

export function fixtureSha(path: string): string {
  const content = readFileSync(path, "utf-8");
  return createHash("sha256").update(content).digest("hex").slice(0, 16);
}

export function apiKeyFingerprint(): string {
  const key = process.env.CURSOR_API_KEY;
  if (!key || key.length < 8) {
    return "unset";
  }
  return `***${key.slice(-4)}`;
}

/**
 * Deterministic Fisher-Yates shuffle using a seeded mulberry32 PRNG so the
 * skill ordering inside the routing prompt is reproducible for a given seed.
 */
export function shuffleSeeded<T>(input: T[], seed: number): T[] {
  const out = input.slice();
  let state = seed >>> 0;
  const next = () => {
    state += 0x6d2b79f5;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

export function buildRunPlan(
  promptIds: string[],
  models: string[],
  reps: number,
  baseSeed: number,
): RunPlanItem[] {
  const plan: RunPlanItem[] = [];
  for (const promptId of promptIds) {
    for (const modelId of models) {
      for (let rep = 0; rep < reps; rep++) {
        plan.push({
          promptId,
          modelId,
          rep,
          shuffleSeed: hash32(`${promptId}|${modelId}|${rep}|${baseSeed}`),
        });
      }
    }
  }
  return plan;
}

export function hash32(text: string): number {
  const digest = createHash("sha256").update(text).digest();
  return digest.readUInt32BE(0);
}

export function loadSkillDescriptions(): Array<{ name: string; description: string }> {
  const corpusPath = join(RESEARCHER_DIR, "corpus", "index.json");
  if (!existsSync(corpusPath)) {
    throw new Error(`Corpus index missing at ${corpusPath}`);
  }
  const corpus = JSON.parse(readFileSync(corpusPath, "utf-8")) as {
    skills: Array<{ name: string; path: string }>;
  };
  const out: Array<{ name: string; description: string }> = [];
  for (const skill of corpus.skills) {
    const skillPath = join(REPO_ROOT, skill.path);
    if (!existsSync(skillPath)) {
      throw new Error(`Skill missing: ${skillPath}`);
    }
    const text = readFileSync(skillPath, "utf-8");
    const description = extractDescription(text);
    if (!description) {
      throw new Error(`Skill ${skill.name} has no frontmatter description`);
    }
    out.push({ name: skill.name, description });
  }
  return out;
}

export function extractDescription(text: string): string | null {
  if (!text.startsWith("---")) return null;
  const end = text.indexOf("\n---", 4);
  if (end === -1) return null;
  const body = text.slice(4, end);
  let inDescription = false;
  const lines: string[] = [];
  for (const raw of body.split("\n")) {
    if (raw.startsWith("description:")) {
      inDescription = true;
      const value = raw.slice("description:".length).trim();
      if (value && value !== ">" && value !== ">-") {
        lines.push(value.replace(/^"|"$/g, ""));
        inDescription = false;
      }
      continue;
    }
    if (inDescription) {
      if (/^[a-z_]+:/i.test(raw)) {
        inDescription = false;
        continue;
      }
      const trimmed = raw.trim();
      if (trimmed) lines.push(trimmed);
    }
  }
  return lines.join(" ").trim() || null;
}

export interface CostForecast {
  totalRuns: number;
  estimatedTokensPerRunInput: number;
  estimatedTokensPerRunOutput: number;
  estimatedUsdPerRun: number;
  estimatedTotalUsd: number;
}

export function forecastCost(
  plan: RunPlanItem[],
  estimatedTokensPerRunInput: number,
  estimatedTokensPerRunOutput: number,
  estimatedUsdPerRun: number,
): CostForecast {
  return {
    totalRuns: plan.length,
    estimatedTokensPerRunInput,
    estimatedTokensPerRunOutput,
    estimatedUsdPerRun,
    estimatedTotalUsd: Number((estimatedUsdPerRun * plan.length).toFixed(4)),
  };
}

export function assertBudget(plan: RunPlanItem[], forecast: CostForecast, config: ResolvedConfig): void {
  if (plan.length > config.maxRuns) {
    throw new Error(`Plan size ${plan.length} exceeds --max-runs ${config.maxRuns}`);
  }
  if (forecast.estimatedTotalUsd > config.maxBudgetUsd) {
    throw new Error(
      `Forecast ${forecast.estimatedTotalUsd} USD exceeds --max-budget-usd ${config.maxBudgetUsd}`,
    );
  }
}

export function runHeader(label: string): string {
  const sep = "=".repeat(72);
  return `${sep}\n${label}\n${sep}`;
}
