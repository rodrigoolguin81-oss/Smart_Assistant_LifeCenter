"""Shared fixtures. Database tests run only against the Neon `test` branch (see plan: Test environment)."""

import os

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL is not set in .env (see tasks T0)")
    for production_key in ("DATABASE_URL", "DIRECT_URL"):
        if url == os.environ.get(production_key):
            pytest.fail(f"TEST_DATABASE_URL equals {production_key}: refusing to run against main")
    return url


@pytest.fixture
def test_db(test_database_url):
    """Autocommit connection to the test branch."""
    with psycopg.connect(test_database_url, autocommit=True) as conn:
        yield conn
