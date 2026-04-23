# TEP 0.4 JSON Schemas

These schemas are the exported public contract for the 0.4 MCP-first runtime.
The matching Python dataclass helpers live in
`plugins/trust-evidence-protocol/tep_runtime/contracts/`.

The schemas intentionally define stable outer payload shape first. Domain
validators still enforce semantic rules such as provenance reachability,
agent-owned WCTX signatures, REASON progression, chain-ledger hash/seal/PoW
verification, and GRANT/RUN authorization.

Canonical records created in 0.4 use `contract_version` for the public runtime
contract and `record_version` for the concrete JSON record shape. Records with
strict 0.4 ownership or navigation contracts, including `AGENT-*`, `WCTX-*`,
and `MAP-*`, require both fields. Legacy records without `record_version` stay
readable until an explicit migration rewrites or wraps them.

`AGENT-*` identity records expose only local-agent key metadata and fingerprints.
Private key material is runtime-private. `WCTX-*` records are owner-bound with
`ownership_mode=owner-only`; other agents must fork/adopt through the runtime
instead of using someone else's WCTX as current focus.
