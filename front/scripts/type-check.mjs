import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");

const nextBin = require.resolve("next/dist/bin/next");
const tscBin = require.resolve("typescript/bin/tsc");
const requiredTypeMarkers = [
  path.join(projectRoot, ".next", "types", "package.json"),
  path.join(projectRoot, ".next", "types", "app", "page.ts"),
];

function runNodeScript(scriptPath, args, label) {
  const result = spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: projectRoot,
    env: process.env,
    encoding: "utf8",
  });

  if (result.stdout) {
    process.stdout.write(result.stdout);
  }

  if (result.stderr) {
    process.stderr.write(result.stderr);
  }

  if (result.error) {
    console.error(`[type-check] Failed to run ${label}:`, result.error.message);
    process.exit(1);
  }

  return result;
}

function hasGeneratedTypes() {
  return requiredTypeMarkers.every((filePath) => fs.existsSync(filePath));
}

function shouldRebuildFromTypecheck(result) {
  const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  return output.includes(".next/types") || output.includes("TS6053");
}

function ensureGeneratedTypes(reason) {
  console.log(`[type-check] ${reason}`);
  const buildResult = runNodeScript(nextBin, ["build"], "next build");

  if (buildResult.status !== 0) {
    process.exit(buildResult.status ?? 1);
  }
}

if (!hasGeneratedTypes()) {
  ensureGeneratedTypes("Next generated types are missing; bootstrapping them with `next build`.");
}

let typecheckResult = runNodeScript(
  tscBin,
  ["--noEmit", "--incremental", "false"],
  "tsc --noEmit --incremental false",
);

if (typecheckResult.status !== 0 && shouldRebuildFromTypecheck(typecheckResult)) {
  ensureGeneratedTypes(
    "Detected stale or missing `.next/types` references during type-check; rebuilding once before retry.",
  );
  typecheckResult = runNodeScript(
    tscBin,
    ["--noEmit", "--incremental", "false"],
    "tsc --noEmit --incremental false",
  );
}

process.exit(typecheckResult.status ?? 1);
