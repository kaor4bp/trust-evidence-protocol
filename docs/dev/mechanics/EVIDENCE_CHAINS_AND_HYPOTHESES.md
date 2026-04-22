# Evidence Chains And Hypotheses

## Responsibility

This mechanic defines how agents expose reasoning in a compact, public,
mechanically checkable form.

## Chain Shape

Evidence chains use ids and quotes, not hidden chain-of-thought.

Example:

```text
fact: CLM-* "quote"
-> observation: CLM-* runtime observation "quote"
-> provenance: SRC/RUN/INP/ART links surfaced by augmentation
-> decision
```

Allowed roles:

- fact
- observation
- hypothesis
- exploration_context
- permission
- requested_permission
- restriction
- guideline
- proposal
- task
- working_context
- project
- model
- flow
- open_question

## Validation Rules

- Every proof chain needs at least one supported/corroborated fact.
- Quotes must match the target record or its source quotes.
- Navigation ids cannot be proof.
- Control records cannot support truth.
- Task/project/WCTX/context cannot support truth.
- Hypothesis cannot support another truth node as proof.
- Proof modes reject hypothesis and exploration context.
- Planning/proposal/curiosity/debugging may include uncertainty if it is
  explicitly marked.

## Hypothesis Semantics

Hypothesis is a claim lifecycle stage:

```text
CLM-* status=tentative
```

The hypothesis index is runtime/index support, not a second truth store.

Durable hypotheses can guide planning/proposal/debugging when they fit known
facts. Exploration hypotheses can guide lookup and safe probes, but cannot be
proof.

Multiple hypotheses may coexist if each is compatible with known facts. The
system should encourage agents to test, ask, or record observations that promote
or close them.

## API Requirements

- `augment-chain` should add missing source quotes and provenance links when it
  can do so mechanically.
- `validate-evidence-chain` checks graph correctness.
- `validate-decision` applies mode-specific proof policy.
- Hypothesis nodes must reference tentative CLM records and active hypothesis
  entries.
- The API should make it cheaper to record a hypothesis than to silently rely on
  a guess.

## Coherence Notes

- REASON ledger stores a validated chain snapshot.
- Lookup extension proposes candidate new nodes.
- MODEL/FLOW promotion rejects tentative hypothesis support.

## Known Gaps

- The boundary between `hypothesis` and `exploration_context` needs more
  examples in tests.
- There is no complete formal solver for hypothesis compatibility yet; current
  checks are structural and source-backed.
- Runtime staleness hypotheses need stricter lifecycle guidance.

