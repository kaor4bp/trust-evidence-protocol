# TEP 0.4.0 Agent Interface Contracts

This document defines the agent-facing interface for the 0.4.0 rebuild.

It is intentionally not a command reference. It describes the contracts another
agent needs to implement a new compatible runtime without reading the current
codebase.

Normative behavior and closed 0.4.0 system decisions live in
`docs/dev/TEP_0_4_0_FUNCTIONAL_SPEC.md`. This document focuses on the
agent-facing interface shape.

## 1. Design Goal

The agent should not need to memorize TEP internals.

The runtime must provide:

- one normal entry point for orientation and retrieval
- explicit route graphs for the next safe actions
- mechanical creation of provenance records when the agent supplies support
- validated public reasoning chains
- task-local REASON progression before protected planning/action/finalization
- clear refusal and repair paths when a contract is not satisfied

The skill should explain the mental model. MCP should be the normal
agent-facing API that enforces the behavior. CLI commands are development,
migration, debugging, and CI wrappers over the same services.

## 2. Agent Work Loop

Normal loop:

```text
hydrate / next-step
-> lookup(reason, task, cwd, mode)
-> optional drill-down through returned commands
-> record-evidence or chain-draft/augment-chain
-> reason-step
-> optional reason-review -> GRANT
-> protected action / final response / task outcome
```

The runtime should make this path cheaper than bypassing it. If the agent is
blocked, every response should include a repair route instead of only an error.

## 3. Mandatory Front Doors

### `next-step`

Purpose: choose a route before work, after focus drift, after mutation, or
before finalization.

Required inputs:

- `intent`: `answer`, `plan`, `edit`, `test`, `debug`, `persist`,
  `permission`, `final`, or `auto`
- `task`: compact natural-language task summary
- `cwd`: current working directory

Required output:

```json
{
  "contract_version": "0.4",
  "focus": {
    "workspace_ref": "WSP-*",
    "project_ref": "PRJ-*|null",
    "task_ref": "TASK-*|null",
    "wctx_ref": "WCTX-*|null",
    "focus_source": "local-tep|explicit|missing"
  },
  "route_graph": {
    "start": "lookup",
    "branches": [
      {"if": "needs facts", "then": "lookup(kind=facts)"},
      {"if": "needs code", "then": "lookup(kind=code)"},
      {"if": "needs protected action", "then": "reason-step -> grant"}
    ]
  },
  "required_next": ["lookup"],
  "blocked": false,
  "repair": []
}
```

Rules:

- If no workspace is available, do not fall back to global current context.
- If the task does not match current focus, return a focus-drift repair route.
- If a different repository is referenced, ask for workspace/project admission
  instead of silently attaching it.
- If the selected `WCTX-*` is owned by a different agent identity, return a
  fork/adopt repair route instead of using it as current focus.

### `lookup`

Purpose: retrieve facts, models, flows, code index entries, map context, and
chain-extension candidates.

Required inputs:

- `query`: what the agent needs
- `reason`: why the lookup is happening
- `kind`: `facts`, `code`, `theory`, `policy`, `research`, or `auto`
- `mode`: `general`, `research`, `theory`, or `code`
- `cwd`: current working directory

Required output:

```json
{
  "contract_version": "0.4",
  "lookup_is_proof": false,
  "focus": {"workspace_ref": "WSP-*", "project_ref": "PRJ-*|null"},
  "ranked_context": [
    {
      "ref": "MODEL-*|FLOW-*|CLM-*|CIX-*|GLD-*",
      "role": "integrated_picture|fact|hypothesis|meta_summary|code_navigation|policy",
      "status": "active|tentative|resolved|stale",
      "summary": "...",
      "quote": "...",
      "why_returned": "..."
    }
  ],
  "chain_candidates": [
    {"ref": "CLM-*", "role": "fact|observation|hypothesis", "quote": "..."}
  ],
  "curiosity": {
    "clusters": [],
    "bridges": [],
    "cold_zones": [],
    "probe_suggestions": []
  },
  "map_navigation": {
    "map_navigation_is_proof": false,
    "map_session_ref": "WCTX-*#map-session",
    "cells": []
  },
  "next_allowed_tools": ["record_detail", "linked_records", "augment_chain"],
  "route_token": "ROUTE-*",
  "repair": []
}
```

Rules:

- Lookup is navigation, not proof.
- Lookup should prefer `MODEL-*`/`FLOW-*` for compact integrated context.
- Lookup may return durable `MAP-*` cells in `map_navigation` as bounded
  navigation memory. They are not proof and must not become chain nodes.
- Lookup may return `CLM-* plane=meta` as compact summaries over many records,
  but these summaries are not object-level proof without drill-down.
