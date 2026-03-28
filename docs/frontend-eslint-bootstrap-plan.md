# Frontend ESLint Bootstrap Plan

## Goal

Make `npm run lint` non-interactive and repeatable by checking in the minimal ESLint configuration required for Next 14 in this repository.

## Checklist

- [pending] Reproduce the current `next lint` first-run prompt and document which config file shape removes the interactive setup flow.
- [pending] Add the minimal repository-owned ESLint config needed for Next and existing TypeScript usage.
- [pending] Validate that `npm run lint` can run non-interactively on a clean checkout and after a regular `npm run build`.
- [pending] Sync `README.md`, `docs/README.md`, and relevant frontend docs with the finalized lint workflow.
