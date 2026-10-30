import json
import logging
import os
import re
from datetime import UTC, datetime

REDACT_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"password=([^\s&]+)", re.IGNORECASE),
]


def redact_sensitive(text: str) -> str:
    """Mask credentials, auth tokens, and sensitive headers."""
    for pattern in REDACT_PATTERNS:
        text = pattern.sub("Bearer [REDACTED]", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "service": "sourcingiq-api",
            "environment": os.environ.get("APP_ENV", "local"),
            "message": redact_sensitive(record.getMessage()),
            "logger": record.name,
        }
        for key in (
            "request_id",
            "workflow_id",
            "step_name",
            "event_type",
            "duration_ms",
            "outcome",
            "error_code",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
