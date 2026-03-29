# Frontend Playwright CI Hardening Plan

## Goal

Reduce GitHub Actions smoke runtime and improve failure triage for flaky infrastructure or browser regressions.

## Checklist

- [pending] Add workflow-level caching or reuse guidance for backend and frontend image builds where it materially reduces rerun time.
- [pending] Expand failure diagnostics so the artifact bundle includes the latest smoke summary plus focused backend/front health context.
- [pending] Decide whether the smoke workflow should also run on `push` to `master`, on a schedule, or stay limited to pull requests and manual dispatch.
- [pending] Sync `README.md`, `docs/README.md`, and the smoke runbooks with the final CI hardening decisions.
