# Skills Incident Review

## Goal

When a skill rollout causes unexpected chat behavior, teams need one comparison path that spans install, binding, and runtime output.

This document explains how to compare those layers without guessing.

## The Three Surfaces To Compare

| Surface | Where to inspect | Key questions |
| :--- | :--- | :--- |
| Install task | `/admin/skills` task drawer | What package was installed, from where, and with what verification result? |
| Binding change | Robot edit page and audit log timeline | Which robot was changed, at what priority, and with which `install_task_id`? |
| Final chat behavior | `/chat` active skills, runtime hint, and answer output | Did the observed answer match the installed skill and binding state? |

## Comparison Workflow

1. Start from the install task id that is suspected to be related.
2. In `/admin/skills`, inspect the task drawer and copy the installed slug, version, and verification metadata.
3. Read the related audit timeline filtered by the same `install_task_id`.
4. Confirm whether the task led to a new bind, an update, a rebind, or no robot change at all.
5. Open the affected robot and confirm the active binding version, priority, status, and provenance task id.
6. Open `/chat` with that robot and verify the active skills list plus the runtime validation hint.
7. Re-run the prompt that exposed the issue and compare the answer against:
   - the installed skill prompts
   - the robot binding order
   - the expected baseline behavior

## What To Record In Review Notes

For each incident, capture:
- install task id
- skill slug and version
- affected robot ids
- binding action type
- prompt used to reproduce
- expected behavior
- actual behavior
- whether rollback, rebind, or prompt fix is needed

## Decision Guide

Use this quick routing:
- install metadata looks wrong: treat it as a package governance problem
- install is correct but binding changed unexpectedly: treat it as a robot configuration problem
- install and binding are correct but answer output is wrong: treat it as a runtime prompt or retrieval problem

## Related Docs

- [skills-validation-playbook.md](./skills-validation-playbook.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
- [skills-install-handoff.md](./skills-install-handoff.md)
- [skills-provenance.md](./skills-provenance.md)
