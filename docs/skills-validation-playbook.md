# Skills Validation Playbook

## Goal

This playbook turns a provenance-linked skill rollout into a short, repeatable operator check instead of an ad hoc chat demo.

Use it after:
- a controlled remote install finished successfully
- a robot binding was added or updated with `install_task_id`
- a team needs to confirm that runtime behavior matches the newly installed skill package

## Validation Sequence

1. Open `/admin/skills` and find the completed install task.
2. Confirm the package host, checksum result, signature result, installed slug, and installed version.
3. Open the task drawer and review related audit events for the same `install_task_id`.
4. Jump to the robot edit page from the handoff links and confirm the skill is bound to the intended robot.
5. Check that the binding still carries the same provenance task id.
6. Open `/chat`, select the same robot, and confirm the active skill badges include the expected skill.
7. Use the runtime validation hint in chat to verify that the current robot is still linked to the same install task.
8. Run three focused prompts:
   - one prompt that should trigger the skill's retrieval guidance
   - one prompt that should trigger the skill's answer style or answer constraints
   - one prompt that should *not* change behavior, to detect overreach
9. Compare the observed answer with the skill prompts and recent binding changes.
10. Record the result as pass, partial pass, or fail together with the install task id.

## Suggested Prompt Set

Use a compact three-check set for every rollout:

| Check | Intent | Example result to look for |
| :--- | :--- | :--- |
| Retrieval check | Confirm the skill changed what context is favored | The answer cites the expected knowledge area or source style |
| Response shape check | Confirm answer prompt guidance is active | The answer follows the expected structure, tone, or policy |
| Boundary check | Confirm the skill did not leak into unrelated questions | A neutral question behaves like the baseline robot |

## Evidence To Capture

Keep the following evidence together for one validation pass:
- install task id
- installed skill slug and version
- robot id or robot name
- binding priority and status
- validation prompts used
- short answer excerpts or screenshots
- final pass / fail decision

## Fast Failure Clues

Common signs that the rollout did not land correctly:
- install task completed, but no binding was created
- binding exists, but no provenance task id is attached
- chat badges show the skill, but the runtime hint references the wrong task id
- expected answer style is missing even though the skill is active
- unrelated prompts are unexpectedly affected

## Related Docs

- [skills-install-handoff.md](./skills-install-handoff.md)
- [skills-provenance.md](./skills-provenance.md)
- [skills-admin-console.md](./skills-admin-console.md)
- [skills-incident-review.md](./skills-incident-review.md)
