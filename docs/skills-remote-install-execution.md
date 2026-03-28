# Skills Remote Install Execution

## What Completed In This Slice

This slice turns remote skill install from a governance placeholder into a controlled execution path.

Completed outcomes:
- Remote install now downloads packages only when `ENABLE_REMOTE_SKILL_INSTALL=true`.
- Downloads stay behind `SKILL_REMOTE_ALLOWED_HOSTS` and refuse redirect-based source switching.
- Remote packages enforce sha256 checksum verification when configured.
- Optional Ed25519 detached signature verification is supported through `SKILL_REMOTE_ED25519_PUBLIC_KEY`.
- Install task details now persist download size, content type, checksum verification, signature verification, and extracted install path.
- Remote install reuses the same extraction and registry flow as local zip installation, so success and failure behavior stay consistent.
- Operators can still inspect a single task and use retry / cancel through `/admin/skills`.

## Runtime Flow

```mermaid
flowchart LR
    A["POST /api/v1/skills/install-remote"] --> B["Create install task"]
    B --> C["Validate host / checksum / signature policy"]
    C --> D["Download package to uploads/"]
    D --> E["Compute sha256"]
    E --> F["Verify optional Ed25519 signature"]
    F --> G["Extract to quarantine/"]
    G --> H["Validate skill.yaml and entrypoints"]
    H --> I["Move into extracted/<slug>/<version>"]
    I --> J["Update registry + install task + audit log"]
```

## Task Status Lifecycle

Current remote install status progression:
- `pending`
- `downloading`
- `verifying`
- `extracting`
- `installed`

Failure branches:
- `rejected`: allowlist violation, checksum mismatch, signature mismatch, oversized package, invalid archive path
- `failed`: network errors or unexpected execution failures
- `cancelled`: operator cancellation before extraction begins

## Verification Model

Current trust checks:
- checksum: supports `sha256` hex digests, including `sha256:<digest>` format
- signature: optional Ed25519 detached signature over the raw zip bytes
- package size: enforced by `SKILL_REMOTE_MAX_PACKAGE_MB`
- redirects: rejected so an allowlisted URL cannot bounce into a different host

The project deliberately keeps remote install behind explicit operator configuration. Installing a package is still separate from binding it to a robot.

## Recommended Operator Settings

Use these knobs together:
- `ENABLE_REMOTE_SKILL_INSTALL=true` only in controlled environments
- `SKILL_REMOTE_ALLOWED_HOSTS=...` for trusted package hosts
- `SKILL_REMOTE_REQUIRE_CHECKSUM=true`
- `SKILL_REMOTE_REQUIRE_SIGNATURE=true` only after `SKILL_REMOTE_ED25519_PUBLIC_KEY` is configured
- `SKILL_REMOTE_DOWNLOAD_TIMEOUT_SECONDS=60` or another environment-appropriate limit

## Validation

This slice was validated with:
- `backend/tests/test_skill_service.py`
- `backend/tests/test_skill_runtime_integration.py`
- backend `py_compile` on `skill_service.py`, `skills.py`, and `config.py`
- front `npm run type-check`

## Related Docs

- [skills-remote-install-security.md](./skills-remote-install-security.md)
- [skills-remote-allowlist-runbook.md](./skills-remote-allowlist-runbook.md)
- [skills-admin-console.md](./skills-admin-console.md)
- [skills-governance-hardening.md](./skills-governance-hardening.md)
