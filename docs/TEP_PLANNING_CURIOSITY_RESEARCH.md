# TEP Planning And Curiosity Research

This document is the academic foundation for two TEP behaviors:

- letting agents plan realistically under bounded time and context
- motivating agents to turn useful hypotheses into facts through questions,
  inspection, tests, or other safe observations

It extends `docs/TEP_REASONING_RESEARCH.md`.

## Executive Summary

Agent "laziness" is often a bounded-rationality failure, not only a motivation
failure.

When a task is too large for the current context, time budget, or confidence
level, the agent may try to cover everything superficially. TEP should instead
make partial progress legitimate if the agent:

- states the chosen scope
- records what was deferred
- explains why it was deferred
- preserves enough context for return
- defines triggers or success criteria for resuming
- does not present partial coverage as full completion

Curiosity is the complementary force.

When the agent creates a useful hypothesis, TEP should push it to ask:

```text
What cheap, safe observation would most reduce uncertainty here?
```

The agent should not be forced to verify every hypothesis immediately, but
high-value hypotheses should create inquiry pressure. A hypothesis that becomes a
fact enables deeper and longer reasoning chains.

## User Requirement

The user wants two behaviors:

1. **Legitimate deferral instead of fake completion.**
   If the task is large, the agent should plan work, finish a coherent slice, and
   persist deferred work so a future agent can resume.

2. **Curiosity pressure instead of passive hypothesis hoarding.**
   If the agent builds hypotheses, it should be motivated to verify, falsify, or
   ask about the most valuable ones when doing so is safe and useful.

TEP should therefore reward:

- explicit scope boundaries
- useful partial deliverables
- durable plans/debt/open questions
- safe probes
- user questions that unlock important uncertainty
- conversion of tentative claims into supported/corroborated claims

TEP should discourage:

- pretending the whole task is done
- hiding skipped work in prose
- accumulating hypotheses without next observations
- interrupting the user for low-value questions
- running risky probes just to satisfy curiosity

## Academic Anchors

### Bounded Rationality And Satisficing

Bounded rationality replaces perfect rationality with behavior compatible with
limited information, limited computation, and limited time. Herbert Simon's
tradition also gives a name to "good enough under constraints": satisficing.

TEP implication:

- partial progress is not a defect if constraints are explicit
- "good enough for this slice" must be separated from "complete for the whole
  task"
- the agent should optimize under context/time/risk bounds rather than pretend
  bounds do not exist

Source: https://plato.stanford.edu/entries/bounded-rationality/

### Rational Metareasoning

Russell and Wefald frame computations themselves as actions selected by expected
utility under resource bounds. The cost of thinking, searching, testing, or
asking is part of the decision.

TEP implication:

- planning, searching, testing, and asking the user should be treated as
  resource-consuming actions
- the agent should choose the next reasoning/probing action by expected value,
  not by habit
- stopping to deliver a partial result can be rational if additional reasoning
  has low expected value or high opportunity cost

Source: https://iiif.library.cmu.edu/file/Newell_box00014_fld01011_doc0001/Newell_box00014_fld01011_doc0001.pdf

### Anytime Algorithms And Operational Rationality

Anytime computation offers a quality/time tradeoff: an interrupted process can
still return a useful result, and quality improves with more time. Operational
rationality separates output quality from utility and uses runtime monitoring to
decide when more computation is worth it.

TEP implication:

- large agent tasks should behave more like anytime work than all-or-nothing work
- the agent should expose a "current best result" plus known quality/coverage
- deferred work should be the continuation path for improving quality
- plans should include coverage and confidence, not just steps

Sources:

- https://www2.eecs.berkeley.edu/Pubs/TechRpts/1993/CSD-93-743.pdf
- https://www.ijcai.org/Proceedings/2018/208

### Least-Commitment Planning

Partial-order planning delays unnecessary ordering commitments and keeps plans
flexible until constraints force a choice.

TEP implication:

- the agent should not prematurely commit to one full task decomposition when
  several paths remain plausible
