# Skills Versioning And Rollback

## Current Policy

The current repository treats a skill as:
- `slug`
- `version`
- manifest-defined prompt entrypoints

Robot bindings point to a `skill_slug`, and the runtime resolves the currently installed version recorded in the registry and binding table.

## Recommended Version Pinning Rule

For the next controlled phase, use these rules:

1. A robot binding should always store the exact installed `skill_version`.
2. Upgrading a skill should never silently rewrite every robot to the new version.
3. Upgrades should be explicit operator actions.
4. A binding should be able to stay pinned to an older installed version until the operator changes it.

## Recommended Rollback Rule

If a new skill version fails:
- keep the previous installed version available
- do not rewrite live robot bindings automatically
- mark the new install task as `failed` or `rolled_back`
- keep the failed version metadata for auditability

If a version is already active on robots and must be rolled back:
- install or re-activate the previous known-good version
- move robot bindings back to that version explicitly
- emit one audit record for the rollback action

## Operator Guidance

Before upgrading a skill:
- verify prompt diffs
- verify robot scope
- identify pinned robots
- test on one non-critical robot first

After upgrading:
- verify chat output on a controlled robot
- review audit logs
- keep the old version available until validation completes

## Future Schema Direction

If this project continues into a marketplace phase, add:
- explicit `is_current` or `is_active` registry metadata
- robot binding version pinning controls
- rollback action APIs
- upgrade comparison view in the admin console
