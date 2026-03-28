# Skills Remote Install Smoke Test

## Goal

Provide one operator walkthrough from remote install request to post-install review.

## Preconditions

Before running the smoke test:
- set `ENABLE_REMOTE_SKILL_INSTALL=true`
- set `SKILL_REMOTE_ALLOWED_HOSTS` to the trusted package host
- keep `SKILL_REMOTE_REQUIRE_CHECKSUM=true`
- configure `SKILL_REMOTE_ED25519_PUBLIC_KEY` if signatures are required
- ensure the remote package contains exactly one `skill.yaml`, `SKILL.md`, and valid prompt entrypoints

## Walkthrough

1. Open `/admin/skills`.
2. In the remote install form, paste the package URL.
3. Fill checksum.
4. If the environment requires it, fill the detached signature and keep `signature_algorithm=ed25519`.
5. Submit the request.
6. Confirm a new remote install task appears in the task list.
7. Check the task badges for:
   - host
   - package size
   - checksum status
   - signature status
   - registry landing status after install
8. Open task detail and confirm:
   - package URL
   - content type
   - checksum expected vs actual
   - signature algorithm
   - install path
9. Move to the version comparison panel and confirm the newly installed skill version is visible.
10. Review whether any robot should bind to the new skill version.

## Expected Outcomes

Successful run:
- install task reaches `installed`
- task detail contains download and verification metadata
- audit logs contain `skill.install_remote` with `success`
- the skill appears in the registry and in `/skills`

Rejected run:
- install task reaches `rejected`
- task detail still records enough metadata to explain why
- audit logs contain `skill.install_remote` with `rejected`

## Suggested Follow-Up

After a successful smoke test:
- review the skill detail page
- decide whether to bind it to a robot
- validate robot behavior in `/chat` before wider rollout
