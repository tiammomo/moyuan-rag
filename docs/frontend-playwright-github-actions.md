# Frontend Playwright GitHub Actions

## What Completed In This Slice

This slice promotes the local operator smoke flow into a repository-owned GitHub Actions workflow.

Completed outcomes:
- `.github/workflows/frontend-playwright-smoke.yml` now provisions the smoke credential contract, boots the local compose stack, and runs the operator Playwright smoke flow.
- The workflow uses the same `python backend/scripts/rag_stack.py smoke --ensure-admin` entrypoint as local operators.
- The workflow uploads `front/test-results/playwright-smoke/operator/latest/` together with stack status and compose logs as GitHub Actions artifacts.
- The workflow validates the frontend baseline with `npm run lint`, `npm run build`, and `npm run type-check` before browser smoke.

## Workflow Trigger

The workflow currently runs on:

- `workflow_dispatch`
- `pull_request` to `master` when the smoke workflow, backend, frontend, or related docs change

## Required Secrets And Variables

Recommended GitHub configuration:

- repository secret: `PLAYWRIGHT_SMOKE_PASSWORD`
- repository variable: `PLAYWRIGHT_SMOKE_USERNAME`
- repository variable: `PLAYWRIGHT_SMOKE_EMAIL`

If the repository variables are not set, the workflow falls back to:

- `playwright_smoke_admin`
- `playwright-smoke@example.com`

The password remains mandatory and is validated explicitly at workflow start.

## Workflow Flow

The workflow follows this sequence:

1. Checkout the repository.
2. Set up Python and Node.js.
3. Materialize `backend/.env` from `backend/.env.example`.
4. Inject a per-run JWT secret, AES key, and the dedicated `PLAYWRIGHT_SMOKE_*` credentials.
5. Install frontend dependencies and Playwright Chromium.
6. Run `npm run lint`, `npm run build`, and `npm run type-check`.
7. Start the local stack with `python backend/scripts/rag_stack.py start --build`.
8. Run `python backend/scripts/rag_stack.py smoke --ensure-admin`.
9. Upload the latest Playwright smoke artifacts plus stack diagnostics.
10. Stop the stack and remove compose containers.

## Artifact Contract

The workflow uploads:

- `front/test-results/playwright-smoke/operator/latest/`
- `front/test-results/playwright-smoke/operator/latest-run.json`
- `.github/artifacts/playwright-smoke/stack-status.json`
- `.github/artifacts/playwright-smoke/compose-logs.txt`

That gives a single latest smoke bundle plus text diagnostics for failed runs.

## Related Files

- [../.github/workflows/frontend-playwright-smoke.yml](../.github/workflows/frontend-playwright-smoke.yml)
- [frontend-playwright-operator.md](./frontend-playwright-operator.md)
- [frontend-playwright-credential-provisioning.md](./frontend-playwright-credential-provisioning.md)
- [../README.md](../README.md)
