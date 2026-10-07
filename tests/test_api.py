"""Integration tests for API endpoints and Review Queue lifecycle."""

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.schemas.ticket import TicketCategory, TicketPriority, TriageResult
from src.services.triage import get_triage_service

client = TestClient(app)


def test_root_endpoint():
    """Verify root status endpoint returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "app" in data


def test_health_endpoint():
    """Verify api/v1/health endpoint returns healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_list_tickets_and_stats():
    """Verify GET /api/v1/tickets and /api/v1/tickets/stats."""
    # List tickets
    response = client.get("/api/v1/tickets?limit=10")
    assert response.status_code == 200
    tickets = response.json()
    assert isinstance(tickets, list)
    assert len(tickets) <= 10

    # Get queue stats
    stats_resp = client.get("/api/v1/tickets/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_tickets" in stats
    assert "by_status" in stats


def test_create_and_get_ticket():
    """Verify POST /api/v1/tickets creates a ticket and GET returns it."""
    payload = {
        "id": "T-API-01",
        "subject": "Can't access invoice PDF",
        "body": "Download button returns 403 error",
        "from": "accounting@corp.example",
        "channel": "email",
    }
    create_resp = client.post("/api/v1/tickets", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["ticket"]["id"] == "T-API-01"
    assert created["status"] == "pending"

    # Get details
    get_resp = client.get("/api/v1/tickets/T-API-01")
    assert get_resp.status_code == 200
    assert get_resp.json()["ticket"]["subject"] == "Can't access invoice PDF"

    # Non-existent ticket returns 404
    assert client.get("/api/v1/tickets/NON_EXISTENT").status_code == 404


def test_patch_ticket_edit_reply_and_reclassify():
    """Verify PATCH /api/v1/tickets/{id} updates reply and reclassifies priority."""
    # Ensure ticket exists
    ticket_payload = {
        "id": "T-API-PATCH",
        "subject": "Need seat upgrade",
        "body": "Want to add 5 more users",
    }
    client.post("/api/v1/tickets", json=ticket_payload)

    # Patch ticket with edited reply and reclassified priority
    patch_payload = {
        "edited_reply": "Hi there, I can help you add 5 seats immediately.",
        "priority": "high",
        "notes": "VIP customer request",
    }
    patch_resp = client.patch("/api/v1/tickets/T-API-PATCH", json=patch_payload)
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["edited_reply"] == "Hi there, I can help you add 5 seats immediately."
    assert data["notes"] == "VIP customer request"


def test_approve_and_escalate_actions():
    """Verify 1-click approve and escalate actions."""
    ticket_payload = {
        "id": "T-API-ACTIONS",
        "subject": "Action test ticket",
        "body": "Testing approve and escalate buttons",
    }
    client.post("/api/v1/tickets", json=ticket_payload)

    # Approve action
    approve_resp = client.post(
        "/api/v1/tickets/T-API-ACTIONS/approve",
        json={"final_reply": "Approved response sent to user."},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"
    assert approve_resp.json()["edited_reply"] == "Approved response sent to user."

    # Escalate action
    escalate_resp = client.post(
        "/api/v1/tickets/T-API-ACTIONS/escalate",
        json={"reason": "Requires engineering team review"},
    )
    assert escalate_resp.status_code == 200
    assert escalate_resp.json()["status"] == "escalated"


def test_stateless_triage_endpoint():
    """Verify POST /api/v1/triage executes AI triage."""
    mock_service = AsyncMock()
    mock_service.triage_ticket.return_value = TriageResult(
        ticket_id="T-999",
        category=TicketCategory.BILLING,
        priority=TicketPriority.HIGH,
        summary="Refund request",
        suggested_reply="Refund is on the way.",
        confidence=0.98,
        escalate=False,
    )

    app.dependency_overrides[get_triage_service] = lambda: mock_service
    try:
        response = client.post(
            "/api/v1/triage",
            json={
                "id": "T-999",
                "subject": "Refund please",
                "body": "Accidental charge on my account",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "billing"
        assert data["priority"] == "high"
        assert data["confidence"] == 0.98
    finally:
        app.dependency_overrides.clear()
