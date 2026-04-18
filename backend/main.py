from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generator, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("LITESQL_PATH", BASE_DIR / "litesql.db"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601_utc(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise APIError(
            status_code=422,
            code="invalid_request",
            message=f"{field_name} must be an ISO 8601 datetime",
        ) from exc

    if parsed.tzinfo is None:
        raise APIError(
            status_code=422,
            code="invalid_request",
            message=f"{field_name} must include a timezone offset and be in UTC",
        )

    return parsed.astimezone(timezone.utc)


def parse_yyyy_mm_dd(value: str, *, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise APIError(
            status_code=422,
            code="invalid_request",
            message=f"{field_name} must be in YYYY-MM-DD format",
        ) from exc


def today_utc_str() -> str:
    return utc_now().date().isoformat()


@dataclass(slots=True)
class APIError(Exception):
    status_code: int
    code: str
    message: str


class FoodEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    calories: int = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    logged_at: str


class FoodEntry(BaseModel):
    id: str
    name: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    logged_at: str
    source: Literal["manual", "chat"]


class FoodLogResponse(BaseModel):
    entries: list[FoodEntry]


class DailySummary(BaseModel):
    date: str
    total_calories: int
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    entry_count: int


class DashboardHistoryResponse(BaseModel):
    days: list[DailySummary]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    created_entries: list[FoodEntry]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS food_entries (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    calories INTEGER NOT NULL CHECK(calories >= 0),
                    protein_g REAL NOT NULL CHECK(protein_g >= 0),
                    carbs_g REAL NOT NULL CHECK(carbs_g >= 0),
                    fat_g REAL NOT NULL CHECK(fat_g >= 0),
                    logged_at TEXT NOT NULL,
                    source TEXT NOT NULL CHECK(source IN ('manual', 'chat')),
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_food_entries_logged_at
                ON food_entries(logged_at);

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at
                ON chat_messages(created_at);
                """
            )
            conn.commit()

    def insert_food_entry(self, payload: FoodEntryCreate, source: Literal["manual", "chat"]) -> FoodEntry:
        entry_id = str(uuid.uuid4())
        logged_at = to_utc_iso(parse_iso8601_utc(payload.logged_at, field_name="logged_at"))
        created_at = to_utc_iso(utc_now())

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO food_entries (
                    id, name, calories, protein_g, carbs_g, fat_g, logged_at, source, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    payload.name.strip(),
                    payload.calories,
                    payload.protein_g,
                    payload.carbs_g,
                    payload.fat_g,
                    logged_at,
                    source,
                    created_at,
                ),
            )
            conn.commit()

        return self.get_food_entry(entry_id)

    def get_food_entry(self, entry_id: str) -> FoodEntry:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, calories, protein_g, carbs_g, fat_g, logged_at, source
                FROM food_entries
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()

        if row is None:
            raise APIError(status_code=404, code="not_found", message="Food entry not found")
        return self._row_to_food_entry(row)

    def get_log_for_date(self, day: str) -> list[FoodEntry]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, calories, protein_g, carbs_g, fat_g, logged_at, source
                FROM food_entries
                WHERE substr(logged_at, 1, 10) = ?
                ORDER BY logged_at ASC, created_at ASC
                """,
                (day,),
            ).fetchall()

        return [self._row_to_food_entry(row) for row in rows]

    def delete_food_entry(self, entry_id: str) -> bool:
        with self.connection() as conn:
            cursor = conn.execute("DELETE FROM food_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_daily_summary(self, day: str) -> DailySummary:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(calories), 0) AS total_calories,
                    COALESCE(SUM(protein_g), 0) AS total_protein_g,
                    COALESCE(SUM(carbs_g), 0) AS total_carbs_g,
                    COALESCE(SUM(fat_g), 0) AS total_fat_g,
                    COUNT(*) AS entry_count
                FROM food_entries
                WHERE substr(logged_at, 1, 10) = ?
                """,
                (day,),
            ).fetchone()

        return DailySummary(
            date=day,
            total_calories=int(row["total_calories"]),
            total_protein_g=float(row["total_protein_g"]),
            total_carbs_g=float(row["total_carbs_g"]),
            total_fat_g=float(row["total_fat_g"]),
            entry_count=int(row["entry_count"]),
        )

    def get_dashboard_history(self, days: int) -> list[DailySummary]:
        end_date = utc_now().date()
        start_date = end_date - timedelta(days=days - 1)

        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    substr(logged_at, 1, 10) AS day,
                    COALESCE(SUM(calories), 0) AS total_calories,
                    COALESCE(SUM(protein_g), 0) AS total_protein_g,
                    COALESCE(SUM(carbs_g), 0) AS total_carbs_g,
                    COALESCE(SUM(fat_g), 0) AS total_fat_g,
                    COUNT(*) AS entry_count
                FROM food_entries
                WHERE substr(logged_at, 1, 10) BETWEEN ? AND ?
                GROUP BY day
                ORDER BY day ASC
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

        by_day = {
            row["day"]: DailySummary(
                date=row["day"],
                total_calories=int(row["total_calories"]),
                total_protein_g=float(row["total_protein_g"]),
                total_carbs_g=float(row["total_carbs_g"]),
                total_fat_g=float(row["total_fat_g"]),
                entry_count=int(row["entry_count"]),
            )
            for row in rows
        }

        history: list[DailySummary] = []
        for day_offset in range(days):
            curr_day = start_date + timedelta(days=day_offset)
            key = curr_day.isoformat()
            if key in by_day:
                history.append(by_day[key])
            else:
                history.append(
                    DailySummary(
                        date=key,
                        total_calories=0,
                        total_protein_g=0.0,
                        total_carbs_g=0.0,
                        total_fat_g=0.0,
                        entry_count=0,
                    )
                )
        return history

    def insert_chat_message(self, role: Literal["user", "assistant"], content: str) -> ChatMessage:
        message_id = str(uuid.uuid4())
        created_at = to_utc_iso(utc_now())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (message_id, role, content, created_at),
            )
            conn.commit()

        return ChatMessage(id=message_id, role=role, content=content, created_at=created_at)

    def get_chat_history(self, limit: int) -> list[ChatMessage]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at
                FROM chat_messages
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        ordered_rows = list(reversed(rows))
        return [
            ChatMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in ordered_rows
        ]

    @staticmethod
    def _row_to_food_entry(row: sqlite3.Row) -> FoodEntry:
        return FoodEntry(
            id=row["id"],
            name=row["name"],
            calories=int(row["calories"]),
            protein_g=float(row["protein_g"]),
            carbs_g=float(row["carbs_g"]),
            fat_g=float(row["fat_g"]),
            logged_at=row["logged_at"],
            source=row["source"],
        )


LOG_MESSAGE_PATTERN = re.compile(
    r"^\s*log\s+(?P<name>.+?)\s+(?P<calories>\d+(?:\.\d+)?)\s*cal(?:ories)?\s+"
    r"(?P<protein>\d+(?:\.\d+)?)\s*p(?:rotein)?\s+"
    r"(?P<carbs>\d+(?:\.\d+)?)\s*c(?:arbs)?\s+"
    r"(?P<fat>\d+(?:\.\d+)?)\s*f(?:at)?\s*$",
    flags=re.IGNORECASE,
)


def parse_log_message(message: str) -> FoodEntryCreate | None:
    match = LOG_MESSAGE_PATTERN.match(message)
    if not match:
        return None

    return FoodEntryCreate(
        name=match.group("name").strip(),
        calories=int(float(match.group("calories"))),
        protein_g=float(match.group("protein")),
        carbs_g=float(match.group("carbs")),
        fat_g=float(match.group("fat")),
        logged_at=to_utc_iso(utc_now()),
    )


store = SQLiteStore(DB_PATH)
app = FastAPI(title="Claude Hackathon Backend")


@app.exception_handler(APIError)
async def handle_api_error(_request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Request validation failed")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": message}},
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(_request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == 404:
        code = "not_found"
    elif 400 <= exc.status_code < 500:
        code = "invalid_request"
    else:
        code = "server_error"

    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "server_error", "message": "An unexpected error occurred"}},
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/log", response_model=FoodLogResponse)
async def get_log(date: str | None = Query(default=None)) -> FoodLogResponse:
    query_date = date or today_utc_str()
    parse_yyyy_mm_dd(query_date, field_name="date")
    return FoodLogResponse(entries=store.get_log_for_date(query_date))


@app.post("/api/log", response_model=FoodEntry, status_code=status.HTTP_201_CREATED)
async def create_log_entry(payload: FoodEntryCreate) -> FoodEntry:
    return store.insert_food_entry(payload, source="manual")


@app.delete("/api/log/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log_entry(entry_id: str) -> Response:
    deleted = store.delete_food_entry(entry_id)
    if not deleted:
        raise APIError(status_code=404, code="not_found", message="Food entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/dashboard/today", response_model=DailySummary)
async def dashboard_today() -> DailySummary:
    return store.get_daily_summary(today_utc_str())


@app.get("/api/dashboard/history", response_model=DashboardHistoryResponse)
async def dashboard_history(days: int = Query(default=7, ge=1, le=30)) -> DashboardHistoryResponse:
    return DashboardHistoryResponse(days=store.get_dashboard_history(days))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    user_message = payload.message.strip()
    store.insert_chat_message(role="user", content=user_message)

    created_entries: list[FoodEntry] = []
    maybe_entry = parse_log_message(user_message)
    if maybe_entry is not None:
        created_entries.append(store.insert_food_entry(maybe_entry, source="chat"))
        reply = f"Logged 1 item: {created_entries[0].name}."
    else:
        reply = (
            "I can log food for you. Try: "
            "'log grilled chicken 300 cal 40p 0c 8f'."
        )

    store.insert_chat_message(role="assistant", content=reply)
    return ChatResponse(reply=reply, created_entries=created_entries)


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
async def chat_history(limit: int = Query(default=50, ge=1, le=500)) -> ChatHistoryResponse:
    return ChatHistoryResponse(messages=store.get_chat_history(limit))
