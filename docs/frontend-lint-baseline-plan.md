# Frontend Lint Baseline Plan

## Goal

Reduce the current frontend lint warning backlog without weakening the repository-owned Next.js lint baseline.

## Checklist

- [pending] Audit the current lint warnings by category and file so the cleanup order is explicit.
- [pending] Fix the highest-signal hook dependency warnings in the admin, chat, and skills flows.
- [pending] Replace or harden the current raw `<img>` usage so image-related warnings stop accumulating.
- [pending] Re-run `npm run lint`, `npm run type-check`, and `npm run build` after the cleanup slice.
- [pending] Sync `README.md`, `docs/README.md`, and relevant frontend/docs references with the updated lint baseline status.
