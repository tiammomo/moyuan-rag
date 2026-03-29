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
const nextExportDir = path.join(projectRoot, ".next", "export");

function runNextBuild() {
  const result = spawnSync(process.execPath, [nextBin, "build"], {
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
    console.error(`[next-build] Failed to run next build: ${result.error.message}`);
    process.exit(1);
  }

  return result;
}

function shouldRetryExportCleanup(result) {
  const output = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  return output.includes("ENOTEMPTY") && output.includes(".next") && output.includes("export");
}

function resetExportArtifacts() {
  fs.rmSync(nextExportDir, {
    recursive: true,
    force: true,
    maxRetries: 5,
    retryDelay: 200,
  });
}

let buildResult = runNextBuild();

if (buildResult.status !== 0 && shouldRetryExportCleanup(buildResult)) {
  console.log("[next-build] Resetting stale `.next/export` artifacts before one retry.");
  resetExportArtifacts();
  buildResult = runNextBuild();
}

process.exit(buildResult.status ?? 1);
