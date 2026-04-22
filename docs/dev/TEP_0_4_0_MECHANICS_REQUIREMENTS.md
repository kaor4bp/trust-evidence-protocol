# TEP 0.4.0 Mechanics Requirements

This document is the working intent for the 0.4.0 line.

It is not a changelog and not a command manual. It defines the mechanics the
runtime must enforce so the implementation can be rebuilt without losing the
system shape.

Reference data semantics live in `docs/reference/TEP_DATA_MODEL.md`. Command
syntax lives in plugin README and generated command docs. Research and future
algorithm notes live in `docs/research/`.

Related developer docs:

- `docs/dev/TEP_API_FIRST_CONTRACT.md`
- `docs/dev/TEP_0_4_0_AGENT_INTERFACE_CONTRACTS.md`
- `docs/dev/mechanics/README.md`
- `docs/dev/TEP_MAP_GRAPH_V1.md`
- `docs/dev/TICK_TOCK_ADOPTION.md`

## 1. System Purpose

TEP exists to let agents think and act with more freedom while keeping durable
claims, decisions, and mutations mechanically accountable.

The agent may explore, hypothesize, and criticize. The runtime must control the
boundary between:

- navigation and proof
- exploration and durable belief
- thought and authorized action
- current task context and unrelated global memory
- user-confirmed theory and runtime-only observation

The goal is not to make the agent mechanical. The goal is to make the API do
the mechanical work so the agent can spend tokens on useful reasoning.

TEP does not mechanically prove that an agent's reasoning is adequate. It can
validate provenance, ids, quotes, graph shape, mode boundaries, and progression.
Evidence chains are therefore a cognitive scaffold: by forcing the agent to
fit facts, observations, and marked hypotheses into a valid graph, TEP increases
the chance that the agent builds a correct local working context before acting.
Invalid chains are rejected; weak or incomplete thinking is surfaced as gaps,
open questions, competing hypotheses, or curator/review work.

## 2. Architecture Stance

TEP 0.4.0 should be API-first.

The skill should contain the short mental model. The runtime API, hooks, and
validators should provide the route, decide what is allowed, and return the next
safe actions.

Normal flow:

```text
hydrate / next-step
-> lookup
-> drill down through returned route
-> record support or build/augment chain
-> append REASON step
-> validate preflight
-> action or final response
```

Agents should not need to memorize a long checklist. If the agent is unsure,
the API should give a route graph with explicit branches.

## 3. Source Of Truth

Canonical records are typed JSON records under the TEP context. Generated
views, topic indexes, attention maps, curiosity maps, backend hits, and CIX
entries are navigation unless promoted through canonical records.

Truth path:

```text
INP / FILE / ART / RUN -> SRC -> CLM -> MODEL / FLOW
```

Operational path:

```text
WSP -> PRJ -> TASK / WCTX / PLAN / DEBT / ACT
```

Reasoning path:

```text
lookup -> chain draft -> REASON -> optional GRANT -> RUN / protected write
```

No `SRC-*` should exist without a provenance surface. The provenance surface is
one of:

- `INP-*`: captured user input or prompt metadata
- `FILE-*`: original file metadata
- `ART-*`: copied or generated artifact payload
- `RUN-*`: command execution trace

When possible, `FILE-*` should have a linked `ART-*` copy or snapshot. If a
`FILE-*` is covered by `CIX-*`, `SRC-*` should be able to carry code index links
for navigation, but CIX is not proof.

Runtime claims must transitively reach `RUN-*`. They should not be treated the
same as user-confirmed theory.

## 4. Workspace And Focus

Global current context is a bug-prone fallback. Normal operation requires an
explicit workspace.

Rules:

- Every durable record should belong to a `WSP-*` unless it is explicitly
  migrating legacy data.
- `PRJ-*` is optional only when the record genuinely spans projects.
- Local `.tep` anchors select workspace/project/task for a working directory.
- If the user points the agent at a different repository, the agent must not
  silently add it to the current workspace. It must ask whether to create a new
  workspace, add a project to the current workspace, or inspect read-only.
- `WCTX-*` is agent working memory, not user-facing truth. Agents may create
  WCTX records to keep their own operational context, but WCTX cannot prove
  factual claims.

Hydration must show the current workspace, project, task, and active controls
clearly.

## 5. Task, Plan, And Debt Mechanics

All meaningful work should be scoped to `TASK-*`.

Task rules:

