#!/usr/bin/env node
// Enma sidecar launcher — one cross-platform entry point for the local Python
// sidecar in services/enma-api (see services/enma-api/server.py).
//
//   node scripts/enma.mjs setup   -> create venv (only if missing) + install deps
//   node scripts/enma.mjs start   -> run the sidecar (blocks; Ctrl+C stops it)
//   node scripts/enma.mjs smoke   -> run the sidecar's end-to-end smoke checks
//
// npm scripts (app/package.json): `npm run enma:setup` / `enma` / `enma:smoke`.
//
// Why a script instead of a one-liner: `python -m venv <existing dir>` REWRITES
// pyvenv.cfg to point at whatever interpreter runs it, silently re-basing a
// working venv onto another Python version and breaking its installed native
// wheels. This launcher therefore creates the venv exactly once (when missing)
// and never touches an existing one.

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SIDECAR = path.resolve(HERE, "..", "..", "services", "enma-api");
const VENV = path.join(SIDECAR, ".venv");
const PY = path.join(
  VENV,
  process.platform === "win32" ? path.join("Scripts", "python.exe") : path.join("bin", "python"),
);

// Enma is installed without its pinned dependencies: Enma 2.4.4 requires
// pydantic==2.8.2, whose pydantic-core has no wheels for current Python, while
// Enma runs fine on the modern versions pinned in requirements.txt (verified).
const ENMA_PIN = "enma==2.4.4";

// Preferred interpreters, in order. 3.13 is first because the sidecar's native
// dependency set is verified against it; anything >= 3.9 is accepted.
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
        ["python3", []],
        ["python", []],
      ];

function fail(message) {
  console.error(`enma: ${message}`);
  process.exit(1);
}

/** Returns "major.minor" when cmd+args runs and reports Python >= 3.9. */
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
  if (existsSync(PY)) return; // never re-create (and never re-base) an existing venv
  const interp = findInterpreter();
  if (!interp) {
    fail(
      "no Python >= 3.9 found (tried: " +
        CANDIDATES.map(([c, a]) => [c, ...a].join(" ")).join(", ") +
        "). Install Python or create services/enma-api/.venv manually.",
    );
  }
  console.log(`enma: creating venv with Python ${interp.version}`);
  const res = spawnSync(interp.cmd, [...interp.args, "-m", "venv", VENV], { stdio: "inherit" });
  if (res.status !== 0) fail(`venv creation failed (exit ${res.status})`);
  if (!existsSync(PY)) fail(`venv was created but ${PY} is missing`);
}

function pip(args) {
  const res = spawnSync(PY, ["-m", "pip", "install", ...args], {
    stdio: "inherit",
    cwd: SIDECAR,
  });
  if (res.status !== 0) fail(`pip install failed (exit ${res.status})`);
}

function requireVenv(command) {
  if (!existsSync(PY)) {
    fail(`venv missing — run \`npm run enma:setup\` before \`npm run ${command}\`.`);
  }
}

const command = process.argv[2];

switch (command) {
  case "setup": {
    ensureVenv();
    pip(["--no-deps", ENMA_PIN]);
    pip(["-r", path.join(SIDECAR, "requirements.txt")]);
    console.log("enma: sidecar ready — start it with `npm run enma`.");
    break;
  }

  case "start": {
    requireVenv("enma");
    const child = spawn(PY, [path.join(SIDECAR, "server.py")], {
      stdio: "inherit",
      cwd: SIDECAR,
    });
    const stop = (signal) => {
      child.kill(signal);
    };
    process.on("SIGINT", () => stop("SIGINT"));
    process.on("SIGTERM", () => stop("SIGTERM"));
    child.on("exit", (code, signal) => {
      process.exit(signal ? 0 : (code ?? 0));
    });
    child.on("error", (err) => fail(`could not start sidecar: ${err.message}`));
    break;
  }

  case "smoke": {
    requireVenv("enma:smoke");
    const res = spawnSync(PY, [path.join(SIDECAR, "smoke.py")], {
      stdio: "inherit",
      cwd: SIDECAR,
    });
    process.exit(res.status ?? 1);
    break;
  }

  default:
    console.error("usage: node scripts/enma.mjs <setup|start|smoke>");
    process.exit(command ? 1 : 0);
}