- Runtime-only observations rank below supported/user-confirmed theory.
- Resolved/stale claims are fallback unless regression suspicion is detected.
- If a current `REASON-*` exists, lookup defaults to chain-extension mode and
  proposes nodes not already used in the current branch.
- Raw record paths should not be returned for normal agent work.
- Drill-down tools should require a `route_token`, `lookup_ref`, or
  `map_session_ref` so the runtime can verify that the agent followed the
  front-door route.

### Map Navigation

Purpose: give the agent a bounded cognitive map of the fact space without
turning generated views into proof.

Normal map loop:

```text
map_open(task/query/mode)
-> map_view(session)
-> map_move(session, zone/probe)
-> map_drilldown(session, ref)
-> map_checkpoint(session)

optional explicit mutation:
map_refresh(session|scope)
```

Current implementation status:

- `map_open`, `map_view`, `map_move`, `map_drilldown`, and `map_checkpoint`
  are exposed as MCP tools and have CLI mirrors for development/CI.
- The default session reference is encoded as `WCTX-*#map-session`.
- Session state is stored under `WCTX.map_sessions.default` and is covered by
  the owner signature. A non-owner agent must fork/adopt the WCTX before using
  the session.
- `map_open`, `map_move`, and `map_checkpoint` mutate only WCTX operational
  state. They do not create facts, proposals, debts, open questions, or durable
  `MAP-*` cells.
- `map_view` and `map_drilldown` are read-only. `map_drilldown` returns proof
  routes that still require record detail and chain validation before use.

Required map view output:

```json
{
  "contract_version": "0.4",
  "map_is_proof": false,
  "map_session_ref": "WCTX-*#map-session",
  "zone": {
    "id": "MZONE-*",
    "kind": "scope|topology|topic|activity|code|risk|probe",
    "summary": "..."
  },
  "anchor_facts": [],
  "ignored_but_relevant": [],
  "bridge_facts": [],
  "tension_facts": [],
  "signals": {
    "tap_smell": [],
    "neglect_pressure": [],
    "inquiry_pressure": [],
    "promotion_pressure": []
  },
  "allowed_moves": [],
  "proof_routes": []
}
```

Rules:

- Map output is navigation only.
- Anchor facts still require drill-down and chain validation before proof use.
- Ignored-but-relevant facts are connected facts with low recent use, absence
  from the current REASON branch, or low lookup/tap presence despite relevance.
- Tap smell is a decaying signal that repeated access may indicate agent
  fixation, missing MODEL/FLOW integration, or repeated task reuse.
- Inquiry pressure summarizes facts with many hypotheses, tentative branches,
  unresolved probes, or aggregate/meta claims around them.
- Candidate, missing, rejected, and unknown links must be labelled separately.
- Map sessions are persisted in `WCTX-*` as operational state.
- Durable `MAP-*` records are shared navigation cells; the WCTX map session is
  personal to the owning agent.
- Read-only map tools must not silently create or rewrite `MAP-*` records.
- `map_refresh` is the explicit mutating tool for materializing/updating
  `MAP-*` cells.
- New map-relevant `CLM-*` records and new or changed `MODEL-*`/`FLOW-*`
  records are refresh triggers.
- `lookup.map_navigation` and `map_refresh` expose these as navigation-only
  `refresh_triggers` with `refresh_triggers_are_proof=false`; agents should run
  `attention-index build`, then `map_refresh` dry-run/apply explicitly.
- Map tools must not automatically create `OPEN-*`, `DEBT-*`, `PRP-*`, or truth
  records.
- `map_drilldown` returns a proof route, not proof.

### Agent-Owned WCTX

Purpose: make `WCTX-*` a personal operational focus for one agent, not a shared
global scratchpad.

The runtime creates or reuses a local agent identity:

```json
{
  "id": "AGENT-*",
  "record_type": "agent_identity",
  "contract_version": "0.4",
  "record_version": 1,
  "scope": "agent.local",
  "key_algorithm": "hmac-sha256",
  "key_fingerprint": "sha256:*",
  "key_scope": "local-agent",
  "status": "active"
}
```

Every active `WCTX-*` must be owner-bound:

```json
{
  "id": "WCTX-*",
  "record_type": "working_context",
  "contract_version": "0.4",
  "record_version": 1,
  "agent_identity_ref": "AGENT-*",
  "agent_key_fingerprint": "sha256:*",
  "ownership_mode": "owner-only",
  "handoff_policy": "fork-required",
  "owner_signature": {
    "algorithm": "hmac-sha256",
    "signed_payload_hash": "sha256:*",
    "signature": "hmac-sha256:*"
  }
}
```

Rules:

- WCTX is operational state, not proof.
- Private agent key material is never stored in the public WCTX record.
- The local HMAC key is runtime-private state under
  `.tep_context/runtime/agent_identity/`; only its `sha256:` fingerprint is
  exposed through `AGENT-*`.
