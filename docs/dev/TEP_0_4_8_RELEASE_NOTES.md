# TEP 0.4.8 Release Notes

TEP 0.4.8 makes the agent's current rights visible in the runtime briefing.

## Changed

- `start_briefing` now includes `permission_snapshot` with:
  - always-allowed front doors (`next_step`, `lookup`)
  - current agent identity
  - active scoped `PRM-*` permissions
  - current matching `GRANT-*` entries for the same agent and focus
  - default-denied reminders for protected actions
- `next_step` compact text now prints a `rights:` line from that snapshot.
- `lookup` compact text now prints the same `rights:` line so agents do not
  lose permission context after leaving `next_step`.
- Skill and reference docs now tell agents to read the briefing before acting,
  while keeping runtime grant checks authoritative at use time.

## Rationale

Not every agent action can be intercepted equally early. The briefing should
therefore expose the current operational envelope before the agent attempts a
write, shell mutation, or autonomous task completion. This reduces accidental
policy misses without turning the briefing into an authorization cache.
