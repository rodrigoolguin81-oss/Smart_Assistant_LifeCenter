---
type: spec
spec_id: SPEC-002
title: rag-retrieval — Functional Spec
description: Functional requirements for indexing LifeCenter's knowledge base and retrieving relevant, sourced fragments via lexical search (RF-001, RF-002), in EARS notation.
tags: [spec, rag-retrieval, SPEC-002]
status: verified
sources: [./clarifications.md, ../../docs/03-prd.md]
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: 2026-11-11T00:00:00Z }
stale_after: null
---

# rag-retrieval — Specification

Traceability: PRD `docs/03-prd.md` §4 (US-001), §5.1 (RF-001, RF-002), §11 (**SPEC-002**).

## Context

Recepción pierde tiempo respondiendo siempre las mismas preguntas sobre tratamientos, precios,
horarios, seguros y cuidados. Smart Assistant debe responder esas preguntas citando la fuente
exacta y su fecha de vigencia, sin inventar información. Este feature cubre la indexación de la
base de conocimiento de LifeCenter y la recuperación de los fragmentos relevantes para una
consulta, usando búsqueda léxica (full-text search) sobre Postgres/Neon — sin base de datos
vectorial, por decisión registrada en [clarifications](./clarifications.md) Q1.

## Requirements (EARS)

- R1. The system SHALL store each knowledge base document as a Markdown file in `kb/`, with
  frontmatter fields `id`, `tipo`, `titulo` and `vigente_desde`.
- R2. The system SHALL chunk each knowledge base document into one fragment per Markdown section
  introduced by a level-2 heading (`##`), with each fragment retaining the source document's
  `titulo` (from frontmatter).
- R3. The system SHALL index each fragment's text in a Neon Postgres table using a `tsvector`
  column built with the `spanish` text search configuration over `unaccent`-normalized text, with
  a GIN index; the same `unaccent` + `spanish` normalization SHALL be applied to incoming queries,
  so accented and unaccented spellings match equally.
- R4. WHEN a query is received, the system SHALL combine the query's terms with OR (not AND),
  rank candidate fragments using `ts_rank` over the `tsvector` column, and return the top `k`
  ranked fragments, with `k` defaulting to 5 and configurable — so a patient's wording does not
  need to match every term of the source document to retrieve it.
- R5. WHEN ranking fragments for a document `id`, the system SHALL only consider the document
  version whose `vigente_desde` is less than or equal to the current date and is the most recent
  such version for that `id`; superseded or future-dated versions SHALL be excluded.
- R6. WHEN the system returns a fragment to be used in an answer, the system SHALL also return
  that fragment's source `id` and `vigente_desde`, formatted as `[ID | vigente desde
  dd/mm/aaaa]`.
- R7. WHERE a document's frontmatter has `ejemplo: true`, the system SHALL propagate that flag
  with the retrieved fragment, so downstream components never present example data as real
  pricing or schedule information.
- R8. IF the top-ranked fragment's normalized `ts_rank` score (normalization option 32, range
  0–1) is below the configured relevance threshold, THEN the system SHALL report that no
  sufficiently relevant fragment was found (consumed by the abstention feature, RF-003 /
  SPEC-001), instead of returning a low-confidence fragment. The initial threshold value is an
  assumption, to be adjusted against eval NFR-03.
- R9. The system SHALL provide a manually-triggered, idempotent ingestion command, run after
  changes under `kb/`, that replaces all indexed fragments with the current content of `kb/` —
  including deleting the fragments of any document removed from `kb/` — so the indexed table
  never serves a stale or orphaned fragment.
- R10. IF a knowledge base document contains any non-whitespace content outside a Markdown
  section introduced by a level-2 heading (`##`) — including text before the first `##`, or a
  document with no `##` heading at all — THEN the system SHALL reject that document with an
  error that names its file and explains, in plain Spanish, that all content must be placed
  inside a `##` section, instead of silently dropping that content from the index.
- R11. IF two knowledge base documents share the same `id` and the same `vigente_desde`, THEN
  the ingestion command SHALL reject them with an error that names both files and the shared
  `id`, explaining in plain Spanish that each version of a document must have a different
  `vigente_desde`, and SHALL leave the indexed fragments unchanged. Documents sharing an `id`
  with different `vigente_desde` dates are distinct versions and SHALL be accepted (R5).

## Acceptance criteria

- [ ] Given a `kb/` document with `vigente_desde` in the past, a query matching its content
  returns a fragment citing that document's `id` and `vigente_desde`.
- [ ] Given two versions of the same `id` (one superseded, one current), only the current one is
  returned.
- [ ] Given a `kb/` document with `vigente_desde` in the future, it is never returned by a query
  before that date.
- [ ] Given a query with no lexical match above the relevance threshold, the retrieval result
  signals "no sufficiently relevant fragment" rather than returning an unrelated fragment.
- [ ] Given a document flagged `ejemplo: true`, any fragment retrieved from it carries that flag
  through to the caller.
- [ ] Given a query whose wording only overlaps partially with a relevant document's terms, the
  OR-combined, `ts_rank`-ordered search still surfaces that fragment, instead of requiring every
  query term to match.
- [ ] Given the same query written with and without tildes, both return the same fragments
  (`unaccent` normalization applied at index time and query time).
- [ ] Given a `kb/` document with three `##` sections, ingestion produces three fragments, each
  one carrying that document's `titulo`.
- [ ] Given the `eval_retrieval` eval (NFR-05: Recall@5 ≥ 90% over annotated questions), the
  top-5 fragments contain the expected source `id` for at least 90% of the dataset's questions;
  until a real annotated question bank exists (PRD DEP-01), this eval runs against a small
  dataset built over the example (`ejemplo: true`) documents.
- [ ] Given a `kb/` document removed from disk, running the ingestion command removes its
  fragments from the indexed table; running it twice in a row with no changes under `kb/` leaves
  the table unchanged (idempotent).
- [ ] Given a `kb/` document with text before its first `##` heading (or with no `##` heading),
  it is rejected with an error naming its file and explaining in Spanish that all content must
  go inside a `##` section.
- [ ] Given two `kb/` documents with the same `id` and the same `vigente_desde`, ingestion is
  rejected with an error naming both files and the `id`, and the indexed table is unchanged;
  given the same `id` with different `vigente_desde` dates, both versions are ingested.

## Out of scope

- Embeddings, vector databases, or semantic/hybrid search (explicitly excluded per
  [clarifications](./clarifications.md) Q1).
- Deciding the final wording of the abstention message or the urgency/complaint detection logic
  (covered by other specs, e.g. SPEC-001, SPEC-003).
- Real LifeCenter knowledge base content — pending PRD DEP-01; only example (`ejemplo: true`)
  documents are in scope here. A full-scale `eval_retrieval` run (100 real annotated questions,
  NFR-05) is likewise pending that data.
- Tuning the production relevance threshold value — the normalization method is specified (R8),
  but the numeric threshold itself is tracked as an open assumption in
  [clarifications](./clarifications.md).
- Automatic re-ingestion on file change (e.g. a file-watcher) — R9 only requires a manual,
  idempotent command.
