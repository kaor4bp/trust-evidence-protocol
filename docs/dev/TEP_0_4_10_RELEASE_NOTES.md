# TEP 0.4.10 Release Notes

TEP 0.4.10 makes personal `agent_private_key` a hard front-door requirement.

## Changed

- `next_step` now requires `agent_private_key` and returns
  `agent_identity_required` immediately when it is missing.
- `brief_context` now requires `agent_private_key` for the same reason.
- The runtime error text now explicitly tells the agent to generate or provide
  a personal key before starting work, including front-door calls such as
  `next_step` and `lookup`.
- Skill and route wording now consistently treat `agent_private_key` as
  mandatory start-of-session state rather than a late mutation-only credential.

## Rationale

Before this change, the agent could enter the system through briefing or route
tools and only discover the missing key later. That kept producing avoidable
confusion. The front door now fails fast and tells the agent what prerequisite
it is missing.
