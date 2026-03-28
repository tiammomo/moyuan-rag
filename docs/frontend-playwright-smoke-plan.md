# Frontend Playwright Smoke Plan

## Goal

Add a repository-owned Playwright smoke workflow for the key RAG paths so UI regressions can be checked with the same repeatable discipline as lint, type-check, and build.

## Checklist

- [pending] Audit the current browser-accessible routes and decide the smallest smoke path set worth automating first.
- [pending] Add a non-interactive Playwright smoke script that covers login, chat, knowledge, and skills/admin entry points against the local stack.
- [pending] Decide which smoke run outputs should be kept as CI/operator artifacts, such as screenshots or a short JSON summary.
- [pending] Sync `README.md`, `docs/README.md`, and relevant frontend/operator docs with the smoke-test workflow.
