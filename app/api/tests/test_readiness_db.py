import os

import pytest
from app.core.db import get_engine
from app.services.health import check_readiness

pytestmark = pytest.mark.skipif(
    os.environ.get("SOURCINGIQ_INTEGRATION") != "1",
    reason="Set SOURCINGIQ_INTEGRATION=1 when PostgreSQL is migrated and seeded.",
)


def test_readiness_against_postgres() -> None:
    get_engine.cache_clear()
    report = check_readiness(get_engine())
    assert report.ok
    assert report.data_mode == "synthetic_demo"
