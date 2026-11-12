"""Ingestion command (R9): fully and idempotently replace `kb_fragments` with the content of `kb/`.

Usage:  python -m app.infra.kb_ingest [--kb-dir kb] [--database-url-env DIRECT_URL]

The schema is applied first (DDL), so it connects with the direct, unpooled URL by default.
"""

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from app.domain.retrieval.chunking import chunk_document
from app.domain.retrieval.kb_document import InvalidKbDocument, KbDocument, parse_kb_document
from app.infra.schema import apply_schema

# Fixed namespace so the same fragment always gets the same id across runs (idempotency).
_FRAGMENT_NAMESPACE = uuid.UUID("6f1d5a3e-7c0b-4d2a-9b61-2f3c8e4a5d10")

_INSERT = """
    INSERT INTO kb_fragments
        (fragment_id, source_id, tipo, titulo, vigente_desde, ejemplo, chunk_text)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


@dataclass(frozen=True)
class IngestReport:
    documents: int
    fragments: int


def _load_documents(kb_dir: Path) -> list[KbDocument]:
    """Parse and validate every `kb_dir/*.md` before anything touches the database."""
    documents: list[KbDocument] = []
    seen: dict[tuple[str, object], str] = {}
    for path in sorted(kb_dir.glob("*.md")):
        doc = parse_kb_document(path.read_text(encoding="utf-8"), source_name=path.name)
        version = (doc.id, doc.vigente_desde)
        if version in seen:
            raise InvalidKbDocument(
                f"Los documentos «{seen[version]}» y «{path.name}» tienen el mismo id «{doc.id}» "
                f"y la misma fecha vigente_desde ({doc.vigente_desde.isoformat()}). Cada versión "
                "de un documento debe tener una fecha vigente_desde distinta: cambia la fecha de "
                "uno de ellos o elimina el duplicado."
            )
        seen[version] = path.name
        documents.append(doc)
    return documents


def ingest(conn: psycopg.Connection, kb_dir: Path) -> IngestReport:
    documents = _load_documents(kb_dir)
    rows = [
        (
            uuid.uuid5(
                _FRAGMENT_NAMESPACE, f"{doc.id}|{doc.vigente_desde.isoformat()}|{position}"
            ),
            f.source_id,
            f.tipo,
            f.titulo,
            f.vigente_desde,
            f.ejemplo,
            f.text,
        )
        for doc in documents
        for position, f in enumerate(chunk_document(doc))
    ]

    with conn.transaction():
        apply_schema(conn)
        conn.execute("DELETE FROM kb_fragments")
        with conn.cursor() as cur:
            cur.executemany(_INSERT, rows)

    return IngestReport(documents=len(documents), fragments=len(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reemplaza kb_fragments con el contenido de kb/.")
    parser.add_argument("--kb-dir", type=Path, default=Path("kb"))
    parser.add_argument(
        "--database-url-env",
        default="DIRECT_URL",
        help="Variable de entorno con la URL de conexión directa (por defecto: DIRECT_URL).",
    )
    args = parser.parse_args(argv)

    load_dotenv(".env")
    url = os.environ.get(args.database_url_env)
    if not url:
        print(f"Error: la variable {args.database_url_env} no está definida.", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(url) as conn:
            report = ingest(conn, args.kb_dir)
    except InvalidKbDocument as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("No se ha modificado la base de datos.", file=sys.stderr)
        return 1

    print(f"Ingesta completada: {report.documents} documentos, {report.fragments} fragmentos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
