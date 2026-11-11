---
type: tasks
spec_id: SPEC-002
title: rag-retrieval — Task Breakdown
description: Granular, testable tasks derived from the plan for knowledge base ingestion and retrieval.
tags: [tasks, rag-retrieval, SPEC-002]
status: verified
sources: [./plan.md]
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: 2026-11-11T00:00:00Z }
stale_after: null
---

# rag-retrieval — Tasks

- [x] T0 — Create a dedicated Neon branch for tests (via the Neon CLI), separate from `main`, so
  test runs never touch `main`'s data; add `TEST_DATABASE_URL` to `.env.example` (placeholder)
  and `.env` (populated with that branch's connection string) · test: connecting with
  `TEST_DATABASE_URL` resolves to the test branch, not `main` (e.g. distinct branch id/host) ·
  covers: (infra prerequisite for T4–T7, T10)
- [ ] T1 — Define the `kb/*.md` frontmatter schema and write 2-3 example documents
  (`ejemplo: true`) covering `tarifa`, `horario` and `tratamiento` · test: a schema validator
  rejects a document missing `id`/`tipo`/`titulo`/`vigente_desde` · covers: R1
- [ ] T2 — Implement the domain `Fragment` entity and the chunking function (pure, no I/O): one
  fragment per Markdown `##` section, with the document's `titulo` carried on every fragment ·
  test: chunking a document with three `##` sections produces three fragments, each carrying
  that document's `titulo` · covers: R1, R2
- [ ] T3 — Implement "current version per id" selection logic in the domain layer, taking
  "today" as an injectable `date` parameter (defaulting to now in the `Europe/Madrid` timezone
  when not supplied) · test: given two versions of the same `id` (past and future
  `vigente_desde`) and an injected fixed `today`, only the valid current one is selected ·
  covers: R5
- [ ] T4 — Against the Neon test branch (`TEST_DATABASE_URL`, see T0): create the
  `spanish_unaccent` text search configuration (`CREATE EXTENSION unaccent`, `CREATE TEXT SEARCH
  CONFIGURATION spanish_unaccent (COPY = spanish)`, mapping `hword`/`hword_part`/`word` through
  `unaccent, spanish_stem`) and the `kb_fragments` table migration, with `search_vector` as a
  generated `tsvector` column over `to_tsvector('spanish_unaccent', chunk_text)`, GIN-indexed ·
  test: (a) the generated column creation succeeds (confirming the expression is accepted as
  immutable, unlike a direct `unaccent()` call); (b) inserting a row with accented text
  auto-populates `search_vector`, and a query for the unaccented term matches it · covers: R3
- [ ] T5 — Implement the idempotent ingestion command: read `kb/*.md`, chunk, and fully replace
  `kb_fragments` with the current content of `kb/`, deleting fragments for any `source_id` no
  longer present on disk · test: (a) running it twice on unchanged files does not duplicate or
  change rows; (b) removing a `kb/` document and re-running it deletes that document's fragments
  · covers: R2, R3, R9
- [ ] T6 — Implement `KnowledgeRepository.search(query, k=5)`: build the `tsquery` via
  parameterized `plainto_tsquery('spanish_unaccent', %s)` (never by concatenating the user's text
  into a SQL/tsquery string) and rewrite its `&` operators to `|` so matching is OR-combined, then
  rank with `ts_rank` over `search_vector` · test: (a) a query whose terms only partially overlap
  a seeded fragment's text still returns that fragment among the top `k`; (b) an accented vs.
  unaccented variant of the same query returns the same fragments; (c) a query containing special
  characters (`:`, `!`, `&`, quotes) does not raise an error and returns a (possibly empty) ranked
  result · covers: R3, R4
- [ ] T7 — Wire R5 (current-version filtering, with its injectable `today`) into the repository
  query path · test: a query matching a superseded version, evaluated with a fixed injected
  `today`, returns the current version's fragment, not the stale one · covers: R5
- [ ] T8 — Add the relevance threshold check using the normalized `ts_rank` score (normalization
  option 32, 0–1 range) and the `below_threshold` flag · test: a query with no lexical overlap
  with any fragment returns `below_threshold: true` and an empty fragment list · covers: R8
- [ ] T9 — Map `Fragment` → API response, including `titulo`, the `cita` field (`[ID | vigente
  desde dd/mm/aaaa]`), and the propagated `ejemplo` flag · test: a fragment from an `ejemplo:
  true` document is returned with `ejemplo: true` and a correctly formatted `cita` in the
  response · covers: R6, R7
- [ ] T10 — Against the Neon test branch (`TEST_DATABASE_URL`, see T0): implement the internal
  `POST /internal/retrieval/query` FastAPI endpoint per the contract in [plan](./plan.md), with
  `k` defaulting to 5, caller-configurable, and the `cita` field populated · test: an integration
  test posts a known query and asserts the response shape (including `cita`) and a 200 status ·
  covers: R3, R4, R6, R7, R8
- [ ] T11 — Build the `eval_retrieval` dataset and script (NFR-05): a small, hand-built set of
  annotated questions over the example (`ejemplo: true`) documents, each with its expected
  source `id`, plus a script that runs `KnowledgeRepository.search()` (against the test branch)
  for each question and computes Recall@5 · test: the script reports Recall@5 ≥ 90% on the
  interim dataset; flagged to re-run against the real 100-question bank once PRD DEP-01 is
  delivered · covers: NFR-05
