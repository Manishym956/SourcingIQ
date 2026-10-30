"""Read-only search of approved demo documents."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.retrieval import search_chunks
from app.core.config import get_settings
from app.models.procurement import KnowledgeChunk, KnowledgeDocument
from app.services.workflow import _user


def search_knowledge(session: Session, query: str, *, actor_email: str) -> dict[str, object]:
    if not get_settings().enable_rag:
        raise HTTPException(status_code=403, detail="Document search is disabled.")
    _user(session, actor_email)
    rows = session.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.source_label == "approved_demo")
        .order_by(KnowledgeDocument.title, KnowledgeChunk.position)
    ).all()
    chunks = [
        {
            "document_id": str(document.id),
            "title": document.title,
            "version": str(document.version),
            "checksum": document.checksum,
            "text": chunk.text,
            "source_label": document.source_label,
        }
        for chunk, document in rows
    ]
    matches, reason = search_chunks(chunks, query)
    return {
        "query": query,
        "abstained": reason is not None,
        "reason": reason,
        "citations": [
            {
                "document_id": item["document_id"],
                "title": item["title"],
                "version": int(item["version"]),
                "checksum": item["checksum"],
                "excerpt": item["text"],
                "source_label": item["source_label"],
            }
            for item in matches
        ],
        "data_mode": "synthetic_demo",
    }