- The WCTX owner signature covers the canonical focus payload that the runtime
  uses for `next_step`, lookup routing, map sessions, and protected actions.
- `map_sessions` is part of the signed WCTX payload. Tampering with a map
  session must invalidate the owner signature.
- Agent-facing WCTX creation and mutation paths, including lookup auto-create
  and manual create/fork/close, must produce signed 0.4 owner-bound records.
- A non-owner agent may inspect a WCTX as navigation or handoff context, but
  must not use it as current focus.
- To continue from another agent's WCTX, the runtime must create a new signed
  fork/adopted WCTX with `parent_context_ref` and `supersedes_refs` links.
- REASON/GRANT created under a WCTX must bind the same `agent_identity_ref` or
  be rejected by validation.

## 4. Evidence Capture Contract

The agent should not manually create `SRC-*` for normal work.

The agent supplies a support surface:

```json
{
  "kind": "file-line|url|command-output|user-input|artifact",
  "quote": "...",
  "path": "...",
  "line_start": 1,
  "line_end": 1,
  "url": "...",
  "command": "...",
  "input_ref": "INP-*",
  "claim_text": "optional candidate claim"
}
```

The runtime creates or links:

```text
INP / FILE / ART / RUN -> SRC -> optional CLM
```

Rules:

- `SRC-*` without a provenance surface is invalid for new records.
- File evidence must create `FILE-*` metadata and, when allowed by settings,
  an `ART-*` snapshot.
- Command evidence must create or link `RUN-*`; runtime CLM must transitively
  reach `RUN-*`.
- If `FILE-*` is covered by `CIX-*`, the runtime may attach CIX navigation links
  to the generated source/chain output, but CIX is not proof.

## 5. Evidence Chain Contract

The agent supplies a draft chain:

```json
{
  "mode": "planning|proof|permission|final|debug|proposal",
  "nodes": [
    {"ref": "CLM-*", "role": "fact", "quote": "..."},
    {"ref": "CLM-*", "role": "hypothesis", "quote": "..."},
    {"ref": "CLM-*", "role": "observation_summary", "quote": "..."}
  ],
  "edges": [
    {"from": "CLM-*", "to": "CLM-*", "relation": "supports|constrains|contrasts"}
  ],
  "conclusion": "..."
}
```

The runtime returns:

```json
{
  "valid": true,
  "proof_allowed": false,
  "augmented_nodes": [],
  "missing_links": [],
  "gaps": [],
  "repair": []
}
```

Rules:

- The validator checks graph validity, quote matches, role legality, source
  boundaries, and mode policy.
- The validator does not prove that the reasoning is adequate or optimal.
- Hypotheses are allowed in exploration/planning/proposal when compatible with
  known facts.
- Proof/final/action modes reject unsupported hypotheses.
- Hypothesis-on-hypothesis is invalid for proof paths.
- Summary roles over meta claims require underlying object-level support for
  decisive proof.
- If the chain is incomplete, the API should suggest open questions, competing
  hypotheses, or lookup extension candidates.

## 6. REASON And GRANT Contract

`REASON-*` is the task-local ledger of justified progression.

The agent appends a reason step when it wants to plan, request permission, take
protected action, or finalize:

```json
{
  "task_ref": "TASK-*",
  "mode": "planning|edit|test|final|permission",
  "parent_reason_ref": "REASON-*|null",
  "branch": "main|alternative-name",
  "chain": {"nodes": [], "edges": [], "conclusion": "..."},
  "intent": "why this step is needed"
}
```

Rules:

- A REASON step belongs to exactly one workspace/task focus.
- Direct same-mode continuation cannot duplicate the parent chain hash on the
  same branch.
- Forks are allowed when the agent explores an alternative.
- A REASON step created under a WCTX must bind the same agent identity as the
  WCTX owner.
- The runtime should reject direct ledger file writes.
- Hash-chain sealing and weak proof-of-work are tamper friction, not a security
  boundary.
- Version-2 ledger entries must preserve and validate `prev_ledger_hash`,
  `entry_hash`, `ledger_hash`, `seal`, `pow`, `chain_hash` for steps, and the
  public `signed_chain` summary.

`GRANT-*` is the only authorization record for protected work:

```text
REASON -> GRANT -> RUN / protected write
```

Rules:

- GRANT binds workspace, project, task, WCTX owner agent identity, mode, action
  kind, cwd, optional command hash, context fingerprint, and time window.
- GRANT is valid only inside its window.
- GRANT is not consumed by mutating the grant record; use is inferred from
  linked `RUN-*` or protected records.

## 7. Task And Plan Contract

Tasks must be executable by an agent, not just named.

Required task states:

- `draft`: not ready for work
- `atomic`: can be completed in one working iteration
- `decomposed`: has valid subtasks/subplans
- `active`: current execution focus
- `blocked`: blocked by linked open question/debt/action
- `done`: completed and final reason exists when autonomous

