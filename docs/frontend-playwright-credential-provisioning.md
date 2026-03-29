# Frontend Playwright Credential Provisioning

## What Completed In This Slice

This slice removes the ad hoc local-admin dependency from the Playwright operator workflow.

Completed outcomes:
- `backend/scripts/ensure_smoke_admin.py` now provisions a dedicated smoke admin directly in the local database.
- `python backend/scripts/rag_stack.py smoke --ensure-admin` now creates or updates that admin before launching the browser smoke workflow.
- `backend/.env.example` now documents the dedicated `PLAYWRIGHT_SMOKE_*` credentials instead of relying on `DEFAULT_ADMIN_*`.
- `front/scripts/playwright-smoke.mjs` now resolves `PLAYWRIGHT_SMOKE_USERNAME` and `PLAYWRIGHT_SMOKE_PASSWORD` from both environment variables and `backend/.env` before falling back to default admin settings.

## Recommended Credential Contract

For local operator or CI-style smoke runs, provide these variables:

- `PLAYWRIGHT_SMOKE_USERNAME`
- `PLAYWRIGHT_SMOKE_EMAIL`
- `PLAYWRIGHT_SMOKE_PASSWORD`

The repository now treats these as the dedicated browser smoke identity. They are intentionally separate from:

- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_PASSWORD`

That keeps smoke validation isolated from bootstrap admin flows and avoids coupling the smoke workflow to whatever demo or manual admin account happens to exist already.

## Operator Flow

Provision and run the smoke workflow through one command:

```bash
python backend/scripts/rag_stack.py smoke --ensure-admin
```

If the stack is not running yet:

```bash
python backend/scripts/rag_stack.py smoke --start-stack --ensure-admin
```

The `--ensure-admin` step is idempotent:
- if the smoke admin does not exist, it is created
- if it already exists, its email, password hash, role, and status are synchronized

## Why This Closes The Gap

Before this slice, smoke validation depended on one-off local admin accounts that were created manually during debugging. That worked for a single workstation, but it was not predictable or repeatable.

Now the workflow is explicit:
- credentials come from environment variables or `backend/.env`
- the repository owns the provisioning step
- the browser smoke and the admin provisioning use the same credential source

## Validation

Validated in this slice:
- `python backend/scripts/ensure_smoke_admin.py --print-json`
- `python backend/scripts/rag_stack.py smoke --ensure-admin`
- `npm run lint`
- `npm run type-check`
- `npm run build`

## Related Files

- [backend/scripts/ensure_smoke_admin.py](../backend/scripts/ensure_smoke_admin.py)
- [backend/scripts/rag_stack.py](../backend/scripts/rag_stack.py)
- [backend/.env.example](../backend/.env.example)
- [front/scripts/playwright-smoke.mjs](../front/scripts/playwright-smoke.mjs)
- [frontend-playwright-operator.md](./frontend-playwright-operator.md)
