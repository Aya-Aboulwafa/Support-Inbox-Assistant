"""Triage service implementing resilient 3-tier classification and analysis using Instructor."""

from typing import Optional
from instructor.core import InstructorRetryException

from src.core.logging import logger
from src.schemas.ticket import Ticket, TicketCategory, TicketPriority, TriageResult
from src.services.llm import LLMService, get_llm_service
from src.services.prompts import build_triage_messages


SECURITY_KEYWORDS = {
    "idor",
    "vulnerability",
    "exploit",
    "breach",
    "sql injection",
    "xss",
    "rce",
    "security disclosure",
    "leaked credentials",
}


class TriageService:
    """Resilient business logic service for triaging support inbox tickets using Instructor."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def _detect_security_signal(self, ticket: Ticket) -> bool:
        """Tier 1 Pre-filter: Check for critical security triggers in subject or body."""
        combined = f"{ticket.subject} {ticket.body}".lower()
        return any(kw in combined for kw in SECURITY_KEYWORDS)

    def _build_safe_fallback(self, ticket: Ticket, reason: str) -> TriageResult:
        """Tier 3 Fallback: Return safe, non-crashing fallback with mandatory human escalation."""
        logger.warning(f"Invoking safe fallback for ticket {ticket.id or 'unknown'}. Reason: {reason}")
        return TriageResult(
            ticket_id=ticket.id,
            category=TicketCategory.OTHER,
            priority=TicketPriority.MEDIUM,
            summary=f"Auto-fallback: Requires manual agent triage ({ticket.subject[:40]})",
            suggested_reply="Thank you for reaching out. A support agent will review your inquiry shortly.",
            suggested_tags=["fallback", "manual-review"],
            confidence=0.0,
            escalate=True,
        )

    async def triage_ticket(self, ticket: Ticket) -> TriageResult:
        """Triage an incoming support ticket following the 3-tier resilience architecture with Instructor."""
        logger.info(f"Triaging ticket {ticket.id or 'anonymous'}: '{ticket.subject}'")

        # Tier 1: Deterministic Pre-Filtering
        has_security_signal = self._detect_security_signal(ticket)

        # Tier 2: In-Context Prompting via Instructor
        messages = build_triage_messages(ticket)
        try:
            # Instructor automatically executes model call, schema validation, and self-correction retries
            result: TriageResult = await self.llm_service.instructor_client.chat.completions.create(
                model=self.llm_service.model,
                messages=messages,
                response_model=TriageResult,
                max_retries=2,
                temperature=0.1,
            )
            result.ticket_id = ticket.id
        except (InstructorRetryException, Exception) as exc:
            # Tier 3: Safe Fallback when retries are exhausted or network errors occur
            return self._build_safe_fallback(ticket, reason=str(exc))

        # Business Invariant Enforcement for security pre-filtering
        if has_security_signal:
            result.category = TicketCategory.SECURITY
            result.priority = TicketPriority.URGENT
            result.escalate = True

        return result


_triage_service: Optional[TriageService] = None


def get_triage_service() -> TriageService:
    """Retrieve singleton Triage service instance."""
    global _triage_service
    if _triage_service is None:
        _triage_service = TriageService()
    return _triage_service
