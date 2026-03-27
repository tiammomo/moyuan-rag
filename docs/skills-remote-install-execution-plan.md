# Skills Remote Install Execution Plan

## Goal

Move remote skill installation from a rejected placeholder into a controlled execution workflow with explicit verification, task lifecycle visibility, and safe operator recovery actions.

## Checklist

- [pending] Add per-task detail and status endpoints so the admin console can poll a single remote install task.
- [pending] Implement a controlled remote package download worker behind `ENABLE_REMOTE_SKILL_INSTALL`.
- [pending] Verify checksum and optional signature before extraction, and persist verification results to the install task.
- [pending] Add operator retry and cancel actions for remote install tasks that are still pending or failed before extraction.
- [pending] Document the remote install execution runbook and rollout guardrails in README and related docs.
