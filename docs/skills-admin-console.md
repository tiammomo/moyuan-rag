# Skills Admin Console

## What Completed In This Slice

This slice turns `skills` governance data into a real operator console instead of requiring direct API inspection.

Completed outcomes:
- Admins can now open `/admin/skills` to review install tasks, audit logs, installed variants, and robot binding drift in one page.
- Install tasks support filtering by status, source type, skill slug, and requesting username.
- Audit logs support filtering by action, status, actor username, skill slug, and robot ID.
- Install task details and audit log details are now visible in JSON drawers for direct troubleshooting.
- Installed skill variants are compared side by side with the current registry version and pinned robot bindings.
- Operators can rebind drifted robot bindings back to the current skill version from the console.
- Rollback remains controlled, but the console now includes a rollback preparation workflow so teams can review impact before changing registry state.

## UI Coverage

The admin console now includes:
- summary cards for install tasks, failed/rejected tasks, audit logs, and version-drifted bindings
- install task filters and task detail drawer
- audit log filters and audit detail drawer
- installed variant comparison cards
- robot binding drift panel with one-click rebind to the current version
- rollback preparation modal for historical installed variants

## Operator Workflow

Recommended usage:
1. Open `/admin/skills`.
2. Filter install tasks or audit logs to narrow the incident scope.
3. Inspect raw task or audit JSON in the detail drawer.
4. Select the affected skill in the version comparison panel.
5. Review which robots are still pinned to a historical version.
6. Rebind drifted robots to the current registry version, or open the rollback preparation modal if a controlled rollback is needed.

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
- [skills-remote-install-execution-plan.md](./skills-remote-install-execution-plan.md)
