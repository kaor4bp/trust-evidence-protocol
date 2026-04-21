# Information Lookup Workflow

Use this workflow when searching, answering, investigating, reconciling facts, or deciding what is known.

## Lookup Order

Search known context before deriving from scratch:

1. hydration summary: current project, current task, active restrictions, active guidelines, active permissions, active proposals, conflicts
2. generated attention/brief views as navigation only
3. active `WCTX-*` working contexts for pinned refs, focus paths, assumptions, concerns, and handoff notes
4. generated `topic_index/` search as lexical prefilter when direct record search is too broad
5. generated `logic_index/` search/check as predicate prefilter when claims have `CLM.logic`
6. canonical `MODEL-*` and `FLOW-*` for the current project/task/domain
7. active canonical `CLM-*` records ordered by trust: `corroborated`, `supported`, `contested/rejected`, `tentative`
8. active `GLD-*` records for coding, tests, review, debugging, architecture, and agent behavior
9. active `PRP-*` records for critique, recommended options, risks, and stop conditions
10. canonical `SRC-*` records behind selected claims and guidelines, preferring accepted and independent sources
11. resolved/historical `CLM-*` records only as fallback when active records do not answer the task
12. archived `CLM-*` records only by explicit id, audit, rollback, or user request
13. `OPEN-*`, `PLN-*`, and `DEBT-*` for unresolved questions and continuity
14. new code/runtime/doc/user investigation only for gaps, contradictions, stale claims, or missing support

## Rules

```text
generated attention/brief -/-> proof
canonical CLM-* + accepted SRC-* -> proof candidate
active GLD-* + accepted SRC-* -> scoped operational guidance
active PRP-* -> constructive agent recommendation, not proof
WCTX-* -> operational focus/handoff context, not proof
topic_index -> lexical prefilter, not proof
logic_index -> predicate prefilter/checking, not proof
contested/rejected claims must be noticed before acting
tentative claims guide exploration, not proof
resolved/historical claims are fallback context, not primary current context
archived claims require explicit reference or audit intent
new investigation should update context when the result matters later
```

## Search Behavior

- Start from the resolved TEP context root, preferring `~/.tep_context` when available; only fall back to fresh investigation for gaps, contradictions, staleness, or missing support.
- Use `lookup --reason ...` as the front door when choosing a route. The reason is mandatory and should describe why the agent is looking: `orientation`, `planning`, `answering`, `permission`, `editing`, `debugging`, `retrospective`, `curiosity`, or `migration`.
- Follow `lookup.next_allowed_commands` and `lookup.output_contract` before opening broader record searches. `search-records`, `claim-graph`, `record-detail`, and `linked-records` are drill-down tools after lookup in normal work.
- Let lookup create a lightweight `WCTX-*` when no active working context exists and the workspace is known. Treat that WCTX as operational focus only, not proof or authorization.
- Use `topic-search` to narrow broad lookup, but follow up with `record-detail`, `linked-records`, or direct code/source inspection before citing.
- Use `logic-search` / `logic-check` for typed predicate claims, but follow up with canonical `CLM-*` and `SRC-*` before citing.
- Prefer confirming, falsifying, narrowing, or superseding existing claims over rediscovering the same fact.
- If a known claim is true historically but no longer current, run `resolve-claim` instead of leaving it as a high-priority active fact.
- If a claim is audit-only noise for current work, run `archive-claim` instead of deleting it.
- Keep project/task scope active so local claims, permissions, restrictions, guidelines, and proposals do not leak globally.
- Treat code, tests, docs, user statements, logs, screenshots, and command outputs as sources that need classification before use.
- Keep source quotes short enough that a later agent can reconstruct why the claim exists.
- If a search reveals a reusable result, persist it as `SRC-*` plus `CLM-*` instead of leaving it only in the chat.
- Do not read raw `records/claim/*.json` in normal lookup. Use compact projections first; raw reads require an explicit debug/migration/forensics/plugin-dev escape hatch.

## Conflict Handling

- If a new observation contradicts a supported or corroborated claim, do not choose silently.
- Mark the old or new claim `contested` when the conflict is meaningful.
- Use `scan-conflicts` for structured comparable facts when `comparison` fields exist.
- If a conflict is accepted as normal by the user, record that acceptance as a source-backed claim or restriction.
- If a conflict is only temporal because the old claim was resolved, move the old claim to resolved/historical lifecycle and keep the current claim active.
- If a claim change affects the overall picture, update or mark stale dependent `MODEL-*` and `FLOW-*` records.

## Building The Overall Picture

- Use `MODEL-*` for the current understanding of one domain/aspect.
- Use `FLOW-*` for end-to-end behavior across models, including preconditions, oracle, accepted deviations, and open questions.
- Investigation-local models/flows are allowed, but they should later be promoted, superseded, or marked stale when domain knowledge changes.
- A model or flow summary is never proof by itself; it must cite underlying `CLM-*` records.
- `MODEL-*` and `FLOW-*` should rank high in lookup because they are compact integrated pictures, but their write path must remain stricter than ordinary observations: do not build them from tentative/runtime-only claims.

## Public Output

For non-trivial lookup, show a compact `Reasoning Checkpoint` before a long tool batch and after surprising results.
For user-facing conclusions, include decisive ids and short quotes when records exist.
