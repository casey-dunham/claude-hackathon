from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("LITESQL_PATH", BASE_DIR / "health.db"))
LOGGER = logging.getLogger(__name__)


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


class ChatContext(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    local_time: str | None = Field(default=None, min_length=1, max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    context: ChatContext | None = None


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


class NearbyPlace(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    address: str
    rating: float | None = None
    user_ratings_total: int | None = None
    price_level: int | None = None
    is_open: bool | None = None
    distance_m: int
    maps_url: str


class NearbyPlacesResponse(BaseModel):
    places: list[NearbyPlace]


class ClaudeFoodEntryDraft(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    calories: int = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    logged_at: str | None = None


class ClaudeChatPlan(BaseModel):
    reply: str = Field(min_length=1, max_length=4000)
    entries_to_log: list[ClaudeFoodEntryDraft] = Field(default_factory=list)


CLAUDE_SYSTEM_PROMPT = """
You are the assistant inside a nutrition tracking app.

Return ONLY valid JSON with exactly this shape:
{
  "reply": "string",
  "entries_to_log": [
    {
      "name": "string",
      "calories": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "logged_at": "2026-04-18T14:30:00Z"
    }
  ]
}

Behavior rules:
- Use `entries_to_log` only when the user asks to log/add food.
- If nutrition values are missing or uncertain, ask a follow-up question in `reply` and keep `entries_to_log` empty.
- You may include recommendations/coaching in `reply` when asked.
- When recommendations are requested, use `chat_context.local_time`, `chat_context.meal_window`, and `chat_context.nearby_restaurants`.
- If nearby restaurants are available, mention 2-4 places by name and explain why they fit the meal timing and nutrition goal.
- Use `today_summary` and `recent_entries_today` to keep recommendations aligned with the current day.
- Keep `entries_to_log` to 10 or fewer items.
- `logged_at` is optional; omit it if unknown.
- Do not include any keys other than `reply` and `entries_to_log`.
- Do not wrap JSON in markdown.
""".strip()


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()  # type: ignore[call-arg]


def _validate_claude_plan(payload: dict[str, Any]) -> ClaudeChatPlan:
    if hasattr(ClaudeChatPlan, "model_validate"):
        return ClaudeChatPlan.model_validate(payload)  # type: ignore[attr-defined]
    return ClaudeChatPlan.parse_obj(payload)


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_logged_at(value: str | None) -> str:
    if value is None or not value.strip():
        return to_utc_iso(utc_now())
    try:
        parsed = parse_iso8601_utc(value, field_name="logged_at")
        return to_utc_iso(parsed)
    except APIError:
        return to_utc_iso(utc_now())


def parse_optional_iso_datetime(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def resolve_timezone(value: str | None) -> ZoneInfo | None:
    if value is None:
        return None

    tz_name = value.strip()
    if not tz_name:
        return None

    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        LOGGER.warning("Invalid timezone provided in chat context: %s", tz_name)
        return None


def meal_window_for_hour(hour: int) -> str:
    if 5 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 15:
        return "lunch"
    if 15 <= hour < 17:
        return "afternoon_snack"
    if 17 <= hour < 22:
        return "dinner"
    return "late_night"


def resolve_chat_time_context(context: ChatContext | None) -> tuple[datetime, str, str]:
    tzinfo = resolve_timezone(context.timezone if context else None)
    parsed_local = parse_optional_iso_datetime(context.local_time if context else None)

    if parsed_local is None:
        local_dt = utc_now().astimezone(tzinfo or timezone.utc)
    else:
        if parsed_local.tzinfo is None:
            local_dt = parsed_local.replace(tzinfo=tzinfo or timezone.utc)
        elif tzinfo is not None:
            local_dt = parsed_local.astimezone(tzinfo)
        else:
            local_dt = parsed_local

    if context and context.timezone and tzinfo is not None:
        timezone_name = context.timezone.strip()
    else:
        timezone_name = str(local_dt.tzinfo) if local_dt.tzinfo is not None else "UTC"
    meal_window = meal_window_for_hour(local_dt.hour)
    return local_dt, timezone_name, meal_window


def nearby_places_for_prompt(places: list[NearbyPlace]) -> list[dict[str, Any]]:
    return [
        {
            "name": place.name,
            "address": place.address,
            "distance_m": place.distance_m,
            "rating": place.rating,
            "price_level": place.price_level,
            "is_open": place.is_open,
        }
        for place in places
    ]


def fallback_chat_plan(
    user_message: str,
    *,
    meal_window: str | None = None,
    nearby_places: list[NearbyPlace] | None = None,
) -> ClaudeChatPlan:
    maybe_entry = parse_log_message(user_message)
    if maybe_entry is not None:
        return ClaudeChatPlan(
            reply=f"Logged 1 item: {maybe_entry.name}.",
            entries_to_log=[
                ClaudeFoodEntryDraft(
                    name=maybe_entry.name,
                    calories=maybe_entry.calories,
                    protein_g=maybe_entry.protein_g,
                    carbs_g=maybe_entry.carbs_g,
                    fat_g=maybe_entry.fat_g,
                    logged_at=maybe_entry.logged_at,
                )
            ],
        )

    nearby_places = nearby_places or []
    user_text = user_message.lower()
    wants_recommendations = any(
        token in user_text
        for token in ("recommend", "nearby", "restaurant", "food", "meal", "eat", "breakfast", "lunch", "dinner")
    )

    if wants_recommendations and nearby_places:
        nearby_lines: list[str] = []
        for place in nearby_places[:3]:
            rating_label = f", {place.rating:.1f}★" if place.rating is not None else ""
            open_label = "open now" if place.is_open is True else "currently closed" if place.is_open is False else "hours unknown"
            nearby_lines.append(f"{place.name} ({place.distance_m}m away{rating_label}, {open_label})")

        meal_label = (meal_window or "current").replace("_", " ")
        return ClaudeChatPlan(
            reply=(
                f"For {meal_label}, here are nearby options: "
                + "; ".join(nearby_lines)
                + ". Tell me your macro target and I can narrow this further."
            ),
            entries_to_log=[],
        )

    return ClaudeChatPlan(
        reply=(
            "I can log food and suggest recommendations. "
            "Try 'log grilled chicken 300 cal 40p 0c 8f' or ask for meal ideas."
        ),
        entries_to_log=[],
    )


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    earth_radius_m = 6_371_000
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    delta_lat = lat2_rad - lat1_rad
    delta_lng = lng2_rad - lng1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(earth_radius_m * c))


class GooglePlacesEngine:
    api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def nearby_restaurants(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int,
    ) -> list[NearbyPlace]:
        if not self.enabled:
            raise APIError(
                status_code=503,
                code="upstream_error",
                message="Google Maps API key is not configured",
            )

        params = {
            "key": self.api_key,
            "location": f"{lat},{lng}",
            "radius": str(radius_m),
            "type": "restaurant",
            "keyword": "healthy food",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(self.api_url, params=params)
        except httpx.HTTPError as exc:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Google Places request failed: {exc.__class__.__name__}",
            ) from exc

        if response.status_code >= 400:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Google Places request failed with status {response.status_code}",
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message="Google Places returned invalid JSON",
            ) from exc

        google_status = str(payload.get("status", ""))
        if google_status == "ZERO_RESULTS":
            return []
        if google_status != "OK":
            upstream_message = payload.get("error_message")
            message_suffix = f": {upstream_message}" if isinstance(upstream_message, str) else ""
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Google Places request failed ({google_status}){message_suffix}",
            )

        results = payload.get("results")
        if not isinstance(results, list):
            return []

        places: list[NearbyPlace] = []
        for result in results:
            if not isinstance(result, dict):
                continue

            place_id = result.get("place_id")
            name = result.get("name")
            if not isinstance(place_id, str) or not isinstance(name, str):
                continue

            geometry = result.get("geometry")
            location = geometry.get("location") if isinstance(geometry, dict) else None
            place_lat = location.get("lat") if isinstance(location, dict) else None
            place_lng = location.get("lng") if isinstance(location, dict) else None
            if not isinstance(place_lat, (float, int)) or not isinstance(place_lng, (float, int)):
                continue

            address_raw = result.get("vicinity")
            if not isinstance(address_raw, str) or not address_raw.strip():
                formatted_address = result.get("formatted_address")
                address = formatted_address.strip() if isinstance(formatted_address, str) else "Address unavailable"
            else:
                address = address_raw.strip()

            rating_raw = result.get("rating")
            rating = float(rating_raw) if isinstance(rating_raw, (float, int)) else None

            ratings_count_raw = result.get("user_ratings_total")
            ratings_count = int(ratings_count_raw) if isinstance(ratings_count_raw, int) else None

            price_level_raw = result.get("price_level")
            price_level = int(price_level_raw) if isinstance(price_level_raw, int) else None

            opening_hours = result.get("opening_hours")
            open_now_raw = opening_hours.get("open_now") if isinstance(opening_hours, dict) else None
            is_open = open_now_raw if isinstance(open_now_raw, bool) else None

            places.append(
                NearbyPlace(
                    id=place_id,
                    name=name,
                    lat=float(place_lat),
                    lng=float(place_lng),
                    address=address,
                    rating=rating,
                    user_ratings_total=ratings_count,
                    price_level=price_level,
                    is_open=is_open,
                    distance_m=haversine_distance_m(lat, lng, float(place_lat), float(place_lng)),
                    maps_url=f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                )
            )

        places.sort(key=lambda place: place.distance_m)
        return places[:limit]


class ClaudeChatEngine:
    api_url = "https://api.anthropic.com/v1/messages"
    anthropic_version = "2023-06-01"

    def __init__(self) -> None:
        self.api_key = os.getenv("CLAUDE_API_KEY", "").strip()
        self.model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6").strip() or "claude-opus-4-6"
        timeout_raw = os.getenv("CLAUDE_TIMEOUT_SECONDS", "8").strip()
        try:
            self.timeout_seconds = max(1.0, float(timeout_raw))
        except ValueError:
            self.timeout_seconds = 8.0

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def create_plan(
        self,
        *,
        user_message: str,
        today_summary: DailySummary,
        today_entries: list[FoodEntry],
        chat_context: dict[str, Any] | None = None,
    ) -> ClaudeChatPlan:
        if not self.enabled:
            raise APIError(
                status_code=503,
                code="upstream_error",
                message="Claude API key is not configured",
            )

        prompt_payload = {
            "user_message": user_message,
            "utc_now": to_utc_iso(utc_now()),
            "today_summary": _model_to_dict(today_summary),
            "recent_entries_today": [_model_to_dict(entry) for entry in today_entries[-10:]],
            "chat_context": chat_context or {},
        }

        request_payload = {
            "model": self.model,
            "max_tokens": 700,
            "temperature": 0.2,
            "system": CLAUDE_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": json.dumps(prompt_payload, ensure_ascii=True)}],
                }
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.api_url, headers=headers, json=request_payload)
        except httpx.HTTPError as exc:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Claude request failed: {exc.__class__.__name__}",
            ) from exc

        if response.status_code >= 400:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Claude request failed with status {response.status_code}",
            )

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message="Claude returned invalid JSON",
            ) from exc

        text_output = self._extract_text(response_payload)
        plan_payload = extract_json_object(text_output)
        if plan_payload is None:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message="Claude response did not contain a valid JSON plan",
            )

        try:
            return _validate_claude_plan(plan_payload)
        except ValidationError as exc:
            raise APIError(
                status_code=502,
                code="upstream_error",
                message=f"Claude response did not match expected shape: {exc.errors()}",
            ) from exc

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if not isinstance(content, list):
            return ""
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts).strip()


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

