# Skills Remote Install Operator UI

## What Completed In This Slice

This slice makes the controlled remote install workflow directly operable from the admin console.

Completed outcomes:
- `/admin/skills` now includes an admin-only remote install request form.
- Operators can submit package URL, checksum, optional detached signature, and signature algorithm without dropping to raw API calls.
- Task cards now surface host, package size, checksum state, signature state, and registry landing state in the main list.
- Task drawers now show readable download metadata and verification results before the raw JSON section.
- The current remote install plan is complete, and the next plan now moves on to install-to-binding handoff.

## UI Coverage

The admin console now supports:
- entering a controlled remote package URL
- sending checksum and optional Ed25519 signature metadata
- reading verification badges directly from the task list
- opening a single task to inspect download size, content type, checksum expectation vs actual value, signature algorithm, and install path
- retrying or cancelling eligible remote tasks in place

## Operator Notes

The UI does not bypass backend policy:
- `ENABLE_REMOTE_SKILL_INSTALL` must still be enabled
- the package host must still be present in `SKILL_REMOTE_ALLOWED_HOSTS`
- checksum and signature requirements still follow backend configuration

If policy rejects a request, the task and audit trail are still persisted and visible from the same page.

## Validation

This slice was validated with:
- `front` type checking via `npm run type-check`
- backend tests already covering remote install success and rejection flows
- backend `py_compile` on the updated skills API schema contract

## Related Docs

- [skills-admin-console.md](./skills-admin-console.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
- [skills-remote-install-smoke-test.md](./skills-remote-install-smoke-test.md)
