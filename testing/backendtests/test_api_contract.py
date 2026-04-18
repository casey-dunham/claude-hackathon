from __future__ import annotations

import importlib
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient


APP_IMPORT_ENV_VAR = "TEST_APP_IMPORT"
DEFAULT_APP_IMPORT = "backend.main:app"


def _parse_utc_datetime(value: Any) -> datetime:
    assert isinstance(value, str), "Expected ISO-8601 datetime string"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"Invalid datetime format: {value}") from exc
    assert parsed.tzinfo is not None, f"Datetime must include timezone: {value}"
    return parsed.astimezone(timezone.utc)


def _assert_uuid(value: Any) -> None:
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

    _assert_uuid(payload["id"])
    assert isinstance(payload["name"], str)
    for numeric_field in ("calories", "protein_g", "carbs_g", "fat_g"):
        assert isinstance(payload[numeric_field], (int, float)), f"{numeric_field} must be numeric"
    _parse_utc_datetime(payload["logged_at"])
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

    _assert_uuid(payload["id"])
    assert payload["role"] in {"user", "assistant"}
    assert isinstance(payload["content"], str)
    _parse_utc_datetime(payload["created_at"])


def _load_backend_app() -> Any:
    import_path = os.getenv(APP_IMPORT_ENV_VAR, DEFAULT_APP_IMPORT)
    if ":" not in import_path:
        pytest.fail(
            f"{APP_IMPORT_ENV_VAR} must be in 'module:attribute' format; got '{import_path}'"
        )

    module_path, attr_name = import_path.split(":", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # pragma: no cover - explicit failure path
        pytest.fail(
            f"Failed to import backend app from '{import_path}'. "
            f"Set {APP_IMPORT_ENV_VAR} if your app uses a different path. Error: {exc}"
        )

    if not hasattr(module, attr_name):
        pytest.fail(f"Module '{module_path}' has no attribute '{attr_name}'")

    app = getattr(module, attr_name)
    if callable(app) and not hasattr(app, "router"):
        app = app()

    return app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(_load_backend_app())


def test_healthcheck_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_log_without_date_returns_entries_list(client: TestClient) -> None:
    response = client.get("/api/log")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "entries" in payload
    assert isinstance(payload["entries"], list)
    for entry in payload["entries"]:
        assert_food_entry_shape(entry)


def test_create_log_entry_and_query_by_date(client: TestClient) -> None:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    marker = f"contract-test-{uuid.uuid4()}"
    request_payload = {
        "name": marker,
        "calories": 250,
        "protein_g": 12,
        "carbs_g": 30,
        "fat_g": 8,
        "logged_at": timestamp,
    }

    create_response = client.post("/api/log", json=request_payload)
    assert create_response.status_code == 201, create_response.text
    created_entry = create_response.json()
    assert_food_entry_shape(created_entry)
    assert created_entry["name"] == marker

    query_response = client.get("/api/log", params={"date": timestamp[:10]})
    assert query_response.status_code == 200
    entries = query_response.json()["entries"]
    assert any(entry["id"] == created_entry["id"] for entry in entries)


def test_delete_log_entry_returns_204_then_404_on_repeat(client: TestClient) -> None:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    create_response = client.post(
        "/api/log",
        json={
            "name": f"delete-test-{uuid.uuid4()}",
            "calories": 180,
            "protein_g": 10,
            "carbs_g": 20,
            "fat_g": 6,
            "logged_at": timestamp,
        },
    )
    assert create_response.status_code == 201, create_response.text
    created_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/log/{created_id}")
    assert delete_response.status_code == 204
    assert delete_response.text in {"", "null"}

    repeat_delete = client.delete(f"/api/log/{created_id}")
    assert repeat_delete.status_code == 404
    assert_error_shape(repeat_delete.json())
    assert repeat_delete.json()["error"]["code"] == "not_found"


def test_dashboard_today_returns_daily_summary(client: TestClient) -> None:
    response = client.get("/api/dashboard/today")
    assert response.status_code == 200
    assert_daily_summary_shape(response.json())


def test_dashboard_history_returns_oldest_to_newest(client: TestClient) -> None:
    response = client.get("/api/dashboard/history", params={"days": 7})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "days" in payload
    assert isinstance(payload["days"], list)

    summaries = payload["days"]
    parsed_dates: list[date] = []
    for summary in summaries:
        assert_daily_summary_shape(summary)
        parsed_dates.append(date.fromisoformat(summary["date"]))

    assert parsed_dates == sorted(parsed_dates), "Dashboard history must be oldest -> newest"


def test_chat_returns_reply_and_created_entries_shape(client: TestClient) -> None:
    marker = f"chat-contract-{uuid.uuid4()}"
    response = client.post("/api/chat", json={"message": f"Echo marker: {marker}"})
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload, dict)
    assert isinstance(payload.get("reply"), str)
    assert isinstance(payload.get("created_entries"), list)
    for created_entry in payload["created_entries"]:
        assert_food_entry_shape(created_entry)


def test_chat_history_returns_messages_oldest_to_newest(client: TestClient) -> None:
    response = client.get("/api/chat/history", params={"limit": 50})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("messages"), list)

    parsed_datetimes: list[datetime] = []
    for message in payload["messages"]:
        assert_chat_message_shape(message)
        parsed_datetimes.append(_parse_utc_datetime(message["created_at"]))

    assert parsed_datetimes == sorted(parsed_datetimes), "Chat history must be oldest -> newest"

