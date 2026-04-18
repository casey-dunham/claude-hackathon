# Claude Hackathon

Nutrition tracking app prototype with:
- React frontend (folder scaffolded)
- FastAPI backend
- SQLite ("lite SQL") persistence for food logs and chat history

The backend implementation is contract-first and follows [API_CONTRACT.md](API_CONTRACT.md).

## Current scope

- Track food entries (manual + chat-created)
- Show daily totals and recent history for dashboard charts
- Provide chat endpoint with simple food-log command parsing
- Persist data locally in SQLite

## Tech stack

- Python + FastAPI
- SQLite (native `sqlite3`)
- Pydantic models for request/response validation
- Pytest + FastAPI TestClient for backend contract tests

## Repository layout

```text
backend/
  main.py                  # FastAPI app + routes + SQLite data layer
testing/
  backendtests/
    test_api_contract.py   # API contract tests
  frontendtests/           # frontend test notes/scaffold
  end2endtests/            # e2e notes/scaffold
frontend/                  # frontend notes/scaffold
mock data/                 # mock data notes/scaffold
API_CONTRACT.md            # source-of-truth API interface
requirements.txt
README.md
```

## Prerequisites

- Python 3.10+ (verified with Python 3.12)

## Quickstart

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` in project root:

```env
CLAUDE_API_KEY=
CLAUDE_MODEL=claude-opus-4-6
# Optional: Claude API timeout in seconds
# CLAUDE_TIMEOUT_SECONDS=8
# Optional: override sqlite file path
# LITESQL_PATH=backend/health.db
```

4. Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

5. Open docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API overview

Base URL: `http://localhost:8000`

- `GET /api/health`
- `GET /api/log?date=YYYY-MM-DD`
- `POST /api/log`
- `DELETE /api/log/{id}`
- `GET /api/dashboard/today`
- `GET /api/dashboard/history?days=7`
- `POST /api/chat`
- `GET /api/chat/history?limit=50`

Error responses use:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "human-readable description"
  }
}
```

## cURL examples

Health check:

```bash
curl http://localhost:8000/api/health
```

Create a food entry:

```bash
curl -X POST http://localhost:8000/api/log \
  -H "Content-Type: application/json" \
  -d '{
    "name": "banana",
    "calories": 105,
    "protein_g": 1.3,
    "carbs_g": 27,
    "fat_g": 0.4,
    "logged_at": "2026-04-18T14:30:00Z"
  }'
```

Get entries for a day:

```bash
curl "http://localhost:8000/api/log?date=2026-04-18"
```

Chat log command (creates a food entry with source `chat`):

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"log oatmeal 300 cal 10p 54c 5f"}'
```

## Chat behavior (current)

`POST /api/chat` uses Claude (Anthropic Messages API) to:

- log food entries from natural language
- provide nutrition and meal recommendations
- return any created log entries in `created_entries`

The backend still supports this quick-log format as a fallback:

```text
log <name> <calories> cal <protein>p <carbs>c <fat>f
```

Example quick-log command:

```text
log grilled chicken 300 cal 40p 0c 8f
```

If Claude is unavailable, the backend falls back to local quick-log parsing and usage guidance.

## Data persistence

- Default database file: `backend/health.db`
- You can override via `LITESQL_PATH` in `.env`
- SQLite tables are auto-created at app startup
- DB files are git-ignored (`backend/health.db*`)

## Running tests

Run backend contract tests:

```bash
python3 -m pytest -q testing/backendtests/test_api_contract.py
```

Run frontend-facing contract tests:

```bash
python3 -m pytest -q testing/frontendtests/test_frontend_contract.py
```

Run end-to-end flow tests:

```bash
python3 -m pytest -q testing/end2endtests/test_end_to_end_flows.py
```

## Notes for contributors

- Treat `API_CONTRACT.md` as the integration source of truth.
- Coordinate contract changes across frontend and backend before editing the contract.
- Frontend and additional e2e assets are currently scaffolded and can be expanded incrementally.
