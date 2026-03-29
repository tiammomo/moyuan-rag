# Frontend Playwright Reporting

## What Completed In This Slice

This slice makes Playwright smoke results readable directly inside GitHub without downloading the artifact bundle first.

Completed outcomes:
- `backend/scripts/write_playwright_smoke_report.py` now generates both `artifact-manifest.json` and `job-summary.md` from the latest smoke run plus stack diagnostics.
- `.github/workflows/frontend-playwright-smoke.yml` now calls that script after collecting diagnostics.
- The workflow appends a compact markdown report to the GitHub job summary through `GITHUB_STEP_SUMMARY`.
- Reporting now follows a clear policy: workflow summaries only for now, no automatic pull request comments.

## Generated Outputs

The reporting script writes:

- `.github/artifacts/playwright-smoke/artifact-manifest.json`
- `.github/artifacts/playwright-smoke/job-summary.md`

The manifest provides a single index for:
- smoke status
- base frontend and backend URLs
- latest run paths
- step screenshots
- endpoint warnings
- artifact file names

The markdown summary is also appended to the GitHub job summary when `--write-job-summary` is enabled.

## Current Reporting Policy

The repository currently keeps reporting inside workflow summaries and uploaded artifacts only.

That means:
- no automatic pull request comments
- no duplicated noise on active pull requests
- one consistent summary view in the Actions UI

If later we decide that failed smoke runs should comment on pull requests, that should be an explicit follow-up change rather than an implicit side effect of every workflow run.

## Related Files

- [../backend/scripts/write_playwright_smoke_report.py](../backend/scripts/write_playwright_smoke_report.py)
- [../.github/workflows/frontend-playwright-smoke.yml](../.github/workflows/frontend-playwright-smoke.yml)
- [frontend-playwright-github-actions.md](./frontend-playwright-github-actions.md)
- [frontend-playwright-ci-hardening.md](./frontend-playwright-ci-hardening.md)
