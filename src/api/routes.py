"""API route definitions for support ticket triage and human-in-the-loop review queue."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.schemas.ticket import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketRecord,
    TicketStatus,
    TicketUpdate,
    TriageResult,
)
from src.services.store import TicketStore, get_ticket_store
from src.services.triage import TriageService, get_triage_service

router = APIRouter(prefix="/api/v1", tags=["triage", "review-queue"])


class HealthResponse(BaseModel):
    status: str
    version: str


class ApproveRequest(BaseModel):
    final_reply: Optional[str] = None


class EscalateRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


# -------------------------------------------------------------------------
# Stateless Direct Triage Endpoint
# -------------------------------------------------------------------------
@router.post("/triage", response_model=TriageResult, status_code=status.HTTP_200_OK, tags=["triage"])
async def triage_ticket_endpoint(
    ticket: Ticket,
    service: TriageService = Depends(get_triage_service),
) -> TriageResult:
    """Stateless AI Triage: Analyze any incoming ticket and return structured classification & reply."""
    try:
        return await service.triage_ticket(ticket)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage error: {str(exc)}",
        ) from exc


# -------------------------------------------------------------------------
# Review Queue Management Endpoints
# -------------------------------------------------------------------------
@router.get("/tickets", response_model=List[TicketRecord], tags=["review-queue"])
async def list_tickets(
    status: Optional[TicketStatus] = Query(None, description="Filter by review status"),
    category: Optional[TicketCategory] = Query(None, description="Filter by AI category"),
    priority: Optional[TicketPriority] = Query(None, description="Filter by AI priority"),
    escalate: Optional[bool] = Query(None, description="Filter by escalation flag"),
    limit: int = Query(50, ge=1, le=100, description="Max tickets to retrieve"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    store: TicketStore = Depends(get_ticket_store),
) -> List[TicketRecord]:
    """Retrieve ticket review queue with status/priority filtering and pagination."""
    return store.list_tickets(
        status=status,
        category=category,
        priority=priority,
        escalate=escalate,
        limit=limit,
        offset=offset,
    )


@router.get("/tickets/stats", response_model=Dict[str, Any], tags=["review-queue"])
async def get_queue_statistics(
    store: TicketStore = Depends(get_ticket_store),
) -> Dict[str, Any]:
    """Retrieve ticket count breakdowns and urgency metrics for UI badges."""
    return store.get_stats()


@router.post("/tickets", response_model=TicketRecord, status_code=status.HTTP_201_CREATED, tags=["review-queue"])
async def create_ticket(
    ticket: Ticket,
    store: TicketStore = Depends(get_ticket_store),
) -> TicketRecord:
    """Ingest a new incoming ticket into the review queue."""
    return store.add_ticket(ticket)


@router.get("/tickets/{ticket_id}", response_model=TicketRecord, tags=["review-queue"])
async def get_ticket_details(
    ticket_id: str,
    store: TicketStore = Depends(get_ticket_store),
) -> TicketRecord:
    """Retrieve details and AI triage output for a specific ticket."""
    record = store.get_ticket(ticket_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return record


@router.post("/tickets/{ticket_id}/triage", response_model=TicketRecord, tags=["review-queue"])
async def trigger_ticket_triage(
    ticket_id: str,
    store: TicketStore = Depends(get_ticket_store),
    service: TriageService = Depends(get_triage_service),
) -> TicketRecord:
    """Run AI Triage on an existing ticket and save the structured result to its record."""
    record = store.get_ticket(ticket_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )

    triage_result = await service.triage_ticket(record.ticket)
    updated_record = store.set_triage_result(ticket_id, triage_result)
    return updated_record or record


@router.patch("/tickets/{ticket_id}", response_model=TicketRecord, tags=["review-queue"])
async def update_ticket_record(
    ticket_id: str,
    update: TicketUpdate,
    store: TicketStore = Depends(get_ticket_store),
) -> TicketRecord:
    """Agent Action: Edit suggested reply, reclassify category/priority, or update status."""
    updated = store.update_ticket(ticket_id, update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return updated


@router.post("/tickets/{ticket_id}/approve", response_model=TicketRecord, tags=["review-queue"])
async def approve_and_send_ticket(
    ticket_id: str,
    body: Optional[ApproveRequest] = None,
    store: TicketStore = Depends(get_ticket_store),
) -> TicketRecord:
    """1-Click Action: Approve the draft response and mark the ticket as approved."""
    final_reply = body.final_reply if body else None
    approved = store.approve_ticket(ticket_id, final_reply=final_reply)
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return approved


@router.post("/tickets/{ticket_id}/escalate", response_model=TicketRecord, tags=["review-queue"])
async def escalate_ticket_to_tier2(
    ticket_id: str,
    body: Optional[EscalateRequest] = None,
    store: TicketStore = Depends(get_ticket_store),
) -> TicketRecord:
    """1-Click Action: Escalate ticket to human Tier-2 support team."""
    reason = body.reason if body else None
    escalated = store.escalate_ticket(ticket_id, reason=reason)
    if not escalated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return escalated