- A task is valid for work only when it is `atomic` or `decomposed`.
- Atomic task means one working iteration, explicit deliverable, done criteria,
  verification, boundary, and blocker policy.
- Parent task is orchestration only.
- Mutating work belongs on an atomic leaf task.
- Autonomous tasks cannot end without a terminal outcome.
- Before starting work, the agent should confirm that the current task is the
  intended task.

Plan/debt rules:

- `PLN-*` and `DEBT-*` are persistent work records, not prose backlog.
- Plans and debts must be linked to task/workspace/project context.
- Completion of an autonomous task must account for linked blocking open
  questions, plans, debt, and planned actions.
- Agents should be able to split a task into subtasks and plans, then work only
  on leaf units.

## 6. Lookup As The Default Read Path

`lookup` is the front door for facts, code, theory, research, and policy.

It should return:

- selected route
- next allowed commands
- output contract
- compact candidate records
- chain starter or chain extension draft
- fallback route
- proof boundary reminders

Raw record reads are abnormal. They remain possible for plugin development,
migration, debugging, or forensics, but normal agents should use lookup, graph,
record detail, linked records, MCP tools, and map views.

When a current `REASON-*` exists, lookup defaults to chain-extension mode:

- exclude refs already present in the current reason chain
- propose records that can become new chain nodes
- include task node when useful
- report how many existing refs were excluded
- if no new proof-capable nodes are found, explicitly suggest the fallback:
  revisit existing nodes and record a fact-compatible hypothesis or open
  question

This prevents agents from reusing the same chain as a reusable permit.

## 7. Evidence Chains

Evidence chains are the public, compact, mechanically validated form of agent
reasoning.

A chain is not hidden chain-of-thought. It is an inspectable graph of ids and
quotes:

```text
fact: CLM-* "quote"
-> observation: CLM-* runtime observation "quote"
-> provenance: SRC/RUN/INP/ART links surfaced by augmentation
-> decision
```

The validator does not judge whether the conclusion is clever, complete, or the
best possible interpretation. It judges whether the conclusion is allowed to
stand on the cited graph. This distinction is deliberate: the chain gives the
agent a disciplined local memory and gives the user/reviewer a compact audit
surface, but it does not replace human or curator review.

Allowed chain roles:

- `fact`
- `observation`
- `hypothesis`
- `exploration_context`
- `permission`
- `requested_permission`
- `restriction`
- `guideline`
- `proposal`
- `task`
- `working_context`
- `project`
- `model`
- `flow`
- `open_question`

Generated/backend/navigation ids such as `CIX-*`, backend hits, topic index
hits, logic index hits, and map nodes cannot be proof nodes.

Core proof rules:

- A proof chain must contain at least one supported or corroborated fact.
- Quotes must match the referenced record or its source quotes.
- Control records cannot support truth claims.
- Task/project/WCTX/context records cannot support truth claims.
- Hypothesis cannot support another truth node as proof.
- Proof modes reject unsupported hypotheses and exploration context.
- Planning/debugging/curiosity/proposal may contain uncertainty when it remains
  explicitly marked.

## 8. Hypotheses

Hypothesis is a lifecycle stage of a claim, not a separate truth type.

Implementation may use an index such as `hypotheses.jsonl`, but the durable
claim is still `CLM-* status=tentative`.

Two kinds matter:

- durable hypothesis: tentative claim compatible with known facts and available
  for planning/proposal/debugging
- exploration hypothesis: local probe idea used to search or test, not valid as
  proof

Agents may use multiple hypotheses while exploring if they fit known facts. A
proof chain must not rely on hypothesis-on-hypothesis. If a hypothesis becomes
supported, it should be promoted into a normal claim lifecycle and removed from
the active hypothesis index.

If old facts appear contradicted by current runtime observations, "fact is
stale" is itself only a hypothesis until supported. The agent cannot stack a new
system theory on top of an unsupported staleness hypothesis.

## 9. Reason Ledger

`REASON-*` is the append-only task-local ledger of justified reasoning.

It is not a loose permit. It is the record of how the agent's reasoning
progressed.

Rules:

- Each `REASON-*` belongs to the current task/workspace/project focus.
- A new reason step continues from the latest task step unless explicit parents
  are provided.
- Explicit parent refs and branch labels create forks.
- A reason step cannot parent across another task.
- Same-mode continuation cannot duplicate the direct parent chain hash on the
  same branch.
- If the agent wants to continue, it must extend the chain with new support or
  fork a named alternative branch.
