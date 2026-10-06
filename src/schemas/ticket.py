"""Ticket and triage Pydantic schemas."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TicketPriority(str, Enum):
    """Priority levels for support tickets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    """Categories for support tickets."""
    BILLING = "billing"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT = "account"
    SECURITY = "security"
    OTHER = "other"


class Ticket(BaseModel):
    """Schema representing an incoming support ticket."""
    id: Optional[str] = Field(default=None, description="Unique ticket identifier")
    subject: str = Field(..., description="Subject or title of the ticket")
    body: str = Field(..., description="Main content or email text of the ticket")
    sender: Optional[str] = Field(default=None, description="Sender email or customer id")


class TriageResult(BaseModel):
    """Schema for AI-powered ticket triage output."""
    ticket_id: Optional[str] = Field(default=None, description="ID of the triaged ticket")
    category: Optional[TicketCategory] = Field(default=None, description="Predicted ticket category")
    priority: Optional[TicketPriority] = Field(default=None, description="Assigned priority level")
    summary: Optional[str] = Field(default=None, description="One-line summary for rapid review")
    suggested_reply: Optional[str] = Field(default=None, description="Draft response for the agent")
    suggested_tags: List[str] = Field(default_factory=list, description="Categorical tags")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model prediction confidence score")
    escalate: bool = Field(default=False, description="Flag for immediate human intervention")
