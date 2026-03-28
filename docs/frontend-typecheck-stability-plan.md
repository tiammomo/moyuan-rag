# Frontend Typecheck Stability Plan

## Goal

Make `npm run type-check` reliable on the first run by removing the recurring dependency on transient `.next/types` generation timing.

## Checklist

- [pending] Reproduce and document why `tsc --noEmit` intermittently fails before `.next/types` is fully available.
- [pending] Decide whether the fix should live in `tsconfig.json`, package scripts, or a small pre-typecheck bootstrap step.
- [pending] Validate that the stabilized type-check command passes consistently before and after a fresh build.
