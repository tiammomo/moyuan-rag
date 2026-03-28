# Skills Validation Evidence

## What Completed In This Slice

This slice turns the manual validation playbook into a reusable evidence workflow that operators can copy directly out of the admin console.

Completed outcomes:
- Install task drawers now show a copy-friendly validation summary with install metadata, binding state, recent audit events, and the expected chat check.
- Install task drawers now show a lightweight evidence template that operators can paste into incident notes, release review comments, or team handoff records.
- Install task drawers now support Markdown and JSON export so the same evidence can move into human review notes or structured systems.
- The validation workflow now has a minimal storage convention, so evidence does not get scattered across chat screenshots, ad hoc notes, and task comments.

## Admin Console Flow

Recommended usage from `/admin/skills`:
1. Open the relevant install task drawer.
2. Review the verification metadata and related audit timeline.
3. Copy the validation summary when you need a quick operator-facing incident note.
4. Copy the evidence template when you need a structured record for release review or rollout follow-up.
5. Export Markdown when a reviewer needs a human-readable artifact.
6. Export JSON when the same artifact needs to be attached to a structured incident or automation workflow.
7. Run the actual chat checks and fill in the prompt, outcome, and verdict fields before sharing.

## Minimal Evidence Template

Use the template below when you do not copy directly from the UI:

```md
# Skill Validation Evidence

- install_task_id:
- skill:
- task_status:
- admin_review_entry: /admin/skills

## Binding
- robot:
- binding_action:
- expected_provenance_task_id:

## Validation Prompts
- retrieval_check:
- response_shape_check:
- boundary_check:

## Observed Runtime
- active_skill_badges:
- chat_summary:
- answer_excerpt_or_screenshot:

## Verdict
- result:
- next_action:
```

## Storage Convention

Keep one evidence record per install task.

Recommended convention:
- local ops notes: `docs/ops/skills-validation/<date>-task-<id>-<skill-slug>.md`
- release review: paste the same summary or filled template into the release ticket or rollout comment
- incident review: attach the same install task id and robot ids so the review can be traced back to the exact rollout

Attachment guidance:
- release approval: attach the Markdown export, then link the matching chat screenshots if reviewers need visual proof
- incident review: attach the JSON export when the review system needs structured fields, and attach the Markdown export when humans need a readable timeline
- handoff notes: prefer the Markdown export plus the final verdict and next action

The important rule is consistency:
- do not create multiple independent summaries for the same install task
- always include `install_task_id`
- always include the final verdict and next action

## Related Docs

- [skills-validation-playbook.md](./skills-validation-playbook.md)
- [skills-incident-review.md](./skills-incident-review.md)
- [skills-admin-console.md](./skills-admin-console.md)
- [skills-validation-automation.md](./skills-validation-automation.md)