Rules:

- A task is not valid for active work until it is `atomic` or `decomposed`.
- Subtasks should be one-iteration units.
- Plans and debts must be linked to task/workspace/project focus.
- Autonomous `done` requires final REASON and final outcome validation.
- If the agent changes task type, it should run retrospective lookup for prior
  same-type tasks when available.

## 8. Model And Flow Contract

`CLM-*` stores atomic claims. `MODEL-*` and `FLOW-*` store compressed,
integrated pictures.

Rules:

- MODEL/FLOW can only be built from supported/user-confirmed theory claims.
- MODEL/FLOW cannot rely on tentative hypotheses, exploration context, or
  runtime-only observations.
- FLOW references MODEL; MODEL does not need reverse links for v0.4.
- Lookup prioritizes MODEL/FLOW because they reduce token pressure.
- If the agent wants knowledge to rank higher, the correct path is validated
  MODEL/FLOW promotion, not repeated raw CLM reading.

## 9. Error And Repair Contract

Every blocking response should contain:

```json
{
  "blocked": true,
  "reason": "short machine-readable reason",
  "message": "short human-readable explanation",
  "repair": [
    {"command": "lookup", "why": "gather support"},
    {"command": "reason-step", "why": "append valid chain"},
    {"command": "workspace-admission", "why": "resolve focus"}
  ]
}
```

Do not block with a dead end when a safe route exists.

## 10. Agent Anti-Patterns To Block Or Discourage

- Reading raw `records/claim/*.json` as a normal retrieval path.
- Reading or writing raw `~/.tep_context` records in normal agent mode.
- Creating `SRC-*` without INP/FILE/ART/RUN provenance.
- Creating runtime CLM without RUN provenance.
- Promoting MODEL/FLOW from tentative or runtime-only claims.
- Reusing the same reason chain as a reusable permit.
- Falling back to global current task/workspace.
- Reusing another agent's `WCTX-*` as current focus instead of creating a signed
  fork/adopted WCTX.
- Silently attaching a foreign repository to the current workspace.
- Treating generated views, CIX, backend hits, telemetry, or maps as proof.
- Calling drill-down tools without first receiving a route from `next_step`,
  `lookup`, or map navigation.

## 11. Acceptance Criteria

A compatible 0.4 implementation should pass deterministic tests for:

- no workspace fallback
- WCTX owner signature and agent identity mismatch are rejected for active focus
- lookup returns route graph and chain candidates
- lookup defaults to chain-extension mode when current REASON exists
- evidence capture creates provenance graph
- runtime CLM without RUN is rejected
- MODEL/FLOW from runtime-only or tentative support is rejected
- duplicate same-branch reason continuation is rejected
- protected action without valid GRANT is rejected
- autonomous finalization without final REASON is rejected
- stale/resolved claims rank below active theory unless regression route applies

Live-agent smoke tests should verify behavior, not model intelligence:

- agent follows route graph instead of raw records
- agent uses MCP front doors instead of the legacy CLI command zoo
- agent records competing hypotheses when facts underdetermine the answer
- agent extends REASON before protected action/final answer
- agent uses MODEL/FLOW when available instead of rereading many CLM records
- telemetry records lookup, raw-read attempts, reason failures, and grant checks
- map navigation surfaces neglected relevant facts and tap smell without using
  map output as proof

## 12. Rebuild Documentation Map

Another agent should be able to rebuild 0.4.0 from these documents in order:

1. `docs/dev/TEP_0_4_0_FUNCTIONAL_SPEC.md`
2. `docs/dev/TEP_0_4_0_MECHANICS_REQUIREMENTS.md`
3. `docs/dev/TEP_0_4_0_AGENT_INTERFACE_CONTRACTS.md`
4. `docs/dev/mechanics/*.md`
5. `docs/reference/TEP_DATA_MODEL.md`
6. plugin README and generated command help
7. deterministic and live-agent tests

If an implementation detail is required to pass acceptance but appears only in
the existing code, it is a documentation bug.

## 13. Documentation Artifacts To Produce Next

The current contract is strong enough to guide the next implementation slice.
The functional spec closes the main logical gaps. Remaining documentation work
should now be concrete schemas and command examples, not new policy debates:

- JSON Schema files or typed dataclasses for `lookup`, `next-step`,
  `record-evidence`, `reason-step`, `GRANT`, `RUN`, migration reports, and map
  sessions
- MCP examples for each normal-agent contract and CLI examples only for
  development/migration/debugging contracts
- deterministic fixtures for each acceptance criterion
- live-agent test prompts and pass/fail assertions

Do not solve these by expanding `SKILL.md`. Each artifact should become a
runtime contract, schema, command output, or test fixture.
