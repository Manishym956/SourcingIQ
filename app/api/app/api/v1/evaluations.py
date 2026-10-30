import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_demo_auth

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(require_demo_auth)],
)

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "evals" / "reports"


@router.get("/latest")
def get_latest_evaluation() -> dict[str, Any]:
    """Retrieve the most recent evaluation report or indicate 'not_run'."""
    latest_file = REPORTS_DIR / "latest.json"
    if not latest_file.exists():
        return {
            "status": "not_run",
            "message": "Evaluation suite has not run yet. Run POST /api/v1/evaluations/run.",
        }
    try:
        with open(latest_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to read latest evaluation report: %s", exc)
        return {
            "status": "not_run",
            "message": "Evaluation report could not be read.",
        }


@router.post("/run")
def post_run_evaluation() -> dict[str, Any]:
    """Execute the evaluation runner on demand and return generated report."""
    try:
        from app.evals.runner import run_evaluations

        report = run_evaluations()
        return report
    except Exception as exc:
        logger.error("Failed to execute evaluation runner: %s", exc, exc_info=True)
        return {
            "status": "failed",
            "error": str(exc),
        }


@router.get("/reports")
def list_reports() -> dict[str, Any]:
    """List available historical evaluation reports."""
    if not REPORTS_DIR.exists():
        return {"reports": []}
    files = sorted(
        REPORTS_DIR.glob("report_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    summaries = []
    for p in files[:10]:
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
                summaries.append({
                    "filename": p.name,
                    "timestamp": data.get("timestamp"),
                    "total_cases": data.get("total_cases"),
                    "passed_cases": data.get("passed_cases"),
                    "pass_rate": data.get("pass_rate"),
                })
        except Exception:
            continue
    return {"reports": summaries}
