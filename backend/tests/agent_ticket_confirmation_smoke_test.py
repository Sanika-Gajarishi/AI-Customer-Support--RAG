from uuid import uuid4

from sqlalchemy import delete, select

from app.database import SessionLocal, engine
from app.models import SupportTicket, User
from app.services.agent_service import answer_with_mcp_agent


EXPECTED_DATABASE = "shopease_migration_test_20261021"


def main() -> None:
    # Safety check: never run this test against the main database.
    if engine.url.database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"Expected test database {EXPECTED_DATABASE!r}; "
            f"got {engine.url.database!r}. Test cancelled."
        )

    print(f"Test database confirmed: {engine.url.database}")

    suffix = uuid4().hex[:10]
    email = f"mcp-ticket-{suffix}@example.invalid"

    user_id = None
    original_request = (
        "Please create a support ticket because my product arrived "
        "damaged. The screen is cracked and I need help with a replacement."
    )

    try:
        # Create a temporary, non-admin test user.
        with SessionLocal() as db:
            user = User(
                email=email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_id = user.id

        print("\nTest 1: Request a ticket without confirming")

        draft_result = answer_with_mcp_agent(
            original_request,
            user_id=user_id,
        )

        draft_answer = draft_result["answer"]
        print("\nDraft response:")
        print(draft_answer)

        assert "confirm ticket" in draft_answer.casefold(), (
            "The agent did not ask for explicit ticket confirmation."
        )

        with SessionLocal() as db:
            ticket_count = len(
                db.scalars(
                    select(SupportTicket).where(
                        SupportTicket.user_id == user_id
                    )
                ).all()
            )

        assert ticket_count == 0, (
            "SECURITY FAILURE: a ticket was created before confirmation."
        )

        print("PASS: No ticket was created before confirmation.")

        print("\nTest 2: Try confirmation without a pending draft")

        unrelated_confirmation = answer_with_mcp_agent(
            "CONFIRM TICKET",
            user_id=user_id,
        )

        print(unrelated_confirmation["answer"])

        assert "could not find a pending ticket draft" in (
            unrelated_confirmation["answer"].casefold()
        ), "Confirmation without a pending draft should be rejected."

        print("PASS: Confirmation without a pending draft was rejected.")

        print("\nTest 3: Confirm the displayed ticket draft")

        conversation_history = [
            {
                "role": "user",
                "content": original_request,
            },
            {
                "role": "assistant",
                "content": draft_answer,
            },
        ]

        confirmed_result = answer_with_mcp_agent(
            "CONFIRM TICKET",
            user_id=user_id,
            chat_history=conversation_history,
        )

        print("\nConfirmation response:")
        print(confirmed_result["answer"])

        assert "created" in confirmed_result["answer"].casefold(), (
            "The agent did not confirm successful ticket creation."
        )

        with SessionLocal() as db:
            tickets = db.scalars(
                select(SupportTicket).where(
                    SupportTicket.user_id == user_id
                )
            ).all()

            assert len(tickets) == 1, (
                f"Expected exactly one ticket; found {len(tickets)}."
            )

            ticket = tickets[0]

            assert ticket.subject == "Damaged or defective product"
            assert ticket.status == "open"
            assert ticket.priority == "medium"
            assert ticket.user_id == user_id

            ticket_number = ticket.ticket_number

        assert ticket_number in confirmed_result["answer"], (
            "The response should include the created ticket number."
        )

        print(f"PASS: Ticket {ticket_number} was created.")
        print("PASS: Ticket belongs to the authenticated test user.")
        print("\nSUCCESS: All ticket-confirmation checks passed.")

    finally:
        # Remove only this test user's tickets and account.
        if user_id is not None:
            with SessionLocal() as db:
                db.execute(
                    delete(SupportTicket).where(
                        SupportTicket.user_id == user_id
                    )
                )
                db.execute(
                    delete(User).where(User.id == user_id)
                )
                db.commit()

            print("Temporary test user and tickets cleaned up.")


if __name__ == "__main__":
    main()