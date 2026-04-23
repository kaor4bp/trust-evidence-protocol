# TEP 0.4.9 Release Notes

TEP 0.4.9 hardens per-agent identity isolation and narrows reason-ledger
validation to the current agent.

## Changed

- Replaced the old token-first owner model with `agent_private_key` /
  `TEP_AGENT_PRIVATE_KEY` and `sha256:` key fingerprints.
- Bound `AGENT-*` resolution to current private-key fingerprint, with optional
  `CODEX_THREAD_ID` thread binding as an isolation guard.
- Stopped storing private key material in runtime state. Runtime-private
  bindings keep only `agent_identity_ref` and `key_fingerprint`.
- Made reason-ledger validation current-agent-only by default. Foreign
  `runtime/reasoning/agents/*/reasons.jsonl` files no longer block hydration,
  `load_clean_context`, or normal preflight for the active agent.
- Removed the separate `seal.json` runtime artifact. Ledger integrity remains
  inside append-only `reasons.jsonl` entries through `entry_hash`, `seal`,
  `ledger_hash`, and PoW.
- Renamed MCP owner-bound input from `agent_token` to `agent_private_key` and
  updated skill/reference docs accordingly.

## Rationale

The old model mixed two concerns:

- who the current agent is
- whether some other agent left a malformed runtime file behind

That made isolation too weak in one place and too strict in another. The new
shape is narrower:

- owner-bound identity comes from the current agent-held key
- thread binding is only an isolation guard
- validation of owner-bound ledgers applies only to the current agent unless an
  explicit audit path asks for broader inspection
