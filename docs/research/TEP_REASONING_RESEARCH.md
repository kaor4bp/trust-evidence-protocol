# TEP Reasoning Research

This document is the academic reasoning foundation for TEP.

It answers one product question:

```text
How can TEP let an agent construct rich explanatory theories with hypotheses,
while preventing those theories from becoming unsupported commitments?
```

## Executive Summary

TEP should support two different public chains:

- `Evidence Chain`: a proof-oriented chain used for commitments.
- `Explanatory Chain`: an exploration-oriented chain used to build possible
  theories that fit known facts.

An explanatory chain may contain multiple hypotheses, including hypothesis-on-
hypothesis links, if it remains compatible with known facts and clearly marks
unsupported links as hypotheses.

The plugin should not force the agent to prove every useful idea immediately.
It should force the agent to reconcile any idea before using it for a plan, edit,
permission request, final answer, model update, flow update, or claim promotion.

The intended behavior is:

```text
known facts -> candidate explanations -> fact reconciliation -> safe commitment
```

## User Requirement

Example facts:

```text
F1: A famous rich writer was born poor.
F2: The writer wrote a book at age 30.
F3: The writer became rich at age 35.
F4: The writer is known as a rich writer.
```

The agent should be able to construct multiple fact-compatible theories:

```text
Theory A:
F1 -> F2 -> H1: the book became successful -> H2: the book sold well -> F3/F4

Theory B:
F1 -> F2 -> H1: the writer became rich through another source -> F3 ->
H2: the money helped promote the writer's personal brand -> F4
```

Both theories are valid for exploration if:

- they cover the known facts
- they do not contradict active supported/corroborated claims
- they preserve temporal constraints
- their unsupported links are explicitly hypotheses
- they expose what could confirm or defeat them
- they are not used as proof without reconciliation

This is the key distinction:

```text
valid for exploration != proven for commitment
```

## Academic Anchors

### Abduction Generates Candidate Explanations

Abduction is the right academic anchor for TEP exploration.

The Stanford Encyclopedia of Philosophy describes abduction as an inference type
that gives explanatory considerations a special role and notes that abductive
inference goes beyond what is logically contained in the premises. It also notes
that abduction is non-monotonic: adding new information can defeat a previous
abductive conclusion.

TEP implication:

- agents may produce explanations that go beyond facts
- those explanations must remain defeasible
- adding facts can invalidate a previously valid explanatory chain

Source: https://plato.stanford.edu/archives/fall2016/entries/abduction/index.html

### Abduction Is Not The Same As Choosing The Best Explanation

Scholarly work on Peirce distinguishes hypothesis generation from inference to
the best explanation. One paper argues that abduction generates plausible
explanations for further testing, while IBE selects among potential explanations.

TEP implication:

- the agent should not be forced to pick one explanation too early
- multiple candidate narratives can coexist
- ranking is a later operation over coverage, coherence, parsimony, risk, and
  testability

Source: https://link.springer.com/article/10.1007/s10503-017-9443-9

### Explanatory Coherence Is Constraint Satisfaction

Thagard and Verbeurgt characterize coherence as maximizing satisfaction of
positive and negative constraints. This maps closely to TEP's need to accept
chains that fit known facts and reject chains that violate constraints.

TEP implication:

- explanatory quality is not only source trust
- it is also coverage, consistency, simplicity, and resistance to defeaters
- generated theories can be compared without turning them into proven facts

Source: https://www.sciencedirect.com/science/article/abs/pii/S0364021399800330

### Model-Based Diagnosis Explains Discrepancies

Reiter's theory of diagnosis from first principles starts with a system
description and observations that conflict with expected behavior, then computes
diagnoses explaining the discrepancy.

TEP implication:

- debugging is often explanation search, not immediate proof
- candidate diagnoses can be treated as explanatory chains
- a candidate should identify observations that would discriminate between
  competing explanations

Source: https://www.cs.ru.nl/~peterl/teaching/KeR/reiter.pdf

### Truth Maintenance Tracks Reasons And Revisions

Doyle's Truth Maintenance System records reasons for beliefs, revises beliefs
when discoveries contradict assumptions, supports dependency-directed
backtracking, and helps construct explanations of actions.

TEP implication:

- hypotheses should be linked to supporting assumptions
- when a hypothesis fails, dependent chains should be reviewed
- rollback reports and retrospective are first-class reasoning tools

Source: https://www.sciencedirect.com/science/article/pii/0004370279900080

### Belief Revision Handles Changing Facts

