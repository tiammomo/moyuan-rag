# Frontend Playwright CI Hardening

## What Completed In This Slice

This slice hardens the GitHub Actions smoke workflow for runtime, trigger policy, and failure triage.

Completed outcomes:
- The workflow now runs on `pull_request`, `push` to `master`, and `workflow_dispatch`.
- Docker Buildx cache-backed prebuild steps now warm the Elasticsearch, backend, and frontend images before the compose stack starts.
- The compose start step now reuses those prebuilt images instead of rebuilding everything inline.
- The diagnostics bundle now includes `stack-status.json`, `compose-logs.txt`, `compose-ps.json`, `backend-health.json`, `front-index.html`, `latest-run.json`, and `latest-summary.json`.
- Workflow concurrency now cancels superseded smoke runs for the same pull request or ref.

## Trigger Decision

The workflow now runs on:

- pull requests targeting `master`
- pushes to `master`
- manual dispatch

The workflow does not run on a schedule yet. That keeps runtime predictable while still protecting merge-time and post-merge smoke paths.

## Build Reuse Strategy

Instead of relying on `docker compose up --build` inside the workflow, the CI job now prebuilds:

- `rag-elasticsearch-ik:local`
- `rag-backend:local`
- `rag-front:local`

Each image uses GitHub Actions cache scopes so reruns and subsequent pull requests can reuse previously built layers.

After those image builds complete, the workflow starts the stack through the existing operator CLI:

```bash
python backend/scripts/rag_stack.py start --health-timeout-sec 300
```

## Failure Diagnostics

The uploaded artifact bundle now contains:

- `front/test-results/playwright-smoke/operator/latest/`
- `front/test-results/playwright-smoke/operator/latest-run.json`
- `.github/artifacts/playwright-smoke/stack-status.json`
- `.github/artifacts/playwright-smoke/compose-logs.txt`
- `.github/artifacts/playwright-smoke/compose-ps.json`
- `.github/artifacts/playwright-smoke/backend-health.json`
- `.github/artifacts/playwright-smoke/front-index.html`
- `.github/artifacts/playwright-smoke/latest-run.json`
- `.github/artifacts/playwright-smoke/latest-summary.json`

This makes it easier to tell whether a failure came from:
- stack startup
- backend health
- frontend route rendering
- the browser smoke itself

## Related Files

- [../.github/workflows/frontend-playwright-smoke.yml](../.github/workflows/frontend-playwright-smoke.yml)
- [frontend-playwright-github-actions.md](./frontend-playwright-github-actions.md)
- [frontend-playwright-operator.md](./frontend-playwright-operator.md)
- [../README.md](../README.md)
