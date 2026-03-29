# Frontend Playwright Operator Workflow

## What Completed In This Slice

This slice promotes the existing local Playwright smoke script into the shared operator CLI.

Completed outcomes:
- `python backend/scripts/rag_stack.py smoke` is now the primary operator entrypoint for browser smoke validation.
- The operator command can optionally start the compose stack first with `--start-stack`.
- The operator command can optionally install the Chromium browser with `--install-browser`.
- Smoke artifacts are now normalized under `front/test-results/playwright-smoke/operator/`.
- Each operator run writes both a timestamped artifact directory and a stable `latest/` mirror.

## Operator Entry Point

Run the smoke workflow directly from the repository root:

```bash
python backend/scripts/rag_stack.py smoke
```

Useful variants:

```bash
python backend/scripts/rag_stack.py smoke --start-stack
python backend/scripts/rag_stack.py smoke --start-stack --build
python backend/scripts/rag_stack.py smoke --ensure-admin
python backend/scripts/rag_stack.py smoke --install-browser
python backend/scripts/rag_stack.py smoke --username local_admin --password your-password
```

The command delegates to `front/scripts/playwright-smoke.mjs`, so the underlying browser flow stays in one place while the operator workflow stays discoverable next to the other stack commands.

## Stable Artifact Layout

Operator runs now write to:

- `front/test-results/playwright-smoke/operator/runs/<timestamp>/`
- `front/test-results/playwright-smoke/operator/latest/`
- `front/test-results/playwright-smoke/operator/latest-run.json`

This gives us:
- one immutable directory per run
- one stable path for the latest screenshots and `summary.json`
- one machine-readable index file that points to the latest run

## Credential Provisioning

The recommended operator path is now:

```bash
python backend/scripts/rag_stack.py smoke --ensure-admin
```

That command provisions a dedicated smoke admin from `PLAYWRIGHT_SMOKE_USERNAME`, `PLAYWRIGHT_SMOKE_EMAIL`, and `PLAYWRIGHT_SMOKE_PASSWORD` before opening the browser flow.

The repository-owned GitHub Actions workflow uses the same credential contract and the same operator command so local runs and CI stay aligned.

## Remaining Gap

The next open item is CI wiring. The operator workflow now has a stable credential contract and artifact layout, but it still needs a concrete automated workflow definition for shared pipelines.

## Validation

Validated in this slice:
- `python backend/scripts/rag_stack.py smoke --help`
- `python backend/scripts/rag_stack.py smoke --username <local-admin> --password <password>`
- `npm run lint`
- `npm run type-check`
- `npm run build`

## Related Files

- [backend/scripts/rag_stack.py](../backend/scripts/rag_stack.py)
- [front/scripts/playwright-smoke.mjs](../front/scripts/playwright-smoke.mjs)
- [front/README.md](../front/README.md)
- [full-stack-compose.md](./full-stack-compose.md)
- [frontend-playwright-smoke.md](./frontend-playwright-smoke.md)
