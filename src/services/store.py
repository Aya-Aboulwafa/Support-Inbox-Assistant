"""In-memory ticket repository and review queue store."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logging import logger
from src.schemas.ticket import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketRecord,
    TicketStatus,
    TicketUpdate,
    TriageResult,
)


DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "tickets.json"


class TicketStore:
    """Thread-safe and fast in-memory store for support tickets and review queue lifecycle."""

    def __init__(self, data_file: Optional[Path] = None):
        self._records: Dict[str, TicketRecord] = {}
        self.data_file = Path(data_file) if data_file else DEFAULT_DATA_FILE
        self._initialize_from_dataset()

    def _initialize_from_dataset(self) -> None:
        """Load initial tickets from data/tickets.json if present."""
        if not self.data_file.exists():
            logger.warning(f"Data file '{self.data_file}' not found. Starting with empty store.")
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw_tickets = json.load(f)

            for idx, item in enumerate(raw_tickets):
                ticket = Ticket.model_validate(item)
                if not ticket.id:
                    ticket.id = f"T-{idx+1:03d}"
                self._records[ticket.id] = TicketRecord(
                    ticket=ticket,
                    status=TicketStatus.PENDING,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
            logger.info(f"TicketStore initialized with {len(self._records)} tickets from {self.data_file}")
        except Exception as exc:
            logger.error(f"Failed to load dataset from {self.data_file}: {exc}")

    def list_tickets(
        self,
        status: Optional[TicketStatus] = None,
        category: Optional[TicketCategory] = None,
        priority: Optional[TicketPriority] = None,
        escalate: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TicketRecord]:
        """List tickets with optional filtering and pagination."""
        items = list(self._records.values())

        if status:
            items = [t for t in items if t.status == status]
        if category:
            items = [t for t in items if t.triage and t.triage.category == category]
        if priority:
            items = [t for t in items if t.triage and t.triage.priority == priority]
        if escalate is not None:
            items = [t for t in items if t.triage and t.triage.escalate == escalate]

        # Return paginated slice
        return items[offset : offset + limit]

    def get_ticket(self, ticket_id: str) -> Optional[TicketRecord]:
        """Retrieve a specific ticket record by ID."""
        return self._records.get(ticket_id)

    def add_ticket(self, ticket: Ticket) -> TicketRecord:
        """Add a newly received ticket to the queue."""
        if not ticket.id:
            ticket.id = f"T-{len(self._records) + 1:03d}"
        record = TicketRecord(
            ticket=ticket,
            status=TicketStatus.PENDING,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._records[ticket.id] = record
        return record

    def update_ticket(self, ticket_id: str, update: TicketUpdate) -> Optional[TicketRecord]:
        """Apply agent modifications, reclassifications, or replies to a ticket."""
        record = self._records.get(ticket_id)
        if not record:
            return None

        now = datetime.now(timezone.utc).isoformat()
        if update.status:
            record.status = update.status
        if update.edited_reply is not None:
            record.edited_reply = update.edited_reply
        if update.notes is not None:
            record.notes = update.notes

        # Allow reclassifying category/priority/escalate on the associated triage result
        if record.triage:
            if update.category:
                record.triage.category = update.category
            if update.priority:
                record.triage.priority = update.priority
            if update.suggested_reply:
                record.triage.suggested_reply = update.suggested_reply
            if update.escalate is not None:
                record.triage.escalate = update.escalate

        record.updated_at = now
        return record

    def set_triage_result(self, ticket_id: str, triage: TriageResult) -> Optional[TicketRecord]:
        """Attach an AI triage result to a ticket."""
        record = self._records.get(ticket_id)
        if not record:
            return None

        record.triage = triage
        if record.status == TicketStatus.PENDING:
            record.status = TicketStatus.TRIAGED
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    def approve_ticket(self, ticket_id: str, final_reply: Optional[str] = None) -> Optional[TicketRecord]:
        """1-Click action: approve draft response and transition to APPROVED status."""
        record = self._records.get(ticket_id)
        if not record:
            return None

        if final_reply:
            record.edited_reply = final_reply
        elif record.triage and record.triage.suggested_reply and not record.edited_reply:
            record.edited_reply = record.triage.suggested_reply

        record.status = TicketStatus.APPROVED
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    def escalate_ticket(self, ticket_id: str, reason: Optional[str] = None) -> Optional[TicketRecord]:
        """1-Click action: escalate ticket to Tier-2 human support."""
        record = self._records.get(ticket_id)
        if not record:
            return None

        record.status = TicketStatus.ESCALATED
        if record.triage:
            record.triage.escalate = True
        if reason:
            record.notes = f"{record.notes or ''}\nEscalation note: {reason}".strip()

        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    def get_stats(self) -> Dict[str, Any]:
        """Get summary metrics of queue statuses and urgency for frontend badges."""
        items = list(self._records.values())
        return {
            "total_tickets": len(items),
            "by_status": {
                status.value: sum(1 for t in items if t.status == status)
                for status in TicketStatus
            },
            "escalated_count": sum(1 for t in items if t.triage and t.triage.escalate),
            "urgent_count": sum(
                1 for t in items if t.triage and t.triage.priority == TicketPriority.URGENT
            ),
        }


_ticket_store: Optional[TicketStore] = None


def get_ticket_store() -> TicketStore:
    """Retrieve singleton TicketStore instance."""
    global _ticket_store
    if _ticket_store is None:
        _ticket_store = TicketStore()
    return _ticket_store
