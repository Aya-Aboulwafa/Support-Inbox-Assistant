"""Integration tests for frontend serving and API integration contract."""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_frontend_ui_route():
    """Verify /ui route serves the frontend HTML document."""
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Penta-Labs" in response.text
    assert "Support Copilot" in response.text


def test_frontend_static_assets():
    """Verify static assets such as api.js are served cleanly."""
    response = client.get("/frontend/js/api.js")
    assert response.status_code == 200
    assert "ApiClient" in response.text


def test_full_frontend_action_api_flow():
    """Verify the full lifecycle of actions performed by the frontend UI."""
    # 1. Health check
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # 2. Ingest new ticket via UI modal action
    new_ticket_payload = {
        "id": "T-UI-TEST",
        "channel": "email",
        "sender": "ui.tester@pentallabs.com",
        "subject": "Integration test for UI frontend",
        "body": "Testing the frontend API integration flow end-to-end.",
        "received_at": "2026-10-07T12:00:00Z"
    }
    create_resp = client.post("/api/v1/tickets", json=new_ticket_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["ticket"]["id"] == "T-UI-TEST"
    assert created_data["status"] == "pending"

    # 3. Retrieve stats
    stats_resp = client.get("/api/v1/tickets/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_tickets"] >= 1

    # 4. Agent edit draft response & notes via PATCH
    patch_resp = client.patch(
        "/api/v1/tickets/T-UI-TEST",
        json={
            "edited_reply": "Custom agent response crafted in the UI draft editor.",
            "notes": "Internal review note verified.",
            "category": "billing",
            "priority": "high"
        }
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["edited_reply"] == "Custom agent response crafted in the UI draft editor."
    assert patched["notes"] == "Internal review note verified."

    # 5. 1-Click Approve action via POST /approve
    approve_resp = client.post(
        "/api/v1/tickets/T-UI-TEST/approve",
        json={"final_reply": "Final verified reply sent to customer."}
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.json()
    assert approved["status"] == "approved"
    assert approved["updated_at"] is not None

    # 6. Escalate another ticket via POST /escalate
    escalate_resp = client.post(
        "/api/v1/tickets/T-UI-TEST/escalate",
        json={"reason": "Escalating for integration verification"}
    )
    assert escalate_resp.status_code == 200
    escalated = escalate_resp.json()
    assert escalated["status"] == "escalated"
    assert escalated["updated_at"] is not None
