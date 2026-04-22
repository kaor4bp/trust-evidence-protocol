# TEP 0.4 JSON Schemas

These schemas are the exported public contract for the 0.4 MCP-first runtime.
The matching Python dataclass helpers live in
`plugins/trust-evidence-protocol/tep_runtime/contracts/`.

The schemas intentionally define stable outer payload shape first. Domain
validators still enforce semantic rules such as provenance reachability,
REASON progression, chain-ledger hash/seal/PoW verification, and GRANT/RUN
authorization.
