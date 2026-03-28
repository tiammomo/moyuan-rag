# Skills Admin Console

## What Completed In This Slice

This slice turns `skills` governance data into a real operator console instead of requiring direct API inspection.

Completed outcomes:
- Admins can now open `/admin/skills` to review install tasks, audit logs, installed variants, and robot binding drift in one page.
- Admins can now submit controlled remote install requests directly from `/admin/skills`.
- Install tasks support filtering by status, source type, skill slug, and requesting username.
- Audit logs support filtering by action, status, actor username, skill slug, and robot ID.
- Install task details and audit log details are now visible in JSON drawers for direct troubleshooting.
- Install task drawers can reload a single task via `GET /api/v1/skills/install-tasks/{task_id}` without refreshing the whole console.
- Remote install tasks now expose safe operator actions for retry and cancel directly in the drawer.
- Once `ENABLE_REMOTE_SKILL_INSTALL=true`, the drawer also shows persisted download and verification metadata for successful or rejected remote packages.
- Successful install task drawers now include quick links into skill review, robot edit entry points, and chat validation.
- Successful install task drawers now include a task-scoped audit timeline so operators can review one install trail in place.
- Successful install task drawers now include copy-friendly validation summary and evidence template blocks for review handoff.
- Robot edit entry points can now carry install provenance forward, and provenance-linked binding actions will appear in the same task timeline.
- Installed skill variants are compared side by side with the current registry version and pinned robot bindings.
- Operators can rebind drifted robot bindings back to the current skill version from the console.
- Rollback remains controlled, but the console now includes a rollback preparation workflow so teams can review impact before changing registry state.

## UI Coverage

The admin console now includes:
- a controlled remote install request form with package URL, checksum, optional signature, and signature algorithm
- summary cards for install tasks, failed/rejected tasks, audit logs, and version-drifted bindings
- install task filters and task detail drawer
- remote install task retry and cancel buttons when the current task status allows it
- verification badges and download metadata on task cards, so operators do not need raw JSON for the first pass
- handoff guidance for review -> bind -> validate after a successful install
- copyable validation summary and evidence template blocks inside the install task drawer
- related audit events inside the install task drawer
- provenance-preserving jump paths from install handoff into robot editing
- audit log filters and audit detail drawer
- installed variant comparison cards
- robot binding drift panel with one-click rebind to the current version
- rollback preparation modal for historical installed variants

## Operator Workflow

Recommended usage:
1. Open `/admin/skills`.
2. Filter install tasks or audit logs to narrow the incident scope.
3. Use the remote install form to submit a controlled package URL when the environment allowlist and feature flag are ready.
4. Inspect task badges to confirm host, package size, checksum, and signature state without opening raw JSON.
5. Open a single install task to inspect full verification details, retry / cancel affordances, task-scoped audit events, and the raw task JSON when needed.
6. Use the handoff block to jump into skill review, robot editing, and chat validation.
7. Inspect raw audit JSON in the detail drawer when you need the full action trail.
8. Select the affected skill in the version comparison panel.
9. Review which robots are still pinned to a historical version.
10. Rebind drifted robots to the current registry version, or open the rollback preparation modal if a controlled rollback is needed.

## Validation

This slice was validated with:
- `backend/tests/test_skill_service.py`
- `backend/tests/test_skill_runtime_integration.py`
- `front` type checking via `npm run type-check`
- a local Next.js route boot check on an alternate port while the current Docker backend process on this machine is unhealthy

## Related Docs

- [skills-governance-hardening.md](./skills-governance-hardening.md)
- [skills-runtime-integration.md](./skills-runtime-integration.md)
- [skills-remote-install-security.md](./skills-remote-install-security.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
- [skills-remote-install-operator-ui.md](./skills-remote-install-operator-ui.md)
- [skills-install-handoff.md](./skills-install-handoff.md)
- [skills-provenance.md](./skills-provenance.md)
- [skills-validation-playbook.md](./skills-validation-playbook.md)
- [skills-incident-review.md](./skills-incident-review.md)
- [skills-validation-evidence.md](./skills-validation-evidence.md)
