# Skills Validation Automation

## What Completed In This Slice

This slice turns validation evidence from a copy-only note into an exportable operator artifact.

Completed outcomes:
- Install task drawers now support direct Markdown export for release review or handoff notes.
- Install task drawers now support direct JSON export for structured incident or automation pipelines.
- The admin console now shows a release-review checklist that ties install verification, robot binding confirmation, chat validation, and final rollout verdict together.
- Validation evidence documentation now explains how exported artifacts should be attached to release approval and incident review workflows.
- Validation exports now follow a history-friendly naming pattern so repeated rollouts can be archived and compared.

## Operator Workflow

Recommended usage:
1. Open `/admin/skills` and inspect the relevant install task.
2. Copy or export the validation summary and evidence template.
3. Run the release-review checklist after chat validation is complete.
4. Attach the Markdown export to human-readable rollout review notes.
5. Attach the JSON export when a structured incident or automation system needs the same artifact.

## Export Guidance

Use Markdown export when:
- a reviewer needs a readable summary
- the result is being pasted into a release note, issue comment, or handoff document

Use JSON export when:
- the same artifact needs to be parsed later
- the result is being attached to an incident workflow or external system that expects machine-readable payloads

## Related Docs

- [skills-validation-evidence.md](./skills-validation-evidence.md)
- [skills-validation-playbook.md](./skills-validation-playbook.md)
- [skills-incident-review.md](./skills-incident-review.md)
- [skills-validation-history.md](./skills-validation-history.md)
- [skills-validation-regression.md](./skills-validation-regression.md)
