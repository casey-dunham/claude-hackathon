from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_today_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def parse_utc_datetime(value: Any) -> datetime:
    assert isinstance(value, str), "Expected ISO-8601 datetime string"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"Invalid datetime format: {value}") from exc
    assert parsed.tzinfo is not None, f"Datetime must include timezone: {value}"
    return parsed.astimezone(timezone.utc)


def assert_uuid(value: Any) -> None:
    assert isinstance(value, str), "Expected UUID string"
    uuid.UUID(value)


def assert_error_shape(payload: Any) -> None:
    assert isinstance(payload, dict), "Error response must be an object"
    assert "error" in payload, "Missing top-level 'error' object"
    assert isinstance(payload["error"], dict), "'error' must be an object"
    assert isinstance(payload["error"].get("code"), str), "error.code must be a string"
    assert isinstance(payload["error"].get("message"), str), "error.message must be a string"


def assert_food_entry_shape(payload: Any) -> None:
    required_keys = {
        "id",
        "name",
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "logged_at",
        "source",
    }
    assert isinstance(payload, dict), "FoodEntry must be an object"
    assert required_keys.issubset(payload.keys()), f"Missing keys: {required_keys - set(payload)}"

    assert_uuid(payload["id"])
    assert isinstance(payload["name"], str)
    for numeric_field in ("calories", "protein_g", "carbs_g", "fat_g"):
        assert isinstance(payload[numeric_field], (int, float)), f"{numeric_field} must be numeric"
    parse_utc_datetime(payload["logged_at"])
    assert payload["source"] in {"manual", "chat"}


def assert_daily_summary_shape(payload: Any) -> None:
    required_keys = {
        "date",
        "total_calories",
        "total_protein_g",
        "total_carbs_g",
        "total_fat_g",
        "entry_count",
    }
    assert isinstance(payload, dict), "DailySummary must be an object"
    assert required_keys.issubset(payload.keys()), f"Missing keys: {required_keys - set(payload)}"

    assert isinstance(payload["date"], str)
    date.fromisoformat(payload["date"])
    for numeric_field in (
        "total_calories",
        "total_protein_g",
        "total_carbs_g",
        "total_fat_g",
        "entry_count",
    ):
        assert isinstance(payload[numeric_field], (int, float)), f"{numeric_field} must be numeric"


def assert_chat_message_shape(payload: Any) -> None:
    required_keys = {"id", "role", "content", "created_at"}
    assert isinstance(payload, dict), "ChatMessage must be an object"
    assert required_keys.issubset(payload.keys()), f"Missing keys: {required_keys - set(payload)}"

    assert_uuid(payload["id"])
    assert payload["role"] in {"user", "assistant"}
    assert isinstance(payload["content"], str)
    parse_utc_datetime(payload["created_at"])
