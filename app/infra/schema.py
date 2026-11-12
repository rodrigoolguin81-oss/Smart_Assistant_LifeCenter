"""Applies the idempotent database schema (`app/infra/sql/*.sql`, in file-name order)."""

from pathlib import Path

import psycopg

SQL_DIR = Path(__file__).parent / "sql"


def apply_schema(conn: psycopg.Connection) -> None:
    for script in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(script.read_text(encoding="utf-8"))
