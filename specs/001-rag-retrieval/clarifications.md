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

- Q8: Under the Q6 chunking rule, content placed before a document's first `##` heading belongs
  to no fragment. Should that content be silently dropped, or should the document be rejected?
  (Raised during implementation of T2, 2026-11-11.)
  → A: Rejected. A document with any non-whitespace content outside a `##` section (text before
  the first `##`, or no `##` heading at all) fails validation, so the problem surfaces when the
  document is parsed instead of that content silently becoming unsearchable. The error names the
  offending file and explains in plain Spanish that all content must go inside a `##` section,
  since whoever maintains `kb/` is not necessarily technical. Captured as R10.

- Q9: What happens if two `kb/` files declare the same `id` and the same `vigente_desde`?
  (Raised during implementation of T5, 2026-11-12.)
  → A: Ingestion rejects them before touching the database. A version of a document is
  identified by `(id, vigente_desde)`; two files with the same pair are ambiguous (R5 could not
  pick one) and would also collide on the deterministic `fragment_id` that makes ingestion
  idempotent (R9), surfacing as an opaque Postgres duplicate-key error. Instead, the error names
  both files and the shared `id`, and explains in plain Spanish that each version must have a
  different `vigente_desde`. The same `id` with different dates remains valid: those are distinct
  versions. Captured as R11.

- Q10: Which numeric relevance threshold (R8) should retrieval use?
  (Raised during T10/T11, decided by the human on 2026-11-12.)
  → A: **`0.01`** (`DEFAULT_RELEVANCE_THRESHOLD`, overridable via the
  `RETRIEVAL_RELEVANCE_THRESHOLD` env var).

  Evidence — threshold sweep over the Neon test branch with the example `kb/`, using two
  interim, hand-built datasets: 23 answerable questions (`evals/retrieval_dataset.yaml`) and 19
  unanswerable ones (`evals/abstention_dataset.yaml`; 10 share words with `kb/`, 9 share none).
  Column (1): answerable questions whose correct document is in the top-5 *and* whose top score
  is ≥ the threshold. Column (2): unanswerable questions whose top score is < the threshold.

  | Threshold | (1) Answerable kept | (2) Unanswerable rejected |
  |---|---|---|
  | 0.005 | 21/23 (91.3%) | 9/19 (47.4%) |
  | 0.0075 | 21/23 (91.3%) | 9/19 (47.4%) |
  | **0.010** | **21/23 (91.3%)** | **9/19 (47.4%)** |
  | 0.0125 | 20/23 (87.0%) | 9/19 (47.4%) |
  | 0.015 | 19/23 (82.6%) | 12/19 (63.2%) |
  | 0.0175 | 19/23 (82.6%) | 12/19 (63.2%) |
  | 0.020 | 19/23 (82.6%) | 14/19 (73.7%) |
  | 0.0225 | 18/23 (78.3%) | 14/19 (73.7%) |
  | 0.025 | 17/23 (73.9%) | 16/19 (84.2%) |
  | 0.0275 | 16/23 (69.6%) | 16/19 (84.2%) |
  | 0.030 | 14/23 (60.9%) | 16/19 (84.2%) |

  Rationale: no threshold separates unanswerable questions on its own. Top scores of answerable
  questions (≈0.012–0.071) overlap those of unanswerable questions that share vocabulary with
  `kb/` (≈0.015–0.038; e.g. "¿La limpieza dental la cubre mi seguro?" scores 0.038): lexical
  rank measures topic overlap, not whether the answer is present. Even at `0.030` only 84.2% of
  unanswerable questions are rejected, while 39% of the answerable ones are lost (long questions
  first, as `ts_rank` dilutes over many OR terms). Questions with no shared vocabulary return no
  fragment at all, so any threshold > 0 rejects them. `0.010` keeps every hit `search()` finds
  (91.3%, same as no threshold) and sits mid-plateau (0.005–0.010), with margin below the
  lowest-scoring answerable question (≈0.0116).

  Therefore the threshold acts as a **recall filter**, not as the abstention guarantee. Final
  abstention is the responsibility of **SPEC-001** (prompt + citation validation), which must meet
  **NFR-03 (≥ 98% abstention on unsupported questions) end to end**. `evals/abstention_dataset.yaml`
  is kept as the interim base for that SPEC-001 eval.

  Conditions:
  1. If SPEC-001 does not reach NFR-03 end to end, this threshold will be revisited.
  2. The threshold will be recalibrated (re-running this sweep) with LifeCenter's real data once
     PRD DEP-01 is delivered — both the real `kb/` and the real question bank. With the interim
     datasets each question moves a percentage by ≈4–5 points.

## Known limitations

- **Vocabulary mismatch (lexical search).** Retrieval only matches words that share a stem with
  the `kb/` text (Q1 excludes semantic search). In the interim `eval_retrieval` run (T11,
  2026-11-12; Recall@5 = 91.3%, 21/23) the 2 misses are both of this kind, against `HOR-001`:
  "¿A qué hora abrís?" (the document says "abre", never "hora") and "¿Cerráis a mediodía entre
  semana?" (the document only gives the time ranges; "cerrada" appears only for Sundays). Possible
  improvements, neither implemented yet:
  1. A synonym dictionary in Postgres (a `synonym` / `thesaurus` text search dictionary chained
     into `spanish_unaccent`, mapping patient wording to the documents' wording, e.g.
     `abrís → abre`, `hora → horario`, `cerráis → cerrada`), applied equally at index and query
     time.
  2. Writing `kb/` documents to include the ways patients actually ask (e.g. "¿A qué hora
     abrís? La clínica abre…", "cerramos a mediodía de 14:00 a 16:00"), so the wording overlaps
     by construction. Needs no code; relies on whoever maintains `kb/`.

## Assumptions

- The `ts_rank` relevance threshold is set to `0.01` (decision and evidence in Q10). It remains
  provisional: the normalization method (option 32, 0–1 range) is fixed by R8, but the numeric
  cutoff is to be revisited under the two conditions recorded in Q10. (History: T8 first set a
  `0.02` placeholder from short queries only; the T11 eval showed it cut long answerable
  questions.)
- Until LifeCenter delivers the real knowledge base (DEP-01), `kb/` only contains example
  documents marked `ejemplo: true`; these must not be treated as real pricing/schedule data. For
  the same reason, the `eval_retrieval` eval (NFR-05: Recall@5 ≥ 90%) initially runs against a
  small, hand-built dataset of questions over those example documents rather than the 100 real
  annotated patient questions the PRD specifies — the full-scale run is pending DEP-01.
- One active document per `(id, tema)` at any given time is assumed sufficient for v1.0 — no
  need to reconcile multiple simultaneously-valid versions of the same topic.