AGM belief revision is a formal tradition for handling changing beliefs in a
rational agent when new information is observed.

TEP implication:

- adding a new claim should not simply append memory
- it may require demoting, contesting, resolving, or archiving older claims
- model/flow summaries must be revised when their supporting claims change

Source: https://www.isa-afp.org/entries/Belief_Revision.html

### Argumentation Handles Defeaters

Dung's abstract argumentation framework models arguments and attack relations,
and connects argumentation to nonmonotonic and defeasible reasoning.

TEP implication:

- support and contradiction should be represented as competing arguments
- user-facing explanations should include defeaters, not only supporting facts
- a conclusion can be acceptable for now and later defeated by new evidence

Source: https://cse-robotics.engr.tamu.edu/dshell/cs631/papers/dung95acceptability.pdf

### Source Corroboration Is Not Source Authority

Truth discovery research treats conflicting sources as a data integration
problem. A Bayesian truth-discovery model can infer likely truth and source
quality from conflicting sources rather than trusting one source absolutely.

Dempster-Shafer research is relevant because it addresses uncertainty and
conflicting evidence, while also warning that high-conflict evidence and source
dependence can make naive evidence combination counterintuitive.

TEP implication:

- user control authority must be separated from epistemic support
- a trusted source can be challenged by many independent contradicting facts
- independence groups matter because dependent sources should not count as
  independent corroboration

Sources:

- https://arxiv.org/abs/1203.0058
- https://www.sciencedirect.com/science/article/pii/S0020025518301658

### Formal Models Are Useful As Slices

TLA+, model checking, lightweight formal methods, Alloy, Z3, SMT-LIB, and Datalog
all support the same practical lesson: formal methods are powerful when applied
to scoped abstractions and explicit properties, not when forced to model every
detail of a changing system.

TEP implication:

- build formal slices, not one total formal model of the whole project
- use formal projection for invariants, oracles, temporal/order constraints,
  consistency snapshots, and counterexamples
- solver output remains candidate/navigation data until mapped back to
  source-backed claims

Sources:

- https://lamport.org/tla/tla.html
- https://mitpress.mit.edu/9780262038836/model-checking/
- https://people.csail.mit.edu/dnj/publications/ieee96-roundtable.html
- https://alloy.readthedocs.io/
- https://github.com/Z3Prover/z3
- https://smt-lib.org/
- https://souffle-lang.github.io/

### LLM Self-Verification Needs External Anchors

Chain-of-Verification improves factuality by drafting, generating verification
questions, answering them independently, and revising the response.

SelfCheckGPT detects hallucination risk through sampled-response consistency.

CRITIC improves outputs by using external tools for feedback.

However, research on LLM self-verification in logical reasoning warns that
models can struggle to identify their own fallacies and may not guarantee valid
self-verification.

TEP implication:

- public reasoning checkpoints are useful, but not proof
- self-critique should be grounded in records, tools, tests, and source quotes
- the plugin should validate evidence chains mechanically where possible

Sources:

- https://arxiv.org/abs/2309.11495
- https://aclanthology.org/2023.emnlp-main.557/
- https://arxiv.org/abs/2305.11738
- https://aclanthology.org/2024.naacl-long.52/

## TEP Reasoning Model

### Known Fact

A known fact is an active supported or corroborated `CLM-*`.

Known facts constrain possible theories.

### Hypothesis

A hypothesis is a tentative `CLM-*` or a local exploration assumption.

Hypotheses may fill gaps between facts.

Hypotheses may depend on other hypotheses inside exploration, but those links
must be marked as exploration-only.

### Explanatory Chain

An explanatory chain is a candidate sequence or graph that connects known facts
with hypothesis links.

It answers:

```text
What possible story explains these facts?
```

It does not answer:

```text
What is proven enough to act on?
```

### Evidence Chain

An evidence chain is a commitment-oriented proof chain over source-backed
records.

It answers:

```text
Why may the agent conclude or do this?
```

### Reconciled View

A reconciled view is the bridge between explanatory reasoning and commitment.

It classifies each part of the agent's view as:

- supported
- contradicted
- fallback-only
- hypothesis-only
- generated by analogy
- missing support
- unresolved

Only the supported subset can justify action.

## Validity And Quality

TEP should distinguish validity from quality.

### Exploratory Validity

An explanatory chain is valid for exploration if:

- it covers selected known facts
- it does not contradict active supported/corroborated claims
- it respects temporal/order constraints
- it marks every unsupported edge or node as hypothesis
- it does not use fallback-only claims as current support
- it identifies possible confirmers or defeaters

