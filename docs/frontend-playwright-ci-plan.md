# Frontend Playwright CI Plan

## Goal

Promote the local Playwright smoke workflow into a repeatable CI or operator automation step with stable inputs and artifact collection.

## Checklist

- [completed] Decide whether the first integration target should be local operator tooling, CI, or both.
- [pending] Define how smoke credentials are provisioned safely outside a developer workstation, without depending on ad hoc local admin accounts.
- [completed] Wire the Playwright smoke summary and screenshots into a stable artifact export path for automated runs.
- [completed] Sync `README.md`, `docs/README.md`, and relevant runbooks with the finalized CI/operator smoke workflow.

## Completed In The Latest Slice

- Chose local operator tooling as the first integration target by extending `python backend/scripts/rag_stack.py`.
- Added a `smoke` subcommand that can optionally start the stack and then run the Playwright smoke workflow from the repository.
- Standardized automated smoke artifacts under `front/test-results/playwright-smoke/operator/` with both `runs/<timestamp>/` and `latest/` mirrors plus `latest-run.json`.
- Synced the new operator entrypoint into `README.md`, `docs/README.md`, `front/README.md`, and `docs/full-stack-compose.md`.
