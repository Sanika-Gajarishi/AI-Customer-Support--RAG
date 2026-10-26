from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from app.database import SessionLocal, engine
from app.models import (
    Conversation,
    PendingTicketConfirmation,
    SupportTicket,
    User,
)
from app.services.ticket_confirmation_service import (
    consume_pending_ticket_confirmation,
    create_pending_ticket_confirmation,
)


EXPECTED_DATABASE = "shopease_migration_test_20261021"


def main() -> None:
    if engine.url.database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"Safety check failed: expected {EXPECTED_DATABASE!r}, "
            f"got {engine.url.database!r}. Test cancelled."
        )

    print(f"Test database confirmed: {engine.url.database}")

    suffix = uuid4().hex[:10]
    owner_email = f"confirmation-owner-{suffix}@example.invalid"
    other_email = f"confirmation-other-{suffix}@example.invalid"
    conversation_session_id = f"confirmation-session-{suffix}"

    confirmation_codes = []
    created_ticket_numbers = []
    user_ids = []

    try:
        # Set up two test customers and one conversation belonging
        # to the owner.
        with SessionLocal() as db:
            owner = User(
                email=owner_email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )
            other_customer = User(
                email=other_email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )

            db.add_all([owner, other_customer])
            db.flush()

            owner_id = owner.id
            other_id = other_customer.id
            user_ids.extend([owner_id, other_id])

            conversation = Conversation(
                session_id=conversation_session_id,
                user_id=owner_id,
            )
            db.add(conversation)
            db.commit()

        # Create a confirmation. This must not create a ticket yet.
        draft = create_pending_ticket_confirmation(
            user_id=owner_id,
            conversation_session_id=conversation_session_id,
            subject="Damaged or defective product",
            description=(
                "The product arrived with a cracked screen "
                "and needs replacement assistance."
            ),
            priority="medium",
        )

        code = draft["confirmation_code"]
        confirmation_codes.append(code)

        print("\nTest 1: Creating a pending confirmation")
        assert draft["expires_in_minutes"] == 10

        with SessionLocal() as db:
            pending = db.scalar(
                select(PendingTicketConfirmation).where(
                    PendingTicketConfirmation.confirmation_code == code
                )
            )
            assert pending is not None
            assert pending.consumed_at is None
            assert pending.ticket_id is None

            tickets_before = db.scalars(
                select(SupportTicket).where(
                    SupportTicket.user_id == owner_id
                )
            ).all()

            assert len(tickets_before) == 0

        print("PASS: Draft saved; no ticket created.")

        print("\nTest 2: Another customer tries to use the code")
        result = consume_pending_ticket_confirmation(
            confirmation_code=code,
            user_id=other_id,
            conversation_session_id=conversation_session_id,
        )

        assert result["created"] is False
        print("PASS: Confirmation rejected for the wrong customer.")

        print("\nTest 3: Wrong conversation tries to use the code")
        result = consume_pending_ticket_confirmation(
            confirmation_code=code,
            user_id=owner_id,
            conversation_session_id=f"wrong-session-{suffix}",
        )

        assert result["created"] is False
        print("PASS: Confirmation rejected for the wrong conversation.")

        print("\nTest 4: Owner confirms the valid code")
        result = consume_pending_ticket_confirmation(
            confirmation_code=code,
            user_id=owner_id,
            conversation_session_id=conversation_session_id,
        )

        assert result["created"] is True, result
        assert result["subject"] == "Damaged or defective product"
        assert result["status"] == "open"
        assert result["conversation_id"] is not None

        ticket_number = result["ticket_number"]
        created_ticket_numbers.append(ticket_number)

        print(f"PASS: Ticket {ticket_number} created.")
        print("Linked conversation ID:", result["conversation_id"])

        print("\nTest 5: Reusing the same confirmation")
        replay = consume_pending_ticket_confirmation(
            confirmation_code=code,
            user_id=owner_id,
            conversation_session_id=conversation_session_id,
        )

        assert replay["created"] is False

        with SessionLocal() as db:
            tickets = db.scalars(
                select(SupportTicket).where(
                    SupportTicket.ticket_number == ticket_number
                )
            ).all()
            assert len(tickets) == 1

        print("PASS: Replay rejected; no duplicate ticket created.")

        print("\nTest 6: Expired confirmation")
        expired_draft = create_pending_ticket_confirmation(
            user_id=owner_id,
            conversation_session_id=conversation_session_id,
            subject="Expired confirmation test",
            description=(
                "This is a test of an expired confirmation code."
            ),
            priority="low",
        )

        expired_code = expired_draft["confirmation_code"]
        confirmation_codes.append(expired_code)

        with SessionLocal() as db:
            pending = db.scalar(
                select(PendingTicketConfirmation).where(
                    PendingTicketConfirmation.confirmation_code
                    == expired_code
                )
            )
            assert pending is not None
            pending.expires_at = datetime.now(timezone.utc) - timedelta(
                minutes=1
            )
            db.commit()

        expired_result = consume_pending_ticket_confirmation(
            confirmation_code=expired_code,
            user_id=owner_id,
            conversation_session_id=conversation_session_id,
        )

        assert expired_result["created"] is False

        with SessionLocal() as db:
            expired_ticket = db.scalar(
                select(SupportTicket).where(
                    SupportTicket.user_id == owner_id,
                    SupportTicket.subject == "Expired confirmation test",
                )
            )
            assert expired_ticket is None

        print("PASS: Expired confirmation rejected.")

        print("\nSUCCESS: All confirmation-service checks passed.")

    finally:
        # Remove only records belonging to this test run.
        with SessionLocal() as db:
            if confirmation_codes:
                db.execute(
                    delete(PendingTicketConfirmation).where(
                        PendingTicketConfirmation.confirmation_code.in_(
                            confirmation_codes
                        )
                    )
                )

            if created_ticket_numbers:
                db.execute(
                    delete(SupportTicket).where(
                        SupportTicket.ticket_number.in_(
                            created_ticket_numbers
                        )
                    )
                )

            db.execute(
                delete(Conversation).where(
                    Conversation.session_id == conversation_session_id
                )
            )

            if user_ids:
                db.execute(
                    delete(User).where(User.id.in_(user_ids))
                )

            db.commit()

        print("Temporary confirmation, ticket, and test-user records cleaned up.")


if __name__ == "__main__":
    main()