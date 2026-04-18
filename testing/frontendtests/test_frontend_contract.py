from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient

from testing.assertions import (
    assert_daily_summary_shape,
    assert_food_entry_shape,
    utc_today_str,
)


def test_frontend_bootstrap_healthcheck(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_log_table_contract_shape(client: TestClient) -> None:
    response = client.get("/api/log", params={"date": utc_today_str()})
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, dict)
    assert "entries" in payload
    assert isinstance(payload["entries"], list)
    for entry in payload["entries"]:
        assert_food_entry_shape(entry)


def test_frontend_dashboard_history_chart_contract(client: TestClient) -> None:
    days_requested = 14
    response = client.get("/api/dashboard/history", params={"days": days_requested})
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("days"), list)

    summaries = payload["days"]
    assert len(summaries) == days_requested

    parsed_dates: list[date] = []
    for summary in summaries:
        assert_daily_summary_shape(summary)
        parsed_dates.append(date.fromisoformat(summary["date"]))

    assert parsed_dates == sorted(parsed_dates), "History must be oldest -> newest for charting"


def test_frontend_chat_non_log_message_has_empty_created_entries(client: TestClient) -> None:
    message = f"frontend-general-message-{uuid.uuid4()}"
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("reply"), str)
    assert payload.get("created_entries") == []


def test_frontend_chat_log_message_returns_chat_sourced_entry(client: TestClient) -> None:
    marker = f"frontend-chat-{uuid.uuid4()}"
    response = client.post(
        "/api/chat",
        json={"message": f"log {marker} 225 cal 14p 20c 9f"},
    )
    assert response.status_code == 200

    payload = response.json()
    created_entries = payload.get("created_entries")
    assert isinstance(created_entries, list)
    assert len(created_entries) == 1

    created_entry = created_entries[0]
    assert_food_entry_shape(created_entry)
    assert created_entry["name"] == marker
    assert created_entry["source"] == "chat"

    created_entry_id = created_entry["id"]
    try:
        log_response = client.get("/api/log", params={"date": utc_today_str()})
        assert log_response.status_code == 200
        entries = log_response.json()["entries"]
        assert any(entry["id"] == created_entry_id for entry in entries)
    finally:
        client.delete(f"/api/log/{created_entry_id}")
