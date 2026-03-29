# Frontend Playwright Reporting Plan

## Goal

Make smoke failures easier to consume directly inside GitHub without downloading artifacts first.

## Checklist

- [pending] Add a workflow step that writes a compact GitHub job summary from the latest smoke `summary.json` and stack diagnostics.
- [pending] Decide whether to post pull request comments for smoke failures or keep reporting inside workflow summaries only.
- [pending] Standardize a small artifact manifest so operators can find the latest screenshots and diagnostics without opening multiple files.
- [pending] Sync `README.md`, `docs/README.md`, and smoke runbooks with the final reporting flow.