DELETE_INTENT_PATTERN = re.compile(r"\b(delete|remove|unlog|undo)\b", flags=re.IGNORECASE)
DELETE_LOG_CONTEXT_PATTERN = re.compile(
    r"\b(log|logged|add|added|track|tracked|entry|entries|tracker|food\s*log|meal\s*log)\b",
    flags=re.IGNORECASE,
)
EXPLICIT_DELETE_COMMAND_PATTERN = re.compile(r"^\s*(delete|unlog)\b", flags=re.IGNORECASE)
DELETE_LAST_PATTERN = re.compile(r"\b(delete|remove|unlog|undo)\s+(?:the\s+)?(last|latest)\b", flags=re.IGNORECASE)
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    flags=re.IGNORECASE,
)
DELETE_NAME_PATTERN = re.compile(
    r"\b(?:delete|remove|unlog)\s+(?:the\s+)?(?:entry\s+)?(?P<name>.+)$",
    flags=re.IGNORECASE,
)
LOG_CREATE_INTENT_PATTERN = re.compile(r"\b(log|add|track)\b", flags=re.IGNORECASE)
DELETE_TOKEN_STOPWORDS = {
    "a",
    "an",
    "the",
    "my",
    "our",
    "your",
    "this",
    "that",
    "it",
    "meal",
    "food",
    "entry",
    "item",
    "i",
    "we",
    "logged",
    "added",
    "tracked",
    "earlier",
    "today",
    "yesterday",
    "just",
    "please",
    "from",
    "in",
    "log",
}


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


