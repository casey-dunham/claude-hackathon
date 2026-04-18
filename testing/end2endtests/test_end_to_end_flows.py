from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from testing.assertions import (
    assert_chat_message_shape,
    assert_daily_summary_shape,
    assert_food_entry_shape,
    utc_iso_now,
    utc_today_str,
)


def _today_summary(client: TestClient) -> dict:
    response = client.get("/api/dashboard/today")
    assert response.status_code == 200
    payload = response.json()
    assert_daily_summary_shape(payload)
    return payload


def test_manual_food_entry_lifecycle_updates_dashboard_and_log(client: TestClient) -> None:
    before_summary = _today_summary(client)
    marker = f"e2e-manual-{uuid.uuid4()}"
    request_payload = {
        "name": marker,
        "calories": 410,
        "protein_g": 31.5,
        "carbs_g": 44.0,
        "fat_g": 12.0,
        "logged_at": utc_iso_now(),
    }

    created_id: str | None = None
    try:
        create_response = client.post("/api/log", json=request_payload)
        assert create_response.status_code == 201, create_response.text
        created_entry = create_response.json()
        assert_food_entry_shape(created_entry)
        assert created_entry["source"] == "manual"
        assert created_entry["name"] == marker
        created_id = created_entry["id"]

        log_response = client.get("/api/log", params={"date": utc_today_str()})
        assert log_response.status_code == 200
        entries = log_response.json()["entries"]
        assert any(entry["id"] == created_id for entry in entries)

        after_create_summary = _today_summary(client)
        assert after_create_summary["entry_count"] == before_summary["entry_count"] + 1
        assert after_create_summary["total_calories"] == before_summary["total_calories"] + 410
        assert after_create_summary["total_protein_g"] == pytest.approx(
            before_summary["total_protein_g"] + 31.5
        )
        assert after_create_summary["total_carbs_g"] == pytest.approx(
            before_summary["total_carbs_g"] + 44.0
        )
        assert after_create_summary["total_fat_g"] == pytest.approx(
            before_summary["total_fat_g"] + 12.0
        )

        delete_response = client.delete(f"/api/log/{created_id}")
        assert delete_response.status_code == 204
        created_id = None

        log_after_delete = client.get("/api/log", params={"date": utc_today_str()})
        assert log_after_delete.status_code == 200
        assert all(entry["id"] != created_entry["id"] for entry in log_after_delete.json()["entries"])
    finally:
        if created_id is not None:
            client.delete(f"/api/log/{created_id}")

    after_delete_summary = _today_summary(client)
    assert after_delete_summary["entry_count"] == before_summary["entry_count"]
    assert after_delete_summary["total_calories"] == before_summary["total_calories"]
    assert after_delete_summary["total_protein_g"] == pytest.approx(before_summary["total_protein_g"])
    assert after_delete_summary["total_carbs_g"] == pytest.approx(before_summary["total_carbs_g"])
    assert after_delete_summary["total_fat_g"] == pytest.approx(before_summary["total_fat_g"])


def test_chat_log_flow_creates_entry_and_records_history(client: TestClient) -> None:
    marker = f"e2e-chat-{uuid.uuid4()}"
    user_message = f"log {marker} 333 cal 22p 35c 11f"

    chat_response = client.post("/api/chat", json={"message": user_message})
    assert chat_response.status_code == 200
    chat_payload = chat_response.json()
    assert isinstance(chat_payload.get("reply"), str)

    created_entries = chat_payload.get("created_entries")
    assert isinstance(created_entries, list)
    assert len(created_entries) == 1
    created_entry = created_entries[0]
    assert_food_entry_shape(created_entry)
    assert created_entry["name"] == marker
    assert created_entry["source"] == "chat"

    created_id = created_entry["id"]
    try:
        log_response = client.get("/api/log", params={"date": utc_today_str()})
        assert log_response.status_code == 200
        assert any(entry["id"] == created_id for entry in log_response.json()["entries"])

        history_response = client.get("/api/chat/history", params={"limit": 100})
        assert history_response.status_code == 200
        history_payload = history_response.json()
        messages = history_payload.get("messages")
        assert isinstance(messages, list)
        for message in messages:
            assert_chat_message_shape(message)

        assert any(
            message["role"] == "user" and message["content"] == user_message for message in messages
        )
        assert any(
            message["role"] == "assistant" and message["content"] == chat_payload["reply"]
            for message in messages
        )
    finally:
        client.delete(f"/api/log/{created_id}")
