# Frontend Lint Baseline

## What Completed In This Slice

This slice clears the current frontend lint warning backlog without weakening the repository-owned Next.js lint baseline.

Completed outcomes:
- `npm run lint` now completes with zero warnings and zero errors.
- Hook dependency warnings in the admin, chat, skills, and thinking-process flows were resolved by stabilizing callbacks and effect dependencies instead of suppressing the rules.
- The remaining raw image warnings were removed by hardening preview and avatar rendering with `next/image` or equivalent accessible props.
- The frontend validation baseline is now: `npm run lint`, `npm run type-check`, and `npm run build` all pass in the repository.

## Warning Audit That Was Closed

The previous warning backlog was concentrated in three categories:

1. Hook dependency warnings
2. Raw `<img>` usage warnings
3. Missing `alt` coverage on Markdown-rendered images

Files cleaned in this slice:
- `front/src/app/admin/llms/page.tsx`
- `front/src/app/admin/skills/page.tsx`
- `front/src/app/chat/page.tsx`
- `front/src/app/knowledge/[id]/page.tsx`
- `front/src/app/robots/[id]/edit-test/page.tsx`
- `front/src/components/skills/robot-skill-manager.tsx`
- `front/src/components/thinking-process/thinking-process.tsx`

## Implementation Notes

Key cleanup patterns used here:
- wrap reused async loaders in `useCallback` so `useEffect` dependencies stay accurate
- move hook-bearing UI logic into proper React components instead of inline renderer callbacks
- use `next/image` for avatar and preview scenarios where the framework warning was signaling real cleanup debt
- keep lint rules active instead of solving the warning backlog with broad rule disables

## Validation

Validated in this slice:
- `npm run lint`
- `npm run type-check`
- `npm run build`

All three commands now pass.

## Related Files

- [front/.eslintrc.json](../front/.eslintrc.json)
- [front/src/app/chat/page.tsx](../front/src/app/chat/page.tsx)
- [front/src/app/knowledge/[id]/page.tsx](../front/src/app/knowledge/[id]/page.tsx)
- [front/src/app/robots/[id]/edit-test/page.tsx](../front/src/app/robots/[id]/edit-test/page.tsx)
- [front/README.md](../front/README.md)
