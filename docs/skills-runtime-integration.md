# Skills Runtime Integration

## What Completed In This Slice

This slice takes `skills` from a bootstrap registry feature into the real robot runtime.

Completed outcomes:
- Bound skill prompts now enter the real RAG runtime before retrieval and answer generation.
- Robot edit pages now support binding, reprioritizing, disabling, and unbinding skills.
- Active robot skills are visible in the chat sidebar and robot edit page.
- Active robot skills can now expose install provenance metadata when a binding came from a controlled install task.
- Skill binding now validates manifest constraints such as `allowed_robot_modes`.
- Regression tests now cover runtime prompt composition, retrieval guidance, and incompatible binding rejection.
- Remote install remains disabled in this phase and stays behind `ENABLE_REMOTE_SKILL_INSTALL=false`.

## Runtime Flow

1. Robot skill bindings are loaded from `rag_robot_skill_binding`.
2. The local registry resolves each bound skill to its `skill.yaml`, `SKILL.md`, and prompt entrypoints.
3. Active prompt files are split into:
   - `system_prompt`
   - `retrieval_prompt`
   - `answer_prompt`
4. Retrieval guidance is appended to the effective retrieval query before hybrid search.
5. System and answer guidance are merged into the final chat system prompt before LLM generation.
6. Active skill metadata, including optional provenance, is returned to the frontend and shown alongside the current robot.

## Frontend Coverage

Current robot-facing UI now includes:
- `/robots/[id]/edit-test`
  - View currently active skills
  - Bind installed skills to the robot
  - Adjust priority
  - Disable or re-enable a binding
  - Remove a binding
- `/chat`
  - Show active skills for the currently selected robot
  - Show provenance badges when a skill binding was linked to an install task
  - Show a runtime validation hint when active skills carry install provenance metadata

## Validation Rules

The current runtime phase enforces:
- Only active skills can be bound.
- `constraints.allowed_robot_modes` must include the current robot mode.
- Current project mode is treated as `rag_chat`.

## Test Coverage

This slice is covered by:
- `backend/tests/test_skill_service.py`
- `backend/tests/test_skill_runtime_integration.py`
- `front` type checking via `npm run type-check`

## Remote Install Decision

The project decision in this phase is to keep remote skill installation disabled.

Reason:
- The repository is still focused on stable local RAG delivery rather than a general plugin marketplace.
- The current safety model is not yet ready for direct remote package ingestion in production-like environments.

Later operator-facing phases are documented in:
- [skills-governance-hardening.md](./skills-governance-hardening.md)
- [skills-admin-console.md](./skills-admin-console.md)
- [skills-remote-install-execution.md](./skills-remote-install-execution.md)
- [skills-provenance.md](./skills-provenance.md)
