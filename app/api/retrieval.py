"""Internal retrieval endpoint. Thin: validation and mapping only; logic lives in the domain.

Not called by n8n directly — consumed by the application's own answer-generation flow.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas import RetrievalRequest, RetrievalResponse
from app.domain.retrieval.ports import KnowledgeRepository
from app.domain.retrieval.relevance import retrieve

router = APIRouter(prefix="/internal/retrieval", tags=["internal"])


def get_repository(request: Request) -> Iterator[KnowledgeRepository]:
    """Per-request repository, opened by the factory that `create_app` puts on `app.state`."""
    with request.app.state.open_repository() as repository:
        yield repository


@router.post("/query", response_model=RetrievalResponse)
def query_knowledge_base(
    body: RetrievalRequest,
    request: Request,
    repository: Annotated[KnowledgeRepository, Depends(get_repository)],
) -> RetrievalResponse:
    result = retrieve(
        repository, body.query, k=body.k, threshold=request.app.state.relevance_threshold
    )
    return RetrievalResponse.from_result(result)
