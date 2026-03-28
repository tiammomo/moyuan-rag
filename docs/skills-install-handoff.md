# Skills Install Handoff

## What Completed In This Slice

This slice turns a successful remote install into an operator handoff flow instead of leaving the next steps implicit.

Completed outcomes:
- Successful install tasks now expose direct links to the installed skill detail page.
- Task drawers now provide quick entry points into robot editing so operators can move from install to binding without leaving the console.
- Task drawers now include a post-install guidance block that makes the expected sequence explicit: review, bind, then validate in chat.
- Task drawers now show a task-scoped audit timeline by filtering audit records with `install_task_id`, so operators can inspect one install trail without manually cross-filtering the global audit list.
- Task drawers now surface task-adjacent robot binding context when the installed skill is already present in the registry and bound to robots.
- Robot edit entry points can now preserve the originating `install_task_id`, so later bindings and updates stay connected to the original install event.

## Operator Workflow

Recommended usage after a successful install:
1. Open the completed install task from `/admin/skills`.
2. Confirm the package source, checksum, signature state, and extracted registry path.
3. Review the installed skill detail page to inspect prompts and documentation.
4. Open the relevant robot edit page and decide whether the new skill should be bound immediately.
5. If you bind or update the skill from that path, keep the carried `install_task_id` so provenance remains visible in audit logs and runtime badges.
6. Open `/chat` and run a validation conversation to confirm the runtime prompt stack behaves as expected.
7. Use the related audit events card when you need the install-specific timeline or raw audit JSON.

## Why This Matters

Before this slice, remote install ended at “task completed”. Operators still had to remember the next steps and manually jump across pages.

After this slice:
- install tasks are actionable instead of informational
- one drawer is enough to inspect the install trail
- the operator can move directly from install to binding and validation

## Validation

This slice was validated with:
- `backend/tests/test_skill_service.py`
- `backend/tests/test_skill_runtime_integration.py`
- `front` type checking via `npm run type-check`

## Related Docs

- [skills-admin-console.md](./skills-admin-console.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
- [skills-remote-install-operator-ui.md](./skills-remote-install-operator-ui.md)
- [skills-provenance.md](./skills-provenance.md)
