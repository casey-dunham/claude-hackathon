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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    lat: float | None = None
    lng: float | None = None


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


class Profile(BaseModel):
    calorie_goal: int | None = None
    protein_goal_g: float | None = None
    carbs_goal_g: float | None = None
    fat_goal_g: float | None = None
    dietary_restrictions: list[str] = Field(default_factory=list)


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
- Keep `entries_to_log` to 10 or fewer items.
- `logged_at` is optional; omit it if unknown.
- Do not include any keys other than `reply` and `entries_to_log`.
- Do not wrap JSON in markdown.
- When nearby_restaurants is provided and the user asks for food suggestions or what to eat, recommend specific dishes from those restaurants. Factor in their remaining calories, macro goals, and dietary restrictions.
- When recommending restaurants, mention the restaurant name, what to order, and estimated macros if known.
- Always respect dietary_restrictions — never suggest food that violates them.
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


def fallback_chat_plan(user_message: str) -> ClaudeChatPlan:
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
        profile: Profile | None = None,
        nearby_restaurants: list[NearbyPlace] | None = None,
    ) -> ClaudeChatPlan:
        if not self.enabled:
            raise APIError(
                status_code=503,
                code="upstream_error",
                message="Claude API key is not configured",
            )

        prompt_payload: dict[str, Any] = {
            "user_message": user_message,
            "utc_now": to_utc_iso(utc_now()),
            "today_summary": _model_to_dict(today_summary),
            "recent_entries_today": [_model_to_dict(entry) for entry in today_entries[-10:]],
        }

        if profile:
            prompt_payload["user_profile"] = {
                "calorie_goal": profile.calorie_goal,
                "protein_goal_g": profile.protein_goal_g,
                "carbs_goal_g": profile.carbs_goal_g,
                "fat_goal_g": profile.fat_goal_g,
                "dietary_restrictions": profile.dietary_restrictions,
            }

        if nearby_restaurants:
            prompt_payload["nearby_restaurants"] = [
                {
                    "name": p.name,
                    "address": p.address,
                    "distance_m": p.distance_m,
                    "rating": p.rating,
                    "price_level": p.price_level,
                    "is_open": p.is_open,
                    "maps_url": p.maps_url,
                }
                for p in nearby_restaurants[:10]
            ]

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

                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    calorie_goal INTEGER,
                    protein_goal_g REAL,
                    carbs_goal_g REAL,
                    fat_goal_g REAL,
                    dietary_restrictions TEXT NOT NULL DEFAULT '[]'
                );

                INSERT OR IGNORE INTO profile (id) VALUES (1);
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

    def get_profile(self) -> Profile:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT calorie_goal, protein_goal_g, carbs_goal_g, fat_goal_g, dietary_restrictions FROM profile WHERE id = 1"
            ).fetchone()
        restrictions = json.loads(row["dietary_restrictions"]) if row["dietary_restrictions"] else []
        return Profile(
            calorie_goal=row["calorie_goal"],
            protein_goal_g=row["protein_goal_g"],
            carbs_goal_g=row["carbs_goal_g"],
            fat_goal_g=row["fat_goal_g"],
            dietary_restrictions=restrictions,
        )

    def update_profile(self, profile: Profile) -> Profile:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE profile SET
                    calorie_goal = ?,
                    protein_goal_g = ?,
                    carbs_goal_g = ?,
                    fat_goal_g = ?,
                    dietary_restrictions = ?
                WHERE id = 1
                """,
                (
                    profile.calorie_goal,
                    profile.protein_goal_g,
                    profile.carbs_goal_g,
                    profile.fat_goal_g,
                    json.dumps(profile.dietary_restrictions),
                ),
            )
            conn.commit()
        return self.get_profile()

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
    profile = store.get_profile()

    nearby_restaurants: list[NearbyPlace] = []
    if payload.lat is not None and payload.lng is not None:
        try:
            nearby_restaurants = await google_places.nearby_restaurants(
                lat=payload.lat,
                lng=payload.lng,
                radius_m=1200,
                limit=10,
            )
        except Exception:
            LOGGER.warning("Failed to fetch nearby places for chat context")

    if claude_chat.enabled:
        try:
            plan = await claude_chat.create_plan(
                user_message=user_message,
                today_summary=today_summary,
                today_entries=today_entries,
                profile=profile,
                nearby_restaurants=nearby_restaurants or None,
            )
        except APIError as exc:
            LOGGER.warning("Claude unavailable (%s): %s", exc.code, exc.message)
            plan = fallback_chat_plan(user_message)
        except Exception:
            LOGGER.exception("Unexpected chat planner failure")
            plan = fallback_chat_plan(user_message)
    else:
        plan = fallback_chat_plan(user_message)

    created_entries: list[FoodEntry] = []
    for draft in plan.entries_to_log[:10]:
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


@app.get("/api/profile", response_model=Profile)
async def get_profile() -> Profile:
    return store.get_profile()


@app.put("/api/profile", response_model=Profile)
async def update_profile(payload: Profile) -> Profile:
    return store.update_profile(payload)
