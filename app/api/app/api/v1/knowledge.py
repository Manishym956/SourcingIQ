from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_actor
from app.core.db import get_session
from app.services.knowledge import search_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class CitationRead(BaseModel):
    document_id: str
    title: str
    version: int
    checksum: str
    excerpt: str
    source_label: str


class KnowledgeRead(BaseModel):
    query: str
    abstained: bool
    reason: str | None
    citations: list[CitationRead]
    data_mode: str


@router.get("")
def get_knowledge(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    q: Annotated[str, Query(min_length=3, max_length=500)],
) -> KnowledgeRead:
    return KnowledgeRead.model_validate(search_knowledge(session, q, actor_email=actor))