- deferral can be a correct planning move, not a failure
- plans should preserve open conditions and unresolved choices explicitly

Source: https://artint.info/2e/html2e/ArtInt2e.Ch6.S5.html

### LLM Agent Planning

Recent LLM-agent planning literature classifies planning improvements into task
decomposition, plan selection, external modules, reflection, and memory.

TEP implication:

- persistent plans and working contexts are part of agent reliability
- reflection without durable records is weak
- memory must include deferred work and not only final conclusions

Source: https://arxiv.org/abs/2402.02716

### Active Learning

Active learning is built on the idea that a learner can perform better with fewer
labels when it chooses informative queries. Settles' survey lists uncertainty
sampling, query-by-committee, expected model change, variance reduction,
estimated error reduction, density-weighted methods, and cost-sensitive active
learning.

TEP implication:

- user questions and runtime probes should be selected by expected usefulness
- disagreement between candidate explanations is a strong signal for what to ask
  or test next
- cost matters: not every informative question is worth asking now

Source: https://burrsettles.com/pub/settles.activelearning_20090109.pdf

### Value Of Information

Value-of-information theory asks how much information is worth before making a
decision. The expected value depends on uncertainty, decision stakes, diagnostic
power, and information cost.

TEP implication:

- curiosity should be ranked, not random
- hypotheses that affect high-stakes actions deserve stronger inquiry pressure
- cheap observations that unlock many downstream claims should be preferred

Source: https://www.semanticscholar.org/paper/Information-Value-Theory-Howard/a7b3c2a88ca459d50010a33db8c2f113f1323e0c

### Curiosity And Intrinsic Motivation

Curiosity-driven learning research treats exploration as a way to improve
predictive power, learning progress, or information gain. Oudeyer/Kaplan-style
learning progress avoids pure novelty chasing: the system seeks regions where it
can make progress, not random noise.

TEP implication:

- curiosity should target learnable uncertainty, not arbitrary novelty
- useful hypotheses should carry confirmers and defeaters
- the agent should prefer safe probes that improve the model of the task

Sources:

- https://www.frontiersin.org/journals/neuroscience/articles/10.3389/neuro.01.1.1.017.2007/full
- https://pubmed.ncbi.nlm.nih.gov/22791268/
- https://people.idsia.ch/~juergen/ieeecreative.pdf

### Information Foraging

Information foraging models search as a cost/benefit process driven by
"information scent": cues about whether a path is likely to yield useful
information.

TEP implication:

- context lookup should expose strong information scent: relevant records,
  linked refs, focus paths, open questions, and likely next probes
- agents should abandon low-scent search paths and persist why
- generated indexes should reduce search cost and improve scent, not become proof

Sources:

- https://devaka.info/wp-content/uploads/2008/11/UIR-1995-07-Pirolli-CHI95-Foraging.pdf
- https://en.wikipedia.org/wiki/Information_foraging

## TEP Planning Model

### Slice Planning

For large tasks, the agent should choose a coherent slice.

A slice should state:

- goal
- included scope
- excluded/deferred scope
- why this slice is highest value now
- success criteria
- stop conditions
- expected follow-up

### Normal Deferral

Deferral is valid when:

- the current slice is coherent and useful
- deferred items are recorded in `PLN-*`, `DEBT-*`, `OPEN-*`, or `WCTX-*`
- the agent gives resume conditions
- the agent does not claim total completion

Deferral is invalid when:

- it hides unhandled required work
- it avoids a critical risk without saying so
- it leaves no durable path to resume
- it is used to avoid verification that is cheap and decisive

### Anytime Deliverable

An anytime deliverable is a useful partial result with explicit quality metadata.

TEP should encourage the agent to report:

- coverage
- confidence
- known gaps
- deferred items
- next best improvement
- expected value of continuing

This makes "I did the most valuable slice and left the rest resumable" acceptable,
while making "I touched everything shallowly" visible as poor work.

## TEP Curiosity Model

### Inquiry Pressure

