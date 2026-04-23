# TEP 0.4.0 Schema Migrations

Status: implementation rule for 0.4.0 record-shape migrations.

## Decision

Record schema migrations are separate from legacy context-root migration.

Legacy root migration answers:

```text
old context root -> ~/.tep_context
```

Schema migration answers:

```text
record JSON shape N -> record JSON shape N+1
```

Every schema change must have one dedicated module under:

```text
plugins/trust-evidence-protocol/tep_runtime/schema_migrations/
```

The module exports one `MIGRATION` object and is registered in
`schema_migrations/__init__.py`.

## Rules

- One schema change equals one migration module.
- Migration ids are stable and ordered by the registry.
- Dry-run must be read-only.
- Apply is two-phase:
  1. build the full plan
  2. run post-migration record validation
  3. write only if the whole plan has no unresolved items
- A migration may add structural defaults, rename fields, or remove obsolete
  fields.
- A migration must not silently change proof semantics. For example,
  `MAP-* map_is_proof=true` is a blocker because `MAP-*` is navigation only.
- `schema_version` must not be treated as `contract_version`. Canonical records
  use `contract_version` and `record_version`.

## First Migration

`20260423_map_record_v1` normalizes early `MAP-*` records:

- removes obsolete `schema_version`
- writes `contract_version="0.4"`
- writes `record_version=1`
- fills missing structural arrays and `scope_refs` keys
- refuses records that claim `map_is_proof=true`

## MCP Surface

Normal access is through MCP:

```text
schema_migration_plan   # read-only
schema_migration_apply  # mutating, writes only after clean validation
```

The tools return the standard 0.4 migration report shape. For schema
migrations, `source` and `target` are the same context root.

## CLI Surface

CLI is dev/migration/CI-only:

```text
context_cli.py schema-migration plan [--migration MIGRATION-ID] [--format json]
context_cli.py schema-migration apply [--migration MIGRATION-ID] [--format json]
```

`plan` exits non-zero when unresolved migration blockers exist. `apply` also
exits non-zero and writes nothing unless the full post-migration validation
passes.