- The ledger is hash-chained, sealed, and contains weak proof-of-work metadata.
- Direct runtime ledger edits are blocked by hooks and detected by validation.

Planning and finalization:

- `preflight-task --mode planning` requires a current valid `REASON-*` for the
  active task.
- `preflight-task --mode final` requires `REASON-* mode=final`.
- Autonomous `TEP TASK OUTCOME: done` requires both `REASON-* mode=final` and
  `GRANT-* mode=final`.
- Read-only lookup/reasoning remains available without a reason step so the
  agent can gather material before constructing a chain.

If the agent is interrupted before finalization, absence of `REASON-* mode=final`
is a resumable state, not corruption.

## 10. Grants, Runs, And Protected Actions

`GRANT-*` is authorization, not reasoning.

Path:

```text
REASON-* -> GRANT-* -> RUN-* / protected write
```

Rules:

- Protected mutating actions require a valid grant when strictness demands it.
- Bash mutations should use command-bound grants.
- A grant is valid only for task, mode, action kind, optional command hash, cwd,
  context fingerprint, and time window.
- Grants are not marked mutable `used=true`. Consumption is detected through
  linked `RUN-*` or protected records.
- Artifacts and support capture should be allowed where safe; writing TEP
  records is a normal supported operation, not a project-code mutation.

`RUN-*` is the execution trace for command-derived facts. Runtime claims without
`RUN-*` provenance should be rejected or downgraded.

## 11. Model And Flow

`MODEL-*` and `FLOW-*` are compact integrated pictures over claims.

They should rank above scattered claims in lookup because they reduce token
pressure and help the agent reason about the system. But they are stricter than
ordinary claims.

Rules:

- MODEL/FLOW must be derived, not primary truth.
- MODEL/FLOW cannot be based on tentative hypotheses.
- MODEL/FLOW cannot be based only on runtime observations.
- At least user-confirmed or supported theory claims are required.
- FLOW describes movement across MODELs.
- FLOW should include preconditions and oracle.
- Contradictory flows should not be split by default. The system should surface
  expected-vs-actual conflict and allow the user to confirm that the
  contradiction is normal.

## 12. Code Index And Backends

`CIX-*` is code navigation and impact metadata, not proof.

Code index goals:

- index files and code parts such as functions/classes when useful
- keep parser support modular per language
- support Markdown metadata extraction
- allow agent annotations on code entries
- track file hash/freshness for notes and smells
- link CIX to claims, sources, guidelines, proposals, and tasks when relevant

External backends are implementation detail behind TEP:

- default search should stay project-scoped
- workspace-level lookup can look broader when explicitly needed
- users and agents should not need to know whether CocoIndex or another backend
  answered the query
- backend status must be explicit and honest: installed, selected, indexed, and
  search-ready are separate facts
- backend hits should be reviewable and linkable into CIX/CLM/MODEL/FLOW through
  TEP feedback tools

Do not introduce a separate backend index abstraction until the boundary with
CIX is clear.

## 13. Curiosity And Map Thinking

Maps are navigation, not proof.

The map system should help agents decide what to inspect next without reading
raw records.

Required mechanics:

- typed map graph format
- topic clusters
- topology clusters from established links
- bridge pressure
- cold zones
- candidate links
- explicit missing or rejected links where known
- activity/heat with decay
- compact LLM-readable views
- optional HTML visualization from the same map graph

Curiosity should prefer useful uncertainty:

- rarely touched zones
- bridges between clusters
- candidate links with no confirmed absence
- contradictions between expected and observed flow
- repeated access to the same hot record that should be promoted to MODEL/FLOW

The map must not create proof. It proposes probes.

## 14. Guidelines, Restrictions, Permissions, And Proposals

Guidelines are operational rules, not factual proof.

Rules:

- `GLD-*` can be global, project-scoped, or task-scoped.
- Agents may propose new guidelines, but user confirmation is required before
  treating them as active policy.
- `RST-*` can block or constrain actions.
- `PRM-*` captures allowed action boundaries.
- `PRP-*` is constructive agent criticism and solution options.

Agents should cite guideline ids and quotes before substantial code edits. The
API should help select relevant guidelines instead of relying on the agent to
search manually.

If the agent disagrees with user direction or current implementation, it should
record a proposal rather than silently dropping the critique.

## 15. Curator Mode

Curator is an organizational role for parallel or sidecar agents.

