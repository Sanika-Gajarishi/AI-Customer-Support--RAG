import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation, SupportTicket, User


logger = logging.getLogger(__name__)

VALID_PRIORITIES = {"low", "medium", "high"}


class TicketValidationError(ValueError):
    """Raised when ticket input is invalid."""


class TicketConversationNotFound(LookupError):
    """Raised when the conversation is not accessible to the customer."""


class TicketUserNotFound(LookupError):
    """Raised when the customer account is unavailable."""


def create_support_ticket_record(
    db: Session,
    *,
    user_id: int,
    subject: str,
    description: str,
    priority: str = "medium",
    conversation_session_id: str | None = None,
) -> SupportTicket:
    """
    Create a support ticket for a verified customer.

    The caller supplies the authenticated user's ID.
    This function does not commit; the caller owns the transaction.
    """

    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        raise TicketValidationError("A valid customer ID is required.")

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

    customer = db.get(User, user_id)

    if customer is None or not customer.is_active:
        raise TicketUserNotFound("The customer account is unavailable.")

    conversation_id = None

    if conversation_session_id is not None:
        if not isinstance(conversation_session_id, str):
            raise TicketValidationError(
                "Conversation session ID must be text."
            )

        clean_session_id = conversation_session_id.strip()

        if clean_session_id:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.session_id == clean_session_id,
                    Conversation.user_id == user_id,
                )
            )

            if conversation is None:
                # Do not disclose whether another customer owns it.
                raise TicketConversationNotFound(
                    "Conversation not found."
                )

            conversation_id = conversation.id

    ticket = SupportTicket(
        ticket_number=f"TKT-{uuid4().hex[:10].upper()}",
        user_id=user_id,
        conversation_id=conversation_id,
        subject=clean_subject,
        description=clean_description,
        priority=priority,
        status="open",
    )

    db.add(ticket)
    db.flush()

    logger.info(
        "Created support ticket %s for customer ID %s",
        ticket.ticket_number,
        user_id,
    )

    return ticket