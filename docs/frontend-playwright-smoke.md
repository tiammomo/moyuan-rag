# Frontend Playwright Smoke

## What Completed In This Slice

This slice adds a repository-owned Playwright smoke workflow for the core browser paths in the local RAG stack.

Completed outcomes:
- `front/package.json` now provides `npm run smoke:playwright` and `npm run smoke:playwright:install`.
- `front/scripts/playwright-smoke.mjs` runs a non-interactive Chromium smoke flow against the local stack.
- The smoke flow covers login, chat, knowledge, skills, and `/admin/skills`.
- Smoke artifacts are now written to `front/test-results/playwright-smoke/<timestamp>/` as a `summary.json` plus step screenshots.
- `front/.gitignore` now ignores `test-results/` so repeated local smoke runs do not pollute the repository.
- The smoke workflow now prefers dedicated `PLAYWRIGHT_SMOKE_*` credentials before any default admin fallback.

## Smoke Scope

The initial route set is intentionally small and high-signal:

1. `GET /health` on the backend
2. `GET /auth/login`
3. Login redirect to `/chat`
4. `GET /knowledge`
5. `GET /skills`
6. `GET /admin/skills`

This gives us one operator-focused smoke path that spans:
- auth
- chat shell
- knowledge management entry
- skills catalog entry
- admin skills governance entry

## Credentials Strategy

The smoke script resolves credentials in this order:

1. CLI flags such as `--username` and `--password`
2. Environment variables:
   - `PLAYWRIGHT_SMOKE_USERNAME`
   - `PLAYWRIGHT_SMOKE_EMAIL`
   - `PLAYWRIGHT_SMOKE_PASSWORD`
   - `PLAYWRIGHT_SMOKE_BASE_URL`
   - `PLAYWRIGHT_SMOKE_API_URL`
3. Local fallback from `backend/.env`:
   - `PLAYWRIGHT_SMOKE_USERNAME`
   - `PLAYWRIGHT_SMOKE_PASSWORD`
   - then `DEFAULT_ADMIN_USERNAME`
   - `DEFAULT_ADMIN_PASSWORD`

The script does not commit or export passwords into repository artifacts. The generated `summary.json` stores only the username and route outcomes.

## Artifact Contract

Each smoke run creates:

- `front/test-results/playwright-smoke/<timestamp>/summary.json`
- `front/test-results/playwright-smoke/<timestamp>/00-backend-health.png`
- `front/test-results/playwright-smoke/<timestamp>/01-login-page.png`
- `front/test-results/playwright-smoke/<timestamp>/02-chat-page.png`
- `front/test-results/playwright-smoke/<timestamp>/03-knowledge-page.png`
- `front/test-results/playwright-smoke/<timestamp>/04-skills-page.png`
- `front/test-results/playwright-smoke/<timestamp>/05-admin-skills-page.png`

These outputs are meant for local validation, CI artifacts, or operator debugging, not for Git tracking.

## Validation

Validated in this slice:
- `npm run smoke:playwright` with a dedicated local admin credential
- `npm run lint`
- `npm run type-check`
- `npm run build`

The latest successful smoke run in this slice produced a passed summary covering all six steps.

## Related Files

- [front/package.json](../front/package.json)
- [front/scripts/playwright-smoke.mjs](../front/scripts/playwright-smoke.mjs)
- [front/.gitignore](../front/.gitignore)
- [front/README.md](../front/README.md)