def normalize_delete_name(raw_name: str) -> str:
    trimmed = raw_name.strip().lower()
    trimmed = re.sub(r"\b(from|in)\s+(my|the)?\s*log\b.*$", "", trimmed)
    trimmed = re.sub(r"\b(?:that\s+)?(?:i|we)\s+(?:logged|added|tracked)\b.*$", "", trimmed)
    trimmed = re.sub(r"\b(?:earlier|today|yesterday|just now)\b.*$", "", trimmed)
    trimmed = re.sub(r"^(the|my|our|a|an)\s+", "", trimmed)
    trimmed = re.sub(r"\b(today|please)\b", "", trimmed)
    trimmed = re.sub(r"[^\w\s-]", "", trimmed)
    return " ".join(trimmed.split())


def resolve_delete_target(message: str, entries: list[FoodEntry]) -> tuple[FoodEntry | None, bool]:
    has_delete_verb = DELETE_INTENT_PATTERN.search(message) is not None
    if not has_delete_verb:
        return None, False

    has_log_context = DELETE_LOG_CONTEXT_PATTERN.search(message) is not None
    has_explicit_command = EXPLICIT_DELETE_COMMAND_PATTERN.search(message) is not None
    has_last_phrase = DELETE_LAST_PATTERN.search(message) is not None
    has_uuid = UUID_PATTERN.search(message) is not None
    clear_delete_signal = has_log_context or has_explicit_command or has_last_phrase or has_uuid

    if not entries:
        return None, clear_delete_signal

    ordered_entries = sorted(entries, key=lambda entry: entry.logged_at, reverse=True)
    lowered_message = message.lower()

    if has_last_phrase or "last" in lowered_message or "latest" in lowered_message:
        return ordered_entries[0], True

    id_match = UUID_PATTERN.search(message)
    if id_match is not None:
        target_id = id_match.group(0).lower()
        for entry in ordered_entries:
            if entry.id.lower() == target_id:
                return entry, True

    name_match = DELETE_NAME_PATTERN.search(message)
    if name_match is not None:
        normalized_query = normalize_delete_name(name_match.group("name"))
        if normalized_query:
            for entry in ordered_entries:
                if entry.name.strip().lower() == normalized_query:
                    return entry, True

            query_tokens = [
                token
                for token in normalized_query.split()
                if token and token not in DELETE_TOKEN_STOPWORDS
            ]
            if query_tokens:
                for entry in ordered_entries:
                    name_lower = entry.name.strip().lower()
                    if all(token in name_lower for token in query_tokens):
                        return entry, True

    return None, clear_delete_signal


