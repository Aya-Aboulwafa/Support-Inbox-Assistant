"""Unit tests for Pydantic schema validation and business rules."""

import pytest
from pydantic import ValidationError
from src.schemas.ticket import Ticket, TicketCategory, TicketPriority, TriageResult


def test_ticket_parsing_with_alias():
    """Verify Ticket model correctly maps 'from' alias and extra fields."""
    raw = {
        "id": "T-100",
        "from": "user@example.com",
        "subject": "Need help with login",
        "body": "Cannot login to my account",
        "channel": "email",
        "unrecognized_field": 1234,
    }
    ticket = Ticket.model_validate(raw)
    assert ticket.id == "T-100"
    assert ticket.sender == "user@example.com"
    assert ticket.subject == "Need help with login"
    assert ticket.channel == "email"


def test_triage_result_normalization():
    """Verify category and priority strings are normalized (case and whitespace)."""
    raw = {
        "category": " BILLING ",
        "priority": "HIGH ",
        "summary": "Customer billing inquiry",
        "suggested_reply": "We will review your invoice.",
        "confidence": 0.95,
        "escalate": False,
    }
    result = TriageResult.model_validate(raw)
    assert result.category == TicketCategory.BILLING
    assert result.priority == TicketPriority.HIGH
    assert result.escalate is False


def test_triage_result_auto_escalation_security():
    """Verify security category automatically enforces escalate=True."""
    raw = {
        "category": "security",
        "priority": "medium",
        "summary": "Vulnerability report",
        "suggested_reply": "Thank you for the disclosure.",
        "confidence": 0.99,
        "escalate": False,
    }
    result = TriageResult.model_validate(raw)
    assert result.escalate is True


def test_triage_result_auto_escalation_urgent():
    """Verify urgent priority automatically enforces escalate=True."""
    raw = {
        "category": "bug",
        "priority": "urgent",
        "summary": "Outage on production server",
        "suggested_reply": "Investigating now.",
        "confidence": 0.9,
        "escalate": False,
    }
    result = TriageResult.model_validate(raw)
    assert result.escalate is True


def test_triage_result_auto_escalation_low_confidence():
    """Verify confidence below 0.7 enforces escalate=True."""
    raw = {
        "category": "feature_request",
        "priority": "low",
        "summary": "Unclear suggestion",
        "suggested_reply": "Could you provide more details?",
        "confidence": 0.45,
        "escalate": False,
    }
    result = TriageResult.model_validate(raw)
    assert result.escalate is True


def test_triage_result_confidence_range_validation():
    """Verify out-of-bounds confidence values raise ValidationError."""
    with pytest.raises(ValidationError):
        TriageResult(
            category=TicketCategory.OTHER,
            priority=TicketPriority.LOW,
            summary="test",
            confidence=1.5,
        )
