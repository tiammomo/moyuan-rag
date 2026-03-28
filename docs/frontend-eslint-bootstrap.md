# Frontend ESLint Bootstrap

## What Completed In This Slice

This slice makes the frontend lint command repository-owned and non-interactive instead of depending on Next.js first-run setup prompts.

Completed outcomes:
- `front/.eslintrc.json` is now checked into the repository with the minimal `next/core-web-vitals` baseline.
- `npm run lint` now runs immediately without prompting for `Strict / Base / Cancel`.
- The blocking lint errors in `front/src/app/chat/page.tsx` were removed by extracting the Markdown code renderer into a proper React component.
- The later lint-baseline cleanup slice has already built on this bootstrap and removed the historical warning backlog.

## Root Cause

The repository previously had `eslint` and `eslint-config-next` installed, but no checked-in ESLint config file.

That meant every fresh environment hit the Next.js interactive bootstrap prompt when running:

```bash
npm run lint
```

As a result:
- lint was not automation-friendly
- validation scripts could not rely on a stable exit path
- the first real lint results were hidden behind setup interaction

## Implementation

The finalized bootstrap is intentionally small:

1. Add `front/.eslintrc.json` with `next/core-web-vitals`.
2. Keep `front/package.json` using the standard `next lint` entry point.
3. Fix the known blocking chat-page lint errors so the command exits successfully once the config exists.
4. Keep the rules active so follow-up cleanup can happen against a real baseline instead of broad rule disables.

## Validation

Validated in this slice:
- `npm run lint` after the config was added
- `npm run lint` after deleting `front/.next`
- `npm run build`
- `npm run lint` again after the build

Current status:
- lint runs non-interactively
- lint exits successfully
- the warning backlog introduced during bootstrap has since been cleared in [frontend-lint-baseline.md](./frontend-lint-baseline.md)

## Related Files

- [front/.eslintrc.json](../front/.eslintrc.json)
- [front/src/app/chat/page.tsx](../front/src/app/chat/page.tsx)
- [front/README.md](../front/README.md)
- [frontend-lint-baseline.md](./frontend-lint-baseline.md)
