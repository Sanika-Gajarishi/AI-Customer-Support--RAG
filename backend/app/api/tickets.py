
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SupportTicket, User
from app.security import get_current_admin, get_current_user
from app.services.ticket_service import (
    TicketConversationNotFound,
    TicketUserNotFound,
    TicketValidationError,
    create_support_ticket_record,
)


logger = logging.getLogger(__name__)

router = APIRouter()

Priority = Literal["low", "medium", "high"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: Priority = "medium"
    conversation_session_id: str | None = None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: Priority | None = None
    assigned_to_user_id: int | None = None


def ticket_to_dict(ticket: SupportTicket) -> dict:
    """Convert a support ticket to a response-friendly dictionary."""

    return {
        "ticket_number": ticket.ticket_number,
        "user_id": ticket.user_id,
        "conversation_id": ticket.conversation_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_to_user_id": ticket.assigned_to_user_id,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
    }


def find_ticket(
    db: Session,
    ticket_number: str,
) -> SupportTicket | None:
    """Find a ticket by its ticket number."""

    return db.scalar(
        select(SupportTicket).where(
            SupportTicket.ticket_number == ticket_number
        )
    )


@router.post("", status_code=201)
def create_ticket(
    request: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a ticket for the currently authenticated customer."""

    try:
        # The shared service validates the data and verifies ownership.
        # The customer ID comes from FastAPI authentication, not the client.
        ticket = create_support_ticket_record(
            db,
            user_id=current_user.id,
            subject=request.subject,
            description=request.description,
            priority=request.priority,
            conversation_session_id=request.conversation_session_id,
        )

        db.commit()
        db.refresh(ticket)

        return ticket_to_dict(ticket)

    except TicketValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except TicketConversationNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from exc

    except TicketUserNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail="Customer account is unavailable.",
        ) from exc

    except Exception:
        db.rollback()
        logger.exception("Support ticket creation failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to create support ticket.",
        )


@router.get("")
def list_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return tickets belonging only to the authenticated customer."""

    tickets = db.scalars(
        select(SupportTicket)
        .where(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
    ).all()

    return {
        "count": len(tickets),
        "tickets": [ticket_to_dict(ticket) for ticket in tickets],
    }


@router.get("/{ticket_number}")
def get_my_ticket(
    ticket_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a ticket only if it belongs to the current customer."""

    ticket = db.scalar(
        select(SupportTicket).where(
            SupportTicket.ticket_number == ticket_number,
            SupportTicket.user_id == current_user.id,
        )
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    return ticket_to_dict(ticket)


@router.get("/admin/all")
def list_all_tickets(
    status: TicketStatus | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Allow administrators to list tickets with optional filters."""

    statement = select(SupportTicket)

    if status is not None:
        statement = statement.where(
            SupportTicket.status == status
        )

    if priority is not None:
        statement = statement.where(
            SupportTicket.priority == priority
        )

    tickets = db.scalars(
        statement
        .order_by(SupportTicket.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return {
        "count": len(tickets),
        "tickets": [ticket_to_dict(ticket) for ticket in tickets],
    }


@router.patch("/admin/{ticket_number}")
def update_ticket(
    ticket_number: str,
    request: TicketUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Allow administrators to update a ticket."""

    ticket = find_ticket(db, ticket_number)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    changes = request.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update.",
        )

    if any(
        field in changes and changes[field] is None
        for field in ("status", "priority")
    ):
        raise HTTPException(
            status_code=422,
            detail="Status and priority cannot be null.",
        )

    if "assigned_to_user_id" in changes:
        assignee_id = changes["assigned_to_user_id"]

        if assignee_id is not None:
            assignee = db.get(User, assignee_id)

            if assignee is None or not assignee.is_admin:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Assignee must be an existing administrator."
                    ),
                )

    for field, value in changes.items():
        setattr(ticket, field, value)

    ticket.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(ticket)

        return ticket_to_dict(ticket)

    except Exception:
        db.rollback()
        logger.exception("Support ticket update failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to update support ticket.",
        )
