"""T0 — TEST_DATABASE_URL must point to a dedicated Neon test branch, never `main`."""

import os

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()


def _neon_ids(url: str) -> tuple[str, str]:
    with psycopg.connect(url) as conn:
        project_id, branch_id = conn.execute(
            "select current_setting('neon.project_id'), current_setting('neon.branch_id')"
        ).fetchone()
    return project_id, branch_id


def test_test_database_url_resolves_to_a_branch_other_than_main():
    test_url = os.environ.get("TEST_DATABASE_URL")
    main_url = os.environ.get("DATABASE_URL")
    if not test_url:
        pytest.fail("TEST_DATABASE_URL is not set in .env")
    assert main_url, "DATABASE_URL is not set in .env"

    test_project, test_branch = _neon_ids(test_url)
    main_project, main_branch = _neon_ids(main_url)

    assert test_project == main_project, "test branch must live in the same Neon project"
    assert test_branch != main_branch, "TEST_DATABASE_URL points at main's branch"
