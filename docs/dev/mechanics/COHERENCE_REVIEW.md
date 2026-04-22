# Coherence Review

This review evaluates whether the mechanics form one system or contradict each
other.

## Coherent Cross-Mechanic Invariants

### Navigation Is Not Proof

Consistent across source-of-truth, lookup, CIX, backend, map, and telemetry
mechanics.

Required implementation pressure:

- generated/backend ids rejected in proof chains
- lookup returns route, not proof
- map graph marks `not_proof`
- CIX omitted from proof nodes unless converted through support capture

### Reasoning Must Progress

Consistent across lookup, evidence chains, reason ledger, and task preflight.

Required implementation pressure:

- lookup proposes new chain nodes by default
- `REASON-*` direct same-mode duplicate chain is rejected
- planning/final preflight requires valid reason
- fallback is fork/new hypothesis/open question, not old-chain reuse

Important limit: this invariant does not mean TEP can prove the agent's
reasoning is adequate. It only proves that the agent is progressing through a
valid, inspectable graph. The expected benefit is cognitive scaffolding: the
agent has to form and update a local working context from records instead of
acting from unstated impressions.

### Agent Freedom With Mechanical Boundaries

Consistent across hypotheses, curiosity, proposals, and reason ledger.

Agents can hypothesize and criticize, but proof/action/final paths validate
ids, quotes, task focus, and mode.

### Workspace Isolation

Consistent across focus, task, reason/grant, code backend, and curator.

Workspace must be explicit. Curator and backend broad search require explicit
scope rather than inheriting global current focus.

## Logical Gaps Closed By Functional Spec

`docs/dev/TEP_0_4_0_FUNCTIONAL_SPEC.md` is normative for the decisions below.
This section keeps the original gap framing as a traceability checklist.

### 1. Runtime Claim Authority

Decision: functional spec defines authority classes and ranking constraints.

Required implementation:

- implement lookup scoring policy for runtime vs theory/user-confirmed claims
- implement MODEL/FLOW authority checker that distinguishes runtime corroboration from
  theory confirmation
- warn/migrate old runtime CLM without RUN

### 2. `SRC-*` Provenance Graph-v2 Migration

Decision: new `SRC-*` without provenance surface is invalid; legacy records are
warnings until migrated.

Required implementation:

- legacy compatibility flag or migration marker
- validator severity levels: error for new records, warning for legacy
- one-shot migration plan

### 3. Hypothesis Compatibility

Decision: 0.4.0 uses conservative structural compatibility, not full semantic
proof.

Required implementation:

- predicate/logic projection for supported facts and hypotheses
- conflict candidate detection before accepting durable hypothesis
- examples where multiple hypotheses are valid
- explicit rejection of hypothesis-on-hypothesis in proof paths

### 4. Planning Gate May Overconstrain Early Exploration

Decision: planning preflight may block, but the block must route to
`lookup -> reason-step -> preflight`.

Required implementation:

- `next-step` route should explain "lookup first, then reason-step"
- hook messages should be short and actionable
- tests for first-planning blocked -> lookup -> reason-step -> planning pass

### 5. Curator Pool Boundary

Decision: curator receives a bounded pool with purpose, max size, and item
reasons.

Required implementation:

- pool scoring
- max size / paging
- allowed curator output types
- user-question workflow
- duplicate/contradiction report format

### 6. Backend Scope

Decision: project scope is default; workspace is explicit; global is rare and
never implicit.

Required implementation:

- backend status per scope
- project default, workspace optional, global rare
- explicit route when workspace search is needed
- no repo pollution from backend markers unless explicitly allowed

### 7. Historical Context Ranking

Decision: cleanup is future work; 0.4.0 implements ranking and regression route.

Required implementation:

- lookup fallback ranking for historical/resolved claims
- "regression suspicion" route that compares old bug with new symptoms
- explicit stale/resolved labels in compact lookup output
- cleanup/archive policy can stay future work

### 8. Token-Pressure Wins Need Measurement

Decision: telemetry counters and smoke-test targets define minimum measurement.

Required implementation:

- telemetry before/after route adoption
- raw-read count targets
- repeated hot-record reduction targets
- live-agent token usage sample

## Potential Contradictions

### Guideline Creation vs User Confirmation

Agents may propose guidelines for consistency, but active guideline use requires
user confirmation. This is coherent if proposed guidelines are PRP/draft GLD,
not active GLD.

Decision: keep active GLD user-confirmed; allow draft/proposal records.

### Curiosity vs No Raw Browsing

Curiosity wants exploration, but raw browsing is discouraged. Coherent route:
curiosity map and lookup produce bounded probes; raw records are for targeted
forensics or plugin development.

Decision: curiosity should produce pool/probe commands, not file paths to raw
claim JSON.

### Weak PoW vs Security Claims

Weak PoW makes bulk rewriting annoying but is not security. Coherent only if
docs avoid cryptographic-safety claims.

Decision: describe as tamper friction/detection, not access control.

## Recommended 0.4.0 Implementation Order

1. Stabilize source-of-truth/provenance validators and legacy warnings.
2. Stabilize focus and task gates.
3. Stabilize lookup chain extension and reason progression.
4. Stabilize final/autonomous/grant/run gates.
5. Stabilize MODEL/FLOW authority checks.
6. Stabilize backend status honesty.
7. Stabilize map/curiosity compact views.
8. Add curator pool mechanics.
9. Stabilize historical/resolved lookup ranking.
10. Run deterministic and then explicit live-agent smoke tests.
