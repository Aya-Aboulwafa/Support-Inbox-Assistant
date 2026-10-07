"""Triage service implementing resilient 3-tier classification and analysis."""

import json
import re
from typing import Any, Dict, Optional
from pydantic import ValidationError

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


def _strip_markdown_fences(content: str) -> str:
    """Strip markdown code block fences if returned by the LLM."""
    content = content.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        return match.group(1).strip()
    return content


class TriageService:
    """Resilient business logic service for triaging support inbox tickets."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def _detect_security_signal(self, ticket: Ticket) -> bool:
        """Tier 1 Pre-filter: Check for critical security triggers in subject or body."""
        combined = f"{ticket.subject} {ticket.body}".lower()
        return any(kw in combined for kw in SECURITY_KEYWORDS)

    async def _execute_self_correction(
        self,
        base_messages: list,
        failed_raw_output: str,
        error_message: str,
    ) -> Optional[Dict[str, Any]]:
        """Attempt a single self-correction retry with actionable error feedback."""
        logger.warning(f"Attempting self-correction retry due to validation error: {error_message}")
        retry_messages = list(base_messages)
        retry_messages.append({"role": "assistant", "content": failed_raw_output})
        retry_messages.append(
            {
                "role": "user",
                "content": (
                    f"The previous output failed validation with error: {error_message}. "
                    "Please fix all issues and return ONLY a valid JSON object matching the exact schema."
                ),
            }
        )

        try:
            retry_raw = await self.llm_service.generate_json(retry_messages, temperature=0.0)
            cleaned = _strip_markdown_fences(retry_raw)
            return json.loads(cleaned)
        except Exception as retry_err:
            logger.error(f"Self-correction retry failed: {retry_err}")
            return None

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
        """Triage an incoming support ticket following the 3-tier resilience architecture."""
        logger.info(f"Triaging ticket {ticket.id or 'anonymous'}: '{ticket.subject}'")

        # Tier 1: Deterministic Pre-Filtering
        has_security_signal = self._detect_security_signal(ticket)

        # Tier 2: In-Context Prompting
        messages = build_triage_messages(ticket)
        raw_output = ""
        try:
            raw_output = await self.llm_service.generate_json(messages, temperature=0.1)
            cleaned = _strip_markdown_fences(raw_output)
            data = json.loads(cleaned)
        except Exception as parse_err:
            # Tier 3: Self-Correction Retry
            data = await self._execute_self_correction(
                base_messages=messages,
                failed_raw_output=raw_output,
                error_message=str(parse_err),
            )
            if not data:
                return self._build_safe_fallback(ticket, reason=f"JSON parse error: {parse_err}")

        # Tier 3: Pydantic Validation & Normalization
        try:
            result = TriageResult.model_validate(data)
            result.ticket_id = ticket.id
        except ValidationError as val_err:
            # Self-correction attempt on schema validation error
            corrected_data = await self._execute_self_correction(
                base_messages=messages,
                failed_raw_output=raw_output,
                error_message=str(val_err),
            )
            if corrected_data:
                try:
                    result = TriageResult.model_validate(corrected_data)
                    result.ticket_id = ticket.id
                except ValidationError:
                    return self._build_safe_fallback(ticket, reason="Validation error after retry")
            else:
                return self._build_safe_fallback(ticket, reason=f"Validation error: {val_err}")

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
