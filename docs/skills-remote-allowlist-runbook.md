# Skills Remote Allowlist Runbook

## Goal

Define how operators should control remote skill sources before any future remote install rollout.

## Current Configuration Knobs

Relevant backend settings:
- `ENABLE_REMOTE_SKILL_INSTALL`
- `SKILL_REMOTE_ALLOWED_HOSTS`
- `SKILL_REMOTE_REQUIRE_CHECKSUM`
- `SKILL_REMOTE_REQUIRE_SIGNATURE`
- `SKILL_REMOTE_MAX_PACKAGE_MB`

## Recommended Default

Keep these defaults in normal environments:
- `ENABLE_REMOTE_SKILL_INSTALL=false`
- `SKILL_REMOTE_ALLOWED_HOSTS=` empty
- `SKILL_REMOTE_REQUIRE_CHECKSUM=true`
- `SKILL_REMOTE_REQUIRE_SIGNATURE=false` unless signed packages are actually available

## Allowlist Design

Only allow:
- internal package domains
- controlled object storage domains
- release hosts owned by the same operator boundary

Do not allow:
- arbitrary raw GitHub URLs
- user-provided unknown hosts
- redirect chains into non-allowlisted domains

## Operator Workflow

1. Decide whether the environment is allowed to test remote skill install at all.
2. Add one or more trusted hosts to `SKILL_REMOTE_ALLOWED_HOSTS`.
3. Keep checksum verification enabled.
4. Enable the feature flag only in a controlled environment.
5. Submit the remote install request.
6. Check `install-tasks` and `audit-logs` before any further action.
7. Bind the skill to a robot only after operator review.

## Failure Handling

If a request is rejected:
- confirm whether the host is missing from the allowlist
- confirm whether checksum or signature was omitted
- review the persisted install task and audit log

If a request reaches validation but cannot proceed:
- keep the failed task record
- do not create or update robot bindings
- do not treat package download approval as runtime approval

## Important Boundary

Installing a skill is not the same as enabling it.

The controlled order should remain:
- install
- review
- bind
- validate in chat
