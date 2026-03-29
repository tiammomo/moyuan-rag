#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a compact Playwright smoke report manifest and optional GitHub job summary."
    )
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--latest-run-json", required=True)
    parser.add_argument("--stack-status-json", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--job-summary-out")
    parser.add_argument("--job-summary-env", default="GITHUB_STEP_SUMMARY")
    parser.add_argument("--write-job-summary", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return {}
    return json.loads(raw)


def normalize_artifact_path(path: str | None, workspace_root: Path) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    try:
        if candidate.is_absolute():
            return str(candidate.relative_to(workspace_root)).replace("\\", "/")
    except ValueError:
        return str(candidate).replace("\\", "/")
    return str(candidate).replace("\\", "/")


def build_manifest(
    *,
    summary_payload: dict[str, Any],
    latest_run_payload: dict[str, Any],
    stack_payload: dict[str, Any],
    artifacts_dir: Path,
    workspace_root: Path,
) -> dict[str, Any]:
    steps = summary_payload.get("steps") or []
    endpoints = stack_payload.get("Endpoints") or []
    summary = stack_payload.get("Summary") or {}

    screenshot_entries: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        screenshot_entries.append(
            {
                "step": step.get("name"),
                "status": step.get("status"),
                "screenshot": normalize_artifact_path(step.get("screenshot"), workspace_root),
            }
        )

    endpoint_entries: list[dict[str, Any]] = []
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            continue
        endpoint_entries.append(
            {
                "name": endpoint.get("Name"),
                "reachable": endpoint.get("Reachable"),
                "status_code": endpoint.get("StatusCode"),
                "warning": endpoint.get("Warning"),
            }
        )

    files = [
        "stack-status.json",
        "compose-logs.txt",
        "compose-ps.json",
        "backend-health.json",
        "front-index.html",
        "latest-run.json",
        "latest-summary.json",
        "artifact-manifest.json",
        "job-summary.md",
    ]

    return {
        "workflow": "frontend-playwright-smoke",
        "status": summary_payload.get("status") or latest_run_payload.get("status") or "unknown",
        "base_url": latest_run_payload.get("base_url") or summary_payload.get("base_url"),
        "api_url": latest_run_payload.get("api_url") or summary_payload.get("api_url"),
        "latest_run_dir": normalize_artifact_path(latest_run_payload.get("latest_run_dir"), workspace_root),
        "latest_summary_path": normalize_artifact_path(latest_run_payload.get("latest_summary_path"), workspace_root),
        "latest_artifact_dir": normalize_artifact_path(latest_run_payload.get("latest_artifact_dir"), workspace_root),
        "stack_summary": {
            "running_services": summary.get("RunningServices"),
            "total_services": summary.get("TotalServices"),
            "healthy_services": summary.get("HealthyServices"),
            "non_running_services": summary.get("NonRunningServices"),
            "unhealthy_services": summary.get("UnhealthyServices"),
        },
        "steps": screenshot_entries,
        "endpoints": endpoint_entries,
        "artifact_files": [str((artifacts_dir / file_name).name) for file_name in files if (artifacts_dir / file_name).exists()],
    }


def build_markdown(
    *,
    summary_payload: dict[str, Any],
    manifest: dict[str, Any],
    stack_payload: dict[str, Any],
) -> str:
    smoke_status = manifest.get("status", "unknown")
    running = manifest.get("stack_summary", {}).get("running_services")
    total = manifest.get("stack_summary", {}).get("total_services")
    healthy = manifest.get("stack_summary", {}).get("healthy_services")

    lines = [
        "# Frontend Playwright Smoke",
        "",
        f"- Status: `{smoke_status}`",
        f"- Frontend: `{manifest.get('base_url')}`",
        f"- Backend: `{manifest.get('api_url')}`",
        f"- Stack services: `{running}/{total}` running, `{healthy}` healthy",
        f"- Latest run dir: `{manifest.get('latest_run_dir')}`",
        "",
        "## Smoke Steps",
    ]

    for step in manifest.get("steps", []):
        lines.append(
            f"- `{step.get('step')}`: `{step.get('status')}`"
            + (f" -> `{step.get('screenshot')}`" if step.get("screenshot") else "")
        )

    endpoint_warnings = [item for item in manifest.get("endpoints", []) if item.get("warning")]
    if endpoint_warnings:
        lines.extend(["", "## Endpoint Warnings"])
        for endpoint in endpoint_warnings:
            lines.append(f"- `{endpoint.get('name')}`: {endpoint.get('warning')}")

    stack_summary = stack_payload.get("Summary") or {}
    if stack_summary.get("NonRunningServices") or stack_summary.get("UnhealthyServices"):
        lines.extend(["", "## Stack Alerts"])
        non_running = stack_summary.get("NonRunningServices") or []
        unhealthy = stack_summary.get("UnhealthyServices") or []
        if non_running:
            lines.append(f"- Non-running services: `{', '.join(non_running)}`")
        if unhealthy:
            lines.append(f"- Unhealthy services: `{', '.join(unhealthy)}`")

    lines.extend(["", "## Artifact Files"])
    for file_name in manifest.get("artifact_files", []):
        lines.append(f"- `{file_name}`")

    lines.extend(
        [
            "",
            "## Reporting Decision",
            "- Current policy: write workflow summaries only; do not post pull request comments automatically.",
        ]
    )

    return "\n".join(lines) + "\n"


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    args = parse_args()
    workspace_root = Path.cwd().resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    summary_payload = load_json(Path(args.summary_json).resolve())
    latest_run_payload = load_json(Path(args.latest_run_json).resolve())
    stack_payload = load_json(Path(args.stack_status_json).resolve())

    manifest = build_manifest(
        summary_payload=summary_payload,
        latest_run_payload=latest_run_payload,
        stack_payload=stack_payload,
        artifacts_dir=artifacts_dir,
        workspace_root=workspace_root,
    )
    markdown = build_markdown(
        summary_payload=summary_payload,
        manifest=manifest,
        stack_payload=stack_payload,
    )
    summary_path = Path(args.job_summary_out).resolve() if args.job_summary_out else artifacts_dir / "job-summary.md"
    write_text(summary_path, markdown)

    manifest_path = artifacts_dir / "artifact-manifest.json"
    manifest["artifact_files"] = sorted(set([*manifest.get("artifact_files", []), manifest_path.name, summary_path.name]))
    write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    if args.write_job_summary:
        summary_env_path = os.environ.get(args.job_summary_env)
        if summary_env_path:
            with Path(summary_env_path).open("a", encoding="utf-8") as handle:
                handle.write(markdown)

    print(json.dumps({"manifest_path": str(manifest_path), "job_summary_path": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
