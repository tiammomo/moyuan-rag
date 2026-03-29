# Frontend Playwright GitHub Actions Plan

## Goal

Promote the local operator Playwright smoke workflow into a repository-owned CI workflow with stable secrets and uploaded artifacts.

## Checklist

- [pending] Add a GitHub Actions workflow that boots the required local stack pieces and runs `python backend/scripts/rag_stack.py smoke --ensure-admin`.
- [pending] Define the expected GitHub Actions secrets and environment variables for the dedicated `PLAYWRIGHT_SMOKE_*` credential contract.
- [pending] Upload `front/test-results/playwright-smoke/operator/latest/` as a workflow artifact for failed and successful runs.
- [pending] Sync `README.md`, `docs/README.md`, and runbooks with the final GitHub Actions entrypoint.
