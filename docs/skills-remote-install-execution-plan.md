# Skills Remote Install Execution Plan

## Goal

Move remote skill installation from a rejected placeholder into a controlled execution workflow with explicit verification, task lifecycle visibility, and safe operator recovery actions.

## Checklist

- [completed] Add per-task detail and status endpoints so the admin console can poll a single remote install task.
- [pending] Implement a controlled remote package download worker behind `ENABLE_REMOTE_SKILL_INSTALL`.
- [pending] Verify checksum and optional signature before extraction, and persist verification results to the install task.
- [completed] Add operator retry and cancel actions for remote install tasks that are still pending or failed before extraction.
- [completed] Document the remote install execution runbook and rollout guardrails in README and related docs.

## Progress

Completed in the current slice:
- Added admin-only `GET /api/v1/skills/install-tasks/{task_id}` so the console can poll one task instead of reloading the whole task list.
- Added admin-only `POST /api/v1/skills/install-tasks/{task_id}/retry` for safe retry creation on terminal remote tasks.
- Added admin-only `POST /api/v1/skills/install-tasks/{task_id}/cancel` for pending remote tasks before extraction starts.
- Wired retry and cancel controls into `/admin/skills`, including task detail refresh after each operator action.
- Synced README and skills governance docs to reflect the current controlled-phase behavior.

Still pending:
- real remote package download and quarantine extraction
- checksum and optional signature verification against downloaded artifacts before extraction
- execution runbook for the first controlled rollout after the worker exists
