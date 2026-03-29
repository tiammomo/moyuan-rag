# Frontend Playwright Artifact Retention Plan

## Goal

Clarify how long smoke artifacts should live and which subset should be retained for normal versus failed workflow runs.

## Checklist

- [pending] Decide whether the workflow should keep the full artifact bundle for successful runs or retain only the compact summary and manifest by default.
- [pending] Define an artifact retention window that balances investigation value and storage cost.
- [pending] Decide whether screenshots should always upload on success or only on failure.
- [pending] Sync `README.md`, `docs/README.md`, and smoke runbooks with the final retention policy.
