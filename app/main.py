"""Application factory: the composition root wiring infrastructure into the API.

Run with:  uvicorn app.main:create_app --factory
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI

from app.api import retrieval
from app.domain.retrieval.relevance import DEFAULT_RELEVANCE_THRESHOLD
from app.infra.kb_repository import PostgresKnowledgeRepository


def create_app(database_url_env: str = "DATABASE_URL") -> FastAPI:
    """Build the app. `database_url_env` names the env var holding the (pooled) connection
    string; tests pass TEST_DATABASE_URL so they never reach `main`.
    """
    load_dotenv(".env")
    threshold = float(os.environ.get("RETRIEVAL_RELEVANCE_THRESHOLD") or DEFAULT_RELEVANCE_THRESHOLD)

    @contextmanager
    def open_repository() -> Iterator[PostgresKnowledgeRepository]:
        with psycopg.connect(os.environ[database_url_env]) as conn:
            yield PostgresKnowledgeRepository(conn)

    app = FastAPI(title="Smart Assistant LifeCenter")
    app.state.open_repository = open_repository
    app.state.relevance_threshold = threshold
    app.include_router(retrieval.router)
    return app
