import logging
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.metadata import AppMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Readiness:
    database: str
    schema: str
    data_mode: str | None

    @property
    def ok(self) -> bool:
        return self.database == "ok" and self.schema == "ok"

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "ok" if self.ok else "unavailable",
            "checks": {"database": self.database, "schema": self.schema},
            "data_mode": self.data_mode,
        }


def check_readiness(engine: Engine) -> Readiness:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning(
            "database readiness check failed",
            extra={"event_type": "health.ready", "outcome": "database_unavailable"},
        )
        return Readiness(database="unavailable", schema="unknown", data_mode=None)

    try:
        with Session(engine) as session:
            data_mode = session.scalar(
                select(AppMetadata.value).where(AppMetadata.key == "data_mode")
            )
    except SQLAlchemyError:
        logger.warning(
            "schema readiness check failed",
            extra={"event_type": "health.ready", "outcome": "schema_unavailable"},
        )
        return Readiness(database="ok", schema="unavailable", data_mode=None)

    return Readiness(database="ok", schema="ok", data_mode=data_mode)
