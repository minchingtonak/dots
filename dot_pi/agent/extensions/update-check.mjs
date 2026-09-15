#!/usr/bin/env node
/**
 * Background extension-update check for the pi statusline.
 *
 * Compares installed versions (~/.pi/agent/npm/node_modules) against the npm
 * registry for every package in settings.json "packages", then writes
 * ~/.pi/agent/cache/extension-updates.json. The statusline renders a ⬆N badge
 * from that cache and re-spawns this script when the cache is stale.
 *
 * Notify-only: never installs anything. Run `pi update --extensions` to apply.
 */

import { execFile } from "node:child_process";
import { mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";

const AGENT_DIR = `${homedir()}/.pi/agent`;
const CACHE = `${AGENT_DIR}/cache/extension-updates.json`;
const LOCK = `${AGENT_DIR}/cache/update-check.lock`;
const LOCK_TTL_MS = 120_000;

function npmView(name) {
  return new Promise((resolve) => {
    execFile("npm", ["view", name, "version"], { timeout: 15_000 }, (err, stdout) => {
      resolve(err ? null : stdout.trim());
    });
  });
}

function semverGt(a, b) {
  const pa = a.split("-")[0].split(".").map(Number);
  const pb = b.split("-")[0].split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) > (pb[i] || 0);
  }
  return false;
}

// single-instance lock: fresh lock means a check is already running
try {
  if (Date.now() - statSync(LOCK).mtimeMs < LOCK_TTL_MS) process.exit(0);
} catch {
  /* no lock */
}
mkdirSync(dirname(LOCK), { recursive: true });
writeFileSync(LOCK, String(process.pid));

try {
  const pkgs = JSON.parse(readFileSync(`${AGENT_DIR}/settings.json`, "utf8")).packages ?? [];
  const updates = [];
  for (const src of pkgs) {
    if (!src.startsWith("npm:")) continue;
    const name = src.slice(4);
    let current;
    try {
      current = JSON.parse(
        readFileSync(`${AGENT_DIR}/npm/node_modules/${name}/package.json`, "utf8"),
      ).version;
    } catch {
      continue; // not materialized yet; pi will install on next start
    }
    const latest = await npmView(name);
    if (latest && current && semverGt(latest, current)) {
      updates.push(`${name} ${current} -> ${latest}`);
    }
  }
  const payload =
    JSON.stringify({ at: Date.now(), count: updates.length, updates }, null, 2) + "\n";
  mkdirSync(dirname(CACHE), { recursive: true });
  const tmp = `${CACHE}.tmp`;
  writeFileSync(tmp, payload);
  renameSync(tmp, CACHE);
} finally {
  try {
    rmSync(LOCK);
  } catch {
    /* already gone */
  }
}
