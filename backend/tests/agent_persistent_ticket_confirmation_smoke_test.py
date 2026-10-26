import re
from uuid import uuid4

from sqlalchemy import delete, select

from app.database import SessionLocal, engine
from app.models import (
    Conversation,
    PendingTicketConfirmation,
    SupportTicket,
    User,
)
from app.services.agent_service import answer_with_mcp_agent


EXPECTED_DATABASE = "shopease_migration_test_20261021"


def main() -> None:
    if engine.url.database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"Expected test database {EXPECTED_DATABASE!r}, "
            f"got {engine.url.database!r}. Test cancelled."
        )

    print(f"Test database confirmed: {engine.url.database}")

    suffix = uuid4().hex[:10]
    email = f"persistent-confirm-{suffix}@example.invalid"
    conversation_session_id = f"persistent-confirm-{suffix}"

    user_id = None
    confirmation_code = None

    request = (
        "Please create a support ticket because my product arrived "
        "damaged. The screen is cracked and I need replacement assistance."
    )

    try:
        # Create a temporary customer and their conversation.
        with SessionLocal() as db:
            user = User(
                email=email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )
            db.add(user)
            db.flush()

            user_id = user.id

            conversation = Conversation(
                session_id=conversation_session_id,
                user_id=user_id,
            )
            db.add(conversation)
            db.commit()

        print("\nTest 1: Request a ticket without confirming")

        draft_result = answer_with_mcp_agent(
            request,
            user_id=user_id,
            conversation_session_id=conversation_session_id,
        )

        draft_answer = draft_result["answer"]
        print(draft_answer)

        assert "no ticket has been created yet" in (
            draft_answer.casefold()
        ), "The draft must clearly state that no ticket was created."

        match = re.search(
            r"CONFIRM TICKET\s+([A-Za-z0-9_-]{20,64})",
            draft_answer,
        )

        assert match, "The draft did not provide a confirmation code."
        confirmation_code = match.group(1)

        # Verify that the draft is stored persistently and no ticket exists.
        with SessionLocal() as db:
            pending = db.scalar(
                select(PendingTicketConfirmation).where(
                    PendingTicketConfirmation.confirmation_code
                    == confirmation_code
                )
            )

            assert pending is not None
            assert pending.user_id == user_id
            assert (
                pending.conversation_session_id
                == conversation_session_id
            )
            assert pending.consumed_at is None
            assert pending.ticket_id is None

            tickets_before = db.scalars(
                select(SupportTicket).where(
                    SupportTicket.user_id == user_id
                )
            ).all()

            assert len(tickets_before) == 0

        print("PASS: Confirmation stored; no ticket created.")

        print("\nTest 2: Confirm the exact stored code")

        confirmation_result = answer_with_mcp_agent(
            f"CONFIRM TICKET {confirmation_code}",
            user_id=user_id,
            conversation_session_id=conversation_session_id,
        )

        print(confirmation_result["answer"])

        assert "created" in (
            confirmation_result["answer"].casefold()
        ), "The confirmation response did not report ticket creation."

        with SessionLocal() as db:
            pending = db.scalar(
                select(PendingTicketConfirmation).where(
                    PendingTicketConfirmation.confirmation_code
                    == confirmation_code
                )
            )

            assert pending is not None
            assert pending.consumed_at is not None
            assert pending.ticket_id is not None

            ticket = db.get(SupportTicket, pending.ticket_id)

            assert ticket is not None
            assert ticket.user_id == user_id
            assert ticket.conversation_id is not None
            assert ticket.subject == "Damaged or defective product"
            assert ticket.status == "open"

            ticket_number = ticket.ticket_number
            ticket_id = ticket.id
            internal_conversation_id = ticket.conversation_id

        assert ticket_number in confirmation_result["answer"]

        print(f"PASS: Ticket {ticket_number} created exactly once.")
        print(
            "PASS: Ticket linked to database conversation "
            f"{internal_conversation_id}."
        )

        print("\nTest 3: Replay the same confirmation code")

        replay_result = answer_with_mcp_agent(
            f"CONFIRM TICKET {confirmation_code}",
            user_id=user_id,
            conversation_session_id=conversation_session_id,
        )

        print(replay_result["answer"])

        with SessionLocal() as db:
            remaining_tickets = db.scalars(
                select(SupportTicket).where(
                    SupportTicket.user_id == user_id
                )
            ).all()

            assert len(remaining_tickets) == 1
            assert remaining_tickets[0].id == ticket_id

            pending = db.scalar(
                select(PendingTicketConfirmation).where(
                    PendingTicketConfirmation.confirmation_code
                    == confirmation_code
                )
            )

            assert pending is not None
            assert pending.ticket_id == ticket_id
            assert pending.consumed_at is not None

        assert ticket_number not in replay_result["answer"], (
            "Replay response must not claim that a new ticket was created."
        )

        print("PASS: Replay did not create a duplicate ticket.")
        print("\nSUCCESS: Persistent confirmation flow passed.")

    finally:
        # Delete only records belonging to this temporary test customer.
        if user_id is not None:
            with SessionLocal() as db:
                db.execute(
                    delete(PendingTicketConfirmation).where(
                        PendingTicketConfirmation.user_id == user_id
                    )
                )

                db.execute(
                    delete(SupportTicket).where(
                        SupportTicket.user_id == user_id
                    )
                )

                db.execute(
                    delete(Conversation).where(
                        Conversation.session_id
                        == conversation_session_id
                    )
                )

                db.execute(
                    delete(User).where(User.id == user_id)
                )

                db.commit()

            print("Temporary test records cleaned up.")


if __name__ == "__main__":
    main()