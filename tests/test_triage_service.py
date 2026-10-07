"""Unit tests for TriageService 3-tier resilience architecture using Instructor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from instructor.core import InstructorRetryException

from src.schemas.ticket import Ticket, TicketCategory, TicketPriority, TriageResult
from src.services.llm import LLMService
from src.services.triage import TriageService


@pytest.fixture
def mock_llm_service():
    """Mock LLMService with instructor_client for offline deterministic testing."""
    service = MagicMock(spec=LLMService)
    service.model = "llama3.2:3b"
    service.instructor_client = MagicMock()
    service.instructor_client.chat = MagicMock()
    service.instructor_client.chat.completions = MagicMock()
    return service


@pytest.mark.asyncio
async def test_triage_ticket_success(mock_llm_service):
    """Verify normal successful triage flow via Instructor."""
    expected_result = TriageResult(
        category=TicketCategory.BILLING,
        priority=TicketPriority.HIGH,
        summary="Customer requesting refund for duplicate transaction.",
        suggested_reply="We are processing your refund.",
        suggested_tags=["billing", "refund"],
        confidence=0.95,
        escalate=False,
    )
    mock_llm_service.instructor_client.chat.completions.create = AsyncMock(
        return_value=expected_result
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
async def test_triage_ticket_security_prefilter(mock_llm_service):
    """Verify security keyword pre-filter forces urgent escalation regardless of LLM output."""
    normal_result = TriageResult(
        category=TicketCategory.OTHER,
        priority=TicketPriority.LOW,
        summary="Security report.",
        suggested_reply="Thanks.",
        confidence=0.8,
        escalate=False,
    )
    mock_llm_service.instructor_client.chat.completions.create = AsyncMock(
        return_value=normal_result
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
async def test_triage_ticket_safe_fallback_on_instructor_retry_exhausted(mock_llm_service):
    """Verify safe fallback is returned when Instructor exhausts retries."""
    mock_llm_service.instructor_client.chat.completions.create = AsyncMock(
        side_effect=InstructorRetryException(
            n_attempts=2,
            total_usage=None,
            failed_attempts=[],
        )
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-099", subject="Crash test", body="Testing crash fallback")

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.OTHER
    assert result.priority == TicketPriority.MEDIUM
    assert result.escalate is True
    assert result.confidence == 0.0
    assert "fallback" in result.suggested_tags


@pytest.mark.asyncio
async def test_triage_ticket_safe_fallback_on_network_error(mock_llm_service):
    """Verify safe fallback is returned on connection or runtime error."""
    mock_llm_service.instructor_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("Connection refused")
    )

    triage_service = TriageService(llm_service=mock_llm_service)
    ticket = Ticket(id="T-100", subject="Offline server", body="Server is down")

    result = await triage_service.triage_ticket(ticket)
    assert result.category == TicketCategory.OTHER
    assert result.escalate is True
    assert result.confidence == 0.0
