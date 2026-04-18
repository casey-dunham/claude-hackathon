# Claude Hackathon

Backend is now implemented in FastAPI with SQLite ("lite SQL") storage and follows `API_CONTRACT.md`.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Add environment variables in `.env`:

```env
CLAUDE_API_KEY=
# Optional override for SQLite file path:
# LITESQL_PATH=backend/litesql.db
```

## Run backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Base URL: `http://localhost:8000`

## Contract endpoints implemented

- `GET /api/health`
- `GET /api/log`
- `POST /api/log`
- `DELETE /api/log/{id}`
- `GET /api/dashboard/today`
- `GET /api/dashboard/history`
- `POST /api/chat`
- `GET /api/chat/history`
