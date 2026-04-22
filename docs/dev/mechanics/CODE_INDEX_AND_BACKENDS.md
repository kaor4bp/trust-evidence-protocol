# Code Index And Backends

## Responsibility

This mechanic lets agents navigate code without confusing code navigation with
proof.

## CIX

`CIX-*` describes code targets such as files, directories, functions, classes,
modules, and Markdown sections.

CIX may hold target path, project/workspace refs, language, parser metadata,
imports/symbols/features, file hash/freshness, guideline refs, claim/source
refs, proposal refs, agent annotations, and smells.

CIX is navigation and impact data. It does not prove CLM truth.

## Parsers

AST/parser support should be modular per language. Markdown should be parsed for
structural metadata because docs are part of the system.

## Backends

External backends such as CocoIndex are behind TEP. Agents should use TEP code
tools, not backend tools directly in normal work.

Backend status must distinguish installed, configured, selected, indexed,
search-ready, and scope. Default search should be project-scoped. Workspace
search is useful for related services and cross-service clients. Broader levels
should be explicit, not silent.

## API Requirements

- `code-search` should proxy selected backends and enrich hits with CIX when
  possible.
- `backend-status` must not report green when semantic search cannot run.
- Backend hits should be reviewable and linkable into CIX/CLM/MODEL/FLOW
  through feedback tools.
- Backend storage should live under TEP-owned storage unless a backend requires
  a safe project marker; this must be explicit.

## Coherence Notes

- CIX links can help augment evidence chains but cannot become proof nodes.
- Guidelines can link to CIX for applicability.
- Code smells are annotations until promoted to claim/proposal/guideline.

## Known Gaps

- CIX vs backend-index boundary is still fragile; avoid introducing BIX until
  the distinction is obvious.
- Workspace/global backend scope needs cache invalidation and project admission
  rules.

