---
type: clarifications
title: rag-retrieval — Clarifications
description: Open questions resolved with the human before writing the spec, plus assumptions.
tags: [clarify, rag-retrieval, SPEC-002]
status: verified
sources: []
generated: { by: claude-code, at: 2026-11-10T00:00:00Z }
verified: { by: human, at: 2026-11-11T00:00:00Z }
stale_after: null
---

# rag-retrieval — Clarifications

Covers PRD (`docs/03-prd.md`) requirements RF-001 and RF-002, traceability row **SPEC-002**
(§11): index LifeCenter's knowledge base and retrieve relevant fragments with their source,
without a vector database.

## Questions & answers

- Q1: RF-001 asks to retrieve relevant fragments "without a vector database". What retrieval
  mechanism do we use over the knowledge base?
  → A: Lexical full-text search on PostgreSQL (Neon): a `tsvector` column with the `spanish`
  configuration, a GIN index, and ranking via `ts_rank`. No embeddings, no pgvector, no vector
  database. The relevance threshold used for abstention (RF-003) is applied over the normalized
  `ts_rank` score (normalization option 32, which maps scores to a 0–1 range), tuned against
  eval NFR-03; the initial numeric value is an open assumption.

- Q2: In what format, and where, will the knowledge base documents (treatments, prices,
  schedules, insurance, aftercare) that the system must index live?
  → A: Markdown files in a `kb/` folder in the repo, one per document (prices, schedules,
  insurance, aftercare, treatments), with frontmatter: `id`, `tipo`, `titulo`, `vigente_desde`.
  These are the editable source of truth. An ingestion command chunks them into fragments and
  loads them into a Neon table with a `tsvector` column, which is what gets searched. Since
  LifeCenter has not yet delivered the real documents (PRD DEP-01), example documents are
  created, explicitly flagged as such in the frontmatter (`ejemplo: true`).

- Q3: RF-002 requires citing "document and validity date" in every answer about prices,
  schedules or treatments. How is a document's validity determined at answer time?
  → A: A `vigente_desde` field per document in the frontmatter. When answering, only versions
  with `vigente_desde` ≤ current date are considered, and for each `id` the most recent one is
  used; superseded or future-dated versions are discarded. The source citation is rendered as
  `[ID | vigente desde dd/mm/aaaa]`.

- Q4: How should a query's terms be combined when ranking fragments, given that a patient's
  wording often differs from the document's wording?
  → A: Terms are combined with OR (not AND) and candidates are ordered by `ts_rank`, so a
  fragment matching only some of the query's terms can still be the top result instead of being
  excluded for not matching all of them. The top `k` fragments are returned, with `k` defaulting
  to 5 and configurable per call.

- Q5: Spanish has accented characters (tildes); should "tratamientos" vs "tratamiéntos"-style
  variation, or a patient typing without accents, affect matching?
  → A: No. The `unaccent` Postgres extension is applied to the text before building the
  `tsvector` at index time, and to the incoming query before parsing it at query time — both
  together with the `spanish` text search configuration — so accented and unaccented spellings
  of the same word match equally.

- Q6: What is the exact chunking granularity for a `kb/` document?
  → A: One fragment per Markdown section introduced by a level-2 heading (`##`). Each fragment
  retains the source document's `titulo` (from frontmatter) so it reads as a standalone,
  self-identifying unit even outside the context of the full document.

- Q7: How does the indexed table stay in sync with edits under `kb/` (adds, edits, and
  deletions), and is that automatic?
  → A: A manually-triggered ingestion command, run by whoever edits `kb/` after they're done.
  It is idempotent and performs a full replace: it re-reads all of `kb/`, re-chunks everything,
  and replaces the indexed fragments with that current content — including deleting the
  fragments of any document that was removed from `kb/`. There is no automatic file-watcher for
  v1.0; running the command twice with no changes leaves the table unchanged.

## Assumptions

- The initial `ts_rank` relevance threshold for abstention is a placeholder value, to be tuned
  against the NFR-03 eval (≥ 98% abstention on unsupported questions) once a real question bank
  exists. The normalization method (option 32, 0–1 range) is fixed by R8; only the numeric
  cutoff is open.
- Until LifeCenter delivers the real knowledge base (DEP-01), `kb/` only contains example
  documents marked `ejemplo: true`; these must not be treated as real pricing/schedule data. For
  the same reason, the `eval_retrieval` eval (NFR-05: Recall@5 ≥ 90%) initially runs against a
  small, hand-built dataset of questions over those example documents rather than the 100 real
  annotated patient questions the PRD specifies — the full-scale run is pending DEP-01.
- One active document per `(id, tema)` at any given time is assumed sufficient for v1.0 — no
  need to reconcile multiple simultaneously-valid versions of the same topic.
