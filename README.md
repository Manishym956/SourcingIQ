# SourcingIQ

Workspace for the SourcingIQ procurement MVP.

| Path | What it is |
| --- | --- |
| `SourcingIQ_AI_Engineering_Pack/` | Specification pack. Source of truth for product and engineering rules. |
| `SourcingIQ/` | Obsidian vault. Open this folder in Obsidian. Gitignored. |
| `app/` | Application. The folder is `app` because Windows treats `sourcingiq` and `SourcingIQ` as the same path, and `SourcingIQ` is the vault. |
| `logs/logs.md` | Session log. The `logs/` directory is gitignored. |

This README is the tracked entry point. Other Markdown is listed in `.gitignore`.

Phase 5 is in place. The system includes versioned evaluation fixtures, an automated evaluation runner, real-time quality gate metrics, dedicated security tests, structured JSON logging with token redaction, and an Evaluations & Observability screen in the UI. All 15 evaluation fixtures pass and scores are derived from real execution. Phase 6 waits for approval.

## Local setup

From `app/`:

```powershell
Copy-Item .env.example .env
docker compose -f infra/docker-compose.yml up -d
.\api\.venv\Scripts\python.exe -m alembic -c database/alembic.ini upgrade head
.\api\.venv\Scripts\python.exe database/seed/seed.py
```

Create the virtualenv the first time:

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

The web app expects Node dependencies from `app/web` (`npm install` on a fresh clone).

## Run

PostgreSQL is published on host port **55432**. Ports 5432 and 5433 were already taken on the machine where this was first run. The database password in `.env.example` is a local placeholder.

```powershell
cd app\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd app\web
npx next dev --hostname 127.0.0.1 --port 3000
```

- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness: `http://127.0.0.1:8000/health/ready`
- Web: `http://127.0.0.1:3000`

Readiness is ok only when PostgreSQL accepts a connection and the `app_metadata` table exists. The seed writes `data_mode=synthetic_demo` and a fictional supplier catalogue.

Protected routes need a local demo token. `Authorization: Bearer local-demo` is the buyer. `Authorization: Bearer local-approver` is the approver. Both work only when `APP_ENV=local` and `DEMO_MODE=true`. They are not production authentication.

- `POST /api/v1/rfqs` creates a validated RFQ. Send `Idempotency-Key` to make a retry return the same record.
- `GET /api/v1/rfqs` and `GET /api/v1/rfqs/{rfq_id}` read that buyer's RFQs.
- `GET /api/v1/rfqs/{rfq_id}/offers` returns eligibility, exclusion reasons, and landed cost. Ineligible suppliers are not ranked as recommendations.
- `GET /api/v1/suppliers` lists the synthetic catalogue.
- `POST /api/v1/sourcing-runs` compares that RFQ and stores the run. `GET /api/v1/sourcing-runs/{run_id}` reads the state, and `/events` and `/offers` read the log and the saved comparison.
- `POST /api/v1/sourcing-runs/{run_id}/negotiations` starts a simulation. Turns go to `POST /api/v1/negotiations/{id}/turns`. The server keeps the round cap and the price floor and ceiling. A message cannot approve a purchase or change those limits.
- `POST /api/v1/purchase-orders/drafts` builds a draft from an eligible quotation, or from an accepted simulation. The response says `Draft — not submitted.`
- `POST /api/v1/purchase-orders/{po_id}/approve` and `/reject` require `Authorization: Bearer local-approver`. The buyer token cannot approve. Approval also refuses a total above the RFQ budget. Nothing is sent to a supplier.
- `POST /api/v1/rfqs/extract` reads free text into RFQ fields. Unknown or disallowed fields, including eligibility, price, and approval, are ignored. Missing fields stay missing.
- `GET /api/v1/knowledge?q=` searches approved demo documents and returns citations. If nothing matches, the response abstains and does not invent an answer.
- Sourcing runs record `orchestrator: langgraph`. The graph calls the same eligibility and landed-cost code. It does not call a model for money or approval.

No embedding database is installed. Document search is lexical. `LLM_API_KEY` stays blank; extraction uses a local pattern stand-in behind the same schema gate a model response would have to pass.

Money uses `Decimal`, quantized half-up to `0.01`. A missing freight, discount, or tax treatment stays unknown and is not stored as zero. Landed cost is material subtotal plus freight plus tax that is not already included, minus an explicit discount.

## Checks

From `app/api`, with `SOURCINGIQ_INTEGRATION=1` after the database is migrated and seeded:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
$env:SOURCINGIQ_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest
```

From `app/web`: `npm run lint` and `npm run build`.
