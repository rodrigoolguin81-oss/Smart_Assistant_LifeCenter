"""Postgres implementation of `KnowledgeRepository` (R3, R4). The only module that queries
`kb_fragments`.
"""

from datetime import date

import psycopg

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.versioning import madrid_today

# The user's text only ever reaches Postgres as a bound parameter of plainto_tsquery, which
# sanitizes and tokenizes it. Its AND (`&`) operators are then rewritten to OR (`|`) so a
# fragment matching only some of the terms can still rank (R4). ts_rank normalization 32 maps
# the score to 0–1 (rank / (rank + 1)) without changing the order.
#
# R5 is applied in the WHERE clause, before LIMIT, so superseded or future-dated versions never
# take top-k slots. It mirrors the reference rule in `select_current_versions`: per source_id,
# keep only the latest vigente_desde that is <= today.
_SEARCH = """
    WITH q AS (
        SELECT replace(
            plainto_tsquery('spanish_unaccent', %(query)s)::text, ' & ', ' | '
        )::tsquery AS tsq
    )
    SELECT f.chunk_text, f.titulo, f.source_id, f.tipo, f.vigente_desde, f.ejemplo,
           ts_rank(f.search_vector, q.tsq, 32) AS score
    FROM kb_fragments f, q
    WHERE f.search_vector @@ q.tsq
      AND f.vigente_desde = (
          SELECT max(v.vigente_desde) FROM kb_fragments v
          WHERE v.source_id = f.source_id AND v.vigente_desde <= %(today)s
      )
    ORDER BY score DESC, f.fragment_id
    LIMIT %(k)s
"""


class PostgresKnowledgeRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def search(self, query: str, k: int = 5, today: date | None = None) -> list[Fragment]:
        params = {"query": query, "k": k, "today": today or madrid_today()}
        rows = self._conn.execute(_SEARCH, params).fetchall()
        return [
            Fragment(
                text=text,
                titulo=titulo,
                source_id=source_id,
                tipo=tipo,
                vigente_desde=vigente_desde,
                ejemplo=ejemplo,
                score=float(score),
            )
            for text, titulo, source_id, tipo, vigente_desde, ejemplo, score in rows
        ]
