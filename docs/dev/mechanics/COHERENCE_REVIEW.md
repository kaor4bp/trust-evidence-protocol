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

## Logical Gaps To Close

### 1. Runtime Claim Authority Is Under-Specified

We say runtime claims must reach `RUN-*` and should rank below theory/user
confirmation for MODEL/FLOW. The exact scoring formula is not specified.

Needed:

- lookup scoring policy for runtime vs theory/user-confirmed claims
- MODEL/FLOW authority checker that distinguishes runtime corroboration from
  theory confirmation
- migration behavior for old runtime CLM without RUN

### 2. `SRC-*` Provenance Graph-v2 Migration

We require `SRC-*` to link to INP/FILE/ART/RUN, but old contexts may contain
source-only records.

Needed:

- legacy compatibility flag or migration marker
- validator severity levels: error for new records, warning for legacy
- one-shot migration plan

### 3. Hypothesis Compatibility Is Mostly Structural

We require hypotheses to fit known facts, but current validation cannot fully
prove semantic compatibility.

Needed:

- predicate/logic projection for supported facts and hypotheses
- conflict candidate detection before accepting durable hypothesis
- examples where multiple hypotheses are valid
- explicit rejection of hypothesis-on-hypothesis in proof paths

### 4. Planning Gate May Overconstrain Early Exploration

`preflight-task --mode planning` requires current reason, while lookup/read is
allowed before reason. This is coherent only if agents understand that lookup is
the way to gather material before planning preflight.

Needed:

- `next-step` route should explain "lookup first, then reason-step"
- hook messages should be short and actionable
- tests for first-planning blocked -> lookup -> reason-step -> planning pass

### 5. Curator Pool Boundary Needs Shape

Curator should receive a pool and not browse everything, but pool construction
rules are not deep enough.

Needed:

- pool scoring
- max size / paging
- allowed curator output types
- user-question workflow
- duplicate/contradiction report format

### 6. Backend Scope Needs Operational Policy

Project/workspace/global backend index layers are conceptually accepted, but
cache invalidation, storage path, and selected scope rules need final policy.

Needed:

- backend status per scope
- project default, workspace optional, global rare
- explicit route when workspace search is needed
- no repo pollution from backend markers unless explicitly allowed

### 7. Historical Context Ranking Is Not Yet Precise

Cleanup is not a 0.4.0 development mechanic. Still, lookup must avoid drowning
agents in resolved or stale high-trust records while keeping them available for
regression analysis.

Needed:

- lookup fallback ranking for historical/resolved claims
- "regression suspicion" route that compares old bug with new symptoms
- explicit stale/resolved labels in compact lookup output
- cleanup/archive policy can stay future work

### 8. Token-Pressure Wins Need Measurement

The design says mechanical routes reduce token use, but acceptance lacks
measurement.

Needed:

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
