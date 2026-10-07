"""Unit tests for TriageService 3-tier resilience architecture using mocked LLM."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.schemas.ticket import Ticket, TicketCategory, TicketPriority
from src.services.llm import LLMService
from src.services.triage import TriageService


@pytest.fixture
def mock_llm_service():
    """Mock LLMService for offline deterministic testing."""
    service = MagicMock(spec=LLMService)
    return service


@pytest.mark.asyncio
async def test_triage_ticket_success(mock_llm_service):
    """Verify normal successful triage flow."""
    mock_llm_service.generate_json = AsyncMock(
        return_value=json.dumps(
            {
                "category": "billing",
                "priority": "high",
                "summary": "Customer requesting refund for duplicate transaction.",
                "suggested_reply": "We are processing your refund.",
                "suggested_tags": ["billing", "refund"],
                "confidence": 0.95,
                "escalate": False,
            }
        )
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-001", subject="Refund request", body="Please refund my money")

    result = await triage_service.triage_ticket(ticket)
    assert result.ticket_id == "T-001"
    assert result.category == TicketCategory.BILLING
    assert result.priority == TicketPriority.HIGH
    assert result.confidence == 0.95
    assert result.escalate is False


@pytest.mark.asyncio
async def test_triage_ticket_markdown_fences_stripped(mock_llm_service):
    """Verify markdown fences (```json ... ```) are safely stripped."""
    mock_llm_service.generate_json = AsyncMock(
        return_value=(
            "```json\n"
            "{\n"
            '  "category": "bug",\n'
            '  "priority": "medium",\n'
            '  "summary": "Export button not working.",\n'
            '  "suggested_reply": "We are investigating the export bug.",\n'
            '  "confidence": 0.88,\n'
            '  "escalate": false\n'
            "}\n"
            "```"
        )
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-002", subject="Export bug", body="The button does nothing")

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.BUG
    assert result.confidence == 0.88


@pytest.mark.asyncio
async def test_triage_ticket_security_prefilter(mock_llm_service):
    """Verify security keyword pre-filter forces urgent escalation."""
    mock_llm_service.generate_json = AsyncMock(
        return_value=json.dumps(
            {
                "category": "other",
                "priority": "low",
                "summary": "Customer reports something.",
                "suggested_reply": "Thanks.",
                "confidence": 0.8,
                "escalate": False,
            }
        )
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(
        id="T-014",
        subject="Found IDOR vulnerability in API",
        body="I found an IDOR exploit in your system",
    )

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.SECURITY
    assert result.priority == TicketPriority.URGENT
    assert result.escalate is True


@pytest.mark.asyncio
async def test_triage_ticket_self_correction_recovery(mock_llm_service):
    """Verify broken JSON triggers self-correction retry and recovers."""
    # First call fails with invalid JSON, second call succeeds with valid JSON
    mock_llm_service.generate_json = AsyncMock(
        side_effect=[
            "Invalid non-json string from LLM",
            json.dumps(
                {
                    "category": "account",
                    "priority": "medium",
                    "summary": "Password reset needed",
                    "suggested_reply": "Click this link to reset password",
                    "confidence": 0.92,
                    "escalate": False,
                }
            ),
        ]
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-005", subject="Reset password", body="Forgot my password")

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.ACCOUNT
    assert result.confidence == 0.92
    assert mock_llm_service.generate_json.call_count == 2


@pytest.mark.asyncio
async def test_triage_ticket_safe_fallback_on_persistent_failure(mock_llm_service):
    """Verify safe fallback is returned when self-correction also fails."""
    # Both initial call and retry return broken data
    mock_llm_service.generate_json = AsyncMock(
        side_effect=[
            "Invalid output 1",
            "Invalid output 2",
        ]
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-099", subject="Crash test", body="Testing crash fallback")

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.OTHER
    assert result.priority == TicketPriority.MEDIUM
    assert result.escalate is True
    assert result.confidence == 0.0
    assert "fallback" in result.suggested_tags
