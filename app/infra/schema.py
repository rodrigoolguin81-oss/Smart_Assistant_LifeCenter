"""Applies the idempotent database schema (`app/infra/sql/*.sql`, in file-name order).

Usage:  python -m app.infra.schema --database-url-env TEST_DATABASE_URL
        (SPEC-006: apply the schema, consent key included, without re-ingesting `kb/`.)
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

SQL_DIR = Path(__file__).parent / "sql"


def apply_schema(conn: psycopg.Connection) -> None:
    for script in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(script.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aplica el esquema de app/infra/sql/ a una base de datos.")
    parser.add_argument(
        "--database-url-env",
        required=True,
        help="Variable de entorno con la URL de conexión directa (obligatoria, sin valor por defecto).",
    )
    args = parser.parse_args(argv)

    load_dotenv(".env")
    url = os.environ.get(args.database_url_env)
    if not url:
        print(f"Error: la variable {args.database_url_env} no está definida.", file=sys.stderr)
        return 2

    host = psycopg.conninfo.conninfo_to_dict(url).get("host", "?")
    with psycopg.connect(url) as conn:
        apply_schema(conn)
    print(f"Esquema aplicado en {host} ({args.database_url_env}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
