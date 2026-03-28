# Skills Validation Ops Conventions

## What Completed In This Slice

This slice turns validation artifacts into a small repository convention that operators can follow without guessing where files should live.

Completed outcomes:
- The repository now includes `docs/ops/skills-validation/README.md` with naming rules, operator expectations, and retention guidance.
- The repository now includes a sample Markdown / JSON validation artifact pair for onboarding and review examples.
- Validation artifact cleanup and archive expectations are now documented so stale rollout records do not accumulate without structure.

## Repository Layout

Current operator-facing layout:
- `docs/ops/skills-validation/README.md`
- `docs/ops/skills-validation/<date>-task-<id>-<skill-slug>.md`
- `docs/ops/skills-validation/<date>-task-<id>-<skill-slug>.json`
- `docs/ops/skills-validation/archive/README.md`

## Why This Matters

Before this slice, operators had naming suggestions but no concrete in-repo home for exported artifacts.

After this slice:
- new operators can start from a real example pair
- reviewers can point to one stable folder for validation evidence
- stale artifacts have an archive rule instead of staying mixed with active rollout records

## Related Docs

- [skills-validation-evidence.md](./skills-validation-evidence.md)
- [skills-validation-history.md](./skills-validation-history.md)
- [skills-validation-regression.md](./skills-validation-regression.md)
- [ops/skills-validation/README.md](./ops/skills-validation/README.md)
