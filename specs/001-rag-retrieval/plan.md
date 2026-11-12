---
type: plan
spec_id: SPEC-002
title: rag-retrieval — Technical Plan
description: Architecture, module boundaries and contracts for indexing and retrieving LifeCenter knowledge base fragments via Postgres full-text search.
tags: [plan, rag-retrieval, SPEC-002]
status: verified
sources: [./spec.md]
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: 2026-11-11T00:00:00Z }
stale_after: null
---

# rag-retrieval — Plan

## Architecture

Clean separation between domain and infrastructure, so retrieval logic is testable without a
live database:

- **`kb/`** — Markdown source documents (not code). Edited by whoever maintains the knowledge
  base; each file has frontmatter `id`, `tipo`, `titulo`, `vigente_desde`, optional `ejemplo`.
- **Domain layer** (`app/domain/retrieval/`) — pure Python: the chunking rule (one fragment per
  `##` section, title carried on each fragment), "current version per `id`" selection logic
  (R5), the `Fragment` entity (text, title, source id, vigente_desde, ejemplo flag, relevance
  score). No Postgres, no FastAPI imports here. The current-version selection function takes
  "today" as an injectable parameter (a `date`), so tests can pin it instead of depending on the
  real clock; when not supplied, it defaults to the current date in the `Europe/Madrid` timezone
  (the clinic's timezone — relevant around UTC day boundaries).
- **Infrastructure layer** (`app/infra/kb_ingest.py`, `app/infra/kb_repository.py`) —
  reads `kb/*.md`, computes the `tsvector` using the custom `spanish_unaccent` text search
  configuration, writes/reads the Neon table; implements a `KnowledgeRepository` port defined in
  the domain layer.
- **API layer** (`app/api/retrieval.py`, FastAPI) — thin HTTP endpoint, internal to the
  application. It is **not** called by n8n directly: n8n only talks to a future conversation
  endpoint (out of this spec's scope), which in turn calls this retrieval endpoint as part of
  answer generation.

## Text search configuration: `spanish_unaccent`

`unaccent()` is not `IMMUTABLE`, so it cannot be called directly inside a generated column
expression or used safely as part of an index expression. Instead of calling the function at
query/index time, a dedicated text search configuration is created once as part of setup (not
per-row, not per-query):

```text
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE TEXT SEARCH CONFIGURATION spanish_unaccent ( COPY = spanish );
ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, spanish_stem;
```

`spanish_unaccent` is then used everywhere `spanish` was previously used — both for building
`search_vector` and for parsing incoming queries — so accent-folding happens as part of the
configuration's own token processing rather than as a separate non-immutable function call on
the indexed expression.

## Contracts

**Ingestion (internal, not HTTP):** a manually-run CLI command (R9) that walks `kb/`, chunks
every document, and performs a full, idempotent replace of the `kb_fragments` table contents —
including deleting rows for any `source_id` no longer present under `kb/`. Not triggered
automatically; the operator re-runs it after editing `kb/`.

**Retrieval HTTP endpoint** — internal only. It is consumed by the application's own
answer-generation flow; n8n never calls it directly, and no other external caller is expected.
The channel adapter (n8n) instead calls a future conversation endpoint (not part of this spec),
which calls this one internally:

```text
POST /internal/retrieval/query
Request:  { "query": "<texto del paciente>", "k": 5 }
Response: {
  "fragments": [
    {
      "text": "<fragmento>",
      "titulo": "<título del documento>",
      "source_id": "<id del documento>",
      "vigente_desde": "<YYYY-MM-DD>",
      "cita": "[ID | vigente desde dd/mm/aaaa]",
      "ejemplo": true | false,
      "score": <float, normalized ts_rank, 0-1>
    }
  ],
  "below_threshold": true | false
}
```

`k` defaults to 5 and is caller-configurable (R4). `cita` is the pre-formatted source citation
string (R6), so callers don't need to re-derive it from `source_id` + `vigente_desde`.

**Query construction (R4):** the user's raw text is never concatenated into a `tsquery` string.
It is passed as a bound parameter to `plainto_tsquery('spanish_unaccent', %s)`, which both
sanitizes it (stripping/escaping anything that isn't a word — safe against `:`, `!`, `&`, quotes,
etc.) and tokenizes it against the `spanish_unaccent` configuration. `plainto_tsquery` combines
its terms with `&` (AND) by default; since R4 requires OR semantics, the resulting `tsquery` is
converted by replacing its `&` operators with `|`, e.g.:

```text
SELECT replace(plainto_tsquery('spanish_unaccent', %s)::text, ' & ', ' | ')::tsquery
```

This keeps all sanitization/parsing inside `plainto_tsquery` (parameterized, so no raw user text
ever reaches the SQL string) while still achieving the OR ranking semantics of R4. The
`below_threshold: true` flag signals R8 (no sufficiently relevant fragment) — consumed by the
abstention feature (SPEC-001), not decided here.

**Current-version filtering in the query (R5):** the R5 filter is applied **inside the SQL
query, before `ORDER BY … LIMIT k`** — never in Python on the already-limited result. Filtering
after the `LIMIT` would let superseded or future-dated fragments take top-`k` slots and then be
discarded, so the caller would get fewer than `k` fragments even when enough current ones exist.
The query keeps only rows whose `vigente_desde` is the latest one `<= today` for their
`source_id` (e.g. a `vigente_desde = (SELECT max(vigente_desde) … WHERE vigente_desde <= %s)`
condition, or an equivalent CTE), with `today` passed as a bound parameter. The pure domain
function `select_current_versions(fragments, today)` (`app/domain/retrieval/versioning.py`)
remains the reference definition of this rule; the SQL must match it, and `today` comes from
the same injectable source (`madrid_today()` by default).

*Future improvement (not implemented):* the filter is a correlated subquery evaluated per
matching row (`max(vigente_desde)` per `source_id`). That is negligible at the current size of
`kb/` (a handful of documents), so no extra index is added for now. If `kb/` grows substantially,
add a B-tree index on `kb_fragments (source_id, vigente_desde)` in a new idempotent migration
(`app/infra/sql/002_…sql`) so that lookup is served by the index.

## Test environment

T4 through T7 and T10 need a live Postgres to run against. They run against a **separate Neon
branch dedicated to tests** — never against the `main` branch, so test runs (including
destructive ones, e.g. truncation between test cases) can never affect the data `main` serves.
That branch's connection string lives in `TEST_DATABASE_URL`, documented alongside `DATABASE_URL`
/ `DIRECT_URL` in `.env.example` (placeholder) and populated in the local `.env` once the branch
exists. Creating the branch itself is a setup task (see [tasks](./tasks.md) T0), not part of any
test's runtime behavior.

## Requirement → Component map

| Requirement | Component | Notes |
|-------------|-----------|-------|
| R1 | `kb/*.md` + frontmatter schema | Source files, validated by ingestion |
| R2 | Domain chunking rule (`app/domain/retrieval/`) | One fragment per `##` section; `titulo` carried on each fragment |
| R3 | `app/infra/kb_ingest.py`, Neon table `kb_fragments`, `spanish_unaccent` text search configuration | `tsvector` over the `spanish_unaccent` config, GIN index; same configuration applied to queries |
| R4 | `app/infra/kb_repository.py` (`ts_rank` query) | Parameterized `plainto_tsquery('spanish_unaccent', %s)` with `&` → `\|` substitution; top `k` (default 5, configurable) |
| R5 | Domain: "current version per id" selection (reference); `app/infra/kb_repository.py` (SQL filter) | Injectable `today: date` parameter; defaults to now in `Europe/Madrid`; applied in SQL before `LIMIT k` |
| R6 | `Fragment` entity + API response mapping | `cita` field, format `[ID \| vigente desde dd/mm/aaaa]` |
| R7 | `Fragment.ejemplo` propagated end-to-end | Never dropped between infra and API |
| R8 | Relevance threshold check in domain layer | Normalized `ts_rank` (normalization 32, 0–1); cutoff `0.01`, a recall filter — final abstention (NFR-03) is SPEC-001's (clarifications Q10) |
| R9 | `app/infra/kb_ingest.py` full-replace command | Manual trigger; idempotent; deletes fragments of removed documents |
| R10 | Domain: `parse_kb_document` (`app/domain/retrieval/kb_document.py`) | Rejects content outside a `##` section; error names the file (`source_name`) and is written in Spanish |
| R11 | `app/infra/kb_ingest.py` (pre-load validation) | Rejects duplicate `(id, vigente_desde)` across files before any DB write; `fragment_id` = uuid5 of `id`, `vigente_desde`, section position |

**Eval `eval_retrieval` (NFR-05):** a small offline script, outside the production code path,
that runs `KnowledgeRepository.search()` against a dataset of annotated questions and computes
Recall@5. Interim dataset: hand-built over the example (`ejemplo: true`) documents, pending the
real 100-question bank (PRD DEP-01). Runs against the test branch (see Test environment above),
not `main`. Tracked in [tasks](./tasks.md), not part of the HTTP contract above.

## Data model

`kb_fragments` table (Neon Postgres):

| Column | Type | Notes |
|---|---|---|
| `fragment_id` | `uuid` (PK) | |
| `source_id` | `text` | matches `kb/*.md` frontmatter `id` |
| `tipo` | `text` | e.g. `tarifa`, `horario`, `seguro`, `cuidado`, `tratamiento` |
| `titulo` | `text` | from frontmatter; also duplicated into `chunk_text` per R2 |
| `vigente_desde` | `date` | from frontmatter |
| `ejemplo` | `boolean` | default `false` |
| `chunk_text` | `text` | one Markdown `##` section's content, prefixed with the document's `titulo` |
| `search_vector` | `tsvector` | `to_tsvector('spanish_unaccent', chunk_text)`, GIN-indexed |

Requires the one-time `spanish_unaccent` text search configuration described above (which in
turn requires the `unaccent` extension) in the Neon database before the first ingestion run.
`to_tsvector('spanish_unaccent', chunk_text)` is immutable with respect to the generated column,
since accent-folding happens inside the configuration's own dictionary mapping rather than via a
separate `unaccent()` call in the generated expression.

Access to this table is confined to `app/infra/kb_repository.py` (the `KnowledgeRepository`
implementation) — the domain and API layers never issue SQL directly, consistent with
`specs/constitution.md`'s clean-boundaries principle.