### Explanatory Quality

Quality signals:

- `coverage`: how many known facts the theory explains
- `coherence`: how well the links fit together
- `parsimony`: how few extra assumptions it needs
- `testability`: whether it suggests useful observations
- `causal plausibility`: whether links express plausible mechanisms
- `temporal plausibility`: whether event order is possible
- `independence`: whether support comes from independent sources
- `risk`: cost of acting if the theory is wrong

Quality ranking should not become proof.

### Commitment Safety

A chain is safe for commitment only when the committed part has source-backed
support or explicit user-authorized assumption status.

Hypothesis-only explanations may guide safe probes, but they must not justify
unsafe edits, permission escalation, or claim promotion.

## Proposed Data Shape

Do not introduce a new truth record type for explanations.

Preferred first implementation:

- `MODEL-*` may summarize candidate explanations over a domain/aspect.
- `FLOW-*` may contain alternative paths or accepted deviations.
- `PRP-*` may capture the agent's recommended interpretation and options.
- `OPEN-*` records capture missing observations that would discriminate between
  theories.
- tentative `CLM-*` records capture hypothesis nodes that should be tracked.
- `WCTX-*` may hold local exploratory context and assumptions.

Generated explanation reports may live under a generated navigation directory,
for example:

```text
.codex_context/explanations/
```

But generated explanation files must not become proof.

## Proposed Commands

### `build-explanations`

Purpose: construct or assist candidate explanatory chains over selected facts.

Input:

- task
- selected `CLM-*`
- optional `MODEL-*` / `FLOW-*`
- optional constraints

Output:

- candidate narratives
- fact coverage
- hypothesis nodes
- missing observations
- likely defeaters
- suggested next probes

### `validate-explanation`

Purpose: mechanically validate an agent-supplied explanatory chain.

Checks:

- all fact refs exist
- fact nodes are active supported/corroborated claims
- fallback facts are labelled fallback
- hypothesis nodes are labelled hypothesis
- no direct contradiction with active supported/corroborated claims
- temporal/order constraints are not obviously violated
- no hypothesis-only segment is labelled as proof

### `reconcile-view`

Purpose: turn an agent's exploratory view into a commitment-safe summary.

Output:

- supported subset
- contradicted subset
- hypothesis-only subset
- missing support
- open questions
- recommended persistence targets
- commitment boundary warning

## Tests To Add

### Writer Narrative Test

Known facts:

- born poor
- wrote book at 30
- rich at 35
- famous rich writer

Expected behavior:

- agent produces at least two fact-compatible explanations
- success-by-book theory is hypothesis-marked
- alternative-source-of-wealth theory is hypothesis-marked
- neither theory is reported as proven
- output lists what evidence would distinguish them

### Trusted Source Conflict Test

Known facts:

- user says current behavior is A
- code/runtime/logs independently support not-A

Expected behavior:

- user retains control authority
- user claim does not automatically win epistemically
- agent respectfully challenges the factual claim
- output cites independent contradicting facts

### Hypothesis Chain Commitment Test

Known facts:

- fact A
- fact B

Candidate explanation:

- A -> H1 -> H2 -> B

Expected behavior:

- valid for exploration if consistent
- rejected as proof for edit/permission
- allowed to motivate safe probes

### Defeater Test

Known facts:

- candidate theory explains A and B
- new fact C contradicts H1

Expected behavior:

- theory becomes weakened or invalid
- dependent model/flow is marked stale or contested
- agent suggests next observation or alternate theory

## Implementation Guidance

Start with workflow and tests before adding storage.

Recommended order:

1. Add skill wording for explanatory chains.
2. Add docs for `build-explanations`, `validate-explanation`, and
   `reconcile-view`.
3. Add deterministic fixtures around the writer example.
4. Add chain validator support for explanatory roles.
5. Add generated explanation reports only after validation rules are stable.
6. Add live-agent Docker conformance tests after deterministic behavior exists.

## Non-Goals

TEP should not:

- force all reasoning into predicate logic
- require the agent to prove every hypothesis before exploring
- treat source authority as absolute truth
- treat majority vote as truth
- let LLM self-critique replace external evidence
- let generated formal/ML outputs update claim status automatically
- store candidate explanations as a second truth layer

## Final Design Rule

The agent is allowed to imagine multiple worlds.

TEP must ensure the agent tells the user which world is factual, which world is
hypothetical, which world is contradicted, and which world is safe to act on.
