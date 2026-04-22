# TEP 0.4 JSON Schemas

These schemas are the exported public contract for the 0.4 MCP-first runtime.
The matching Python dataclass helpers live in
`plugins/trust-evidence-protocol/tep_runtime/contracts/`.

The schemas intentionally define stable outer payload shape first. Domain
validators still enforce semantic rules such as provenance reachability,
agent-owned WCTX signatures, REASON progression, chain-ledger hash/seal/PoW
verification, and GRANT/RUN authorization.

`AGENT-*` identity records expose only local-agent key metadata and fingerprints.
Private key material is runtime-private. `WCTX-*` records are owner-bound with
`ownership_mode=owner-only`; other agents must fork/adopt through the runtime
instead of using someone else's WCTX as current focus.