Every meaningful hypothesis should have an inquiry profile:

- what would confirm it
- what would weaken or falsify it
- cheapest safe observation
- whether the user is the best oracle
- whether code/runtime/docs/tests can answer it
- what downstream chain becomes possible if confirmed

### Curiosity Score

Do not implement this as a rigid numeric score first, but the conceptual scoring
should be:

```text
curiosity_value =
  uncertainty
  * impact_on_current_task
  * downstream_chain_value
  * testability
  * source_independence_gain
  - observation_cost
  - interruption_cost
  - safety_risk
```

The agent should prioritize hypotheses with high curiosity value.

### Inquiry Actions

Possible actions:

- ask the user a focused question
- inspect a source
- run a safe test
- search `.codex_context`
- build or refresh code index
- record an `OPEN-*`
- record a tentative `CLM-*`
- create a small plan/debt item

### Attention-Driven Curiosity

Curiosity should not only target explicit hypotheses.

When topic or attention indexes exist, the agent should also be curious about
attention anomalies:

- a semantically relevant cluster is rarely tapped
- a cluster used to be active but its activity has decayed
- a high-impact record is cold because nobody has rechecked it recently
- a reasoning chain crosses from one cluster into another
- a cluster bridge appears repeatedly without a `MODEL-*` or `FLOW-*` explaining
  the relationship

These anomalies should not force immediate work.
They should create candidates for safe inquiry:

- inspect one representative source
- ask why a cold zone matters if only the user can answer
- create an `OPEN-*` for unexplained cluster isolation
- create or update a `MODEL-*` / `FLOW-*` when a cross-cluster bridge is real
- create cleanup/debt if a hot zone is mostly stale or resolved records

The agent should avoid a rich-get-richer retrieval loop.
Hot records are useful because they show activity.
Cold relevant records are useful because they expose blind spots.

This rule is especially important for explanatory chains.
If a chain moves from one cluster to another, the agent should ask whether that
transition is:

- a real domain dependency
- a missing model/flow edge
- scope drift
- a coincidence from noisy topic modeling
- a useful abstraction boundary
- a sign that the current task is actually crossing into a different task

Cluster membership, coordinates, and tap activity are navigation signals only.
They can motivate curiosity, but they cannot prove a claim or justify a
commitment.

The runtime may intentionally present only a partial attention map when a full
map would overload the agent.
Partial views should expose frontier cues, not hide relevant proof:

- collapsed nearby clusters
- cold-but-near clusters
- expected but unestablished links
- bounded no-link observations
- cross-cluster bridge candidates
- suggested expansion points

This lets the plugin induce curiosity by controlling representation.
The agent sees not only where a link is known, but also where the current map has
a gap.

The gap semantics must be explicit:

- no visible link means "not shown or not established", not "no link exists"
- an expected missing link is an inquiry candidate, not a fact
- a tested absent link requires an explicit scope, corpus/time boundary, and
  method
- evidence of absence must be represented by a source-backed `CLM-*`, not by the
  mere absence of a generated edge

The agent should turn important gaps into `OPEN-*`, tentative `CLM-*`, or
model/flow review only when the gap affects the current task or a reusable
domain picture.

The runtime may also propose bounded stochastic curiosity probes.
These probes intentionally sample non-obvious claim pairs or short claim paths
across cluster boundaries when no fresh `tested_absent`, `established`, or
`rejected` link state already answers the question.

The agent's job is to classify the relation, not to force a connection.
Valid outcomes include:

- `established`: source-backed relation found
- `candidate`: plausible relation found but not enough support yet
- `tested_absent`: bounded search found no relation under recorded scope/method
- `rejected`: proposed relation was weakened by support
- `unknown`: probe was inconclusive or not worth deeper work

Curiosity probes should be budgeted.
They should combine deterministic high-value candidates with a small
reproducible random exploration fraction.
This creates useful surprise without turning every task into all-pairs
relationship search.

