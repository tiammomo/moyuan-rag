# Skills Validation Regression Review

## What Completed In This Slice

This slice turns historical validation exports into a clearer regression review workflow instead of leaving operators to compare ad hoc notes by hand.

Completed outcomes:
- The admin console now shows a regression review template that references the current artifact pair and the expected previous artifact pair for the same skill.
- The admin console now includes a compare hint that tells operators which layers to compare first.
- Regression review documentation now explains how review outcomes should influence release approval or rollback decisions.

## Regression Review Workflow

Recommended usage from `/admin/skills`:
1. Export the current Markdown and JSON validation artifacts.
2. Find the previous artifact pair for the same `skill_slug`.
3. Copy the regression review template from the task drawer.
4. Compare:
   - install metadata
   - robot bindings
   - audit timeline
   - runtime validation output
5. Record whether the change is expected, neutral, improved, or regressed.
6. Feed that result back into the release decision.

## Release And Rollback Rule

Use this routing:
- expected or improved change: release approval can continue
- neutral change: release approval can continue if the task owner agrees the rollout is safe
- regressed change: release approval should pause until the issue is explained or fixed
- severe regression with confirmed runtime impact: prepare rollback using the existing version / rollback workflow before broader rollout

## Related Docs

- [skills-validation-history.md](./skills-validation-history.md)
- [skills-validation-evidence.md](./skills-validation-evidence.md)
- [skills-validation-automation.md](./skills-validation-automation.md)
