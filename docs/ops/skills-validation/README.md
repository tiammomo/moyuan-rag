# Skills Validation Artifacts

This folder is the repository home for exported skills validation artifacts.

## Naming Rules

Keep one Markdown / JSON pair per install task:

- Markdown: `<date>-task-<id>-<skill-slug>.md`
- JSON: `<date>-task-<id>-<skill-slug>.json`

Examples:
- `2026-03-28-task-42-rag-citation-guide.md`
- `2026-03-28-task-42-rag-citation-guide.json`

Rules:
- keep the same basename for Markdown and JSON
- use the real `install_task_id`
- keep the original date segment after review starts
- do not rename files after they are referenced in release or incident notes

## Operator Expectations

For each completed rollout validation:
1. Export both Markdown and JSON artifacts from `/admin/skills`.
2. Confirm the final verdict and next action are filled in before sharing.
3. Store the pair in this directory while the release cycle is active.
4. If screenshots or extra chat captures live elsewhere, reference them from the Markdown artifact.
5. When a later rollout for the same skill is reviewed, compare it against the previous pair before approving release.

## Sample Artifacts

Use these files as onboarding references:
- [2026-03-28-task-42-rag-citation-guide.md](./2026-03-28-task-42-rag-citation-guide.md)
- [2026-03-28-task-42-rag-citation-guide.json](./2026-03-28-task-42-rag-citation-guide.json)

## Cleanup And Archiving

At the end of a release cycle:
- keep the most recent active artifact pair for each deployed skill in this folder only if teams still reference it often
- move superseded pairs into `archive/<release-or-quarter>/` as needed
- never delete artifacts tied to an open incident, rollback review, or active release discussion
- if an artifact pair is incomplete and has been replaced by a newer validated pair, archive it with a short note rather than silently deleting it

Archive guidance lives in [archive/README.md](./archive/README.md).
