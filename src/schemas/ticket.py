"""Ticket and triage Pydantic schemas with resilient validation best practices."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(default=None, description="Unique ticket identifier")
    subject: str = Field(..., description="Subject or title of the ticket")
    body: str = Field(..., description="Main content or email text of the ticket")
    sender: Optional[str] = Field(default=None, alias="from", description="Sender email or customer id")
    received_at: Optional[str] = Field(default=None, description="Timestamp when ticket was received")
    channel: Optional[str] = Field(default=None, description="Channel of origin, e.g. email or webform")


class TriageResult(BaseModel):
    """Schema for AI-powered ticket triage output with hardened validation."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    ticket_id: Optional[str] = Field(default=None, description="ID of the triaged ticket")
    category: Optional[TicketCategory] = Field(default=TicketCategory.OTHER, description="Predicted ticket category")
    priority: Optional[TicketPriority] = Field(default=TicketPriority.MEDIUM, description="Assigned priority level")
    summary: Optional[str] = Field(default=None, description="One-line summary for rapid review")
    suggested_reply: Optional[str] = Field(default=None, description="Draft response for the agent")
    suggested_tags: List[str] = Field(default_factory=list, description="Categorical tags")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model prediction confidence score")
    escalate: bool = Field(default=False, description="Flag for immediate human intervention")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Optional[str]) -> Optional[str]:
        """Normalize category string to lowercase and stripped before enum validation."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Optional[str]) -> Optional[str]:
        """Normalize priority string to lowercase and stripped before enum validation."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def enforce_escalation_rules(self) -> "TriageResult":
        """Enforce business rules for auto-escalating sensitive or low-confidence tickets."""
        if (
            self.category == TicketCategory.SECURITY
            or self.priority == TicketPriority.URGENT
            or (self.confidence is not None and self.confidence < 0.7)
        ):
            self.escalate = True
        return self
