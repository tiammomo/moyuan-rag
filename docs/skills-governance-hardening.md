# Skills Governance Hardening

## What Completed In This Slice

This slice adds the first governance layer for `skills`.

Completed outcomes:
- Future remote install requests now have explicit checksum, signature, and host allowlist requirements in configuration and request validation.
- Local and remote skill install attempts now create persistent install task records.
- Skill install, bind, update, and unbind actions now write audit logs.
- Admin-only query endpoints now expose install tasks and audit logs for operators.
- Controlled remote install can now download allowed packages, verify checksum, optionally verify Ed25519 signatures, and persist verification metadata before extraction.
- Version pinning and rollback behavior are now documented for the next controlled rollout phase.
- Remote source allowlist and operator workflow are now documented as a runbook.

## New Persistence Objects

Added tables:
- `rag_skill_install_task`
- `rag_skill_audit_log`

These tables allow operators to answer:
- who installed a skill
- when an install failed
- which robot changed skill bindings
- whether a remote install was rejected before execution

## New Admin APIs

Admin-only endpoints:
- `GET /api/v1/skills/install-tasks`
- `GET /api/v1/skills/install-tasks/{task_id}`
- `POST /api/v1/skills/install-tasks/{task_id}/retry`
- `POST /api/v1/skills/install-tasks/{task_id}/cancel`
- `GET /api/v1/skills/audit-logs`

Existing install endpoints now also write governance data:
- `POST /api/v1/skills/install-local`
- `POST /api/v1/skills/install-remote`

## Remote Install Status

Remote install is still disabled by default.

Current behavior:
- feature flag disabled: request is rejected and still recorded
- feature flag enabled: request validates host / checksum / signature policy, downloads the package, verifies trust metadata, then extracts and installs the skill
- operator console: admins can inspect a single task and trigger retry / cancel only when the current task status is safe

This keeps the governance trail explicit while still requiring allowlist and signature policy to be configured deliberately.

## Related Docs

- [skills-remote-install-security.md](./skills-remote-install-security.md)
- [skills-versioning-and-rollback.md](./skills-versioning-and-rollback.md)
- [skills-remote-allowlist-runbook.md](./skills-remote-allowlist-runbook.md)
- [skills-admin-console.md](./skills-admin-console.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