The agent should prefer the cheapest safe check first.
If the check matters, persist the result as `OPEN-*`, `CLM-*`, `MODEL-*`,
`FLOW-*`, or generated link-state metadata as appropriate.
If the check does not matter, leave it as navigation-only probe output.

### User Questions

The agent should ask the user when:

- the user is the only practical source
- the uncertainty blocks commitment
- the question is specific and answerable
- the answer would change the plan

The agent should not ask when:

- it can cheaply inspect code/runtime evidence
- the answer is low-impact
- the question is broad or lazy
- the question is a substitute for work the agent can safely do

## Proposed Workflow

Before large work:

1. Build a task slice.
2. Define success criteria.
3. Identify likely deferrals.
4. Identify high-value hypotheses.
5. Choose the first safe inquiry or implementation slice.

During work:

1. Convert discoveries into `SRC-*` / `CLM-*`.
2. Record important deferrals as `PLN-*`, `DEBT-*`, or `OPEN-*`.
3. Update `WCTX-*` when the local focus changes.
4. Promote or reject hypotheses when new observations arrive.

After work:

1. Report completed slice.
2. Report deferred work with record ids.
3. Report high-value remaining inquiries.
4. Report what would make the next slice more reliable.

## Proposed Commands

### `plan-slice`

Generate or validate a bounded work slice.

Output:

- selected scope
- deferred scope
- success criteria
- stop conditions
- relevant plans/debt/open questions
- required records to create/update

### `defer-work`

Create or update the appropriate `PLN-*`, `DEBT-*`, or `OPEN-*` record from a
deferral statement.

### `curiosity-candidates`

List high-value hypotheses/open questions worth verifying.

Inputs:

- task
- current model/flow
- active tentative claims
- open questions
- candidate explanations

Output:

- hypothesis/open question
- possible confirmers
- possible defeaters
- cheapest safe observation
- user-question candidate
- expected downstream value

### `promote-hypothesis`

Close or update a tentative claim when new support arrives.

This should not create a separate hypothesis truth store. It should update the
underlying `CLM-*` lifecycle/status and hypothesis index.

## Tests To Add

### Large Task Deferral Test

Input: a broad task with too much scope for one turn.

Expected:

- agent picks a coherent slice
- records deferred work
- does not claim full completion
- gives resume conditions

### Lazy Coverage Test

Input: task asks for review of many files.

Expected:

- agent refuses shallow all-file claims
- samples or slices explicitly
- records remaining review scope

### Curiosity Promotion Test

Input: a hypothesis blocks a deeper chain and can be checked cheaply.

Expected:

- agent chooses safe inspection/test over leaving hypothesis idle
- if confirmed, creates or promotes `CLM-*`
- if falsified, weakens/rejects dependent explanation

### User Oracle Test

Input: only the user can answer a key domain-intent question.

Expected:

- agent asks a focused question
- records the answer as `SRC-*`
- creates or updates `GLD-*`, `CLM-*`, `PRM-*`, or `RST-*` as appropriate

### Curiosity Restraint Test

Input: interesting but low-impact hypothesis.

Expected:

- agent records it as `OPEN-*` or WCTX concern
- does not interrupt or run costly probes

## Implementation Guidance

Do not add a new canonical "curiosity" record type yet.

Use existing records:

- `PLN-*` for intended future work
- `DEBT-*` for known liabilities
- `OPEN-*` for unresolved questions
- tentative `CLM-*` for hypotheses
- `WCTX-*` for local focus and assumptions
- `PRP-*` for constructive critique/options
- `MODEL-*` / `FLOW-*` when enough facts support an integrated picture

Generated reports may later expose:

```text
.codex_context/review/curiosity.md
.codex_context/review/deferred.md
```

These reports must be navigation only.

## Final Design Rule

The agent should not be punished for bounded partial progress.

It should be punished, mechanically and socially, for hiding the boundary of that
partial progress.

The agent should not be forced to verify every hypothesis.

It should be pushed to verify the hypotheses that are cheap, safe, high-impact,
and capable of turning shallow explanatory chains into deeper fact-backed models.
