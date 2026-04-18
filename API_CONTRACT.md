# API Contract

Defines the interface between the React frontend and the FastAPI backend.

Rules of engagement:
- Frontend devs: do not modify `backend/` or `testing/backendtests/`.
- Backend/testing devs: do not modify `frontend/` or `testing/frontendtests/`.
- Any change to this contract requires agreement from both sides.

---

## 1. Conventions

- **Base URL:** `http://localhost:8000`
- **Content type:** `application/json` for requests and responses.
- **Dates:** ISO 8601 in UTC (e.g. `2026-04-18T14:30:00Z`).
- **IDs:** strings (UUID v4).
- **Auth:** none for hackathon scope (single local user).

### Standard error shape

All 4xx / 5xx responses return:

```json
{
  "error": {
    "code": "string",
    "message": "human-readable description"
  }
}
```

Common codes: `not_found`, `invalid_request`, `upstream_error`, `server_error`.

---

## 2. Data Models

### FoodEntry

```json
{
  "id": "uuid",
  "name": "string",
  "calories": 0,
  "protein_g": 0,
  "carbs_g": 0,
  "fat_g": 0,
  "logged_at": "2026-04-18T14:30:00Z",
  "source": "manual | chat"
}
```

### DailySummary

```json
{
  "date": "2026-04-18",
  "total_calories": 0,
  "total_protein_g": 0,
  "total_carbs_g": 0,
  "total_fat_g": 0,
  "entry_count": 0
}
```

### ChatMessage

```json
{
  "id": "uuid",
  "role": "user | assistant",
  "content": "string",
  "created_at": "2026-04-18T14:30:00Z"
}
```

---

## 3. Food Log

Owned by backend. Persists the source of truth for logged entries.

### `GET /api/log`

Query params:
- `date` (optional, `YYYY-MM-DD`) — filter to a single day. Defaults to today.

Response `200`:
```json
{ "entries": [FoodEntry, ...] }
```

### `POST /api/log`

Request:
```json
{
  "name": "string",
  "calories": 0,
  "protein_g": 0,
  "carbs_g": 0,
  "fat_g": 0,
  "logged_at": "2026-04-18T14:30:00Z"
}
```

Response `201`: `FoodEntry`.

### `DELETE /api/log/{id}`

Response `204` on success, `404` if not found.

---

## 4. Dashboard

Read-only aggregates derived from the food log.

### `GET /api/dashboard/today`

Response `200`: `DailySummary` for today.

### `GET /api/dashboard/history`

Query params:
- `days` (optional int, default `7`, max `30`) — how many days back to include.

Response `200`:
```json
{ "days": [DailySummary, ...] }
```

Used by the frontend line graph. Entries are ordered oldest → newest.

---

## 5. Chat

Claude-powered interface that can read the log and add entries on the user's behalf.

### `POST /api/chat`

Request:
```json
{ "message": "string" }
```

Response `200`:
```json
{
  "reply": "string",
  "created_entries": [FoodEntry, ...]
}
```

`created_entries` is populated when the assistant logged food as part of handling the message; empty otherwise.

### `GET /api/chat/history`

Query params:
- `limit` (optional int, default `50`).

Response `200`:
```json
{ "messages": [ChatMessage, ...] }
```

Ordered oldest → newest.

---

## 6. Health

### `GET /api/health`

Response `200`:
```json
{ "status": "ok" }
```

Used by tests and the frontend to verify the backend is reachable.
