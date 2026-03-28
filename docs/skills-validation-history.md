# Skills Validation History

## What Completed In This Slice

This slice gives teams a lightweight history convention for validation artifacts so repeated skill rollouts can be compared over time.

Completed outcomes:
- Exported validation artifacts now use a date + task id + skill slug naming convention.
- The admin console now shows a small history hint with recommended Markdown and JSON archive paths.
- Validation history docs now explain how to compare two exported artifacts when tracking regressions across skill versions.

## Recommended History Format

Use one pair of files per install task:

- Markdown: `docs/ops/skills-validation/<date>-task-<id>-<skill-slug>.md`
- JSON: `docs/ops/skills-validation/<date>-task-<id>-<skill-slug>.json`

Recommended field grouping:
- install task metadata
- robot bindings
- recent audit events
- release review checklist
- final verdict and next action

The key is stability:
- keep the same install task id in both files
- keep the same basename for Markdown and JSON
- do not rename exports after review starts

## How To Compare Two Historical Exports

When investigating a regression:

1. Find the previous export for the same `skill_slug`.
2. Compare install task metadata first:
   - version
   - checksum and signature state
   - registry path
3. Compare robot bindings next:
   - affected robots
   - priority
   - provenance task id
4. Compare recent audit events:
   - bind / update order
   - actor
   - timestamps
5. Compare runtime validation evidence:
   - chat summary
   - answer excerpt
   - final verdict

If install and binding look identical but runtime changed, treat it as a prompt or retrieval regression. If install metadata differs, treat it as a rollout/package difference first.

## Suggested Review Rhythm

For each new rollout:
- export the new Markdown and JSON artifacts
- compare against the immediately previous artifact for the same skill
- record whether the change is expected, improved, neutral, or regressed

## Related Docs

- [skills-validation-evidence.md](./skills-validation-evidence.md)
- [skills-validation-automation.md](./skills-validation-automation.md)
- [skills-incident-review.md](./skills-incident-review.md)
- [skills-validation-regression.md](./skills-validation-regression.md)
