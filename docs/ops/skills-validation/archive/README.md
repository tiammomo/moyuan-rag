# Skills Validation Archive

Use this folder for validation artifact pairs that are no longer part of the active release cycle.

Recommended archive layout:
- `archive/2026-q1/`
- `archive/release-2026-03/`

Archive a validation pair when:
- a newer validated rollout for the same skill has replaced it
- the release cycle is closed and the artifact is no longer part of active review
- the pair is incomplete but still worth keeping for audit history

Do not archive or delete a pair when:
- it is referenced by an open incident
- it is referenced by a rollback discussion
- the release approval for that rollout is still active
