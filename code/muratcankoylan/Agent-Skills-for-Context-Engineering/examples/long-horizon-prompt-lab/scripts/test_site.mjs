#!/usr/bin/env node
import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import puppeteer from "puppeteer-core";

const HERE = dirname(fileURLToPath(import.meta.url));
const LAB = resolve(HERE, "..");
const PROJECT_PATH = "Agent-Skills-for-Context-Engineering";
const PORT = 8765;

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "/usr/bin/google-chrome-stable",
  "/usr/local/bin/google-chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);

function findChrome() {
  for (const candidate of CHROME_CANDIDATES) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error("Chrome/Chromium not found. Set CHROME_PATH.");
}

async function waitForServer(url, attempts = 30) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch (_) {
      // Server is still starting.
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 100));
  }
  throw new Error(`Server did not become healthy: ${url}`);
}

async function main() {
  const root = mkdtempSync(resolve(tmpdir(), "long-horizon-site-"));
  const site = resolve(root, PROJECT_PATH);
  mkdirSync(site, { recursive: true });
  cpSync(resolve(LAB, "ui"), site, { recursive: true });
  cpSync(resolve(LAB, "screenshots", "shot-hero.png"), resolve(site, "social-card.png"));

  const server = spawn(
    "python3",
    ["-m", "http.server", String(PORT), "--bind", "127.0.0.1", "--directory", root],
    { stdio: "ignore" },
  );
  const origin = `http://127.0.0.1:${PORT}/${PROJECT_PATH}/`;

  let browser;
  try {
    await waitForServer(origin);
    browser = await puppeteer.launch({
      executablePath: findChrome(),
      headless: "new",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
    const page = await browser.newPage();
    const failures = [];
    page.on("console", (message) => {
      if (message.type() === "error") failures.push(`console: ${message.text()}`);
    });
    page.on("pageerror", (error) => failures.push(`pageerror: ${error.message}`));

    const pages = ["index.html", "guide.html", "lab.html#ml-optimization", "references.html", "404.html"];
    for (const width of [320, 390, 768, 1480]) {
      await page.setViewport({ width, height: 900, deviceScaleFactor: 1 });
      for (const path of pages) {
        const response = await page.goto(origin + path, { waitUntil: "networkidle0" });
        if (![200, 304].includes(response.status())) {
          failures.push(`${path}@${width}: HTTP ${response.status()}`);
        }
        const metrics = await page.evaluate(() => ({
          h1: document.querySelectorAll("h1").length,
          nav: document.querySelectorAll(".site-nav a").length,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }));
        if (metrics.h1 !== 1) failures.push(`${path}@${width}: ${metrics.h1} h1 elements`);
        if (metrics.nav !== 4) failures.push(`${path}@${width}: ${metrics.nav} nav links`);
        if (metrics.scrollWidth > metrics.clientWidth + 1) {
          failures.push(`${path}@${width}: horizontal overflow`);
        }
      }
    }

    await page.setViewport({ width: 1480, height: 900, deviceScaleFactor: 1 });
    await page.goto(origin + "index.html", { waitUntil: "networkidle0" });
    await page.click("[data-copy-install]");
    await page.waitForFunction(
      () => document.querySelector("#install-status").textContent.includes("Copied"),
      { timeout: 3000 },
    );

    await page.goto(origin + "guide.html", { waitUntil: "networkidle0" });
    await page.click('[data-copy-target="brief-template"]');
    await page.waitForFunction(
      () => document.querySelector("#template-status").textContent.includes("Copied"),
      { timeout: 3000 },
    );

    await page.goto(origin + "lab.html#ml-optimization", { waitUntil: "networkidle0" });
    const prompts = await page.$$eval("pre.prompt", (nodes) =>
      nodes.map((node) => ({
        clientHeight: node.clientHeight,
        scrollHeight: node.scrollHeight,
        words: node.textContent.trim().split(/\s+/).length,
      })),
    );
    if (prompts.some((prompt) => prompt.scrollHeight > prompt.clientHeight + 1)) {
      failures.push("lab: prompt content clipped");
    }
    if (prompts.map((prompt) => prompt.words).join(",") !== "183,836") {
      failures.push(`lab: unexpected prompt word counts ${JSON.stringify(prompts)}`);
    }

    await page.focus("#tab-ml-optimization");
    await page.keyboard.press("End");
    const selected = await page.$eval(
      '[role="tab"][aria-selected="true"]',
      (node) => node.dataset.id,
    );
    if (selected !== "security-audit") failures.push(`lab: keyboard selected ${selected}`);

    const downloadHref = await page.$eval(
      ".panel-after .download-link",
      (node) => node.getAttribute("href"),
    );
    const downloadResponse = await page.goto(origin + downloadHref);
    if (!downloadResponse.ok()) failures.push(`prompt download: HTTP ${downloadResponse.status()}`);

    await page.goto(origin + "references.html", { waitUntil: "networkidle0" });
    const referenceCount = await page.$$eval(".reference-card", (nodes) => nodes.length);
    if (referenceCount < 25) failures.push(`references: only ${referenceCount} cards`);

    await page.setJavaScriptEnabled(false);
    await page.goto(origin + "lab.html", { waitUntil: "networkidle0" });
    const noScriptDownloads = await page.$$eval(
      'noscript a[href$=".txt"]',
      (nodes) => nodes.length,
    );
    if (noScriptDownloads !== 8) {
      failures.push(`lab no-JS fallback: ${noScriptDownloads} prompt downloads`);
    }

    if (failures.length) throw new Error(failures.join("\n"));
    console.log(
      `Browser checks passed: ${pages.length} pages x 4 widths, copy controls, ` +
      `keyboard tabs, ${referenceCount} references, full prompts, downloads, and no-JS fallback`,
    );
  } finally {
    if (browser) await browser.close();
    server.kill("SIGTERM");
    rmSync(root, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
