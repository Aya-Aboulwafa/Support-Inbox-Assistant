"""API route definitions (placeholder)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.schemas.ticket import Ticket, TriageResult
from src.services.triage import TriageService, get_triage_service

router = APIRouter(prefix="/api/v1", tags=["triage"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(status="healthy", version="0.1.0")


@router.post("/triage", response_model=TriageResult, status_code=status.HTTP_200_OK)
async def triage_ticket_endpoint(
    ticket: Ticket,
    service: TriageService = Depends(get_triage_service),
) -> TriageResult:
    """Triage incoming support ticket (placeholder)."""
    try:
        return await service.triage_ticket(ticket)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage error: {str(exc)}",
        ) from exc
