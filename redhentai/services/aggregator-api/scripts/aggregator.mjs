#!/usr/bin/env node
// Aggregator API launcher - cross-platform startup for the Python FastAPI service
//
//   node scripts/aggregator.mjs setup   -> create venv + install deps
//   node scripts/aggregator.mjs start   -> run the API server
//   node scripts/aggregator.mjs test    -> run API tests

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SERVICE = path.resolve(HERE, "..", "services", "aggregator-api");
const VENV = path.join(SERVICE, ".venv");
const PY = path.join(
  VENV,
  process.platform === "win32"
    ? path.join("Scripts", "python.exe")
    : path.join("bin", "python"),
);

const CANDIDATES =
  process.platform === "win32"
    ? [
        ["py", ["-3.13"]],
        ["py", ["-3.12"]],
        ["py", ["-3.11"]],
        ["py", ["-3"]],
        ["python", []],
      ]
    : [
        ["python3.13", []],
        ["python3.12", []],
        ["python3.11", []],
        ["python3", []],
        ["python", []],
      ];

function fail(message) {
  console.error(`aggregator: ${message}`);
  process.exit(1);
}

function versionOf(cmd, args) {
  const res = spawnSync(cmd, [...args, "--version"], { encoding: "utf8" });
  if (res.error || res.status !== 0) return null;
  const match = `${res.stdout ?? ""}${res.stderr ?? ""}`.match(/Python (\d+)\.(\d+)/);
  if (!match) return null;
  const [, major, minor] = match.map(Number);
  return major === 3 && minor >= 9 ? `${major}.${minor}` : null;
}

function findInterpreter() {
  for (const [cmd, args] of CANDIDATES) {
    const version = versionOf(cmd, args);
    if (version) return { cmd, args, version };
  }
  return null;
}

function ensureVenv() {
  if (existsSync(PY)) return;
  const interp = findInterpreter();
  if (!interp) {
    fail(
      "No Python >= 3.9 found (tried: " +
        CANDIDATES.map(([c, a]) => [c, ...a].join(" ")).join(", ") +
        "). Install Python or create services/aggregator-api/.venv manually.",
    );
  }
  console.log(`aggregator: creating venv with Python ${interp.version}`);
  const res = spawnSync(interp.cmd, [...interp.args, "-m", "venv", VENV], { stdio: "inherit" });
  if (res.status !== 0) fail(`venv creation failed (exit ${res.status})`);
  if (!existsSync(PY)) fail(`venv was created but ${PY} is missing`);
}

function pip(args) {
  const res = spawnSync(PY, ["-m", "pip", "install", ...args], {
    stdio: "inherit",
    cwd: SERVICE,
  });
  if (res.status !== 0) fail(`pip install failed (exit ${res.status})`);
}

function requireVenv(command) {
  if (!existsSync(PY)) {
    fail(`venv missing — run \`npm run aggregator:setup\` before \`npm run ${command}\`.`);
  }
}

const command = process.argv[2];

switch (command) {
  case "setup": {
    ensureVenv();
    pip(["-r", path.join(SERVICE, "requirements.txt")]);
    console.log("aggregator: API service ready — start it with `npm run aggregator`.");
    break;
  }

  case "start": {
    requireVenv("aggregator");
    const child = spawn(PY, [path.join(SERVICE, "app", "main.py")], {
      stdio: "inherit",
      cwd: SERVICE,
      env: { ...process.env, PYTHONPATH: SERVICE },
    });
    const stop = (signal) => child.kill(signal);
    process.on("SIGINT", () => stop("SIGINT"));
    process.on("SIGTERM", () => stop("SIGTERM"));
    child.on("exit", (code, signal) => {
      process.exit(signal ? 0 : (code ?? 0));
    });
    child.on("error", (err) => fail(`could not start API: ${err.message}`));
    break;
  }

  case "test": {
    requireVenv("aggregator:test");
    const res = spawnSync(PY, ["-m", "pytest", "tests/", "-v"], {
      stdio: "inherit",
      cwd: SERVICE,
    });
    process.exit(res.status ?? 1);
    break;
  }

  default:
    console.error("usage: node scripts/aggregator.mjs <setup|start|test>");
    process.exit(command ? 1 : 0);
}