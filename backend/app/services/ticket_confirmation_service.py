import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.database import SessionLocal
from app.models import PendingTicketConfirmation, User
from app.services.ticket_service import (
    TicketConversationNotFound,
    TicketUserNotFound,
    TicketValidationError,
    create_support_ticket_record,
)


CONFIRMATION_TTL_MINUTES = 10
VALID_PRIORITIES = {"low", "medium", "high"}


def create_pending_ticket_confirmation(
    *,
    user_id: int,
    conversation_session_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Save a ticket draft and issue a random confirmation code.

    The draft is tied to one authenticated customer and one conversation.
    This function does not create a support ticket.
    """

    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        raise TicketValidationError(
            "A valid authenticated customer ID is required."
        )

    if not isinstance(conversation_session_id, str):
        raise TicketValidationError(
            "A conversation session ID is required."
        )

    session_id = conversation_session_id.strip()

    if not session_id or len(session_id) > 100:
        raise TicketValidationError(
            "A valid conversation session ID is required."
        )

    if not isinstance(subject, str):
        raise TicketValidationError("Subject must be text.")

    if not isinstance(description, str):
        raise TicketValidationError("Description must be text.")

    clean_subject = subject.strip()
    clean_description = description.strip()

    if not 5 <= len(clean_subject) <= 200:
        raise TicketValidationError(
            "Subject must contain between 5 and 200 characters."
        )

    if not 10 <= len(clean_description) <= 5000:
        raise TicketValidationError(
            "Description must contain between 10 and 5000 characters."
        )

    if not isinstance(priority, str) or priority not in VALID_PRIORITIES:
        raise TicketValidationError(
            "Priority must be low, medium, or high."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=CONFIRMATION_TTL_MINUTES)

    # A cryptographically random, unguessable token.
    confirmation_code = secrets.token_urlsafe(24)

    db = SessionLocal()

    try:
        customer = db.get(User, user_id)

        if customer is None or not customer.is_active:
            raise TicketUserNotFound(
                "The customer account is unavailable."
            )

        pending = PendingTicketConfirmation(
            confirmation_code=confirmation_code,
            user_id=user_id,
            conversation_session_id=session_id,
            subject=clean_subject,
            description=clean_description,
            priority=priority,
            expires_at=expires_at,
            consumed_at=None,
            ticket_id=None,
        )

        db.add(pending)
        db.commit()

        return {
            "confirmation_code": confirmation_code,
            "expires_at": expires_at.isoformat(),
            "expires_in_minutes": CONFIRMATION_TTL_MINUTES,
            "subject": clean_subject,
            "description": clean_description,
            "priority": priority,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def consume_pending_ticket_confirmation(
    *,
    confirmation_code: str,
    user_id: int,
    conversation_session_id: str,
) -> dict[str, Any]:
    """
    Validate and consume a confirmation, creating at most one ticket.

    The confirmation must be unexpired, unused, and bound to the same
    authenticated customer and conversation. Ticket creation and marking
    the confirmation consumed happen in one database transaction.
    """

    if not isinstance(confirmation_code, str):
        raise TicketValidationError(
            "A valid confirmation code is required."
        )

    code = confirmation_code.strip()

    if not 20 <= len(code) <= 64:
        return {
            "created": False,
            "message": (
                "This confirmation is invalid, expired, already used, "
                "or not associated with this conversation. "
                "No ticket was created."
            ),
        }

    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        raise TicketValidationError(
            "A valid authenticated customer ID is required."
        )

    if (
        not isinstance(conversation_session_id, str)
        or not conversation_session_id.strip()
        or len(conversation_session_id.strip()) > 100
    ):
        raise TicketValidationError(
            "A valid conversation session ID is required."
        )

    session_id = conversation_session_id.strip()
    db = SessionLocal()

    try:
        # On PostgreSQL, FOR UPDATE serializes attempts to consume the
        # same confirmation concurrently.
        pending = db.scalar(
            select(PendingTicketConfirmation)
            .where(
                PendingTicketConfirmation.confirmation_code == code,
                PendingTicketConfirmation.user_id == user_id,
                PendingTicketConfirmation.conversation_session_id
                == session_id,
            )
            .with_for_update()
        )

        if pending is None:
            return {
                "created": False,
                "message": (
                    "This confirmation is invalid, expired, already used, "
                    "or not associated with this conversation. "
                    "No ticket was created."
                ),
            }

        now = datetime.now(timezone.utc)
        expires_at = pending.expires_at

        # Some databases return a naive datetime even for timezone-aware
        # columns. Interpret a naive value as UTC for this comparison.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if (
            pending.consumed_at is not None
            or pending.ticket_id is not None
            or expires_at <= now
        ):
            return {
                "created": False,
                "message": (
                    "This confirmation is invalid, expired, already used, "
                    "or not associated with this conversation. "
                    "No ticket was created."
                ),
            }

        # Reuse the shared validation and ownership checks. Because this
        # happens in the same transaction, the ticket and consumption
        # state can be committed atomically.
        ticket = create_support_ticket_record(
            db,
            user_id=user_id,
            subject=pending.subject,
            description=pending.description,
            priority=pending.priority,
            conversation_session_id=session_id,
        )

        pending.consumed_at = now
        pending.ticket_id = ticket.id

        db.commit()
        db.refresh(ticket)

        return {
            "created": True,
            "ticket_number": ticket.ticket_number,
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "priority": ticket.priority,
            "status": ticket.status,
            "conversation_id": ticket.conversation_id,
            "message": "Support ticket created successfully.",
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()