store = SQLiteStore(DB_PATH)
claude_chat = ClaudeChatEngine()
google_places = GooglePlacesEngine()
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


@app.get("/api/maps/nearby", response_model=NearbyPlacesResponse)
async def maps_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(default=1200, ge=100, le=50000),
    limit: int = Query(default=12, ge=1, le=20),
) -> NearbyPlacesResponse:
    places = await google_places.nearby_restaurants(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        limit=limit,
    )
    return NearbyPlacesResponse(places=places)


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

    today = today_utc_str()
    today_summary = store.get_daily_summary(today)
    today_entries = store.get_log_for_date(today)
    local_dt, timezone_name, meal_window = resolve_chat_time_context(payload.context)

    delete_target, is_delete_intent = resolve_delete_target(user_message, today_entries)
    if is_delete_intent:
        if delete_target is None:
            if not today_entries:
                reply = "There are no entries in today's log to delete."
            else:
                recent_names = ", ".join(entry.name for entry in sorted(today_entries, key=lambda e: e.logged_at, reverse=True)[:3])
                reply = (
                    "I couldn't find a matching entry to delete. "
                    f"Try 'delete last' or use one of: {recent_names}."
                )
            store.insert_chat_message(role="assistant", content=reply)
            return ChatResponse(reply=reply, created_entries=[])

        deleted = store.delete_food_entry(delete_target.id)
        if deleted:
            reply = (
                f"Deleted '{delete_target.name}' from today's log "
                f"({delete_target.calories} cal, {delete_target.protein_g:.0f}p/{delete_target.carbs_g:.0f}c/{delete_target.fat_g:.0f}f)."
            )
        else:
            reply = "I couldn't delete that entry because it was already removed."
        store.insert_chat_message(role="assistant", content=reply)
        return ChatResponse(reply=reply, created_entries=[])

    lat = payload.context.lat if payload.context else None
    lng = payload.context.lng if payload.context else None
    nearby_places: list[NearbyPlace] = []
    if lat is not None and lng is not None and google_places.enabled:
        try:
            nearby_places = await google_places.nearby_restaurants(
                lat=lat,
                lng=lng,
                radius_m=1800,
                limit=8,
            )
        except APIError as exc:
            LOGGER.warning("Google Places unavailable during chat (%s): %s", exc.code, exc.message)
        except Exception:
            LOGGER.exception("Unexpected Google Places failure during chat")

    chat_prompt_context = {
        "local_time": local_dt.isoformat(),
        "timezone": timezone_name,
        "meal_window": meal_window,
        "location": {"lat": lat, "lng": lng} if lat is not None and lng is not None else None,
        "nearby_restaurants": nearby_places_for_prompt(nearby_places),
    }

    if claude_chat.enabled:
        try:
            plan = await claude_chat.create_plan(
                user_message=user_message,
                today_summary=today_summary,
                today_entries=today_entries,
                chat_context=chat_prompt_context,
            )
        except APIError as exc:
            LOGGER.warning("Claude unavailable (%s): %s", exc.code, exc.message)
            plan = fallback_chat_plan(
                user_message,
                meal_window=meal_window,
                nearby_places=nearby_places,
            )
        except Exception:
            LOGGER.exception("Unexpected chat planner failure")
            plan = fallback_chat_plan(
                user_message,
                meal_window=meal_window,
                nearby_places=nearby_places,
            )
    else:
        plan = fallback_chat_plan(
            user_message,
            meal_window=meal_window,
            nearby_places=nearby_places,
        )

    created_entries: list[FoodEntry] = []
    allow_log_creation = bool(LOG_CREATE_INTENT_PATTERN.search(user_message))
    entries_to_insert = plan.entries_to_log[:10] if allow_log_creation else []
    if plan.entries_to_log and not allow_log_creation:
        LOGGER.info("Ignoring Claude entries_to_log because user message did not request log adjustment")

    for draft in entries_to_insert:
        payload_to_insert = FoodEntryCreate(
            name=draft.name,
            calories=draft.calories,
            protein_g=draft.protein_g,
            carbs_g=draft.carbs_g,
            fat_g=draft.fat_g,
            logged_at=normalize_logged_at(draft.logged_at),
        )
        try:
            created_entries.append(store.insert_food_entry(payload_to_insert, source="chat"))
        except APIError:
            LOGGER.warning("Skipping invalid Claude-generated entry: %s", payload_to_insert)

    reply = plan.reply.strip()
    if not reply:
        if created_entries:
            noun = "item" if len(created_entries) == 1 else "items"
            reply = f"Logged {len(created_entries)} {noun}."
        else:
            reply = (
                "I can log food and suggest recommendations. "
                "Try 'log grilled chicken 300 cal 40p 0c 8f' or ask for meal ideas."
            )

    store.insert_chat_message(role="assistant", content=reply)
    return ChatResponse(reply=reply, created_entries=created_entries)


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
async def chat_history(limit: int = Query(default=50, ge=1, le=500)) -> ChatHistoryResponse:
    return ChatHistoryResponse(messages=store.get_chat_history(limit))
