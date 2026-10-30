"""Approved demo knowledge. These sentences are data, not instructions."""

import hashlib
from uuid import UUID

DOCUMENTS = [
    {
        "id": UUID("00000000-0000-4000-8000-000000000401"),
        "title": "Demo procurement policy",
        "chunks": [
            (
                UUID("00000000-0000-4000-8000-000000000501"),
                "Supported currency is INR. Supported unit is tonne. Missing freight, tax, or discount stays unknown.",
            ),
            (
                UUID("00000000-0000-4000-8000-000000000502"),
                "A purchase-order draft is not submitted. Approval is a human action, and a model cannot approve a purchase.",
            ),
        ],
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000402"),
        "title": "Demo material note",
        "chunks": [
            (
                UUID("00000000-0000-4000-8000-000000000503"),
                "Fe 500D is the TMT steel grade in the synthetic catalogue. Fe 415 does not match an Fe 500D request.",
            ),
        ],
    },
]


def document_checksum(chunks: list[tuple[UUID, str]]) -> str:
    body = "\n".join(text for _chunk_id, text in chunks)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