Curator should not browse the entire context freely. It receives a pool of
records and a curator-specific route.

Curator responsibilities:

- find duplicate facts
- find contradictions
- propose MODEL/FLOW updates
- identify stale or resolved claims
- prepare questions for the user
- link related records
- produce proposals when the current model looks wrong

Curator may talk to the user, but its task is context hygiene and knowledge
organization, not project-code execution.

## 16. Telemetry And Feedback

Telemetry should show whether the protocol is reducing agent token burden or
creating friction.

Important signals:

- raw claim reads
- repeated reads of one hot record
- lookup reason distribution
- MCP vs CLI access
- backend selected/available/search-ready status
- missing WCTX or task focus
- missing reason chains
- grant misses, expirations, and used-grant rejections
- chain validation failures
- unresolved input records

Telemetry must feed the agent back to compact tools, not just report numbers.

## 17. Cleanup And Forgetting

TEP should not force agents to drown in old high-confidence facts.

Lifecycle rules:

- resolved/historical/stale claims remain searchable but rank lower than active
  claims
- old resolved bug claims should not dominate lookup
- stale facts can be used as fallback context, not primary proof
- cleanup should be staged: candidate -> archive -> delete
- unreferenced `INP-*` should not be archived immediately; only after
  configurable aging
- archive before delete
- cleanup must preserve enough provenance to explain why something was hidden
  or archived

## 18. Token Pressure Strategy

TEP should reduce tokens by moving mechanical work out of the agent.

Preferred mechanical operations:

- route graph from `next-step` and `lookup`
- chain starter and chain extension generation
- chain augmentation with source quotes and links
- guideline selection
- linked record graph retrieval
- backend code search behind TEP
- map/cluster summaries
- telemetry anomaly hints
- generated compact views

Avoid solving token pressure by only truncating. Compression settings are useful,
but the main win is replacing repeated LLM rediscovery with deterministic
retrieval and validation.

## 19. Testing Requirements

Deterministic tests must cover:

- context validation and hydration
- workspace/project/task focus
- task decomposition
- lookup route graph and chain extension
- evidence chain validation
- hypothesis acceptance/rejection by mode
- REASON DAG progression and duplicate-chain rejection
- GRANT/RUN protected action lifecycle
- final and autonomous stop gates
- backend status honesty
- map graph shape and HTML generation
- telemetry counters and hints

Live-agent Docker tests are required for behavior that cannot be validated with
unit tests alone:

- agent actually uses TEP tools, not just answers from model knowledge
- agent builds and extends reasoning chains
- agent responds to blocked hooks by using the intended route
- agent can solve uncertainty tasks by asking/probing rather than guessing
- curator receives a pool and produces useful organization output

Full live-agent runs are expensive and should be gated by explicit user
instruction during beta.

## 20. 0.4.0 Acceptance Criteria

0.4.0 should be considered ready when:

- The short skill describes the mental model without becoming the command
  manual.
- `lookup` is the normal entry point and returns chain-extension candidates by
  default when a current reason exists.
- Planning continuation requires a valid current `REASON-*`.
- Final answers require `REASON-* mode=final`.
- Autonomous `done` requires final reason and final grant.
- Protected mutation creates/link-checks `GRANT-*` and `RUN-*`.
- Runtime claims require runtime provenance.
- MODEL/FLOW cannot be promoted from tentative/runtime-only support.
- Workspace focus cannot fall back silently to global context.
- CIX/backend/map outputs remain navigation only.
- Telemetry can identify whether agents are using compact routes or bypassing
  them.
- Deterministic tests pass.
- A small live-agent smoke suite proves that hooks and route mechanics work with
  a real agent, when explicitly run.

## 21. Known Design Risks

Reason gates can become ceremonial if chains are too easy to reuse. The current
mitigation is chain progression: same-mode direct continuation must extend the
chain or fork.

The API can overconstrain exploration. The current mitigation is to keep
lookup/read/reasoning available before a reason step, and to allow hypotheses in
uncertainty-bearing modes.

Runtime observations can flood the knowledge base. The current mitigation is to
rank theory/user-confirmed MODEL/FLOW above runtime-only bug observations and to
make runtime provenance explicit.

Backend integration can leak implementation details. The current mitigation is
to keep TEP as the single front door and expose backend status honestly.

Curiosity can become random noise. The current mitigation is to drive curiosity
from map graph topology, heat, cold zones, bridge pressure, and candidate links,
not arbitrary prompts.
